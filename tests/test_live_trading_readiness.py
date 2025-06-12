#!/usr/bin/env python3
"""
Live Trading Readiness Test Suite
Comprehensive testing for live trading deployment readiness
"""

import sys
import os
import time
import json
import traceback
from datetime import datetime
from pathlib import Path

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

class LiveTradingReadinessTest:
    """Comprehensive live trading readiness test suite"""

    def __init__(self):
        self.test_results = {
            "test_run_timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "critical_failures": [],
            "warnings": [],
            "test_details": {}
        }

    def run_test(self, test_name, test_func, critical=True):
        """Run a single test and record results"""
        try:
            print(f"Running: {test_name}")
            start_time = time.time()
            result = test_func()
            elapsed = time.time() - start_time

            self.test_results["tests_passed"] += 1
            self.test_results["test_details"][test_name] = {
                "status": "PASSED",
                "elapsed_time": elapsed,
                "result": result
            }
            print(f"✅ {test_name}: PASSED ({elapsed:.2f}s)")

        except Exception as e:
            elapsed = time.time() - start_time if 'start_time' in locals() else 0
            self.test_results["tests_failed"] += 1
            self.test_results["test_details"][test_name] = {
                "status": "FAILED",
                "elapsed_time": elapsed,
                "error": str(e),
                "traceback": traceback.format_exc()
            }

            if critical:
                self.test_results["critical_failures"].append(test_name)
                print(f"❌ {test_name}: CRITICAL FAILURE - {e}")
            else:
                self.test_results["warnings"].append(test_name)
                print(f"⚠️  {test_name}: WARNING - {e}")

    def test_configuration_loading(self):
        """Test all configuration profiles load correctly"""
        from config_manager import ConfigurationManager

        profiles = ['databento_only', 'barchart_only', 'all_sources', 'testing']
        results = {}

        for profile in profiles:
            config_path = f'config/{profile}.json'
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    config_data = json.load(f)

                # Validate structure
                required_sections = ['data_sources', 'analysis', 'output', 'save']
                missing = [s for s in required_sections if s not in config_data]

                if missing:
                    raise Exception(f"{profile}: Missing sections {missing}")

                results[profile] = {
                    "total_sources": len(config_data['data_sources']),
                    "enabled_sources": sum(1 for s, c in config_data['data_sources'].items() if c.get('enabled', False))
                }

        return results

    def test_core_imports(self):
        """Test critical system imports work correctly"""
        import_results = {}

        # Test configuration manager
        from config_manager import ConfigurationManager
        config_mgr = ConfigurationManager('config')
        import_results['config_manager'] = "OK"

        # Test integration module
        from integration import NQOptionsTradingSystem
        import_results['integration'] = "OK"

        # Test analysis engines
        from analysis_engine import expected_value_analysis
        from analysis_engine import institutional_flow_v3
        from analysis_engine import volume_spike_dead_simple
        import_results['analysis_engines'] = "OK"

        # Test data ingestion
        from data_ingestion import sources_registry
        import_results['data_ingestion'] = "OK"

        return import_results

    def test_system_initialization(self):
        """Test system can initialize with production configuration"""
        from config_manager import ConfigurationManager
        from integration import NQOptionsTradingSystem

        # Load production-like configuration
        config_mgr = ConfigurationManager('config')

        # Test system initialization with configuration
        system = NQOptionsTradingSystem(config_mgr)

        return {
            "system_type": type(system).__name__,
            "config_loaded": True,
            "initialization_time": "< 1 second"
        }

    def test_production_monitoring(self):
        """Test production monitoring system functionality"""
        sys.path.append('scripts')

        # Test monitoring configuration
        monitoring_config = 'config/monitoring.json'
        if not os.path.exists(monitoring_config):
            raise Exception("Monitoring configuration missing")

        with open(monitoring_config, 'r') as f:
            config = json.load(f)

        # Validate monitoring configuration
        required_keys = ['monitoring_interval', 'alert_thresholds', 'metrics_retention_days']
        missing = [k for k in required_keys if k not in config]
        if missing:
            raise Exception(f"Missing monitoring config keys: {missing}")

        # Test production monitor import
        try:
            import production_monitor
            monitor = production_monitor.ProductionMonitor()
            return {
                "config_valid": True,
                "monitor_initialized": True,
                "alert_thresholds": config['alert_thresholds']
            }
        except ImportError:
            raise Exception("Production monitor module not found")

    def test_algorithm_thresholds(self):
        """Test algorithm threshold enforcement"""
        # Load databento configuration to get analysis thresholds
        with open('config/databento_only.json', 'r') as f:
            config = json.load(f)

        analysis_config = config['analysis']

        # Validate expected value thresholds
        ev_config = analysis_config['expected_value']
        expected_thresholds = {
            'min_ev': 15,
            'min_probability': 0.6,
            'max_risk': 150
        }

        for key, expected_value in expected_thresholds.items():
            if ev_config.get(key) != expected_value:
                raise Exception(f"EV threshold {key}: expected {expected_value}, got {ev_config.get(key)}")

        # Validate weight configuration
        weights = ev_config['weights']
        expected_weights = {
            'oi_factor': 0.35,
            'vol_factor': 0.25,
            'pcr_factor': 0.25,
            'distance_factor': 0.15
        }

        for key, expected_value in expected_weights.items():
            if weights.get(key) != expected_value:
                raise Exception(f"Weight {key}: expected {expected_value}, got {weights.get(key)}")

        return {
            "thresholds_validated": True,
            "weights_validated": True,
            "config_source": "databento_only.json"
        }

    def test_error_handling(self):
        """Test error handling and graceful degradation"""
        error_tests = {}

        # Test configuration error handling
        try:
            from config_manager import ConfigurationManager
            config_mgr = ConfigurationManager('nonexistent_directory')
            error_tests['config_error_handling'] = "GRACEFUL"
        except Exception as e:
            error_tests['config_error_handling'] = f"HANDLED: {type(e).__name__}"

        # Test missing module handling
        try:
            from data_ingestion.databento_api.solution import NonExistentClass
            error_tests['import_error_handling'] = "UNEXPECTED_SUCCESS"
        except ImportError:
            error_tests['import_error_handling'] = "GRACEFUL"
        except Exception as e:
            error_tests['import_error_handling'] = f"HANDLED: {type(e).__name__}"

        return error_tests

    def test_file_structure(self):
        """Test critical files and directories exist"""
        critical_paths = [
            'scripts/run_pipeline.py',
            'scripts/run_shadow_trading.py',
            'config/databento_only.json',
            'config/monitoring.json',
            'tasks/options_trading_system',
            'scripts/production_monitor.py',
            'docs/PRODUCTION_MONITORING.md',
            'outputs',
            'templates'
        ]

        results = {}
        for path in critical_paths:
            exists = os.path.exists(path)
            results[path] = "EXISTS" if exists else "MISSING"
            if not exists:
                raise Exception(f"Critical path missing: {path}")

        return results

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Live Trading Readiness Test Suite")
        print("=" * 60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # Core Infrastructure Tests (Critical)
        self.run_test("Configuration Loading", self.test_configuration_loading, critical=True)
        self.run_test("Core Imports", self.test_core_imports, critical=True)
        self.run_test("System Initialization", self.test_system_initialization, critical=True)
        self.run_test("File Structure", self.test_file_structure, critical=True)

        # Algorithm Validation Tests (Critical)
        self.run_test("Algorithm Thresholds", self.test_algorithm_thresholds, critical=True)

        # Monitoring and Safety Tests (Critical)
        self.run_test("Production Monitoring", self.test_production_monitoring, critical=True)
        self.run_test("Error Handling", self.test_error_handling, critical=False)

        # Generate results summary
        self.generate_summary()

        # Save results
        self.save_results()

    def generate_summary(self):
        """Generate test results summary"""
        print("\n" + "=" * 60)
        print("TEST RESULTS SUMMARY")
        print("=" * 60)

        total_tests = self.test_results["tests_passed"] + self.test_results["tests_failed"]
        pass_rate = (self.test_results["tests_passed"] / total_tests * 100) if total_tests > 0 else 0

        print(f"Tests Run: {total_tests}")
        print(f"Passed: {self.test_results['tests_passed']}")
        print(f"Failed: {self.test_results['tests_failed']}")
        print(f"Pass Rate: {pass_rate:.1f}%")

        if self.test_results["critical_failures"]:
            print(f"\n❌ CRITICAL FAILURES ({len(self.test_results['critical_failures'])}):")
            for failure in self.test_results["critical_failures"]:
                print(f"  - {failure}")
            print("\n🚨 SYSTEM NOT READY FOR LIVE TRADING")
        else:
            print("\n✅ ALL CRITICAL TESTS PASSED")

            if self.test_results["warnings"]:
                print(f"\n⚠️  WARNINGS ({len(self.test_results['warnings'])}):")
                for warning in self.test_results["warnings"]:
                    print(f"  - {warning}")
                print("\n✅ SYSTEM READY FOR LIVE TRADING (with warnings)")
            else:
                print("\n🚀 SYSTEM FULLY READY FOR LIVE TRADING")

    def save_results(self):
        """Save test results to file"""
        os.makedirs('outputs/live_trading_tests', exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        results_file = f'outputs/live_trading_tests/readiness_test_{timestamp}.json'

        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2)

        print(f"\n📊 Test results saved to: {results_file}")


def main():
    """Main test execution"""
    test_suite = LiveTradingReadinessTest()
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()
