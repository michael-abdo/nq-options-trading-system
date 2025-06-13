#!/usr/bin/env python3
"""
Scheduled Baseline Update System

This module provides automated daily baseline calculations for the IFD v3.0 system:
- Scheduled job execution for baseline updates
- Incremental data fetching to minimize API calls
- Error handling and retry logic
- Job status monitoring and reporting
"""

import os
import json
import logging
import threading
import time
import schedule
from datetime import datetime, timedelta, timezone, time as datetime_time
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import sqlite3

# Import baseline engine
from baseline_calculation_engine import (
    BaselineCalculationEngine,
    HistoricalDataPoint,
    create_baseline_engine
)

# Import data providers
from databento_api.solution import DatabentoMBOIngestion

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Job execution status"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class JobExecutionRecord:
    """Record of a job execution"""
    job_id: str
    job_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: JobStatus = JobStatus.PENDING

    # Execution details
    strikes_processed: int = 0
    data_points_added: int = 0
    errors_encountered: int = 0

    # Performance metrics
    api_calls_made: int = 0
    execution_time_seconds: float = 0.0

    # Error details
    error_message: Optional[str] = None
    retry_count: int = 0

    # Results
    baselines_updated: int = 0
    anomalies_detected: int = 0


class JobDatabase:
    """Database for job execution history"""

    def __init__(self, db_path: str = "outputs/job_history.db"):
        """Initialize job database"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()

    def _init_database(self):
        """Initialize database schema"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS job_executions (
                    job_id TEXT PRIMARY KEY,
                    job_type TEXT NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT NOT NULL,
                    strikes_processed INTEGER DEFAULT 0,
                    data_points_added INTEGER DEFAULT 0,
                    errors_encountered INTEGER DEFAULT 0,
                    api_calls_made INTEGER DEFAULT 0,
                    execution_time_seconds REAL DEFAULT 0.0,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    baselines_updated INTEGER DEFAULT 0,
                    anomalies_detected INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_start_time
                ON job_executions(start_time DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_job_status
                ON job_executions(status)
            """)

            conn.commit()

    def record_execution(self, record: JobExecutionRecord):
        """Record job execution"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO job_executions
                (job_id, job_type, start_time, end_time, status,
                 strikes_processed, data_points_added, errors_encountered,
                 api_calls_made, execution_time_seconds, error_message,
                 retry_count, baselines_updated, anomalies_detected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.job_id,
                record.job_type,
                record.start_time.isoformat(),
                record.end_time.isoformat() if record.end_time else None,
                record.status.value,
                record.strikes_processed,
                record.data_points_added,
                record.errors_encountered,
                record.api_calls_made,
                record.execution_time_seconds,
                record.error_message,
                record.retry_count,
                record.baselines_updated,
                record.anomalies_detected
            ))

            conn.commit()

    def get_last_successful_run(self, job_type: str) -> Optional[JobExecutionRecord]:
        """Get last successful job execution"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM job_executions
                WHERE job_type = ? AND status = ?
                ORDER BY start_time DESC
                LIMIT 1
            """, (job_type, JobStatus.COMPLETED.value))

            row = cursor.fetchone()
            if row:
                # Convert to JobExecutionRecord
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))

                # Convert timestamps
                data['start_time'] = datetime.fromisoformat(data['start_time'])
                if data['end_time']:
                    data['end_time'] = datetime.fromisoformat(data['end_time'])

                # Convert status
                data['status'] = JobStatus(data['status'])

                # Remove non-field columns
                data.pop('created_at', None)

                return JobExecutionRecord(**data)

        return None


