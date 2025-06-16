#!/usr/bin/env python3
"""
Test runner for Live Streaming components
"""

import sys
import os
import unittest
import json
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import timezone utilities
sys.path.append(os.path.join(os.path.dirname(parent_dir), '..', '..', '..'))
from utils.timezone_utils import get_eastern_time

print("=== LIVE STREAMING TEST SUITE ===")
print(f"Running at: {get_eastern_time().isoformat()}")
print("=" * 60)

# Test imports first
print("\nTesting Live Streaming Component Imports...")
test_results = []

try:
    from ..streaming_bridge import StreamingBridge, create_streaming_bridge
    print("✓ StreamingBridge imported successfully")
    test_results.append(("StreamingBridge Import", True, None))
except Exception as e:
    print(f"✗ StreamingBridge import failed: {e}")
    test_results.append(("StreamingBridge Import", False, str(e)))

try:
    from ..event_processor import EventProcessor, create_standard_processor
    print("✓ EventProcessor imported successfully")
    test_results.append(("EventProcessor Import", True, None))
except Exception as e:
    print(f"✗ EventProcessor import failed: {e}")
    test_results.append(("EventProcessor Import", False, str(e)))

try:
    from ..pressure_aggregator import RealTimePressureEngine, create_standard_engine
    print("✓ PressureAggregator imported successfully")
    test_results.append(("PressureAggregator Import", True, None))
except Exception as e:
    print(f"✗ PressureAggregator import failed: {e}")
    test_results.append(("PressureAggregator Import", False, str(e)))

try:
    from ..data_validator import StreamingDataValidator, create_mbo_validation_rules
    print("✓ DataValidator imported successfully")
    test_results.append(("DataValidator Import", True, None))
except Exception as e:
    print(f"✗ DataValidator import failed: {e}")
    test_results.append(("DataValidator Import", False, str(e)))

try:
    from ..baseline_context_manager import RealTimeBaselineManager, create_baseline_manager
    print("✓ BaselineContextManager imported successfully")
    test_results.append(("BaselineContextManager Import", True, None))
except Exception as e:
    print(f"✗ BaselineContextManager import failed: {e}")
    test_results.append(("BaselineContextManager Import", False, str(e)))

# Check if all imports succeeded
all_imports_passed = all(result[1] for result in test_results)

if all_imports_passed:
    print("\n✓ All imports successful. Running unit tests...\n")

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test modules
    test_modules = [
        'test_live_streaming_bridge',
        'test_event_processor',
        'test_pressure_aggregator',
        'test_data_validator',
        'test_baseline_context_manager',
        'test_live_streaming_integration'
    ]

    for module_name in test_modules:
        try:
            module = __import__(module_name)
            suite.addTests(loader.loadTestsFromModule(module))
            print(f"✓ Added tests from {module_name}")
        except Exception as e:
            print(f"✗ Failed to load tests from {module_name}: {e}")
            test_results.append((f"{module_name} Tests", False, str(e)))

    # Run tests
    print("\n" + "="*60)
    print("Running Unit Tests...")
    print("="*60 + "\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Record test results
    test_results.append(("Unit Tests", result.wasSuccessful(),
                        f"{len(result.failures)} failures, {len(result.errors)} errors"))

    # Show summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")

else:
    print("\n✗ Import failures detected. Skipping unit tests.")

# Configuration test
print("\n" + "="*60)
print("Testing Live Streaming Configuration...")
print("="*60)

try:
    config_path = os.path.join(parent_dir, 'pipeline_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)

        streaming_config = config.get('live_streaming', {})

        print("\nLive Streaming Configuration:")
        print(f"  Enabled: {streaming_config.get('enabled', False)}")
        print(f"  Mode: {streaming_config.get('mode', 'unknown')}")
        print(f"  Provider: {streaming_config.get('data_source', {}).get('provider', 'unknown')}")
        print(f"  Daily Budget: ${streaming_config.get('cost_controls', {}).get('daily_budget', 0)}")
        print(f"  IFD Integration: {streaming_config.get('ifd_integration', {}).get('enabled', False)}")

        test_results.append(("Configuration Test", True, "Config loaded successfully"))
    else:
        print("✗ Configuration file not found")
        test_results.append(("Configuration Test", False, "Config file missing"))

except Exception as e:
    print(f"✗ Configuration test failed: {e}")
    test_results.append(("Configuration Test", False, str(e)))

# Integration with main analysis engine
print("\n" + "="*60)
print("Testing Integration with Analysis Engine...")
print("="*60)

try:
    # Import integration module
    sys.path.insert(0, parent_dir)
    from integration import AnalysisEngine

    # Create minimal config
    test_config = {
        "live_streaming": {
            "enabled": True,
            "mode": "development"
        }
    }

    engine = AnalysisEngine(test_config)

    # Test if streaming methods exist
    if hasattr(engine, 'start_live_streaming') and hasattr(engine, 'stop_live_streaming'):
        print("✓ Live streaming methods found in AnalysisEngine")
        test_results.append(("Integration Test", True, None))
    else:
        print("✗ Live streaming methods missing from AnalysisEngine")
        test_results.append(("Integration Test", False, "Methods not found"))

except Exception as e:
    print(f"✗ Integration test failed: {e}")
    test_results.append(("Integration Test", False, str(e)))

# Final summary
print("\n" + "="*60)
print("FINAL TEST RESULTS")
print("="*60)

passed = sum(1 for _, success, _ in test_results if success)
total = len(test_results)

print(f"\nTotal Tests: {total}")
print(f"Passed: {passed}")
print(f"Failed: {total - passed}")
print(f"Success Rate: {(passed/total*100):.1f}%")

print("\nDetailed Results:")
for test_name, success, detail in test_results:
    status = "✓ PASSED" if success else "✗ FAILED"
    print(f"{status} - {test_name}")
    if detail:
        print(f"         └─ {detail}")

# Save results
results_output = {
    "timestamp": get_eastern_time().isoformat(),
    "test_suite": "live_streaming",
    "total_tests": total,
    "passed": passed,
    "failed": total - passed,
    "success_rate": passed/total if total > 0 else 0,
    "results": [
        {
            "test": test_name,
            "status": "PASSED" if success else "FAILED",
            "detail": detail
        }
        for test_name, success, detail in test_results
    ]
}

output_dir = os.path.join(parent_dir, 'outputs')
os.makedirs(output_dir, exist_ok=True)
output_file = os.path.join(output_dir, 'test_live_streaming_results.json')

with open(output_file, 'w') as f:
    json.dump(results_output, f, indent=2)

print(f"\nResults saved to: {output_file}")

# Exit code
exit_code = 0 if passed == total else 1
print(f"\nExiting with code: {exit_code}")
exit(exit_code)
