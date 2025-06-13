#!/usr/bin/env python3
"""Test the latency monitoring system for IFD v3"""

import os
import sys
import json
import time
from datetime import datetime

# Add paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()

def test_latency_monitor():
    """Test the latency monitoring system"""
    print("=" * 60)
    print("LATENCY MONITORING SYSTEM TEST")
    print("=" * 60)

    from phase4.latency_monitor import create_latency_monitor, LatencyComponent

    try:
        print("\n📋 Creating latency monitor...")

        # Create monitor with configuration
        config = {
            'db_path': 'outputs/ifd_v3_latency.db',
            'analysis': {
                'target_latency': 100.0,    # <100ms target for IFD v3
                'warning_latency': 80.0,    # 80ms warning
                'critical_latency': 150.0,  # 150ms critical
                'severe_latency': 300.0,    # 300ms severe
                'min_sample_size': 5,       # Lower for testing
                'trend_window_hours': 1
            }
        }

        monitor = create_latency_monitor(config)

        # Set up alert callback
        alerts_received = []
        def on_alert(alert):
            alerts_received.append(alert)
            print(f"\n🚨 ALERT: {alert.component.value} latency {alert.current_latency:.1f}ms > {alert.threshold_value}ms")

        monitor.on_threshold_breach = on_alert

        # Start monitoring
        monitor.start_monitoring()
        print("✅ Latency monitor started successfully")

        print("\n🔬 Testing IFD v3 pipeline latency tracking...")

        # Simulate IFD v3 processing with realistic timings
        test_scenarios = [
            ("Fast processing (under target)", [5, 15, 10, 8, 5]),  # Total: 43ms
            ("Normal processing (near target)", [10, 30, 15, 12, 8]),  # Total: 75ms
            ("Slow processing (over target)", [20, 50, 25, 20, 15]),  # Total: 130ms
            ("Critical latency", [30, 80, 40, 30, 25]),  # Total: 205ms
        ]

        for scenario_name, component_delays in test_scenarios:
            print(f"\n📊 {scenario_name}:")

            request_id = f"ifd_v3_test_{int(time.time() * 1000)}"

            # Start tracking
            monitor.track_request(request_id, {
                'scenario': scenario_name,
                'test_type': 'ifd_v3_latency'
            })

            # Simulate processing through IFD v3 components
            components = [
                (LatencyComponent.DATA_INGESTION, component_delays[0]),
                (LatencyComponent.PRESSURE_ANALYSIS, component_delays[1]),
                (LatencyComponent.BASELINE_LOOKUP, component_delays[2]),
                (LatencyComponent.MARKET_MAKING_DETECTION, component_delays[3]),
                (LatencyComponent.SIGNAL_GENERATION, component_delays[4])
            ]

            for component, delay_ms in components:
                time.sleep(delay_ms / 1000.0)  # Convert to seconds
                latency = monitor.checkpoint(request_id, component)
                print(f"   {component.value}: {latency:.1f}ms")

            # Finish tracking
            measurements = monitor.finish_request(request_id)

            # Find end-to-end measurement
            e2e_measurements = [m for m in measurements if m.component == LatencyComponent.END_TO_END]
            if e2e_measurements:
                e2e_latency = e2e_measurements[0].latency_ms
                print(f"   📈 End-to-End: {e2e_latency:.1f}ms")

                if e2e_latency <= 100:
                    print(f"   ✅ PASSED: Within target (<100ms)")
                elif e2e_latency <= 150:
                    print(f"   ⚠️  WARNING: Above target but acceptable")
                else:
                    print(f"   ❌ FAILED: Exceeds critical threshold")

            # Small delay between scenarios
            time.sleep(0.5)

        # Wait for monitoring to process
        time.sleep(2)

        # Get system overview
        print("\n📊 System Performance Overview:")
        overview = monitor.get_system_overview()

        print(f"\n  Overall Status: {overview['overall_status'].upper()}")
        print(f"  Active Alerts: {overview['active_alerts']}")
        print(f"  Active Requests: {overview['active_requests']}")

        # Show component statistics
        print("\n  Component Performance:")
        for component_name, stats in overview['components'].items():
            if 'mean_latency' in stats:
                print(f"    {component_name}:")
                print(f"      Mean: {stats['mean_latency']:.1f}ms")
                print(f"      P95: {stats['p95_latency']:.1f}ms")
                print(f"      SLA: {stats['sla_compliance']:.1f}%")
                print(f"      Grade: {stats['performance_grade']}")

        # Generate performance report
        report = monitor.generate_performance_report(hours=1)

        if report.get('summary'):
            print(f"\n📊 Performance Summary:")
            summary = report['summary']
            print(f"  Overall Mean Latency: {summary.get('overall_mean_latency', 0):.1f}ms")
            print(f"  Overall P95 Latency: {summary.get('overall_p95_latency', 0):.1f}ms")
            print(f"  SLA Compliance: {summary.get('overall_sla_compliance', 0):.1f}%")
            print(f"  Performance Grade: {summary.get('overall_performance_grade', 'N/A')}")

        # Check alerts
        if alerts_received:
            print(f"\n🚨 Alerts Received: {len(alerts_received)}")
            for alert in alerts_received[:3]:  # Show first 3
                print(f"  - {alert.component.value}: {alert.current_latency:.1f}ms ({alert.severity})")

        # Stop monitoring
        monitor.stop_monitoring()

        # Save test results
        test_results = {
            "test": "latency_monitor_validation",
            "timestamp": datetime.now().isoformat(),
            "status": "PASSED",
            "overview": overview,
            "alerts_count": len(alerts_received),
            "notes": "Latency monitoring system validated for IFD v3"
        }

        os.makedirs("outputs/latency_monitoring", exist_ok=True)
        with open("outputs/latency_monitoring/test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print("\n✅ Latency monitoring test completed successfully")
        print("📝 Results saved to outputs/latency_monitoring/test_results.json")

        return True

    except Exception as e:
        print(f"\n❌ Latency monitor test failed: {e}")

        test_results = {
            "test": "latency_monitor_validation",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/latency_monitoring", exist_ok=True)
        with open("outputs/latency_monitoring/test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_latency_monitor()
    sys.exit(0 if success else 1)
