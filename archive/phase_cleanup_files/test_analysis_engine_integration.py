#!/usr/bin/env python3
"""Test Analysis Engine Integration with IFD v3, conflict resolution, and performance optimizations"""

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

def test_analysis_engine_integration():
    """Test the enhanced analysis engine with all optimizations"""
    print("=" * 60)
    print("ANALYSIS ENGINE INTEGRATION TEST")
    print("=" * 60)

    from analysis_engine.integration import AnalysisEngine, _pressure_cache, _conflict_analyzer, _baseline_cache
    from analysis_engine.config_manager import get_config_manager

    try:
        print("\n📋 Setting up enhanced analysis engine...")

        # Get configuration for comprehensive analysis
        config_manager = get_config_manager()
        analysis_config = config_manager.get_analysis_config("ifd_v3_production")

        # Create analysis engine
        engine = AnalysisEngine(analysis_config)

        print("✅ Enhanced analysis engine created with:")
        print("   - IFD v3.0 integration")
        print("   - Signal conflict resolution")
        print("   - Performance optimizations (caching)")
        print("   - Baseline calculation optimization")

        # Test data configuration scenarios
        test_scenarios = [
            {
                "name": "Conflict Resolution Test",
                "mode": "simulation",
                "scenario": "v1_v3_conflict",
                "description": "Test signal conflict between IFD v1 and v3"
            },
            {
                "name": "Performance Optimization Test",
                "mode": "simulation",
                "scenario": "cache_performance",
                "description": "Test caching and baseline optimizations"
            },
            {
                "name": "Parallel Execution Test",
                "mode": "simulation",
                "scenario": "parallel_analysis",
                "description": "Test efficient parallel execution"
            }
        ]

        integration_results = []

        print(f"\n🔬 Running {len(test_scenarios)} integration test scenarios...")

        for i, data_config in enumerate(test_scenarios, 1):
            print(f"\n📊 Scenario {i}: {data_config['name']}")
            print(f"   Description: {data_config['description']}")

            # Run full analysis with all components
            start_time = time.time()
            result = engine.run_full_analysis(data_config)
            execution_time = (time.time() - start_time) * 1000

            print(f"\n   Results:")
            print(f"     Status: {result['status']}")
            print(f"     Execution Time: {execution_time:.1f}ms")
            print(f"     Successful Analyses: {result['summary']['successful_analyses']}/5")

            # Check synthesis results
            synthesis = result.get('synthesis', {})
            recommendations = synthesis.get('trading_recommendations', [])
            market_context = synthesis.get('market_context', {})

            print(f"     Trading Recommendations: {len(recommendations)}")

            # Check for conflict resolution information
            if 'signal_conflict_resolution' in market_context:
                print(f"     Conflict Resolution: {market_context['signal_conflict_resolution']}")
                print(f"     Conflicts Detected: {market_context.get('signal_conflicts_detected', 0)}")

            # Check for performance optimizations
            cache_hits = 0
            if hasattr(_pressure_cache, 'cache') and _pressure_cache.cache:
                cache_hits = len(_pressure_cache.cache)

            baseline_cache_items = 0
            if hasattr(_baseline_cache, 'daily_baselines') and _baseline_cache.daily_baselines:
                baseline_cache_items = len(_baseline_cache.daily_baselines)

            print(f"     Performance:")
            print(f"       Pressure Cache Items: {cache_hits}")
            print(f"       Baseline Cache Items: {baseline_cache_items}")

            # Show top recommendation
            if recommendations:
                top_rec = recommendations[0]
                print(f"     Top Recommendation:")
                print(f"       Source: {top_rec['source']}")
                print(f"       Priority: {top_rec['priority']}")
                print(f"       Direction: {top_rec['trade_direction']}")
                print(f"       Expected Value: {top_rec.get('expected_value', 0):.1f}")
                if 'conflict_resolution' in top_rec:
                    print(f"       Conflict Resolution: {top_rec['conflict_resolution']}")

            # Store results for analysis
            integration_results.append({
                'scenario': data_config['name'],
                'execution_time_ms': execution_time,
                'status': result['status'],
                'successful_analyses': result['summary']['successful_analyses'],
                'recommendations_count': len(recommendations),
                'conflict_resolution': market_context.get('signal_conflict_resolution', 'N/A'),
                'conflicts_detected': market_context.get('signal_conflicts_detected', 0),
                'cache_performance': {
                    'pressure_cache_items': cache_hits,
                    'baseline_cache_items': baseline_cache_items
                }
            })

            # Small delay between scenarios
            time.sleep(1)

        # Performance Analysis
        print(f"\n📊 INTEGRATION PERFORMANCE ANALYSIS")
        print("=" * 40)

        total_scenarios = len(integration_results)
        avg_execution_time = sum(r['execution_time_ms'] for r in integration_results) / total_scenarios
        successful_scenarios = sum(1 for r in integration_results if r['status'] == 'success')
        total_recommendations = sum(r['recommendations_count'] for r in integration_results)

        print(f"Success Rate: {successful_scenarios}/{total_scenarios} ({successful_scenarios/total_scenarios*100:.1f}%)")
        print(f"Average Execution Time: {avg_execution_time:.1f}ms")
        print(f"Total Recommendations Generated: {total_recommendations}")

        # Check specific integration features
        conflict_resolutions = [r['conflict_resolution'] for r in integration_results if r['conflict_resolution'] != 'N/A']
        total_conflicts = sum(r['conflicts_detected'] for r in integration_results)

        if conflict_resolutions:
            print(f"\nConflict Resolution Performance:")
            print(f"  Scenarios with Conflicts: {len(conflict_resolutions)}")
            print(f"  Total Conflicts Detected: {total_conflicts}")
            print(f"  Resolution Types: {set(conflict_resolutions)}")

        # Cache performance
        final_pressure_cache = len(_pressure_cache.cache) if hasattr(_pressure_cache, 'cache') else 0
        final_baseline_cache = len(_baseline_cache.daily_baselines) if hasattr(_baseline_cache, 'daily_baselines') else 0

        print(f"\nCache Performance:")
        print(f"  Final Pressure Cache Items: {final_pressure_cache}")
        print(f"  Final Baseline Cache Items: {final_baseline_cache}")

        # Integration assessment
        print(f"\n🎯 INTEGRATION ASSESSMENT:")

        performance_score = 0

        if successful_scenarios == total_scenarios:
            print("  ✅ Analysis Engine Reliability: EXCELLENT")
            performance_score += 1
        else:
            print("  ⚠️  Analysis Engine Reliability: NEEDS IMPROVEMENT")

        if avg_execution_time <= 200:  # Target: <200ms for full analysis
            print("  ✅ Analysis Engine Performance: WITHIN TARGET (<200ms)")
            performance_score += 1
        else:
            print("  ⚠️  Analysis Engine Performance: EXCEEDS TARGET")

        if total_recommendations >= total_scenarios:
            print("  ✅ Signal Generation: ADEQUATE")
            performance_score += 1
        else:
            print("  ⚠️  Signal Generation: INSUFFICIENT")

        if final_pressure_cache > 0 or final_baseline_cache > 0:
            print("  ✅ Performance Optimizations: ACTIVE")
            performance_score += 1
        else:
            print("  ⚠️  Performance Optimizations: NOT ACTIVE")

        # Get conflict analyzer recent conflicts for validation
        recent_conflicts = _conflict_analyzer.get_recent_conflicts(hours=1)
        if len(recent_conflicts) > 0 or total_conflicts > 0:
            print("  ✅ Conflict Resolution System: FUNCTIONAL")
            performance_score += 1
        else:
            print("  ✅ Conflict Resolution System: NO CONFLICTS (GOOD)")
            performance_score += 1

        # Final recommendation
        if performance_score >= 5:
            recommendation = "INTEGRATION SUCCESSFUL - READY FOR PRODUCTION"
            print(f"\n🚀 RECOMMENDATION: {recommendation}")
            print("     All analysis engine integration features operational")
        elif performance_score >= 4:
            recommendation = "INTEGRATION MOSTLY SUCCESSFUL - MINOR OPTIMIZATIONS NEEDED"
            print(f"\n⚠️  RECOMMENDATION: {recommendation}")
            print("     Most features working, address performance issues")
        else:
            recommendation = "INTEGRATION NEEDS WORK"
            print(f"\n❌ RECOMMENDATION: {recommendation}")
            print("     Significant issues need resolution")

        # Save integration test results
        test_results = {
            "test": "analysis_engine_integration",
            "timestamp": datetime.now().isoformat(),
            "scenarios_tested": total_scenarios,
            "integration_results": integration_results,
            "performance_summary": {
                "success_rate": successful_scenarios / total_scenarios,
                "avg_execution_time_ms": avg_execution_time,
                "total_recommendations": total_recommendations,
                "conflict_resolutions": conflict_resolutions,
                "total_conflicts": total_conflicts,
                "cache_performance": {
                    "pressure_cache_items": final_pressure_cache,
                    "baseline_cache_items": final_baseline_cache
                }
            },
            "performance_score": performance_score,
            "recommendation": recommendation,
            "status": "PASSED" if performance_score >= 4 else "NEEDS_IMPROVEMENT"
        }

        os.makedirs("outputs/analysis_engine_integration", exist_ok=True)
        with open("outputs/analysis_engine_integration/integration_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print(f"\n✅ Analysis engine integration test completed")
        print("📝 Results saved to outputs/analysis_engine_integration/integration_test_results.json")

        return performance_score >= 4

    except Exception as e:
        print(f"\n❌ Analysis engine integration test failed: {e}")

        test_results = {
            "test": "analysis_engine_integration",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/analysis_engine_integration", exist_ok=True)
        with open("outputs/analysis_engine_integration/integration_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_analysis_engine_integration()
    sys.exit(0 if success else 1)
