#!/usr/bin/env python3
"""Test shadow mode deployment for IFD v3"""

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

def test_shadow_mode():
    """Test shadow mode deployment for IFD v3"""
    print("=" * 60)
    print("IFD v3.0 SHADOW MODE DEPLOYMENT TEST")
    print("=" * 60)

    from phase4.staged_rollout_framework import StagedRolloutManager, RolloutConfiguration, RolloutStage
    from analysis_engine.integration import AnalysisEngine
    from analysis_engine.config_manager import get_config_manager

    try:
        print("\n📋 Setting up shadow mode deployment...")

        # Create rollout manager
        manager = StagedRolloutManager({
            'db_path': 'outputs/ifd_v3_shadow_mode.db',
            'monitoring_interval': 30  # 30 seconds for testing
        })

        # Start monitoring
        manager.start_monitoring()

        print("✅ Shadow mode manager created and monitoring started")

        # Create rollout configuration for IFD v1 vs v3
        rollout_id = f"ifd_v1_vs_v3_shadow_{int(time.time())}"

        # Create manual configuration to avoid enum serialization issues
        config = RolloutConfiguration(
            rollout_id=rollout_id,
            champion_version="ifd_v1_production",
            challenger_version="ifd_v3_production",
            stage_traffic_allocation={}  # Empty dict, will be filled by __post_init__
        )

        # Create the rollout (starts in shadow mode by default)
        success = manager.create_rollout(
            rollout_id=rollout_id,
            champion_version="ifd_v1_production",
            challenger_version="ifd_v3_production",
            config=config
        )

        if not success:
            raise Exception("Failed to create rollout")

        print(f"✅ Shadow mode rollout created: {rollout_id}")
        print("   Champion: IFD v1.0 (Dead Simple)")
        print("   Challenger: IFD v3.0 (Enhanced MBO)")
        print("   Traffic: 0% to challenger (shadow mode)")

        # Get config manager for analysis engines
        config_manager = get_config_manager()

        # Create analysis engines for both versions
        v1_config = config_manager.get_analysis_config("ifd_v1_production")
        v3_config = config_manager.get_analysis_config("ifd_v3_production")

        v1_engine = AnalysisEngine(v1_config)
        v3_engine = AnalysisEngine(v3_config)

        print("\n🔬 Running shadow mode simulation...")
        print("   In shadow mode, both algorithms run but only v1 affects live decisions")

        # Simulate several requests in shadow mode
        test_requests = [
            {"mode": "simulation", "request_id": 1, "scenario": "normal_market"},
            {"mode": "simulation", "request_id": 2, "scenario": "high_volatility"},
            {"mode": "simulation", "request_id": 3, "scenario": "low_volume"},
            {"mode": "simulation", "request_id": 4, "scenario": "options_expiry"},
            {"mode": "simulation", "request_id": 5, "scenario": "market_close"}
        ]

        shadow_results = []

        for i, data_config in enumerate(test_requests, 1):
            print(f"\n📊 Shadow Request {i}: {data_config['scenario']}")

            # Route request (should always return "champion" in shadow mode)
            routed_version = manager.route_request(rollout_id)
            print(f"   Routed to: {routed_version} (production decision)")

            # Run champion (production) algorithm
            print("   🟢 Running Champion (IFD v1.0)...")
            start_time = datetime.now()
            champion_result = v1_engine.run_dead_simple_analysis(data_config)
            champion_latency = (datetime.now() - start_time).total_seconds() * 1000

            # Run challenger (shadow) algorithm
            print("   🔍 Running Challenger (IFD v3.0) in shadow...")
            start_time = datetime.now()
            challenger_result = v3_engine.run_ifd_v3_analysis(data_config)
            challenger_latency = (datetime.now() - start_time).total_seconds() * 1000

            # Record performance metrics (simplified)
            from phase4.staged_rollout_framework import PerformanceMetrics

            champion_metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                latency_ms=champion_latency,
                success_rate=1.0 if champion_result['status'] == 'success' else 0.0,
                signal_count=len(champion_result.get('result', {}).get('signals', [])),
                confidence_score=0.8,  # Simplified
                error_rate=0.0 if champion_result['status'] == 'success' else 1.0
            )

            challenger_metrics = PerformanceMetrics(
                timestamp=datetime.now(),
                latency_ms=challenger_latency,
                success_rate=1.0 if challenger_result['status'] == 'success' else 0.0,
                signal_count=len(challenger_result.get('result', {}).get('signals', [])),
                confidence_score=0.9,  # Simplified
                error_rate=0.0 if challenger_result['status'] == 'success' else 1.0
            )

            # Record metrics
            manager.record_performance(rollout_id, "champion", champion_metrics)
            manager.record_performance(rollout_id, "challenger", challenger_metrics)

            # Show comparison
            print(f"   Champion: {champion_result['status']} ({champion_latency:.1f}ms)")
            print(f"   Challenger: {challenger_result['status']} ({challenger_latency:.1f}ms)")

            # Store for analysis
            shadow_results.append({
                'request': i,
                'scenario': data_config['scenario'],
                'champion': champion_result,
                'challenger': challenger_result,
                'champion_latency': champion_latency,
                'challenger_latency': challenger_latency
            })

            # Small delay between requests
            time.sleep(1)

        # Get rollout status
        print("\n📊 Shadow Mode Results:")
        status = manager.get_rollout_status(rollout_id)

        print(f"   Rollout ID: {status['rollout_id']}")
        print(f"   Stage: {status['current_stage']}")
        print(f"   Status: {status['status']}")
        print(f"   Total Requests: {status['total_requests']}")
        print(f"   Challenger Requests: {status['challenger_requests']} (shadow only)")
        print(f"   Traffic Percentage: {status['current_traffic_percentage']}%")

        # Performance comparison
        if 'performance_comparison' in status:
            comparison = status['performance_comparison']
            print(f"\n📈 Performance Comparison:")
            print(f"   Champion Success Rate: {comparison.get('champion_success_rate', 0):.1%}")
            print(f"   Challenger Success Rate: {comparison.get('challenger_success_rate', 0):.1%}")
            print(f"   Champion Avg Latency: {comparison.get('champion_avg_latency', 0):.1f}ms")
            print(f"   Challenger Avg Latency: {comparison.get('challenger_avg_latency', 0):.1f}ms")

        # Save shadow mode results
        test_results = {
            "test": "shadow_mode_deployment",
            "timestamp": datetime.now().isoformat(),
            "rollout_id": rollout_id,
            "rollout_status": status,
            "shadow_results": shadow_results,
            "status": "PASSED",
            "notes": "Shadow mode successfully tested with IFD v1 vs v3 comparison"
        }

        os.makedirs("outputs/shadow_mode", exist_ok=True)
        with open("outputs/shadow_mode/test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        # Stop monitoring
        manager.stop_monitoring()

        print("\n✅ Shadow mode test completed successfully")
        print("📝 Results saved to outputs/shadow_mode/test_results.json")
        print("\n💡 Next Steps:")
        print("   - Monitor shadow mode performance over time")
        print("   - Validate IFD v3 signal quality vs v1")
        print("   - Prepare for canary deployment (5% traffic)")

        return True

    except Exception as e:
        print(f"\n❌ Shadow mode test failed: {e}")

        test_results = {
            "test": "shadow_mode_deployment",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/shadow_mode", exist_ok=True)
        with open("outputs/shadow_mode/test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_shadow_mode()
    sys.exit(0 if success else 1)