class BaselineUpdateJob:
    """Daily baseline update job"""

    def __init__(self, baseline_engine: BaselineCalculationEngine,
                 data_provider: DatabentoMBOIngestion,
                 active_strikes: List[float]):
        """
        Initialize baseline update job

        Args:
            baseline_engine: Baseline calculation engine
            data_provider: Data provider for fetching historical data
            active_strikes: List of active strike prices to monitor
        """
        self.baseline_engine = baseline_engine
        self.data_provider = data_provider
        self.active_strikes = active_strikes
        self.job_database = JobDatabase()

        # Job configuration
        self.max_retries = 3
        self.retry_delay = 300  # 5 minutes

        logger.info(f"Baseline update job initialized for {len(active_strikes)} strikes")

    def execute(self) -> JobExecutionRecord:
        """Execute baseline update job"""
        job_id = f"baseline_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}"
        record = JobExecutionRecord(
            job_id=job_id,
            job_type="baseline_update",
            start_time=datetime.now(timezone.utc)
        )

        logger.info(f"Starting baseline update job: {job_id}")

        try:
            record.status = JobStatus.RUNNING
            self.job_database.record_execution(record)

            # Get last successful run to determine incremental update window
            last_run = self.job_database.get_last_successful_run("baseline_update")
            if last_run:
                # Fetch data since last run
                start_date = last_run.end_time or last_run.start_time
                logger.info(f"Performing incremental update since {start_date}")
            else:
                # Full 20-day historical fetch
                start_date = datetime.now(timezone.utc) - timedelta(days=20)
                logger.info("Performing full 20-day baseline initialization")

            # Process each strike
            historical_data = []

            for strike in self.active_strikes:
                try:
                    # Fetch historical data for this strike
                    strike_data = self._fetch_historical_data(
                        strike, start_date, record
                    )

                    if strike_data:
                        historical_data.extend(strike_data)
                        record.strikes_processed += 1
                        record.data_points_added += len(strike_data)

                except Exception as e:
                    logger.error(f"Error processing strike {strike}: {e}")
                    record.errors_encountered += 1

            # Update baselines with all collected data
            if historical_data:
                logger.info(f"Updating baselines with {len(historical_data)} data points")
                self.baseline_engine.update_baselines_incremental(historical_data)
                record.baselines_updated = len(set(
                    (d.strike_price, d.contract_type) for d in historical_data
                ))

            # Mark job as completed
            record.status = JobStatus.COMPLETED
            record.end_time = datetime.now(timezone.utc)
            record.execution_time_seconds = (
                record.end_time - record.start_time
            ).total_seconds()

            logger.info(f"Baseline update job completed: {record.strikes_processed} strikes, "
                       f"{record.data_points_added} data points, "
                       f"{record.baselines_updated} baselines updated")

        except Exception as e:
            logger.error(f"Baseline update job failed: {e}")
            record.status = JobStatus.FAILED
            record.error_message = str(e)
            record.end_time = datetime.now(timezone.utc)
            record.execution_time_seconds = (
                record.end_time - record.start_time
            ).total_seconds()

        finally:
            # Save final job record
            self.job_database.record_execution(record)

        return record

    def _fetch_historical_data(self, strike: float, start_date: datetime,
                              record: JobExecutionRecord) -> List[HistoricalDataPoint]:
        """Fetch historical data for a strike"""
        historical_data = []

        # Simulate fetching data - in production this would call the actual API
        # For now, generate sample data for testing
        end_date = datetime.now(timezone.utc)
        current_date = start_date

        while current_date <= end_date:
            # Skip weekends
            if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                # Generate data for each time bucket
                for time_bucket in self.baseline_engine.time_buckets:
                    for contract_type in ['C', 'P']:
                        # Create sample data point
                        point = HistoricalDataPoint(
                            date=current_date,
                            strike_price=strike,
                            contract_type=contract_type,
                            time_bucket=time_bucket,
                            total_volume=1000 + (strike % 100) * 10,
                            buy_volume=600 + (strike % 50) * 5,
                            sell_volume=400 + (strike % 50) * 5,
                            buy_pressure_ratio=0.6,
                            trade_count=50,
                            avg_trade_size=20,
                            large_trades=5
                        )
                        historical_data.append(point)

                # Count as API call
                record.api_calls_made += 1

            current_date += timedelta(days=1)

        return historical_data


