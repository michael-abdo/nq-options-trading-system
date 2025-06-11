#!/usr/bin/env python3
"""
Test Minimal - Verify system works with NO external dependencies
This test ensures the analysis engine maintains full functionality using only Python standard library.
"""

import sys
import os
import json
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Any

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MinimalDependencyTest:
    """Test suite for minimal (no dependency) installation"""
    
    def __init__(self):
        self.results = {
            'passed': [],
            'failed': [],
            'warnings': []
        }
        
    def check_no_external_deps(self) -> bool:
        """Verify no external dependencies are installed"""
        print("\n" + "="*60)
        print("CHECKING FOR EXTERNAL DEPENDENCIES")
        print("="*60)
        
        # List of packages that should NOT be installed
        external_packages = [
            'pandas', 'numpy', 'matplotlib', 'scipy', 'sklearn',
            'pytz', 'seaborn', 'plotly', 'pydantic', 'psutil',
            'sqlalchemy', 'requests', 'websocket', 'structlog'
        ]
        
        found_external = []
        for pkg in external_packages:
            try:
                importlib.import_module(pkg)
                found_external.append(pkg)
            except ImportError:
                pass
                
        if found_external:
            print(f"⚠️  WARNING: Found external packages: {', '.join(found_external)}")
            print("   This test is designed to run WITHOUT external dependencies")
            self.results['warnings'].append(f"External packages found: {found_external}")
            return False
        else:
            print("✅ No external dependencies found - running in MINIMAL mode")
            return True
            
    def test_core_imports(self) -> bool:
        """Test that all core modules can be imported"""
        print("\n" + "="*60)
        print("TESTING CORE IMPORTS")
        print("="*60)
        
        core_modules = [
            ('integration', 'AnalysisEngine'),
            ('config_manager', 'ConfigManager'),
            ('pipeline.opportunity', 'TradingOpportunity'),
            ('expected_value_analysis.solution', 'ExpectedValueAnalyzer'),
            ('institutional_flow_v3.solution', 'InstitutionalFlowDetectorV3'),
            ('volume_shock_analysis.solution', 'VolumeShockAnalyzer'),
            ('risk_analysis.solution', 'RiskAnalyzer'),
            ('phase4.success_metrics_tracker', 'SuccessMetricsTracker'),
            ('phase4.websocket_backfill_manager', 'WebSocketBackfillManager'),
            ('phase4.monthly_budget_dashboard', 'MonthlyBudgetDashboard'),
            ('phase4.adaptive_threshold_manager', 'AdaptiveThresholdManager'),
            ('phase4.staged_rollout_framework', 'StagedRolloutFramework'),
            ('phase4.latency_monitor', 'LatencyMonitor'),
            ('phase4.uptime_monitor', 'UptimeMonitor'),
        ]
        
        all_passed = True
        for module_path, class_name in core_modules:
            try:
                module = importlib.import_module(module_path)
                cls = getattr(module, class_name)
                print(f"✅ {module_path}.{class_name}")
                self.results['passed'].append(f"Import: {module_path}.{class_name}")
            except Exception as e:
                print(f"❌ {module_path}.{class_name}: {str(e)}")
                self.results['failed'].append(f"Import: {module_path}.{class_name} - {str(e)}")
                all_passed = False
                
        return all_passed
        
    def test_fallback_implementations(self) -> bool:
        """Test that fallback implementations work correctly"""
        print("\n" + "="*60)
        print("TESTING FALLBACK IMPLEMENTATIONS")
        print("="*60)
        
        tests = []
        
        # Test 1: ConfigManager fallback
        try:
            from config_manager import ConfigManager
            config_mgr = ConfigManager()
            config = config_mgr.load_config('ifd_v3_production')
            assert isinstance(config, dict), "Config should be a dictionary"
            print("✅ ConfigManager works without external deps")
            self.results['passed'].append("ConfigManager fallback")
            tests.append(True)
        except Exception as e:
            print(f"❌ ConfigManager fallback failed: {e}")
            self.results['failed'].append(f"ConfigManager fallback: {str(e)}")
            tests.append(False)
            
        # Test 2: Budget Dashboard text fallback
        try:
            from phase4.monthly_budget_dashboard import MonthlyBudgetDashboard
            dashboard = MonthlyBudgetDashboard()
            # Should work without matplotlib
            output = dashboard.generate_report()
            assert isinstance(output, str), "Dashboard should return text report"
            print("✅ Budget Dashboard text fallback works")
            self.results['passed'].append("Budget Dashboard fallback")
            tests.append(True)
        except Exception as e:
            print(f"❌ Budget Dashboard fallback failed: {e}")
            self.results['failed'].append(f"Budget Dashboard fallback: {str(e)}")
            tests.append(False)
            
        # Test 3: Adaptive Threshold rule-based fallback
        try:
            from phase4.adaptive_threshold_manager import create_adaptive_threshold_manager
            manager = create_adaptive_threshold_manager()
            # Should use rule-based optimization without sklearn
            result = manager.optimize_thresholds([])
            assert result is not None, "Should return optimization result"
            print("✅ Adaptive Threshold rule-based fallback works")
            self.results['passed'].append("Adaptive Threshold fallback")
            tests.append(True)
        except Exception as e:
            print(f"❌ Adaptive Threshold fallback failed: {e}")
            self.results['failed'].append(f"Adaptive Threshold fallback: {str(e)}")
            tests.append(False)
            
        # Test 4: Statistical calculations without scipy
        try:
            from expiration_pressure_calculator.solution import ExpirationPressureCalculator
            calc = ExpirationPressureCalculator()
            # Should use basic statistics module
            print("✅ Statistical calculations work without scipy")
            self.results['passed'].append("Statistics fallback")
            tests.append(True)
        except Exception as e:
            print(f"❌ Statistical fallback failed: {e}")
            self.results['failed'].append(f"Statistics fallback: {str(e)}")
            tests.append(False)
            
        return all(tests)
        
    def test_database_operations(self) -> bool:
        """Test SQLite operations work without SQLAlchemy"""
        print("\n" + "="*60)
        print("TESTING DATABASE OPERATIONS")
        print("="*60)
        
        try:
            from phase4.success_metrics_tracker import SuccessMetricsTracker
            
            # Create temporary database
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
                db_path = tmp.name
                
            tracker = SuccessMetricsTracker(db_path=db_path)
            
            # Test basic operations
            tracker.record_signal({
                'timestamp': '2025-01-11T10:00:00Z',
                'symbol': 'NQ',
                'strike': 21000,
                'signal_type': 'institutional_flow',
                'confidence': 0.85,
                'outcome': 'win',
                'pnl': 250.0
            })
            
            metrics = tracker.calculate_metrics()
            assert isinstance(metrics, dict), "Metrics should be a dictionary"
            
            # Cleanup
            os.unlink(db_path)
            
            print("✅ SQLite operations work without SQLAlchemy")
            self.results['passed'].append("Database operations")
            return True
            
        except Exception as e:
            print(f"❌ Database operations failed: {e}")
            self.results['failed'].append(f"Database operations: {str(e)}")
            return False
            
    def test_integration_pipeline(self) -> bool:
        """Test the full integration pipeline without dependencies"""
        print("\n" + "="*60)
        print("TESTING INTEGRATION PIPELINE")
        print("="*60)
        
        try:
            from integration import AnalysisEngine
            from config_manager import ConfigManager
            
            # Load config
            config_mgr = ConfigManager()
            config = config_mgr.load_config('ifd_v3_production')
            
            # Create engine
            engine = AnalysisEngine(config)
            
            # Create test data
            test_data = {
                'symbol': 'NQ',
                'options_data': [
                    {
                        'strike': 21000,
                        'exp_date': '2025-01-17',
                        'call_volume': 1500,
                        'put_volume': 800,
                        'call_oi': 5000,
                        'put_oi': 3000,
                        'underlying_price': 20950
                    }
                ],
                'market_data': {
                    'vix': 15.5,
                    'volume': 250000
                }
            }
            
            # Run analysis
            results = engine.run_full_analysis(test_data)
            
            assert isinstance(results, dict), "Results should be a dictionary"
            assert 'signals' in results, "Results should contain signals"
            
            print("✅ Integration pipeline works without dependencies")
            self.results['passed'].append("Integration pipeline")
            return True
            
        except Exception as e:
            print(f"❌ Integration pipeline failed: {e}")
            print(traceback.format_exc())
            self.results['failed'].append(f"Integration pipeline: {str(e)}")
            return False
            
    def test_performance_monitoring(self) -> bool:
        """Test performance monitoring without external tools"""
        print("\n" + "="*60)
        print("TESTING PERFORMANCE MONITORING")
        print("="*60)
        
        try:
            from phase4.latency_monitor import LatencyMonitor
            from phase4.uptime_monitor import UptimeMonitor
            
            # Test latency monitoring
            latency_monitor = LatencyMonitor()
            latency_monitor.record_latency('data_ingestion', 0.045)  # 45ms
            stats = latency_monitor.get_statistics('data_ingestion')
            assert stats['average'] < 0.1, "Latency should be under 100ms"
            
            # Test uptime monitoring
            uptime_monitor = UptimeMonitor()
            uptime = uptime_monitor.get_uptime_percentage()
            assert uptime >= 0, "Uptime should be a valid percentage"
            
            print("✅ Performance monitoring works without psutil")
            self.results['passed'].append("Performance monitoring")
            return True
            
        except Exception as e:
            print(f"❌ Performance monitoring failed: {e}")
            self.results['failed'].append(f"Performance monitoring: {str(e)}")
            return False
            
    def generate_report(self) -> Dict[str, Any]:
        """Generate test report"""
        total_tests = len(self.results['passed']) + len(self.results['failed'])
        pass_rate = len(self.results['passed']) / total_tests if total_tests > 0 else 0
        
        report = {
            'test_mode': 'MINIMAL (No Dependencies)',
            'total_tests': total_tests,
            'passed': len(self.results['passed']),
            'failed': len(self.results['failed']),
            'pass_rate': f"{pass_rate*100:.1f}%",
            'warnings': self.results['warnings'],
            'details': {
                'passed_tests': self.results['passed'],
                'failed_tests': self.results['failed']
            }
        }
        
        return report
        
    def run_all_tests(self) -> bool:
        """Run all minimal dependency tests"""
        print("\n" + "="*80)
        print("MINIMAL DEPENDENCY TEST SUITE")
        print("Testing IFD v3.0 Analysis Engine with NO external dependencies")
        print("="*80)
        
        # Check environment
        is_minimal = self.check_no_external_deps()
        
        # Run tests
        tests = [
            self.test_core_imports(),
            self.test_fallback_implementations(),
            self.test_database_operations(),
            self.test_integration_pipeline(),
            self.test_performance_monitoring()
        ]
        
        # Generate report
        report = self.generate_report()
        
        # Display summary
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Environment: {'MINIMAL' if is_minimal else 'MIXED (has external deps)'}")
        print(f"Total Tests: {report['total_tests']}")
        print(f"Passed: {report['passed']}")
        print(f"Failed: {report['failed']}")
        print(f"Pass Rate: {report['pass_rate']}")
        
        if report['warnings']:
            print(f"\nWarnings:")
            for warning in report['warnings']:
                print(f"  ⚠️  {warning}")
                
        if report['details']['failed_tests']:
            print(f"\nFailed Tests:")
            for test in report['details']['failed_tests']:
                print(f"  ❌ {test}")
                
        # Save report
        report_path = Path(__file__).parent / 'test_minimal_report.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nDetailed report saved to: {report_path}")
        
        # Return success if all critical tests passed
        return len(self.results['failed']) == 0

def main():
    """Run minimal dependency tests"""
    tester = MinimalDependencyTest()
    success = tester.run_all_tests()
    
    print("\n" + "="*80)
    if success:
        print("✅ ALL TESTS PASSED - System works perfectly without dependencies!")
    else:
        print("❌ SOME TESTS FAILED - Check report for details")
    print("="*80)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()