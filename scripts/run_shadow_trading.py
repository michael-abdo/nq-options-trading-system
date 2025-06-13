#!/usr/bin/env python3
"""
Shadow Trading System Runner - 1-Week Live Market Validation

This script orchestrates a complete 1-week shadow trading validation where the
system runs against live market data without taking real positions, validating
signal generation, timing, and performance against historical backtesting.

Usage:
    python run_shadow_trading.py --config config/shadow_trading.json
    python run_shadow_trading.py --start-date 2025-06-17 --duration 7
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from utils.timezone_utils import format_eastern_timestamp, get_eastern_time

# Add project directories to path
script_dir = Path(__file__).parent
project_root = script_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tasks" / "options_trading_system"))

# Import shadow trading components
from tasks.options_trading_system.analysis_engine.strategies.shadow_trading_orchestrator import (
    ShadowTradingOrchestrator, ShadowTradingConfig, run_shadow_trading_validation
)
from tasks.options_trading_system.analysis_engine.strategies.market_relevance_tracker import (
    create_market_relevance_tracker
)

# Setup logging
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'outputs/shadow_trading_logs/shadow_trading_{format_eastern_timestamp()}.log')
        ]
    )

    # Ensure log directory exists
    log_dir = Path('outputs/shadow_trading_logs')
    log_dir.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str) -> dict:
    """Load shadow trading configuration from file"""
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = json.load(f)

    return config


def create_default_config(start_date: str = None, duration_days: int = 7) -> dict:
    """Create default shadow trading configuration"""

    if start_date is None:
        # Default to next Monday (using Eastern Time)
        today = get_eastern_time()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:  # If today is Monday
            days_until_monday = 7   # Use next Monday
        next_monday = today + timedelta(days=days_until_monday)
        start_date = next_monday.strftime('%Y-%m-%d')

    config = {
        "shadow_trading": {
            "start_date": start_date,
            "duration_days": duration_days,
            "trading_hours_start": "09:30",
            "trading_hours_end": "16:00",
            "report_frequency": "daily",
            "validation_mode": "strict",
            "max_daily_signals": 50,
            "confidence_threshold": 0.65,
            "paper_trading_capital": 100000.0,
            "save_detailed_logs": True,

            # Alert thresholds
            "max_daily_loss_pct": 2.0,
            "min_signal_accuracy": 0.70,
            "max_false_positive_rate": 0.15
        },

        "market_relevance": {
            "relevance_window_minutes": 30,
            "min_confidence_threshold": 0.65,
            "correlation_threshold": 0.7,
            "max_tracking_hours": 8
        },

        "data_sources": {
            "primary": "barchart",
            "fallback": ["databento", "polygon"],
            "cache_enabled": True,
            "cache_ttl_minutes": 5
        },

        "algorithms": {
            "v1_enabled": True,
            "v3_enabled": True,
            "comparison_mode": "parallel",
            "allocation_split": 0.5
        },

        "output": {
            "base_directory": "outputs/shadow_trading",
            "save_daily_reports": True,
            "save_signal_details": True,
            "save_market_data": False,
            "generate_charts": True
        },

        "monitoring": {
            "enable_real_time_monitoring": True,
            "dashboard_update_frequency": 300,  # 5 minutes
            "alert_email": None,
            "slack_webhook": None
        }
    }

    return config


def validate_config(config: dict) -> bool:
    """Validate shadow trading configuration"""
    required_fields = [
        'shadow_trading.start_date',
        'shadow_trading.duration_days',
        'shadow_trading.confidence_threshold',
        'shadow_trading.paper_trading_capital'
    ]

    for field in required_fields:
        keys = field.split('.')
        current = config

        try:
            for key in keys:
                current = current[key]
        except KeyError:
            logging.error(f"Required configuration field missing: {field}")
            return False

    # Validate date format
    try:
        datetime.strptime(config['shadow_trading']['start_date'], '%Y-%m-%d')
    except ValueError:
        logging.error("Invalid start_date format. Use YYYY-MM-DD")
        return False

    # Validate duration
    if config['shadow_trading']['duration_days'] < 1 or config['shadow_trading']['duration_days'] > 14:
        logging.error("Duration must be between 1 and 14 days")
        return False

    return True


def setup_historical_data() -> dict:
    """Load historical backtesting data for comparison"""

    # This would load actual historical backtesting results
    # For now, return sample data structure

    historical_data = {
        "backtesting_results": {
            "total_signals": 287,
            "accuracy_rate": 0.73,
            "false_positive_rate": 0.12,
            "avg_expected_value": 23.5,
            "win_rate": 0.68,
            "avg_time_to_signal": 450,  # seconds
            "peak_performance_hours": ["10:00-11:00", "14:00-15:00"]
        },

        "signal_patterns": {
            "daily_signal_frequency": {
                "monday": 15,
                "tuesday": 18,
                "wednesday": 16,
                "thursday": 14,
                "friday": 12
            },
            "hourly_distribution": {
                "09:30-10:30": 0.15,
                "10:30-11:30": 0.25,
                "11:30-12:30": 0.10,
                "12:30-13:30": 0.05,
                "13:30-14:30": 0.20,
                "14:30-15:30": 0.20,
                "15:30-16:00": 0.05
            }
        },

        "market_conditions": {
            "optimal_volatility_range": [0.20, 0.35],
            "optimal_volume_threshold": 50000,
            "correlation_factors": {
                "vix_correlation": 0.45,
                "volume_correlation": 0.62,
                "time_decay_factor": 0.88
            }
        }
    }

    return historical_data


def run_shadow_trading_system(config: dict) -> bool:
    """
    Run the complete shadow trading system

    Args:
        config: Shadow trading configuration

    Returns:
        True if validation passed, False otherwise
    """

    logging.info("="*80)
    logging.info("SHADOW TRADING SYSTEM - 1-WEEK VALIDATION")
    logging.info("="*80)

    # Extract configuration sections
    shadow_config = config['shadow_trading']
    market_config = config.get('market_relevance', {})

    logging.info(f"Start Date: {shadow_config['start_date']}")
    logging.info(f"Duration: {shadow_config['duration_days']} days")
    logging.info(f"Trading Hours: {shadow_config['trading_hours_start']} - {shadow_config['trading_hours_end']}")
    logging.info(f"Paper Capital: ${shadow_config['paper_trading_capital']:,.2f}")
    logging.info(f"Confidence Threshold: {shadow_config['confidence_threshold']:.1%}")

    try:
        # Setup historical data for comparison
        logging.info("Loading historical backtesting data...")
        historical_data = setup_historical_data()

        # Setup market relevance tracker
        logging.info("Initializing market relevance tracker...")
        relevance_tracker = create_market_relevance_tracker(market_config)

        # Run shadow trading validation
        logging.info("Starting shadow trading validation...")
        results = run_shadow_trading_validation(shadow_config, historical_data)

        if results:
            # Log final results
            logging.info("="*80)
            logging.info("SHADOW TRADING VALIDATION COMPLETED")
            logging.info("="*80)

            logging.info(f"Total Signals Generated: {results.total_signals}")
            logging.info(f"Overall Accuracy: {results.overall_accuracy:.1%}")
            logging.info(f"False Positive Rate: {results.overall_false_positive_rate:.1%}")
            logging.info(f"Final P&L: ${results.final_pnl:,.2f}")
            logging.info(f"Max Drawdown: ${results.max_drawdown:,.2f}")
            logging.info(f"System Uptime: {results.system_uptime_pct:.1%}")
            logging.info(f"Validation Score: {results.validation_score:.2f}/1.00")

            if results.validation_passed:
                logging.info("🎉 VALIDATION PASSED - System ready for live trading!")

                # Save success metrics
                save_validation_success(results, config)

                return True
            else:
                logging.warning("⚠️ VALIDATION FAILED - System needs improvements")

                # Log recommendations
                logging.info("Recommendations:")
                for rec in results.recommendations:
                    logging.info(f"  - {rec}")

                # Save failure analysis
                save_validation_failure(results, config)

                return False

        else:
            logging.error("Shadow trading validation failed to complete")
            return False

    except Exception as e:
        logging.error(f"Shadow trading system error: {e}")
        return False


def save_validation_success(results, config: dict):
    """Save successful validation results"""

    output_dir = Path(config['output']['base_directory']) / results.config.start_date
    output_dir.mkdir(parents=True, exist_ok=True)

    success_file = output_dir / "validation_success_summary.json"

    summary = {
        "validation_status": "PASSED",
        "completion_timestamp": datetime.now().isoformat(),
        "key_metrics": {
            "total_signals": results.total_signals,
            "overall_accuracy": results.overall_accuracy,
            "false_positive_rate": results.overall_false_positive_rate,
            "final_pnl": results.final_pnl,
            "validation_score": results.validation_score
        },
        "system_readiness": {
            "live_trading_approved": True,
            "recommended_start_capital": results.config.paper_trading_capital,
            "recommended_position_size": "Start with 50% of normal size",
            "monitoring_requirements": "Daily performance monitoring recommended"
        },
        "next_steps": [
            "Configure live trading environment",
            "Set up real-time monitoring alerts",
            "Begin with reduced position sizes",
            "Schedule daily performance reviews"
        ]
    }

    with open(success_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)

    logging.info(f"Success summary saved to: {success_file}")


def save_validation_failure(results, config: dict):
    """Save failed validation analysis"""

    output_dir = Path(config['output']['base_directory']) / results.config.start_date
    output_dir.mkdir(parents=True, exist_ok=True)

    failure_file = output_dir / "validation_failure_analysis.json"

    analysis = {
        "validation_status": "FAILED",
        "completion_timestamp": datetime.now().isoformat(),
        "failure_reasons": results.recommendations,
        "key_metrics": {
            "total_signals": results.total_signals,
            "overall_accuracy": results.overall_accuracy,
            "false_positive_rate": results.overall_false_positive_rate,
            "final_pnl": results.final_pnl,
            "validation_score": results.validation_score
        },
        "required_improvements": {
            "accuracy_target": results.config.min_signal_accuracy,
            "current_accuracy": results.overall_accuracy,
            "accuracy_gap": results.config.min_signal_accuracy - results.overall_accuracy,
            "false_positive_target": results.config.max_false_positive_rate,
            "current_false_positive": results.overall_false_positive_rate
        },
        "recommended_actions": [
            "Review and tune signal generation algorithms",
            "Analyze false positive patterns",
            "Consider adjusting confidence thresholds",
            "Re-run validation after improvements"
        ]
    }

    with open(failure_file, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    logging.info(f"Failure analysis saved to: {failure_file}")


def main():
    """Main execution function"""

    parser = argparse.ArgumentParser(
        description="Shadow Trading System - 1-Week Live Market Validation"
    )

    parser.add_argument(
        '--config', '-c',
        help='Path to configuration file',
        default=None
    )

    parser.add_argument(
        '--start-date', '-s',
        help='Start date (YYYY-MM-DD format)',
        default=None
    )

    parser.add_argument(
        '--duration', '-d',
        type=int,
        help='Duration in days (default: 7)',
        default=7
    )

    parser.add_argument(
        '--log-level', '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Validate configuration without running'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.log_level)

    try:
        # Load or create configuration
        if args.config:
            logging.info(f"Loading configuration from: {args.config}")
            config = load_config(args.config)
        else:
            logging.info("Creating default configuration")
            config = create_default_config(args.start_date, args.duration)

            # Save default config for reference
            config_file = f"config/shadow_trading_default_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logging.info(f"Default configuration saved to: {config_file}")

        # Validate configuration
        if not validate_config(config):
            logging.error("Configuration validation failed")
            return 1

        logging.info("Configuration validated successfully")

        if args.dry_run:
            logging.info("Dry run completed - configuration is valid")
            return 0

        # Run shadow trading system
        success = run_shadow_trading_system(config)

        if success:
            logging.info("🎉 Shadow Trading Validation SUCCESSFUL!")
            print("\n" + "="*60)
            print("✅ SHADOW TRADING VALIDATION PASSED")
            print("✅ System is ready for live trading deployment")
            print("="*60)
            return 0
        else:
            logging.warning("⚠️ Shadow Trading Validation FAILED")
            print("\n" + "="*60)
            print("❌ SHADOW TRADING VALIDATION FAILED")
            print("❌ System requires improvements before live deployment")
            print("="*60)
            return 1

    except KeyboardInterrupt:
        logging.info("Shadow trading validation interrupted by user")
        return 1

    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
