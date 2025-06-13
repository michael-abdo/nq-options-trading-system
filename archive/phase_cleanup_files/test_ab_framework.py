#!/usr/bin/env python3
"""Test the A/B testing framework for IFD v1 vs v3 comparison"""

import os
import sys
import json
from datetime import datetime

# Add paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')
sys.path.append('tasks/options_trading_system/analysis_engine')

# Load environment
from dotenv import load_dotenv
load_dotenv()

def test_ab_framework():
    """Test the A/B testing framework"""
    print("=" * 60)
    print("A/B TESTING FRAMEWORK VALIDATION")
    print("=" * 60)

    from analysis_engine.strategies.ab_testing_coordinator import ABTestingCoordinator, create_ab_coordinator
    from analysis_engine.config_manager import get_config_manager

    try:
        print("\n📋 Setting up A/B testing coordinator...")

        # Create config manager
        config_manager = get_config_manager()

        # Create coordinator
        coordinator = ABTestingCoordinator(
            config_manager=config_manager,
            output_dir="outputs/ab_testing"
        )

        print("✅ A/B testing coordinator created successfully")

        # Start a short test (2 minutes)
        print("\n🚀 Starting 2-minute A/B test...")
        print("   v1.0 Profile: ifd_v1_production")
        print("   v3.0 Profile: ifd_v3_production")

        # Data configuration for testing
        data_config = {
            "mode": "simulation",
            "sample_size": 10
        }

        session_id = coordinator.start_ab_test(
            v1_profile="ifd_v1_production",
            v3_profile="ifd_v3_production",
            duration_hours=2/60,  # 2 minutes
            data_config=data_config
        )

        print(f"\n✅ A/B test started successfully")
        print(f"   Session ID: {session_id}")

        # Wait a bit and check status
        import time
        time.sleep(5)

        status = coordinator.get_test_status()
        print(f"\n📊 Test Status:")
        print(f"   Status: {status['status']}")
        print(f"   Elapsed: {status['elapsed_hours']:.3f} hours")
        print(f"   Comparisons: {status['comparisons_collected']}")

        # Save validation results
        validation_results = {
            "test": "ab_framework_validation",
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "status": "PASSED",
            "notes": "A/B testing framework initialized and started successfully"
        }

        os.makedirs("outputs/ab_testing", exist_ok=True)
        with open("outputs/ab_testing/framework_validation.json", "w") as f:
            json.dump(validation_results, f, indent=2)

        print("\n✅ A/B testing framework validated successfully")
        print("📝 Results saved to outputs/ab_testing/framework_validation.json")

        # Note: We don't wait for full completion in this validation test
        print("\n💡 Note: Test will continue running in background for 2 minutes")
        print("   Use coordinator.stop_ab_test() to get final results")

        return True

    except Exception as e:
        print(f"\n❌ A/B framework validation failed: {e}")

        # Save error results
        validation_results = {
            "test": "ab_framework_validation",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/ab_testing", exist_ok=True)
        with open("outputs/ab_testing/framework_validation.json", "w") as f:
            json.dump(validation_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_ab_framework()
    sys.exit(0 if success else 1)
