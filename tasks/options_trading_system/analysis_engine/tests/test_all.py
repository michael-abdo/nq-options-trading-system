#!/usr/bin/env python3
"""
Simple test runner for Analysis Engine
Tests core functionality and imports
"""

import sys
import os
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== ANALYSIS ENGINE TEST SUITE ===")
print(f"Running at: {get_eastern_time().isoformat()}")
print("=" * 60)

test_results = []

# Test 1: Core imports
print("\n1. Testing Core Imports...")
try:
    import integration
    import config_manager
    from pipeline.opportunity import Opportunity
    print("✓ Core modules imported successfully")
    test_results.append(("Core Imports", True, None))
except Exception as e:
    print(f"✗ Core import failed: {e}")
    test_results.append(("Core Imports", False, str(e)))

# Test 2: Analysis modules
print("\n2. Testing Analysis Modules...")
try:
    from expected_value_analysis.solution import analyze_expected_value
    from institutional_flow_v3.solution import create_ifd_v3_analyzer
    from risk_analysis.solution import run_risk_analysis
    from volume_shock_analysis.solution import analyze_volume_shocks
    from expiration_pressure_calculator.solution import ExpirationPressureCalculator
    print("✓ All analysis modules imported successfully")
    test_results.append(("Analysis Modules", True, None))
except Exception as e:
    print(f"✗ Analysis module import failed: {e}")
    test_results.append(("Analysis Modules", False, str(e)))

# Test 3: Phase 4 components
print("\n3. Testing Phase 4 Components...")
try:
    from phase4.success_metrics_tracker import SuccessMetricsTracker
    from phase4.adaptive_threshold_manager import AdaptiveThresholdManager
    from phase4.monthly_budget_dashboard import MonthlyBudgetDashboard
    from phase4.staged_rollout_framework import StagedRolloutFramework
    from phase4.latency_monitor import LatencyMonitor
    from phase4.uptime_monitor import UptimeMonitor
    print("✓ All Phase 4 components imported successfully")
    test_results.append(("Phase 4 Components", True, None))
except Exception as e:
    print(f"✗ Phase 4 component import failed: {e}")
    test_results.append(("Phase 4 Components", False, str(e)))

# Test 4: Strategy modules
print("\n4. Testing Strategy Modules...")
try:
    from strategies.ab_testing_coordinator import ABTestingCoordinator
    from strategies.market_making_filter import MarketMakingFilter
    from strategies.volatility_crush_detector import VolatilityCrushDetector
    from strategies.call_put_coordination_detector import CallPutCoordinationDetector
    print("✓ Strategy modules imported successfully")
    test_results.append(("Strategy Modules", True, None))
except Exception as e:
    print(f"✗ Strategy module import failed: {e}")
    test_results.append(("Strategy Modules", False, str(e)))

# Test 5: Configuration management
print("\n5. Testing Configuration Management...")
try:
    from config_manager import ConfigManager
    config_mgr = ConfigManager()

    # Test loading a configuration
    config = config_mgr.load_config("ifd_v3_production")
    if config:
        print(f"✓ Successfully loaded configuration profile")
        print(f"  Mode: {config.get('mode', 'unknown')}")
        print(f"  Min Quality: {config.get('min_data_quality', 0.0)}")
        test_results.append(("Configuration Management", True, None))
    else:
        print("✗ Failed to load configuration")
        test_results.append(("Configuration Management", False, "No config returned"))
except Exception as e:
    print(f"✗ Configuration test failed: {e}")
    test_results.append(("Configuration Management", False, str(e)))

# Test 6: Integration functionality
print("\n6. Testing Integration Engine...")
try:
    from integration import AnalysisEngine

    # Create minimal test config
    test_config = {
        "expected_value": {"enabled": True},
        "risk_analysis": {"enabled": False},
        "volume_shock": {"enabled": False},
        "institutional_flow_v3": {"enabled": True}
    }

    engine = AnalysisEngine(test_config)
    print("✓ Analysis engine created successfully")
    test_results.append(("Integration Engine", True, None))
except Exception as e:
    print(f"✗ Integration test failed: {e}")
    test_results.append(("Integration Engine", False, str(e)))

# Test 7: Evidence files
print("\n7. Checking Evidence Files...")
evidence_files = [
    "evidence_rollup.json",
    "expected_value_analysis/evidence.json",
    "institutional_flow_v3/evidence.json",
    "risk_analysis/evidence.json",
    "volume_shock_analysis/evidence.json"
]

evidence_count = 0
for file in evidence_files:
    if os.path.exists(file):
        evidence_count += 1

print(f"✓ Found {evidence_count}/{len(evidence_files)} evidence files")
test_results.append(("Evidence Files", evidence_count > 0, f"{evidence_count}/{len(evidence_files)} found"))

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)

passed = sum(1 for _, success, _ in test_results if success)
total = len(test_results)

print(f"Total Tests: {total}")
print(f"Passed: {passed}")
print(f"Failed: {total - passed}")
print(f"Success Rate: {(passed/total*100):.1f}%")

print("\nDetailed Results:")
for test_name, success, detail in test_results:
    status = "✓ PASSED" if success else "✗ FAILED"
    print(f"{status} - {test_name}")
    if detail and not success:
        print(f"         └─ {detail}")

# Save results
results_output = {
    "timestamp": get_eastern_time().isoformat(),
    "total_tests": total,
    "passed": passed,
    "failed": total - passed,
    "success_rate": passed/total,
    "results": [
        {
            "test": test_name,
            "status": "PASSED" if success else "FAILED",
            "detail": detail
        }
        for test_name, success, detail in test_results
    ]
}

output_file = "outputs/test_all_results.json"
os.makedirs(os.path.dirname(output_file), exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(results_output, f, indent=2)

print(f"\nResults saved to: {output_file}")

# Exit code
exit_code = 0 if passed == total else 1
print(f"\nExiting with code: {exit_code}")
exit(exit_code)
