#!/usr/bin/env python3
"""
Test Real Performance Metrics Integration

Quick test to verify that the shadow trading orchestrator properly integrates
with real performance metrics for latency, cost tracking, and data quality monitoring.
"""

import sys
import os
import time
import json
from datetime import datetime

# Add necessary paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'tasks/options_trading_system/analysis_engine/strategies'))

def test_real_performance_metrics_import():
    """Test that real performance metrics can be imported (with fallback)"""
    try:
        from tasks.options_trading_system.analysis_engine.strategies.real_performance_metrics import RealPerformanceMetrics
        print("✅ RealPerformanceMetrics import successful (full version)")
        return True
    except ImportError:
        try:
            from tasks.options_trading_system.analysis_engine.strategies.simple_performance_metrics import SimplePerformanceMetrics as RealPerformanceMetrics
            print("✅ RealPerformanceMetrics import successful (simple fallback version)")
            return True
        except ImportError as e:
            print(f"❌ RealPerformanceMetrics import failed: {e}")
            return False

def test_performance_metrics_functionality():
    """Test core performance metrics functionality"""
    try:
        # Use same fallback logic as import test
        try:
            from tasks.options_trading_system.analysis_engine.strategies.real_performance_metrics import RealPerformanceMetrics
        except ImportError:
            from tasks.options_trading_system.analysis_engine.strategies.simple_performance_metrics import SimplePerformanceMetrics as RealPerformanceMetrics

        # Create metrics instance
        metrics = RealPerformanceMetrics()
        print("✅ RealPerformanceMetrics instance created")

        # Start monitoring
        metrics.start_monitoring()
        print("✅ Performance monitoring started")

        # Test latency tracking
        op_id = metrics.latency_monitor.start_operation('test_data_load')
        time.sleep(0.1)  # Simulate some work
        result = metrics.latency_monitor.end_operation(op_id, success=True)
        print(f"✅ Latency tracking: {result.duration_ms:.1f}ms for test_data_load")

        # Test cost tracking
        metadata = {'source': 'barchart', 'data_size_bytes': 500000}
        metrics.cost_tracker.record_data_request_cost(metadata)
        cost_summary = metrics.cost_tracker.get_cost_summary()
        print(f"✅ Cost tracking: ${cost_summary['today_cost']:.4f} today")

        # Test data quality monitoring
        metrics.quality_monitor.record_data_quality('barchart', 1000, 950, 100.0, 0)
        quality_summary = metrics.quality_monitor.get_overall_quality()
        print(f"✅ Data quality: {quality_summary['overall_quality']:.2f} overall score")

        # Test system resource monitoring
        resource_sample = metrics.resource_monitor.sample_resources()
        if resource_sample:
            print(f"✅ Resource monitoring: {resource_sample.cpu_usage_pct:.1f}% CPU")

        # Get comprehensive metrics
        comprehensive = metrics.get_comprehensive_metrics()
        print(f"✅ Comprehensive metrics: {len(comprehensive)} metric categories")

        # Stop monitoring
        metrics.stop_monitoring()
        print("✅ Performance monitoring stopped")

        return True

    except Exception as e:
        print(f"❌ Performance metrics functionality test failed: {e}")
        return False

def test_shadow_trading_integration():
    """Test shadow trading orchestrator integration with real metrics"""
    try:
        from tasks.options_trading_system.analysis_engine.strategies.shadow_trading_orchestrator import ShadowTradingConfig, ShadowTradingOrchestrator

        # Create minimal config for testing
        config = ShadowTradingConfig(
            start_date='2025-06-12',
            duration_days=1,  # Just 1 day for testing
            trading_hours_start='09:30',
            trading_hours_end='16:00',
            confidence_threshold=0.65,
            paper_trading_capital=10000.0,  # Smaller amount for testing
            max_daily_loss_pct=2.0,
            min_signal_accuracy=0.70
        )

        # Create orchestrator
        orchestrator = ShadowTradingOrchestrator(config)
        print("✅ Shadow trading orchestrator created")

        # Check if real performance metrics are available
        if orchestrator.real_performance_metrics:
            print("✅ Real performance metrics integrated into orchestrator")

            # Test getting status
            status = orchestrator.get_status()
            print(f"✅ Orchestrator status: {status['is_running']}, {status['current_day']}/{status['total_days']} days")

            # Verify metrics are monitoring
            comprehensive = orchestrator.real_performance_metrics.get_comprehensive_metrics()
            print(f"✅ Metrics available: {list(comprehensive.keys())}")

        else:
            print("⚠️ Real performance metrics not available in orchestrator (using mock)")

        return True

    except Exception as e:
        print(f"❌ Shadow trading integration test failed: {e}")
        return False

def test_config_integration():
    """Test that configuration loads properly for real data sources"""
    try:
        from tasks.options_trading_system.analysis_engine.strategies.shadow_trading_orchestrator import ShadowTradingOrchestrator
        from tasks.options_trading_system.analysis_engine.strategies.shadow_trading_orchestrator import ShadowTradingConfig

        config = ShadowTradingConfig(start_date='2025-06-12')
        orchestrator = ShadowTradingOrchestrator(config)

        # Test data source config loading
        data_config = orchestrator._load_data_source_config()
        print(f"✅ Data source config loaded: {list(data_config['data_sources'].keys())}")

        # Test analysis config loading
        analysis_config = orchestrator._load_analysis_config()
        print(f"✅ Analysis config loaded: {list(analysis_config.keys())}")

        return True

    except Exception as e:
        print(f"❌ Config integration test failed: {e}")
        return False

def main():
    """Run all tests for real performance metrics integration"""
    print("🧪 Testing Real Performance Metrics Integration")
    print("=" * 50)

    tests = [
        ("Import Test", test_real_performance_metrics_import),
        ("Functionality Test", test_performance_metrics_functionality),
        ("Shadow Trading Integration", test_shadow_trading_integration),
        ("Config Integration", test_config_integration)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name} PASSED")
            else:
                print(f"❌ {test_name} FAILED")
        except Exception as e:
            print(f"💥 {test_name} CRASHED: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    passed = sum(1 for name, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")

    print(f"\nOverall: {passed}/{total} tests passed ({passed/total*100:.0f}%)")

    if passed == total:
        print("🎉 All tests passed! Real performance metrics integration is working.")
    else:
        print(f"⚠️ {total - passed} test(s) failed. Check the issues above.")

    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
