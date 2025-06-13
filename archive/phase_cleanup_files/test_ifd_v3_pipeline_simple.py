#!/usr/bin/env python3
"""Simple IFD v3 pipeline test"""

import os
import sys
import json
from datetime import datetime

# Add paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

# Load environment
from dotenv import load_dotenv
load_dotenv()

def test_simple_pipeline():
    """Run simple pipeline test with IFD v3"""
    print("=" * 60)
    print("SIMPLE IFD v3.0 PIPELINE TEST")
    print("=" * 60)

    # Import the run_pipeline script directly
    from scripts.run_pipeline import main

    print("\n🚀 Running pipeline with default settings...")

    # Save original argv
    original_argv = sys.argv

    try:
        # Run with no arguments (uses default config)
        sys.argv = ['run_pipeline.py']

        # Capture start time
        start_time = datetime.now()

        # Run the pipeline
        main()

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ Pipeline completed in {execution_time:.2f} seconds")

        # Save test results
        test_results = {
            "test": "ifd_v3_simple_pipeline",
            "timestamp": datetime.now().isoformat(),
            "execution_time": execution_time,
            "status": "PASSED",
            "notes": "Pipeline ran with default configuration including IFD v3"
        }

        os.makedirs("outputs/ifd_v3_e2e_test", exist_ok=True)
        with open("outputs/ifd_v3_e2e_test/simple_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        print("\n📝 Test results saved to outputs/ifd_v3_e2e_test/simple_test_results.json")

        return True

    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")

        test_results = {
            "test": "ifd_v3_simple_pipeline",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "status": "FAILED"
        }

        os.makedirs("outputs/ifd_v3_e2e_test", exist_ok=True)
        with open("outputs/ifd_v3_e2e_test/simple_test_results.json", "w") as f:
            json.dump(test_results, f, indent=2)

        return False

    finally:
        # Restore original argv
        sys.argv = original_argv

if __name__ == "__main__":
    success = test_simple_pipeline()
    sys.exit(0 if success else 1)
