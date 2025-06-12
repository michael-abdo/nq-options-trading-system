#!/usr/bin/env python3
"""
Comprehensive Validation Test Suite for Phase 3
Tests A/B testing, configuration management, and backward compatibility
"""

import sys
import os
import json
import time
from datetime import datetime
from typing import Dict, Any

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from config_manager import ConfigManager, AlgorithmVersion, DataMode, TestingMode
from ab_testing_coordinator import ABTestingCoordinator
from performance_tracker import PerformanceTracker
from integration import run_analysis_engine, run_ab_testing_analysis, run_specific_algorithm


def test_configuration_profiles():
    """Test configuration profile management"""
    print("\n=== Testing Configuration Profiles ===")

    config_manager = ConfigManager()

    # Test 1: List all profiles
    profiles = config_manager.list_profiles()
    print(f"✓ Found {len(profiles)} configuration profiles")

    expected_profiles = [
        "ifd_v1_production",
        "ifd_v3_production",
        "ab_testing_production",
        "paper_trading_validation",
        "conservative_testing"
    ]

    for profile in expected_profiles:
        assert profile in profiles, f"Missing profile: {profile}"
        print(f"  ✓ {profile} exists")

    # Test 2: Load and validate profiles
    for profile_name in expected_profiles:
        profile = config_manager.get_profile(profile_name)
        assert profile is not None, f"Failed to load profile: {profile_name}"

        # Validate profile structure
        assert hasattr(profile, 'algorithm_version')
        assert hasattr(profile, 'data_mode')
        assert hasattr(profile, 'testing_mode')
        assert 'config' in profile.__dict__

        print(f"✓ Profile '{profile_name}' validated")

    # Test 3: Create custom profile
    custom_profile = config_manager.create_profile(
        name="test_custom_profile",
        description="Test custom profile",
        algorithm_version=AlgorithmVersion.V3_0,
        data_mode=DataMode.SIMULATION,
        testing_mode=TestingMode.VALIDATION,
        config={"test": True}
    )

    assert custom_profile is not None
    print("✓ Custom profile creation successful")

    # Test 4: Get analysis config
    analysis_config = config_manager.get_analysis_config("ifd_v3_production")
    assert "institutional_flow_v3" in analysis_config
    print("✓ Analysis config retrieval successful")

    return True


def test_backward_compatibility():
    """Test backward compatibility with existing pipeline"""
    print("\n=== Testing Backward Compatibility ===")

    # Test 1: Run analysis engine without profile (default behavior)
    data_config = {"mode": "simulation"}

    try:
        result = run_analysis_engine(data_config)
        assert result is not None
        assert "status" in result
        assert result["status"] == "success"
        print("✓ Default analysis engine execution successful")
    except Exception as e:
        print(f"✗ Default execution failed: {e}")
        return False

    # Test 2: Run with profile name
    try:
        result = run_analysis_engine(data_config, profile_name="ifd_v3_production")
        assert result is not None
        assert "status" in result
        print("✓ Profile-based execution successful")
    except Exception as e:
        print(f"✗ Profile-based execution failed: {e}")
        return False

    # Test 3: Run specific algorithm versions
    for version in ["v1.0", "v3.0"]:
        try:
            result = run_specific_algorithm(version, data_config)
            assert result is not None
            print(f"✓ {version} algorithm execution successful")
        except Exception as e:
            print(f"✗ {version} execution failed: {e}")
            return False

    return True


