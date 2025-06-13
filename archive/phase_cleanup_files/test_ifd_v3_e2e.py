#!/usr/bin/env python3
"""End-to-end test of the pipeline with IFD v3 enabled"""

import os
import sys
import json
from datetime import datetime

# Add project to path
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

# Load environment
from dotenv import load_dotenv
load_dotenv()

def test_e2e_pipeline():
    """Run end-to-end pipeline test with IFD v3"""
    print("=" * 60)
    print("IFD v3.0 END-TO-END PIPELINE TEST")
    print("=" * 60)

    # Import integration directly
    from tasks.options_trading_system.integration import run_complete_nq_trading_system
    from tasks.options_trading_system.config_manager import get_config_manager

    # Test configuration
    test_config = {
        "config_file": "config/databento_only.json",
        "profile": "ifd_v3_production",  # Use production profile (v3 enabled)
        "output_dir": "outputs/ifd_v3_e2e_test"
    }

    print(f"\n📋 Test Configuration:")
    print(f"   Config: {test_config['config_file']}")
    print(f"   Profile: {test_config['profile']}")
    print(f"   Output: {test_config['output_dir']}")

    # Create output directory
    os.makedirs(test_config['output_dir'], exist_ok=True)

    # Load configuration
    config_manager = get_config_manager()
    profile_config = config_manager.load_profile(test_config['profile'])

    # Use profile config or default
    if profile_config:
        analysis_config = profile_config.get('config', {})
    else:
        # Default config with IFD v3 enabled
        analysis_config = {
            "institutional_flow_v3": {
                "enabled": True,
                "db_path": "outputs/ifd_v3_baselines.db"
            }
        }

    # Run pipeline
    start_time = datetime.now()

    try:
        print(f"\n🚀 Starting pipeline execution...")

        # Run the complete pipeline
        result = run_complete_nq_trading_system(analysis_config)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ Pipeline completed in {execution_time:.2f} seconds")

        # Save test results
        test_results = {
            "test": "ifd_v3_e2e",
            "timestamp": datetime.now().isoformat(),
            "config": test_config,
            "execution_time": execution_time,
            "status": "PASSED"
        }

        results_file = os.path.join(test_config['output_dir'], 'test_results.json')
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)

        print(f"\n📝 Test results saved to: {results_file}")

        return True

    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")

        # Save error results
        test_results = {
            "test": "ifd_v3_e2e",
            "timestamp": datetime.now().isoformat(),
            "config": test_config,
            "error": str(e),
            "status": "FAILED"
        }

        results_file = os.path.join(test_config['output_dir'], 'test_results.json')
        with open(results_file, 'w') as f:
            json.dump(test_results, f, indent=2)

        return False

if __name__ == "__main__":
    success = test_e2e_pipeline()
    sys.exit(0 if success else 1)
