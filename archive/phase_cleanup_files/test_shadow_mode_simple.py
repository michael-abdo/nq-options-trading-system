#!/usr/bin/env python3
"""Simple shadow mode test for IFD v3 without complex framework"""

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

def test_shadow_mode_simple():
    """Simple shadow mode test demonstrating IFD v1 vs v3 comparison"""
    print("=" * 60)
    print("IFD v3.0 SHADOW MODE - SIMPLE TEST")
    print("=" * 60)

    from analysis_engine.integration import AnalysisEngine
    from analysis_engine.config_manager import get_config_manager

    try:
        print("\n📋 Setting up shadow mode comparison...")
        print("   In shadow mode:")
        print("   - Production traffic goes to IFD v1.0 (champion)")
        print("   - IFD v3.0 runs in parallel (challenger) for comparison")
        print("   - No live trading decisions affected by v3.0")

        # Get configuration for both versions
        config_manager = get_config_manager()

        v1_config = config_manager.get_analysis_config("ifd_v1_production")
        v3_config = config_manager.get_analysis_config("ifd_v3_production")

        # Create analysis engines
        v1_engine = AnalysisEngine(v1_config)
        v3_engine = AnalysisEngine(v3_config)

        print("✅ Analysis engines created:")
        print("   🏆 Champion: IFD v1.0 (Dead Simple Volume Spike)")
        print("   🔍 Challenger: IFD v3.0 (Enhanced MBO Streaming)")

        # Shadow mode simulation scenarios
        test_scenarios = [
            {"mode": "simulation", "scenario": "normal_market", "description": "Normal market conditions"},
            {"mode": "simulation", "scenario": "high_volatility", "description": "High volatility period"},
            {"mode": "simulation", "scenario": "options_expiry", "description": "Options expiration day"},
            {"mode": "simulation", "scenario": "market_close", "description": "Market closing hour"},
            {"mode": "simulation", "scenario": "earnings_event", "description": "Post-earnings volatility"}
        ]

        shadow_results = []

        print(f"\n🔬 Running shadow mode analysis on {len(test_scenarios)} scenarios...")

        for i, data_config in enumerate(test_scenarios, 1):
            print(f"\n📊 Scenario {i}: {data_config['description']}")

            # Champion (production) - this would affect live trading
            print("   🏆 Running Champion (IFD v1.0) - PRODUCTION")
            start_time = time.time()
            champion_result = v1_engine.run_dead_simple_analysis(data_config)
            champion_time = (time.time() - start_time) * 1000

            # Challenger (shadow) - this is for comparison only
            print("   🔍 Running Challenger (IFD v3.0) - SHADOW MODE")
            start_time = time.time()
            challenger_result = v3_engine.run_ifd_v3_analysis(data_config)
            challenger_time = (time.time() - start_time) * 1000

            # Extract key metrics
            champion_signals = len(champion_result.get('result', {}).get('signals', []))
            challenger_signals = len(challenger_result.get('result', {}).get('signals', []))

            champion_success = champion_result.get('status') == 'success'
            challenger_success = challenger_result.get('status') == 'success'

            # Show results
            print(f"   Results:")
            print(f"     Champion: {champion_result['status']} | {champion_signals} signals | {champion_time:.1f}ms")
            print(f"     Challenger: {challenger_result['status']} | {challenger_signals} signals | {challenger_time:.1f}ms")

            # Performance comparison
            if challenger_time < champion_time:
                print(f"     ⚡ Challenger is {champion_time - challenger_time:.1f}ms faster")
            else:
                print(f"     🐌 Challenger is {challenger_time - champion_time:.1f}ms slower")

            # Signal comparison
            if challenger_signals > champion_signals:
                print(f"     📈 Challenger detected {challenger_signals - champion_signals} more signals")
            elif challenger_signals < champion_signals:
                print(f"     📉 Challenger detected {champion_signals - challenger_signals} fewer signals")
            else:
                print(f"     ⚖️  Both detected same number of signals")

            # Store for analysis
            shadow_results.append({
                'scenario': data_config['description'],
                'champion': {
                    'status': champion_result['status'],
                    'signals': champion_signals,
                    'latency_ms': champion_time,
                    'success': champion_success
                },
                'challenger': {
                    'status': challenger_result['status'],
                    'signals': challenger_signals,
                    'latency_ms': challenger_time,
                    'success': challenger_success,
                    'result_latency': challenger_result.get('result', {}).get('latency_ms', 0)
                }
            })

        # Aggregate results
        print(f"\n📊 SHADOW MODE SUMMARY")
        print("=" * 40)

        total_scenarios = len(shadow_results)
        champion_successes = sum(1 for r in shadow_results if r['champion']['success'])
        challenger_successes = sum(1 for r in shadow_results if r['challenger']['success'])

        champion_avg_latency = sum(r['champion']['latency_ms'] for r in shadow_results) / total_scenarios
        challenger_avg_latency = sum(r['challenger']['latency_ms'] for r in shadow_results) / total_scenarios

        champion_total_signals = sum(r['champion']['signals'] for r in shadow_results)
        challenger_total_signals = sum(r['challenger']['signals'] for r in shadow_results)

        print(f"Success Rates:")
        print(f"  Champion (IFD v1.0): {champion_successes}/{total_scenarios} ({champion_successes/total_scenarios*100:.1f}%)")
        print(f"  Challenger (IFD v3.0): {challenger_successes}/{total_scenarios} ({challenger_successes/total_scenarios*100:.1f}%)")

        print(f"\nAverage Latency:")
        print(f"  Champion: {champion_avg_latency:.1f}ms")
        print(f"  Challenger: {challenger_avg_latency:.1f}ms")

        print(f"\nSignal Generation:")
        print(f"  Champion: {champion_total_signals} total signals")
        print(f"  Challenger: {challenger_total_signals} total signals")

        # Determine recommendation
        print(f"\n🎯 SHADOW MODE ASSESSMENT:")

        performance_score = 0

        if challenger_successes >= champion_successes:
            print("  ✅ Challenger reliability: EQUAL or BETTER")
            performance_score += 1
        else:
            print("  ⚠️  Challenger reliability: NEEDS IMPROVEMENT")

        if challenger_avg_latency <= 100:  # Target latency
            print("  ✅ Challenger latency: WITHIN TARGET (<100ms)")
            performance_score += 1
        else:
            print("  ⚠️  Challenger latency: EXCEEDS TARGET")

        if challenger_total_signals >= champion_total_signals:
            print("  ✅ Challenger signal detection: EQUAL or BETTER")
            performance_score += 1
        else:
            print("  ⚠️  Challenger signal detection: FEWER SIGNALS")

        # Final recommendation
        if performance_score >= 3:
            recommendation = "READY FOR CANARY DEPLOYMENT"
            print(f"\n🚀 RECOMMENDATION: {recommendation}")
            print("     IFD v3.0 shows good performance in shadow mode")
            print("     Next step: Deploy to 5% of live traffic (canary)")
        elif performance_score >= 2:
            recommendation = "NEEDS OPTIMIZATION"
            print(f"\n⚠️  RECOMMENDATION: {recommendation}")
            print("     IFD v3.0 shows mixed results in shadow mode")
            print("     Optimize before canary deployment")
        else:
            recommendation = "NOT READY FOR DEPLOYMENT"
            print(f"\n❌ RECOMMENDATION: {recommendation}")
            print("     IFD v3.0 needs significant improvement")
            print("     Continue shadow mode testing")

        # Save results
        test_results = {
            "test": "shadow_mode_simple",
            "timestamp": datetime.now().isoformat(),
            "scenarios_tested": total_scenarios,
            "champion_version": "ifd_v1_production",
            "challenger_version": "ifd_v3_production",
            "results": shadow_results,
            "summary": {
                "champion_success_rate": champion_successes / total_scenarios,
                "challenger_success_rate": challenger_successes / total_scenarios,
                "champion_avg_latency": champion_avg_latency,
                "challenger_avg_latency": challenger_avg_latency,
                "champion_total_signals": champion_total_signals,
                "challenger_total_signals": challenger_total_signals,
                "performance_score": performance_score,
                "recommendation": recommendation
            },
            "status": "PASSED"
        }

        os.makedirs("outputs/shadow_mode", exist_ok=True)
        with open("outputs/shadow_mode/simple_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print(f"\n✅ Shadow mode test completed successfully")
        print("📝 Results saved to outputs/shadow_mode/simple_test_results.json")

        if performance_score >= 3:
            print("\n🎉 IFD v3.0 SHADOW MODE: SUCCESSFUL")
            print("   Ready to proceed to next phase of deployment")

        return True

    except Exception as e:
        print(f"\n❌ Shadow mode test failed: {e}")

        test_results = {
            "test": "shadow_mode_simple",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/shadow_mode", exist_ok=True)
        with open("outputs/shadow_mode/simple_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_shadow_mode_simple()
    sys.exit(0 if success else 1)