class ScheduledBaselineUpdater:
    """
    Main scheduled job system for baseline updates

    Features:
    - Daily baseline recalculation
    - Market hours awareness
    - Error handling and retries
    - Job history tracking
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize scheduled baseline updater

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.is_running = False
        self.scheduler_thread = None

        # Initialize components
        self.baseline_engine = create_baseline_engine(
            lookback_days=config.get('lookback_days', 20)
        )

        # Initialize data provider (would be configured based on config)
        self.data_provider = DatabentoMBOIngestion(config.get('databento_config', {}))

        # Active strikes to monitor
        self.active_strikes = config.get('active_strikes', [])
        if not self.active_strikes:
            # Default strikes around current NQ level
            base_strike = 21000
            self.active_strikes = [
                base_strike + (i * 100) for i in range(-10, 11)
            ]

        # Job configuration
        self.update_time = config.get('update_time', '06:30')  # Default 6:30 AM ET
        self.enabled_days = config.get('enabled_days', [0, 1, 2, 3, 4])  # Mon-Fri

        # Initialize job
        self.baseline_job = BaselineUpdateJob(
            self.baseline_engine,
            self.data_provider,
            self.active_strikes
        )

        # Job history
        self.job_database = JobDatabase()

        logger.info(f"Scheduled updater initialized with {len(self.active_strikes)} strikes")

    def start(self):
        """Start the scheduled job system"""
        if self.is_running:
            logger.warning("Scheduler already running")
            return

        self.is_running = True

        # Schedule daily job
        schedule.every().day.at(self.update_time).do(self._run_baseline_update)

        # Start scheduler thread
        self.scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            daemon=True,
            name="BaselineScheduler"
        )
        self.scheduler_thread.start()

        logger.info(f"Baseline scheduler started - Daily updates at {self.update_time} ET")

        # Run immediate update if configured
        if self.config.get('run_immediate', False):
            self._run_baseline_update()

    def stop(self):
        """Stop the scheduled job system"""
        logger.info("Stopping baseline scheduler")
        self.is_running = False

        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=5)

        # Clear all scheduled jobs
        schedule.clear()

        logger.info("Baseline scheduler stopped")

    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                # Check if today is enabled
                if get_eastern_time().weekday() in self.enabled_days:
                    schedule.run_pending()

                time.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

    def _run_baseline_update(self):
        """Run baseline update job with retries"""
        logger.info("Triggering scheduled baseline update")

        retry_count = 0
        while retry_count <= self.baseline_job.max_retries:
            try:
                # Execute job
                record = self.baseline_job.execute()

                if record.status == JobStatus.COMPLETED:
                    logger.info("Baseline update completed successfully")

                    # Send notification if configured
                    if self.config.get('notifications_enabled'):
                        self._send_completion_notification(record)

                    break

                elif record.status == JobStatus.FAILED:
                    retry_count += 1

                    if retry_count <= self.baseline_job.max_retries:
                        logger.warning(f"Baseline update failed, retrying in "
                                     f"{self.baseline_job.retry_delay} seconds "
                                     f"(attempt {retry_count}/{self.baseline_job.max_retries})")
                        time.sleep(self.baseline_job.retry_delay)
                    else:
                        logger.error("Baseline update failed after all retries")

                        # Send failure notification
                        if self.config.get('notifications_enabled'):
                            self._send_failure_notification(record)

            except Exception as e:
                logger.error(f"Unexpected error in baseline update: {e}")
                retry_count += 1

                if retry_count <= self.baseline_job.max_retries:
                    time.sleep(self.baseline_job.retry_delay)

    def _send_completion_notification(self, record: JobExecutionRecord):
        """Send job completion notification"""
        message = (
            f"✅ Baseline Update Completed\n"
            f"Job ID: {record.job_id}\n"
            f"Duration: {record.execution_time_seconds:.1f}s\n"
            f"Strikes: {record.strikes_processed}\n"
            f"Data Points: {record.data_points_added}\n"
            f"Baselines Updated: {record.baselines_updated}"
        )
        logger.info(message)
        # In production, this would send email/slack/etc

    def _send_failure_notification(self, record: JobExecutionRecord):
        """Send job failure notification"""
        message = (
            f"❌ Baseline Update Failed\n"
            f"Job ID: {record.job_id}\n"
            f"Error: {record.error_message}\n"
            f"Retries: {record.retry_count}"
        )
        logger.error(message)
        # In production, this would send email/slack/etc

    def get_job_status(self) -> Dict[str, Any]:
        """Get current job status and history"""
        # Get recent job executions
        with sqlite3.connect(self.job_database.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM job_executions
                WHERE job_type = 'baseline_update'
                ORDER BY start_time DESC
                LIMIT 10
            """)

            recent_jobs = []
            for row in cursor.fetchall():
                columns = [desc[0] for desc in cursor.description]
                job_data = dict(zip(columns, row))
                recent_jobs.append(job_data)

        # Get next scheduled run
        next_run = None
        if schedule.jobs:
            next_run = min(job.next_run for job in schedule.jobs)

        return {
            "scheduler_running": self.is_running,
            "next_scheduled_run": next_run.isoformat() if next_run else None,
            "active_strikes": len(self.active_strikes),
            "update_time": self.update_time,
            "enabled_days": self.enabled_days,
            "recent_jobs": recent_jobs,
            "last_successful_run": self.job_database.get_last_successful_run("baseline_update")
        }

    def add_strike(self, strike: float):
        """Add a strike to monitor"""
        if strike not in self.active_strikes:
            self.active_strikes.append(strike)
            self.active_strikes.sort()

            # Update job
            self.baseline_job.active_strikes = self.active_strikes

            logger.info(f"Added strike {strike} to monitoring")

    def remove_strike(self, strike: float):
        """Remove a strike from monitoring"""
        if strike in self.active_strikes:
            self.active_strikes.remove(strike)

            # Update job
            self.baseline_job.active_strikes = self.active_strikes

            logger.info(f"Removed strike {strike} from monitoring")

    def run_manual_update(self, strikes: Optional[List[float]] = None) -> JobExecutionRecord:
        """Run manual baseline update"""
        logger.info("Running manual baseline update")

        # Use provided strikes or default to active strikes
        original_strikes = self.baseline_job.active_strikes
        if strikes:
            self.baseline_job.active_strikes = strikes

        try:
            # Execute job
            record = self.baseline_job.execute()
            return record

        finally:
            # Restore original strikes
            self.baseline_job.active_strikes = original_strikes


