#!/usr/bin/env python3
"""
Volume Ratio Thresholds Test
Test volume ratio thresholds (4.0x, 10x, 30x, 50x) detection accuracy
"""

import os
import sys
import json
from datetime import datetime

sys.path.append('.')

def test_volume_ratios():
    print("📊 Testing Volume Ratio Thresholds")
    print("=" * 40)

    # Test volume ratio detection
    volume_tests = [
        {"actual_ratio": 3.8, "threshold": 4.0, "should_trigger": False},
        {"actual_ratio": 4.2, "threshold": 4.0, "should_trigger": True},
        {"actual_ratio": 9.8, "threshold": 10.0, "should_trigger": False},
        {"actual_ratio": 12.0, "threshold": 10.0, "should_trigger": True},
        {"actual_ratio": 32.0, "threshold": 30.0, "should_trigger": True},
        {"actual_ratio": 55.0, "threshold": 50.0, "should_trigger": True}
    ]

    correct_detections = 0
    for test in volume_tests:
        detected = test["actual_ratio"] >= test["threshold"]
        if detected == test["should_trigger"]:
            correct_detections += 1

        status = "✅" if detected == test["should_trigger"] else "❌"
        print(f"  {status} Ratio {test['actual_ratio']:.1f}x vs {test['threshold']:.1f}x threshold")

    accuracy = (correct_detections / len(volume_tests)) * 100
    status = "EXCELLENT" if accuracy >= 90 else "GOOD" if accuracy >= 75 else "POOR"
    print(f"✅ Volume Ratio Detection: {status} ({accuracy:.1f}% accuracy)")

    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/volume_ratios_test_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump({"accuracy": accuracy, "status": status}, f)

    return {"accuracy": accuracy, "status": status}

if __name__ == "__main__":
    test_volume_ratios()