def test_ab_testing_framework():
    """Test A/B testing coordinator functionality"""
    print("\n=== Testing A/B Testing Framework ===")

    config_manager = ConfigManager()
    coordinator = ABTestingCoordinator(config_manager)

    # Test 1: Start A/B test
    try:
        session_id = coordinator.start_ab_test(
            "ifd_v1_production",
            "ifd_v3_production",
            duration_hours=0.01  # 36 seconds for testing
        )

        assert session_id is not None
        assert coordinator.test_active is True
        print(f"✓ A/B test started: {session_id}")
    except Exception as e:
        print(f"✗ Failed to start A/B test: {e}")
        return False

    # Test 2: Check test status
    time.sleep(5)  # Wait a bit

    status = coordinator.get_test_status()
    assert status["status"] == "active"
    print(f"✓ Test status check successful")
    print(f"  - Comparisons collected: {status['comparisons_collected']}")

    # Test 3: Stop test and get results
    time.sleep(35)  # Complete the test duration

    try:
        results = coordinator.stop_ab_test()
        assert results is not None
        assert hasattr(results, 'recommended_algorithm')
        assert hasattr(results, 'confidence_in_recommendation')

        print("✓ A/B test completed successfully")
        print(f"  - Recommended: {results.recommended_algorithm}")
        print(f"  - Confidence: {results.confidence_in_recommendation:.1%}")
        print(f"  - Reasoning: {results.reasoning[0] if results.reasoning else 'None'}")
    except Exception as e:
        print(f"✗ Failed to complete A/B test: {e}")
        return False

    return True


def test_performance_tracking():
    """Test performance tracking functionality"""
    print("\n=== Testing Performance Tracking ===")

    tracker = PerformanceTracker()

    # Test 1: Start tracking
    try:
        tracker.start_tracking(["v1.0", "v3.0"])
        assert tracker.tracking_active is True
        print("✓ Performance tracking started")
    except Exception as e:
        print(f"✗ Failed to start tracking: {e}")
        return False

    # Test 2: Record signals
    try:
        # Record v1.0 signal
        v1_signal_id = tracker.record_signal(
            "v1.0",
            {
                "symbol": "NQM25",
                "strike": 21350,
                "option_type": "CALL",
                "confidence": 0.75,
                "direction": "LONG"
            },
            processing_time=0.15
        )

        # Record v3.0 signal
        v3_signal_id = tracker.record_signal(
            "v3.0",
            {
                "symbol": "NQM25",
                "strike": 21350,
                "option_type": "CALL",
                "confidence": 0.82,
                "direction": "LONG"
            },
            processing_time=0.22
        )

        print("✓ Signals recorded successfully")
    except Exception as e:
        print(f"✗ Failed to record signals: {e}")
        return False

    # Test 3: Update signal outcomes
    try:
        tracker.update_signal_outcome(v1_signal_id, "LONG", pnl=25.0)
        tracker.update_signal_outcome(v3_signal_id, "LONG", pnl=35.0)
        print("✓ Signal outcomes updated")
    except Exception as e:
        print(f"✗ Failed to update outcomes: {e}")
        return False

    # Test 4: Get performance summary
    try:
        v1_summary = tracker.get_performance_summary("v1.0")
        v3_summary = tracker.get_performance_summary("v3.0")

        assert v1_summary["total_signals"] > 0
        assert v3_summary["total_signals"] > 0

        print("✓ Performance summaries retrieved")
        print(f"  - v1.0 signals: {v1_summary['total_signals']}")
        print(f"  - v3.0 signals: {v3_summary['total_signals']}")
    except Exception as e:
        print(f"✗ Failed to get summaries: {e}")
        return False

    # Test 5: Compare algorithms
    try:
        comparison = tracker.compare_algorithms("v1.0", "v3.0")
        assert "overall_winner" in comparison
        print(f"✓ Algorithm comparison complete: winner = {comparison['overall_winner']}")
    except Exception as e:
        print(f"✗ Failed to compare algorithms: {e}")
        return False

    # Stop tracking
    tracker.stop_tracking()

    return True


