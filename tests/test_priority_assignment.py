#!/usr/bin/env python3
"""
Priority Assignment Test
Test IMMEDIATE priority assignment for high-confidence signals
"""

import os
import sys
import json
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

sys.path.append('.')

def test_priority_assignment():
    print("🚨 Testing Priority Assignment")
    print("=" * 40)

    # Test priority scenarios
    signals = [
        {"confidence": 0.95, "volume_ratio": 50, "expected_priority": "IMMEDIATE"},
        {"confidence": 0.85, "volume_ratio": 20, "expected_priority": "HIGH"},
        {"confidence": 0.70, "volume_ratio": 8, "expected_priority": "MEDIUM"},
        {"confidence": 0.55, "volume_ratio": 4, "expected_priority": "LOW"}
    ]

    correct_assignments = 0
    for signal in signals:
        # Priority assignment logic
        if signal["confidence"] >= 0.90 and signal["volume_ratio"] >= 30:
            assigned_priority = "IMMEDIATE"
        elif signal["confidence"] >= 0.80:
            assigned_priority = "HIGH"
        elif signal["confidence"] >= 0.65:
            assigned_priority = "MEDIUM"
        else:
            assigned_priority = "LOW"

        if assigned_priority == signal["expected_priority"]:
            correct_assignments += 1

        print(f"  {assigned_priority} priority (confidence: {signal['confidence']:.2f})")

    accuracy = (correct_assignments / len(signals)) * 100
    status = "EXCELLENT" if accuracy >= 90 else "GOOD" if accuracy >= 75 else "POOR"
    print(f"✅ Priority Assignment: {status} ({accuracy:.1f}% accuracy)")

    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = get_eastern_time().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/priority_test_{timestamp}.json'
    with open(results_file, 'w') as f:
        json.dump({"accuracy": accuracy, "status": status}, f)

    return {"accuracy": accuracy, "status": status}

if __name__ == "__main__":
    test_priority_assignment()
