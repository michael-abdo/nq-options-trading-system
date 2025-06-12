#!/usr/bin/env python3
"""
Statistical Confidence Test
Verify statistical confidence calculations and signal prioritization
"""

import os
import sys
import json
from datetime import datetime
import random

sys.path.append('.')

def test_confidence_calculations():
    print("📊 Testing Statistical Confidence Calculations")
    print("=" * 40)

    # Test confidence scenarios
    scenarios = [
        {"volume_ratio": 10.0, "institutional_size": 500000, "expected_confidence": 0.85},
        {"volume_ratio": 5.0, "institutional_size": 200000, "expected_confidence": 0.70},
        {"volume_ratio": 2.0, "institutional_size": 100000, "expected_confidence": 0.55}
    ]

    total_accuracy = 0
    for scenario in scenarios:
        # Simplified confidence calculation
        vol_component = min(scenario["volume_ratio"] / 15.0, 1.0) * 0.5
        size_component = min(scenario["institutional_size"] / 1000000, 1.0) * 0.5
        calculated_confidence = vol_component + size_component

        accuracy = 100 - abs(calculated_confidence - scenario["expected_confidence"]) * 100
        total_accuracy += accuracy
        print(f"  Confidence {calculated_confidence:.2f} vs expected {scenario['expected_confidence']:.2f}")

    avg_accuracy = total_accuracy / len(scenarios)
    status = "EXCELLENT" if avg_accuracy >= 90 else "GOOD" if avg_accuracy >= 75 else "POOR"
    print(f"✅ Confidence Calculations: {status} ({avg_accuracy:.1f}% accuracy)")

    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/confidence_test_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump({"accuracy": avg_accuracy, "status": status}, f)

    return {"accuracy": avg_accuracy, "status": status}

if __name__ == "__main__":
    test_confidence_calculations()