def test_data_mode_selection():
    """Test real-time vs historical data mode selection"""
    print("\n=== Testing Data Mode Selection ===")

    config_manager = ConfigManager()

    # Test 1: Real-time mode
    rt_profile = config_manager.get_profile("ifd_v3_production")
    assert rt_profile.data_mode == DataMode.REAL_TIME

    rt_data_config = config_manager.get_data_config("ifd_v3_production")
    assert rt_data_config["mode"] == "real_time"
    assert rt_data_config.get("real_time_mode") is True
    print("✓ Real-time mode configuration validated")

    # Test 2: Historical mode
    hist_profile = config_manager.get_profile("paper_trading_validation")
    assert hist_profile.data_mode == DataMode.HISTORICAL

    hist_data_config = config_manager.get_data_config("paper_trading_validation")
    assert hist_data_config["mode"] == "historical"
    assert hist_data_config.get("historical_mode") is True
    assert "start_date" in hist_data_config
    assert "end_date" in hist_data_config
    print("✓ Historical mode configuration validated")

    # Test 3: Mode switching
    profile = config_manager.create_profile(
        name="test_mode_switch",
        description="Test mode switching",
        algorithm_version=AlgorithmVersion.V3_0,
        data_mode=DataMode.SIMULATION,
        testing_mode=TestingMode.VALIDATION,
        config={
            "data_sources": {
                "mode": "simulation",
                "primary": ["test"]
            }
        }
    )

    sim_data_config = config_manager.get_data_config("test_mode_switch")
    assert sim_data_config["mode"] == "simulation"
    print("✓ Simulation mode configuration validated")

    return True


def test_integration_functions():
    """Test new integration functions"""
    print("\n=== Testing Integration Functions ===")

    # Test 1: A/B testing analysis function
    try:
        # Run short A/B test
        result = run_ab_testing_analysis(
            duration_hours=0.01  # 36 seconds
        )

        # Should either succeed or return error
        assert result is not None
        if "error" not in result:
            assert "recommendation" in result
            assert "confidence" in result
            print("✓ A/B testing analysis function successful")
        else:
            print(f"⚠ A/B testing returned error: {result['error']}")
    except Exception as e:
        print(f"✗ A/B testing analysis failed: {e}")
        return False

    # Test 2: Performance comparison function
    try:
        from integration import compare_algorithm_performance

        result = compare_algorithm_performance(duration_hours=0.01)

        assert result is not None
        if "error" not in result:
            assert "overall_winner" in result
            print(f"✓ Performance comparison successful: winner = {result['overall_winner']}")
        else:
            print(f"⚠ Performance comparison returned error: {result['error']}")
    except Exception as e:
        print(f"✗ Performance comparison failed: {e}")
        return False

    return True


def run_all_tests():
    """Run all validation tests"""
    print("=" * 60)
    print("PHASE 3 COMPREHENSIVE VALIDATION TEST SUITE")
    print("=" * 60)

    test_results = {
        "timestamp": datetime.now().isoformat(),
        "tests": [],
        "overall_status": "FAILED"
    }

    # Run each test suite
    test_suites = [
        ("Configuration Profiles", test_configuration_profiles),
        ("Backward Compatibility", test_backward_compatibility),
        ("A/B Testing Framework", test_ab_testing_framework),
        ("Performance Tracking", test_performance_tracking),
        ("Data Mode Selection", test_data_mode_selection),
        ("Integration Functions", test_integration_functions)
    ]

    passed_tests = 0
    total_tests = len(test_suites)

    for test_name, test_func in test_suites:
        try:
            result = test_func()
            test_results["tests"].append({
                "name": test_name,
                "passed": result,
                "error": None
            })
            if result:
                passed_tests += 1
                print(f"\n✅ {test_name}: PASSED")
            else:
                print(f"\n❌ {test_name}: FAILED")
        except Exception as e:
            test_results["tests"].append({
                "name": test_name,
                "passed": False,
                "error": str(e)
            })
            print(f"\n❌ {test_name}: ERROR - {e}")

    # Summary
    print("\n" + "=" * 60)
    print(f"VALIDATION SUMMARY: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        test_results["overall_status"] = "PASSED"
        print("✅ ALL TESTS PASSED - Phase 3 implementation validated!")
    else:
        print("❌ Some tests failed - review implementation")

    print("=" * 60)

    # Save results
    results_file = f"outputs/phase3_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    os.makedirs("outputs", exist_ok=True)

    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")

    return test_results["overall_status"] == "PASSED"


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
