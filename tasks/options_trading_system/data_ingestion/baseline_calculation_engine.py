#!/usr/bin/env python3
"""
Historical Baseline Calculation Engine

This module provides statistical baseline calculations for institutional flow detection:
- 20-day lookback for historical patterns
- Statistical metrics (mean, std, percentiles) by strike and time
- Incremental updates to minimize API calls
- Anomaly detection thresholds
"""

import os
import json
import sqlite3
import logging
from datetime import datetime, timedelta, timezone, time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import numpy as np
import pandas as pd
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class BaselineMetrics:
    """Statistical baseline metrics for a strike/time combination"""
    strike_price: float
    contract_type: str
    time_bucket: str  # e.g., "09:30-10:00"
    
    # Volume baselines
    volume_mean: float
    volume_std: float
    volume_p25: float  # 25th percentile
    volume_p50: float  # Median
    volume_p75: float  # 75th percentile
    volume_p95: float  # 95th percentile
    
    # Pressure ratio baselines
    pressure_mean: float
    pressure_std: float
    pressure_p25: float
    pressure_p50: float
    pressure_p75: float
    pressure_p95: float
    
    # Trade size baselines
    avg_trade_size_mean: float
    avg_trade_size_std: float
    large_trade_ratio_mean: float  # Ratio of trades > 100 contracts
    
    # Sample statistics
    sample_count: int
    days_included: int
    last_updated: datetime
    
    # Anomaly thresholds
    volume_threshold_high: float  # e.g., mean + 2*std
    volume_threshold_extreme: float  # e.g., mean + 3*std
    pressure_threshold_high: float
    pressure_threshold_low: float


@dataclass
class HistoricalDataPoint:
    """Individual historical data point for baseline calculation"""
    date: datetime
    strike_price: float
    contract_type: str
    time_bucket: str
    
    total_volume: int
    buy_volume: int
    sell_volume: int
    buy_pressure_ratio: float
    
    trade_count: int
    avg_trade_size: float
    large_trades: int  # Trades > 100 contracts


