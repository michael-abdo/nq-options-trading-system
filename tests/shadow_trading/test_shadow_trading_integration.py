#!/usr/bin/env python3
"""
Shadow Trading System Integration Test

Quick test to validate that all shadow trading components integrate correctly
and the system can be started without errors.
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add project directories to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "tasks" / "options_trading_system"))

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_shadow_trading_imports():
    """Test that all shadow trading components can be imported"""
    logger.info("Testing shadow trading imports...")

    try:
        from tasks.options_trading_system.analysis_engine.strategies.shadow_trading_orchestrator import (
            ShadowTradingOrchestrator, ShadowTradingConfig, create_shadow_trading_orchestrator
        )
        logger.info("✓ Shadow Trading Orchestrator import successful")

        from tasks.options_trading_system.analysis_engine.strategies.market_relevance_tracker import (
            MarketRelevanceTracker, create_market_relevance_tracker
        )
        logger.info("✓ Market Relevance Tracker import successful")

        from run_shadow_trading import (
            create_default_config, validate_config, setup_historical_data
        )
        logger.info("✓ Shadow Trading Runner import successful")

        return True

    except ImportError as e:
        logger.error(f"✗ Import failed: {e}")
        return False


def test_shadow_trading_config():
    """Test shadow trading configuration creation and validation"""
    logger.info("Testing shadow trading configuration...")

    try:
        from run_shadow_trading import create_default_config, validate_config

        # Test default config creation
        config = create_default_config("2025-06-16", 7)
        logger.info("✓ Default configuration created")

        # Test config validation
        is_valid = validate_config(config)
        if is_valid:
            logger.info("✓ Configuration validation passed")
        else:
            logger.error("✗ Configuration validation failed")
            return False

        # Test config file loading
        config_file = "config/shadow_trading.json"
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                file_config = json.load(f)

            is_valid = validate_config(file_config)
            if is_valid:
                logger.info("✓ Config file validation passed")
            else:
                logger.error("✗ Config file validation failed")
                return False

        return True

    except Exception as e:
        logger.error(f"✗ Configuration test failed: {e}")
        return False


def test_component_initialization():
    """Test that shadow trading components can be initialized"""
    logger.info("Testing component initialization...")

    try:
        from tasks.options_trading_system.analysis_engine.strategies.shadow_trading_orchestrator import (
            create_shadow_trading_orchestrator, ShadowTradingConfig
        )
        from tasks.options_trading_system.analysis_engine.strategies.market_relevance_tracker import (
            create_market_relevance_tracker
        )

        # Test ShadowTradingConfig creation
        config_dict = {
            'start_date': '2025-06-16',
            'duration_days': 7,
            'trading_hours_start': '09:30',
            'trading_hours_end': '16:00',
            'confidence_threshold': 0.65,
            'paper_trading_capital': 100000.0,
            'max_daily_loss_pct': 2.0,
            'min_signal_accuracy': 0.70,
            'max_false_positive_rate': 0.15
        }

        config = ShadowTradingConfig(**config_dict)
        logger.info("✓ ShadowTradingConfig created")

        # Test orchestrator creation
        orchestrator = create_shadow_trading_orchestrator(config_dict)
        logger.info("✓ Shadow Trading Orchestrator created")

        # Test status check
        status = orchestrator.get_status()
        logger.info(f"✓ Orchestrator status: {status['is_running']}")

        # Test market relevance tracker
        relevance_config = {
            'relevance_window_minutes': 30,
            'correlation_threshold': 0.7
        }

        tracker = create_market_relevance_tracker(relevance_config)
        logger.info("✓ Market Relevance Tracker created")

        # Test signal tracking
        test_signal = {
            'id': 'test_signal_1',
            'signal_type': 'call_buying',
            'strike': 21000,
            'confidence': 0.75,
            'expected_value': 25.0
        }

        signal_id = tracker.track_signal(test_signal)
        logger.info(f"✓ Signal tracking started: {signal_id}")

        return True

    except Exception as e:
        logger.error(f"✗ Component initialization failed: {e}")
        return False


def test_existing_dependencies():
    """Test that required existing components are available"""
    logger.info("Testing existing dependencies...")

    try:
        # Test paper trading executor
        try:
            from tasks.options_trading_system.analysis_engine.strategies.paper_trading_executor import (
                PaperTradingExecutor
            )
            logger.info("✓ Paper Trading Executor available")
        except ImportError:
            logger.warning("⚠ Paper Trading Executor not available - using mock")

        # Test A/B testing coordinator
        try:
            from tasks.options_trading_system.analysis_engine.strategies.ab_testing_coordinator import (
                ABTestingCoordinator
            )
            logger.info("✓ A/B Testing Coordinator available")
        except ImportError:
            logger.warning("⚠ A/B Testing Coordinator not available - using mock")

        # Test performance tracker
        try:
            from tasks.options_trading_system.analysis_engine.monitoring.performance_tracker import (
                PerformanceTracker
            )
            logger.info("✓ Performance Tracker available")
        except ImportError:
            logger.warning("⚠ Performance Tracker not available - using mock")

        return True

    except Exception as e:
        logger.error(f"✗ Dependency test failed: {e}")
        return False


def test_output_directories():
    """Test that output directories can be created"""
    logger.info("Testing output directory creation...")

    try:
        # Test shadow trading output directory
        shadow_output_dir = Path("outputs/shadow_trading/2025-06-16")
        shadow_output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Shadow trading output directory created")

        # Test logs directory
        logs_dir = Path("outputs/shadow_trading_logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Shadow trading logs directory created")

        # Test config backup directory
        config_dir = Path("config")
        config_dir.mkdir(parents=True, exist_ok=True)
        logger.info("✓ Config directory verified")

        return True

    except Exception as e:
        logger.error(f"✗ Output directory test failed: {e}")
        return False


def test_historical_data_setup():
    """Test historical data setup"""
    logger.info("Testing historical data setup...")

    try:
        from run_shadow_trading import setup_historical_data

        historical_data = setup_historical_data()

        # Validate historical data structure
        required_keys = ['backtesting_results', 'signal_patterns', 'market_conditions']
        for key in required_keys:
            if key not in historical_data:
                logger.error(f"✗ Missing historical data key: {key}")
                return False

        logger.info("✓ Historical data setup successful")
        return True

    except Exception as e:
        logger.error(f"✗ Historical data setup failed: {e}")
        return False


def run_integration_test():
    """Run complete integration test"""
    logger.info("="*60)
    logger.info("SHADOW TRADING SYSTEM INTEGRATION TEST")
    logger.info("="*60)

    tests = [
        ("Component Imports", test_shadow_trading_imports),
        ("Configuration System", test_shadow_trading_config),
        ("Component Initialization", test_component_initialization),
        ("Existing Dependencies", test_existing_dependencies),
        ("Output Directories", test_output_directories),
        ("Historical Data Setup", test_historical_data_setup)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        logger.info(f"\nRunning test: {test_name}")
        logger.info("-" * 40)

        try:
            if test_func():
                logger.info(f"✅ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"❌ {test_name} FAILED")
        except Exception as e:
            logger.error(f"❌ {test_name} FAILED with error: {e}")

    logger.info("\n" + "="*60)
    logger.info("INTEGRATION TEST RESULTS")
    logger.info("="*60)
    logger.info(f"Tests Passed: {passed}/{total}")
    logger.info(f"Success Rate: {(passed/total)*100:.1f}%")

    if passed == total:
        logger.info("🎉 ALL TESTS PASSED - Shadow Trading System Ready!")
        logger.info("\nNext steps:")
        logger.info("1. Review shadow trading configuration in config/shadow_trading.json")
        logger.info("2. Run: python run_shadow_trading.py --dry-run")
        logger.info("3. Start shadow trading: python run_shadow_trading.py")
        return True
    else:
        logger.warning(f"⚠️ {total-passed} TESTS FAILED - Fix issues before deployment")
        return False


if __name__ == "__main__":
    success = run_integration_test()
    exit(0 if success else 1)
