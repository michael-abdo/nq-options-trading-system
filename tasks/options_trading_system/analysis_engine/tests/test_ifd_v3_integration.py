#!/usr/bin/env python3
"""
IFD v3.0 Integration Test
Tests the integration of IFD v3.0 with the analysis engine
"""

import sys
import os
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from integration import AnalysisEngine, run_analysis_engine


def test_ifd_v3_integration():
    """Test IFD v3.0 integration with analysis engine"""
    print("TESTING IFD v3.0 INTEGRATION")
    print("-" * 50)

    # Test configuration with simulated data
    data_config = {'test': 'simulated'}
    analysis_config = {
        'institutional_flow_v3': {
            'db_path': '/tmp/ifd_v3_integration_test.db',
            'pressure_thresholds': {
                'min_pressure_ratio': 1.5,
                'min_volume_concentration': 0.3,
                'min_time_persistence': 0.4,
                'min_trend_strength': 0.5
            },
            'confidence_thresholds': {
                'min_baseline_anomaly': 1.5,
                'min_overall_confidence': 0.6
            },
            'market_making_penalty': 0.3
        }
    }

    test_results = {
        "test": "ifd_v3_integration",
        "timestamp": get_eastern_time().isoformat(),
        "tests": [],
        "status": "FAILED"
    }

    # Test 1: Individual IFD v3.0 analysis
    print("\n1. Testing individual IFD v3.0 analysis...")
    try:
        engine = AnalysisEngine(analysis_config)
        result = engine.run_ifd_v3_analysis(data_config)

        test_passed = (
            result["status"] == "success" and
            "result" in result and
            "total_signals" in result["result"] and
            "summary" in result["result"]
        )

        test_results["tests"].append({
            "name": "individual_ifd_v3_analysis",
            "passed": test_passed,
            "details": {
                "status": result["status"],
                "total_signals": result.get("result", {}).get("total_signals", 0),
                "pressure_snapshots": result.get("result", {}).get("pressure_snapshots_analyzed", 0)
            }
        })

        print(f"   ✓ Test passed: {test_passed}")
        if test_passed:
            print(f"   ✓ Signals: {result['result']['total_signals']}")
            print(f"   ✓ Snapshots: {result['result']['pressure_snapshots_analyzed']}")

    except Exception as e:
        test_results["tests"].append({
            "name": "individual_ifd_v3_analysis",
            "passed": False,
            "error": str(e)
        })
        print(f"   ✗ Error: {e}")

    # Test 2: Full analysis engine with IFD v3.0
    print("\n2. Testing full analysis engine with IFD v3.0...")
    try:
        result = run_analysis_engine(data_config, analysis_config)

        test_passed = (
            result["status"] == "success" and
            "individual_results" in result and
            "institutional_flow_v3" in result["individual_results"] and
            result["individual_results"]["institutional_flow_v3"]["status"] == "success"
        )

        test_results["tests"].append({
            "name": "full_engine_with_ifd_v3",
            "passed": test_passed,
            "details": {
                "status": result["status"],
                "execution_time": result.get("execution_time_seconds", 0),
                "successful_analyses": result.get("summary", {}).get("successful_analyses", 0),
                "ifd_v3_status": result.get("individual_results", {}).get("institutional_flow_v3", {}).get("status", "missing")
            }
        })

        print(f"   ✓ Test passed: {test_passed}")
        if test_passed:
            print(f"   ✓ Execution time: {result['execution_time_seconds']:.2f}s")
            print(f"   ✓ Successful analyses: {result['summary']['successful_analyses']}")

    except Exception as e:
        test_results["tests"].append({
            "name": "full_engine_with_ifd_v3",
            "passed": False,
            "error": str(e)
        })
        print(f"   ✗ Error: {e}")

    # Test 3: Market context integration
    print("\n3. Testing market context integration...")
    try:
        result = run_analysis_engine(data_config, analysis_config)

        market_context = result.get("synthesis", {}).get("market_context", {})
        ifd_v3_keys = [k for k in market_context.keys() if "ifd_v3" in k]

        test_passed = len(ifd_v3_keys) >= 5  # Should have at least 5 IFD v3.0 metrics

        test_results["tests"].append({
            "name": "market_context_integration",
            "passed": test_passed,
            "details": {
                "ifd_v3_keys_count": len(ifd_v3_keys),
                "ifd_v3_keys": ifd_v3_keys,
                "expected_keys": ["ifd_v3_total_signals", "ifd_v3_high_confidence_signals", "ifd_v3_net_flow"]
            }
        })

        print(f"   ✓ Test passed: {test_passed}")
        if test_passed:
            print(f"   ✓ IFD v3.0 context keys: {len(ifd_v3_keys)}")
            print(f"   ✓ Keys: {ifd_v3_keys}")

    except Exception as e:
        test_results["tests"].append({
            "name": "market_context_integration",
            "passed": False,
            "error": str(e)
        })
        print(f"   ✗ Error: {e}")

    # Test 4: Parallel execution
    print("\n4. Testing parallel execution performance...")
    try:
        start_time = get_eastern_time()
        result = run_analysis_engine(data_config, analysis_config)
        execution_time = (get_eastern_time() - start_time).total_seconds()

        # Should complete within reasonable time (< 5 seconds for simulated data)
        test_passed = execution_time < 5.0 and result["status"] == "success"

        test_results["tests"].append({
            "name": "parallel_execution_performance",
            "passed": test_passed,
            "details": {
                "execution_time": execution_time,
                "performance_threshold": 5.0,
                "status": result["status"]
            }
        })

        print(f"   ✓ Test passed: {test_passed}")
        print(f"   ✓ Execution time: {execution_time:.2f}s")

    except Exception as e:
        test_results["tests"].append({
            "name": "parallel_execution_performance",
            "passed": False,
            "error": str(e)
        })
        print(f"   ✗ Error: {e}")

    # Determine overall status
    all_passed = all(test['passed'] for test in test_results['tests'])
    test_results['status'] = "PASSED" if all_passed else "FAILED"

    # Summary
    print("\n" + "-" * 50)
    print(f"IFD v3.0 INTEGRATION TEST: {test_results['status']}")
    print(f"Tests passed: {sum(1 for t in test_results['tests'] if t['passed'])}/{len(test_results['tests'])}")

    return test_results


def save_integration_evidence(test_results):
    """Save integration test evidence"""
    evidence_path = os.path.join(os.path.dirname(__file__), "ifd_v3_integration_evidence.json")

    with open(evidence_path, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\nIntegration evidence saved to: {evidence_path}")


if __name__ == "__main__":
    # Execute integration test
    results = test_ifd_v3_integration()

    # Save evidence
    save_integration_evidence(results)

    # Exit with appropriate code
    exit(0 if results['status'] == "PASSED" else 1)