class BaselineDatabase:
    """SQLite database for baseline storage and retrieval"""
    
    def __init__(self, db_path: str = "outputs/baseline_metrics.db"):
        """Initialize baseline database"""
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Historical data points table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS historical_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    strike_price REAL NOT NULL,
                    contract_type TEXT NOT NULL,
                    time_bucket TEXT NOT NULL,
                    total_volume INTEGER,
                    buy_volume INTEGER,
                    sell_volume INTEGER,
                    buy_pressure_ratio REAL,
                    trade_count INTEGER,
                    avg_trade_size REAL,
                    large_trades INTEGER,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, strike_price, contract_type, time_bucket)
                )
            """)
            
            # Baseline metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS baseline_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strike_price REAL NOT NULL,
                    contract_type TEXT NOT NULL,
                    time_bucket TEXT NOT NULL,
                    volume_mean REAL,
                    volume_std REAL,
                    volume_p25 REAL,
                    volume_p50 REAL,
                    volume_p75 REAL,
                    volume_p95 REAL,
                    pressure_mean REAL,
                    pressure_std REAL,
                    pressure_p25 REAL,
                    pressure_p50 REAL,
                    pressure_p75 REAL,
                    pressure_p95 REAL,
                    avg_trade_size_mean REAL,
                    avg_trade_size_std REAL,
                    large_trade_ratio_mean REAL,
                    sample_count INTEGER,
                    days_included INTEGER,
                    last_updated TEXT,
                    volume_threshold_high REAL,
                    volume_threshold_extreme REAL,
                    pressure_threshold_high REAL,
                    pressure_threshold_low REAL,
                    UNIQUE(strike_price, contract_type, time_bucket)
                )
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_historical_date 
                ON historical_data(date, strike_price, contract_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_baseline_strike 
                ON baseline_metrics(strike_price, contract_type, time_bucket)
            """)
            
            conn.commit()
    
    def store_historical_data(self, data_points: List[HistoricalDataPoint]):
        """Store historical data points"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for point in data_points:
                cursor.execute("""
                    INSERT OR REPLACE INTO historical_data 
                    (date, strike_price, contract_type, time_bucket,
                     total_volume, buy_volume, sell_volume, buy_pressure_ratio,
                     trade_count, avg_trade_size, large_trades)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    point.date.isoformat(),
                    point.strike_price,
                    point.contract_type,
                    point.time_bucket,
                    point.total_volume,
                    point.buy_volume,
                    point.sell_volume,
                    point.buy_pressure_ratio,
                    point.trade_count,
                    point.avg_trade_size,
                    point.large_trades
                ))
            
            conn.commit()
    
    def get_historical_data(self, strike_price: float, contract_type: str, 
                           time_bucket: str, days_back: int = 20) -> pd.DataFrame:
        """Get historical data for baseline calculation"""
        cutoff_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
        
        query = """
            SELECT * FROM historical_data
            WHERE strike_price = ? AND contract_type = ? AND time_bucket = ?
            AND date >= ?
            ORDER BY date DESC
        """
        
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=(
                strike_price, contract_type, time_bucket, cutoff_date
            ))
        
        return df
    
    def store_baseline_metrics(self, metrics: BaselineMetrics):
        """Store calculated baseline metrics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO baseline_metrics 
                (strike_price, contract_type, time_bucket,
                 volume_mean, volume_std, volume_p25, volume_p50, volume_p75, volume_p95,
                 pressure_mean, pressure_std, pressure_p25, pressure_p50, pressure_p75, pressure_p95,
                 avg_trade_size_mean, avg_trade_size_std, large_trade_ratio_mean,
                 sample_count, days_included, last_updated,
                 volume_threshold_high, volume_threshold_extreme,
                 pressure_threshold_high, pressure_threshold_low)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                metrics.strike_price, metrics.contract_type, metrics.time_bucket,
                metrics.volume_mean, metrics.volume_std,
                metrics.volume_p25, metrics.volume_p50, metrics.volume_p75, metrics.volume_p95,
                metrics.pressure_mean, metrics.pressure_std,
                metrics.pressure_p25, metrics.pressure_p50, metrics.pressure_p75, metrics.pressure_p95,
                metrics.avg_trade_size_mean, metrics.avg_trade_size_std,
                metrics.large_trade_ratio_mean,
                metrics.sample_count, metrics.days_included,
                metrics.last_updated.isoformat(),
                metrics.volume_threshold_high, metrics.volume_threshold_extreme,
                metrics.pressure_threshold_high, metrics.pressure_threshold_low
            ))
            
            conn.commit()
    
    def get_baseline_metrics(self, strike_price: float, contract_type: str, 
                           time_bucket: str) -> Optional[BaselineMetrics]:
        """Get baseline metrics for a specific strike/time"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM baseline_metrics
                WHERE strike_price = ? AND contract_type = ? AND time_bucket = ?
            """, (strike_price, contract_type, time_bucket))
            
            row = cursor.fetchone()
            if row:
                # Convert row to dict
                columns = [desc[0] for desc in cursor.description]
                data = dict(zip(columns, row))
                
                # Convert to BaselineMetrics
                data['last_updated'] = datetime.fromisoformat(data['last_updated'])
                del data['id']  # Remove ID field
                
                return BaselineMetrics(**data)
        
        return None


class BaselineCalculationEngine:
    """
    Main engine for calculating statistical baselines
    
    Features:
    - 20-day lookback window
    - Time-bucketed analysis (30-minute buckets)
    - Strike-specific baselines
    - Incremental updates
    """
    
    def __init__(self, db_path: str = "outputs/baseline_metrics.db",
                 lookback_days: int = 20):
        """
        Initialize baseline calculation engine
        
        Args:
            db_path: Path to baseline database
            lookback_days: Number of days to look back
        """
        self.lookback_days = lookback_days
        self.database = BaselineDatabase(db_path)
        self.time_buckets = self._generate_time_buckets()
        
        # Statistics cache
        self._baseline_cache = {}
        self._cache_expiry = timedelta(hours=6)  # Refresh every 6 hours
        
        logger.info(f"Baseline engine initialized with {lookback_days}-day lookback")
    
    def _generate_time_buckets(self) -> List[str]:
        """Generate 30-minute time buckets for market hours"""
        buckets = []
        start_time = time(9, 30)  # 9:30 AM
        end_time = time(16, 0)    # 4:00 PM
        
        current = datetime.combine(datetime.today(), start_time)
        end = datetime.combine(datetime.today(), end_time)
        
        while current < end:
            bucket_start = current.strftime("%H:%M")
            current += timedelta(minutes=30)
            bucket_end = current.strftime("%H:%M")
            buckets.append(f"{bucket_start}-{bucket_end}")
        
        return buckets
    
    def calculate_baselines_for_strike(self, strike_price: float, 
                                     contract_type: str,
                                     historical_data: List[HistoricalDataPoint]) -> Dict[str, BaselineMetrics]:
        """
        Calculate baselines for all time buckets of a strike
        
        Args:
            strike_price: Strike price
            contract_type: 'C' or 'P'
            historical_data: Historical data points
            
        Returns:
            Dict mapping time_bucket to BaselineMetrics
        """
        # Group data by time bucket
        bucket_data = defaultdict(list)
        for point in historical_data:
            bucket_data[point.time_bucket].append(point)
        
        baselines = {}
        
        for time_bucket, points in bucket_data.items():
            if len(points) < 5:  # Need minimum samples
                logger.warning(f"Insufficient data for {strike_price} {contract_type} {time_bucket}")
                continue
            
            # Extract arrays for calculation
            volumes = [p.total_volume for p in points]
            pressures = [p.buy_pressure_ratio for p in points]
            trade_sizes = [p.avg_trade_size for p in points if p.avg_trade_size > 0]
            large_trade_counts = [p.large_trades for p in points]
            trade_counts = [p.trade_count for p in points if p.trade_count > 0]
            
            # Calculate volume statistics
            volume_mean = np.mean(volumes)
            volume_std = np.std(volumes)
            volume_percentiles = np.percentile(volumes, [25, 50, 75, 95])
            
            # Calculate pressure statistics
            pressure_mean = np.mean(pressures)
            pressure_std = np.std(pressures)
            pressure_percentiles = np.percentile(pressures, [25, 50, 75, 95])
            
            # Calculate trade size statistics
            trade_size_mean = np.mean(trade_sizes) if trade_sizes else 0
            trade_size_std = np.std(trade_sizes) if trade_sizes else 0
            
            # Calculate large trade ratio
            large_trade_ratios = []
            for i, tc in enumerate(trade_counts):
                if tc > 0:
                    ratio = large_trade_counts[i] / tc
                    large_trade_ratios.append(ratio)
            
            large_trade_ratio_mean = np.mean(large_trade_ratios) if large_trade_ratios else 0
            
            # Calculate anomaly thresholds
            volume_threshold_high = volume_mean + 2 * volume_std
            volume_threshold_extreme = volume_mean + 3 * volume_std
            pressure_threshold_high = min(0.95, pressure_mean + 2 * pressure_std)
            pressure_threshold_low = max(0.05, pressure_mean - 2 * pressure_std)
            
            # Count unique days
            unique_dates = set(p.date.date() for p in points)
            
            # Create baseline metrics
            metrics = BaselineMetrics(
                strike_price=strike_price,
                contract_type=contract_type,
                time_bucket=time_bucket,
                volume_mean=volume_mean,
                volume_std=volume_std,
                volume_p25=volume_percentiles[0],
                volume_p50=volume_percentiles[1],
                volume_p75=volume_percentiles[2],
                volume_p95=volume_percentiles[3],
                pressure_mean=pressure_mean,
                pressure_std=pressure_std,
                pressure_p25=pressure_percentiles[0],
                pressure_p50=pressure_percentiles[1],
                pressure_p75=pressure_percentiles[2],
                pressure_p95=pressure_percentiles[3],
                avg_trade_size_mean=trade_size_mean,
                avg_trade_size_std=trade_size_std,
                large_trade_ratio_mean=large_trade_ratio_mean,
                sample_count=len(points),
                days_included=len(unique_dates),
                last_updated=datetime.now(timezone.utc),
                volume_threshold_high=volume_threshold_high,
                volume_threshold_extreme=volume_threshold_extreme,
                pressure_threshold_high=pressure_threshold_high,
                pressure_threshold_low=pressure_threshold_low
            )
            
            baselines[time_bucket] = metrics
            
            # Store in database
            self.database.store_baseline_metrics(metrics)
        
        return baselines
    
    def update_baselines_incremental(self, new_data: List[HistoricalDataPoint]):
        """
        Update baselines incrementally with new data
        
        This avoids recalculating from scratch each time
        """
        # Store new historical data
        self.database.store_historical_data(new_data)
        
        # Group by strike and type
        strike_groups = defaultdict(list)
        for point in new_data:
            key = (point.strike_price, point.contract_type)
            strike_groups[key].append(point)
        
        # Update baselines for each strike
        for (strike, contract_type), points in strike_groups.items():
            # Get historical data including new points
            all_historical = []
            
            for time_bucket in self.time_buckets:
                df = self.database.get_historical_data(
                    strike, contract_type, time_bucket, self.lookback_days
                )
                
                # Convert DataFrame to HistoricalDataPoint objects
                for _, row in df.iterrows():
                    point = HistoricalDataPoint(
                        date=datetime.fromisoformat(row['date']),
                        strike_price=row['strike_price'],
                        contract_type=row['contract_type'],
                        time_bucket=row['time_bucket'],
                        total_volume=row['total_volume'],
                        buy_volume=row['buy_volume'],
                        sell_volume=row['sell_volume'],
                        buy_pressure_ratio=row['buy_pressure_ratio'],
                        trade_count=row['trade_count'],
                        avg_trade_size=row['avg_trade_size'],
                        large_trades=row['large_trades']
                    )
                    all_historical.append(point)
            
            # Recalculate baselines
            if all_historical:
                self.calculate_baselines_for_strike(strike, contract_type, all_historical)
    
    def check_anomaly(self, strike_price: float, contract_type: str,
                     time_bucket: str, current_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Check if current metrics are anomalous compared to baseline
        
        Args:
            strike_price: Strike price
            contract_type: 'C' or 'P'
            time_bucket: Time bucket
            current_metrics: Dict with 'volume', 'pressure_ratio', etc.
            
        Returns:
            Dict with anomaly flags and scores
        """
        # Get baseline
        baseline = self.get_baseline(strike_price, contract_type, time_bucket)
        
        if not baseline:
            return {
                'has_baseline': False,
                'is_anomalous': False,
                'anomaly_score': 0.0,
                'anomaly_flags': []
            }
        
        anomaly_flags = []
        anomaly_scores = []
        
        # Check volume anomaly
        current_volume = current_metrics.get('volume', 0)
        if current_volume > baseline.volume_threshold_extreme:
            anomaly_flags.append('EXTREME_VOLUME')
            anomaly_scores.append(3.0)
        elif current_volume > baseline.volume_threshold_high:
            anomaly_flags.append('HIGH_VOLUME')
            anomaly_scores.append(2.0)
        
        # Volume z-score
        if baseline.volume_std > 0:
            volume_z = (current_volume - baseline.volume_mean) / baseline.volume_std
            if abs(volume_z) > 2:
                anomaly_scores.append(abs(volume_z))
        
        # Check pressure anomaly
        current_pressure = current_metrics.get('pressure_ratio', 0.5)
        if current_pressure > baseline.pressure_threshold_high:
            anomaly_flags.append('HIGH_BUY_PRESSURE')
            anomaly_scores.append(2.0)
        elif current_pressure < baseline.pressure_threshold_low:
            anomaly_flags.append('HIGH_SELL_PRESSURE')
            anomaly_scores.append(2.0)
        
        # Pressure z-score
        if baseline.pressure_std > 0:
            pressure_z = (current_pressure - baseline.pressure_mean) / baseline.pressure_std
            if abs(pressure_z) > 2:
                anomaly_scores.append(abs(pressure_z))
        
        # Check trade size anomaly
        current_avg_size = current_metrics.get('avg_trade_size', 0)
        if baseline.avg_trade_size_std > 0:
            size_z = (current_avg_size - baseline.avg_trade_size_mean) / baseline.avg_trade_size_std
            if abs(size_z) > 3:
                anomaly_flags.append('UNUSUAL_TRADE_SIZE')
                anomaly_scores.append(abs(size_z))
        
        # Overall anomaly score
        anomaly_score = max(anomaly_scores) if anomaly_scores else 0.0
        is_anomalous = len(anomaly_flags) > 0
        
        return {
            'has_baseline': True,
            'is_anomalous': is_anomalous,
            'anomaly_score': anomaly_score,
            'anomaly_flags': anomaly_flags,
            'baseline_sample_count': baseline.sample_count,
            'baseline_days': baseline.days_included,
            'volume_z_score': volume_z if 'volume_z' in locals() else None,
            'pressure_z_score': pressure_z if 'pressure_z' in locals() else None
        }
    
    def get_baseline(self, strike_price: float, contract_type: str,
                    time_bucket: str) -> Optional[BaselineMetrics]:
        """Get baseline metrics with caching"""
        cache_key = (strike_price, contract_type, time_bucket)
        
        # Check cache
        if cache_key in self._baseline_cache:
            cached, timestamp = self._baseline_cache[cache_key]
            if datetime.now(timezone.utc) - timestamp < self._cache_expiry:
                return cached
        
        # Load from database
        baseline = self.database.get_baseline_metrics(
            strike_price, contract_type, time_bucket
        )
        
        # Update cache
        if baseline:
            self._baseline_cache[cache_key] = (baseline, datetime.now(timezone.utc))
        
        return baseline
    
    def get_time_bucket(self, timestamp: datetime) -> str:
        """Get the time bucket for a given timestamp"""
        # Convert to market timezone (ET)
        import pytz
        et_tz = pytz.timezone('America/New_York')
        et_time = timestamp.astimezone(et_tz)
        
        # Find matching bucket
        current_time = et_time.time()
        
        for bucket in self.time_buckets:
            start_str, end_str = bucket.split('-')
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))
            
            start_time = time(start_hour, start_min)
            end_time = time(end_hour, end_min)
            
            if start_time <= current_time < end_time:
                return bucket
        
        return "AFTER_HOURS"
    
    def generate_baseline_report(self, strikes: List[float]) -> Dict[str, Any]:
        """Generate comprehensive baseline report for strikes"""
        report = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'lookback_days': self.lookback_days,
            'strikes_analyzed': [],
            'summary_statistics': {}
        }
        
        all_volumes = []
        all_pressures = []
        
        for strike in strikes:
            strike_data = {
                'strike': strike,
                'call_baselines': {},
                'put_baselines': {}
            }
            
            for contract_type in ['C', 'P']:
                for time_bucket in self.time_buckets:
                    baseline = self.get_baseline(strike, contract_type, time_bucket)
                    if baseline:
                        key = f"{contract_type}_baselines"
                        strike_data[key][time_bucket] = {
                            'volume_mean': baseline.volume_mean,
                            'volume_std': baseline.volume_std,
                            'pressure_mean': baseline.pressure_mean,
                            'sample_days': baseline.days_included
                        }
                        
                        all_volumes.append(baseline.volume_mean)
                        all_pressures.append(baseline.pressure_mean)
            
            report['strikes_analyzed'].append(strike_data)
        
        # Summary statistics
        if all_volumes:
            report['summary_statistics'] = {
                'avg_volume_across_strikes': np.mean(all_volumes),
                'avg_pressure_across_strikes': np.mean(all_pressures),
                'total_baselines': len(all_volumes)
            }
        
        return report