def create_scheduled_updater(config: Optional[Dict] = None) -> ScheduledBaselineUpdater:
    """
    Factory function to create scheduled baseline updater

    Args:
        config: Configuration dictionary

    Returns:
        Configured ScheduledBaselineUpdater instance
    """
    if config is None:
        config = {
            'lookback_days': 20,
            'update_time': '06:30',
            'enabled_days': [0, 1, 2, 3, 4],  # Mon-Fri
            'run_immediate': False,
            'notifications_enabled': True
        }

    return ScheduledBaselineUpdater(config)


if __name__ == "__main__":
    # Example usage
    config = {
        'lookback_days': 20,
        'update_time': '06:30',
        'enabled_days': [0, 1, 2, 3, 4],
        'run_immediate': True,  # Run once immediately
        'active_strikes': [20900, 21000, 21100, 21200, 21300]
    }

    # Create and start scheduler
    updater = create_scheduled_updater(config)

    try:
        updater.start()

        # Run for demonstration
        print("Scheduled baseline updater running...")
        print(f"Next update scheduled for: {updater.get_job_status()['next_scheduled_run']}")

        # Keep running
        while True:
            time.sleep(60)

            # Periodically log status
            status = updater.get_job_status()
            if status['recent_jobs']:
                latest = status['recent_jobs'][0]
                print(f"Latest job: {latest['job_id']} - {latest['status']}")

    except KeyboardInterrupt:
        print("\nStopping scheduler...")
        updater.stop()
