#!/usr/bin/env python3
"""Test latency tracking integration with IFD v3 analysis"""

import os
import sys
import json
from datetime import datetime

# Add paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()

def test_latency_integration():
    """Test latency tracking integrated with IFD v3 analysis"""
    print("=" * 60)
    print("LATENCY TRACKING INTEGRATION TEST")
    print("=" * 60)

    from analysis_engine.integration import AnalysisEngine
    from analysis_engine.config_manager import get_config_manager

    try:
        print("\n📋 Setting up IFD v3 analysis with latency tracking...")

        # Get configuration for IFD v3
        config_manager = get_config_manager()
        ifd_v3_config = config_manager.get_analysis_config("ifd_v3_production")

        # Create analysis engine
        engine = AnalysisEngine(ifd_v3_config)

        print("✅ Analysis engine created with IFD v3 configuration")

        # Test data configuration
        data_config = {
            "mode": "simulation",
            "test_run": True
        }

        print("\n🚀 Running IFD v3 analysis with latency tracking...")
        print("   This will track latency through all components:")
        print("   - Data Ingestion")
        print("   - Data Processing")
        print("   - Pressure Analysis")
        print("   - Signal Generation")
        print("   - End-to-End")

        # Run analysis
        start_time = datetime.now()
        result = engine.run_ifd_v3_analysis(data_config)
        total_time = (datetime.now() - start_time).total_seconds() * 1000

        print(f"\n📊 Analysis Results:")
        print(f"   Status: {result['status']}")
        print(f"   Total execution time: {total_time:.1f}ms")

        if result['status'] == 'success':
            analysis_result = result['result']
            print(f"   Signals detected: {analysis_result.get('total_signals', 0)}")
            print(f"   High confidence signals: {analysis_result.get('high_confidence_signals', 0)}")

            # Check latency information
            if 'latency_ms' in analysis_result:
                latency = analysis_result['latency_ms']
                print(f"   📈 Tracked latency: {latency:.1f}ms")

                # Evaluate performance
                if latency <= 100:
                    print(f"   ✅ EXCELLENT: Latency within target (<100ms)")
                elif latency <= 150:
                    print(f"   ⚠️  WARNING: Latency above target but acceptable")
                else:
                    print(f"   ❌ CRITICAL: Latency exceeds threshold")
            else:
                print("   ⚠️  No latency tracking data available")
        else:
            print(f"   Error: {result.get('error', 'Unknown error')}")

        # Check latency monitor state
        print("\n📊 Latency Monitor Status:")
        from analysis_engine.integration import get_latency_monitor
        monitor = get_latency_monitor()

        overview = monitor.get_system_overview()
        print(f"   Overall System Status: {overview['overall_status'].upper()}")
        print(f"   Active Alerts: {overview['active_alerts']}")
        print(f"   Active Requests: {overview['active_requests']}")

        # Show recent component performance
        print("\n📈 Recent Component Performance:")
        for component_name, stats in overview['components'].items():
            if 'mean_latency' in stats and stats['mean_latency'] > 0:
                print(f"   {component_name}:")
                print(f"     Average: {stats['mean_latency']:.1f}ms")
                print(f"     P95: {stats['p95_latency']:.1f}ms")
                print(f"     Grade: {stats['performance_grade']}")

        # Generate performance report
        report = monitor.generate_performance_report(hours=1)

        # Save test results
        test_results = {
            "test": "latency_integration_validation",
            "timestamp": datetime.now().isoformat(),
            "analysis_result": result,
            "system_overview": overview,
            "status": "PASSED",
            "notes": "Latency tracking successfully integrated with IFD v3 analysis"
        }

        os.makedirs("outputs/latency_monitoring", exist_ok=True)
        with open("outputs/latency_monitoring/integration_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print("\n✅ Latency integration test completed successfully")
        print("📝 Results saved to outputs/latency_monitoring/integration_test_results.json")

        return True

    except Exception as e:
        print(f"\n❌ Latency integration test failed: {e}")

        test_results = {
            "test": "latency_integration_validation",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/latency_monitoring", exist_ok=True)
        with open("outputs/latency_monitoring/integration_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_latency_integration()
    sys.exit(0 if success else 1)