def create_baseline_engine(lookback_days: int = 20) -> BaselineCalculationEngine:
    """
    Factory function to create baseline calculation engine
    
    Args:
        lookback_days: Number of days for lookback window
        
    Returns:
        Configured BaselineCalculationEngine instance
    """
    return BaselineCalculationEngine(lookback_days=lookback_days)


if __name__ == "__main__":
    # Example usage
    engine = create_baseline_engine(lookback_days=20)
    
    # Example historical data
    sample_data = []
    base_date = datetime.now(timezone.utc) - timedelta(days=10)
    
    for day in range(10):
        date = base_date + timedelta(days=day)
        
        # Simulate data for 21000 strike call
        point = HistoricalDataPoint(
            date=date,
            strike_price=21000,
            contract_type='C',
            time_bucket='09:30-10:00',
            total_volume=1000 + day * 100,  # Increasing volume
            buy_volume=600 + day * 50,
            sell_volume=400 + day * 50,
            buy_pressure_ratio=0.6,
            trade_count=50 + day * 5,
            avg_trade_size=20,
            large_trades=5 + day
        )
        sample_data.append(point)
    
    # Update baselines
    print("Updating baselines with sample data...")
    engine.update_baselines_incremental(sample_data)
    
    # Check for anomaly
    current_metrics = {
        'volume': 3000,  # Much higher than normal
        'pressure_ratio': 0.9,  # High buy pressure
        'avg_trade_size': 50
    }
    
    anomaly_result = engine.check_anomaly(
        21000, 'C', '09:30-10:00', current_metrics
    )
    
    print(f"\nAnomaly Check Result:")
    print(f"  Has Baseline: {anomaly_result['has_baseline']}")
    print(f"  Is Anomalous: {anomaly_result['is_anomalous']}")
    print(f"  Anomaly Score: {anomaly_result['anomaly_score']:.2f}")
    print(f"  Flags: {anomaly_result['anomaly_flags']}")
    
    # Generate report
    report = engine.generate_baseline_report([21000, 21100, 21200])
    print(f"\nBaseline Report Summary:")
    print(f"  Strikes Analyzed: {len(report['strikes_analyzed'])}")
    print(f"  Generated At: {report['generated_at']}")