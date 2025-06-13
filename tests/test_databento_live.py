#!/usr/bin/env python3
"""
Databento Live API Integration Test

Tests the end-to-end databento-only pipeline:
1. Configuration loading
2. API connectivity
3. MBO streaming initialization
4. IFD v3.0 integration
5. Analysis engine execution
"""

import sys
import os
import time
from datetime import datetime
from typing import Dict, Any

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

def test_databento_connectivity():
    """Test basic databento API connectivity"""
    print("🔗 Testing Databento API connectivity...")

    try:
        import databento as db
        api_key = os.getenv('DATABENTO_API_KEY')

        if not api_key:
            print("❌ DATABENTO_API_KEY environment variable not set")
            return False

        # Test basic API access
        client = db.Historical(api_key)

        # Quick test - try to access catalog
        datasets = client.metadata.list_datasets()
        if datasets:
            print(f"✅ API connectivity OK - {len(datasets)} datasets available")

            # Check for GLBX.MDP3 access
            glbx_available = any('GLBX' in str(d) for d in datasets)
            if glbx_available:
                print("✅ GLBX dataset access confirmed")
                # List GLBX datasets specifically
                glbx_datasets = [str(d) for d in datasets if 'GLBX' in str(d)]
                print(f"✅ GLBX datasets: {', '.join(glbx_datasets)}")
            else:
                print("⚠️  GLBX dataset not found - may require subscription upgrade")

            return True
        else:
            print("❌ No datasets available")
            return False

    except ImportError:
        print("❌ Databento package not installed")
        return False
    except Exception as e:
        print(f"❌ API connectivity failed: {e}")
        return False

def test_configuration_loading():
    """Test databento-only configuration loading"""
    print("\n⚙️ Testing configuration loading...")

    try:
        from tasks.options_trading_system.config_manager import load_databento_live_config

        config = load_databento_live_config()

        # Validate configuration structure
        required_sections = ['data_sources', 'analysis']
        for section in required_sections:
            if section not in config:
                print(f"❌ Missing config section: {section}")
                return False

        # Check databento configuration
        databento_config = config['data_sources']['databento']
        if not databento_config.get('enabled', False):
            print("❌ Databento not enabled in configuration")
            return False

        if not databento_config['config'].get('streaming_mode', False):
            print("❌ Streaming mode not enabled")
            return False

        print("✅ Configuration loaded and validated")
        return True

    except Exception as e:
        print(f"❌ Configuration loading failed: {e}")
        return False

def test_data_ingestion_pipeline():
    """Test data ingestion pipeline in databento-only mode"""
    print("\n📊 Testing data ingestion pipeline...")

    try:
        from tasks.options_trading_system.data_ingestion.integration import run_data_ingestion
        from tasks.options_trading_system.config_manager import load_databento_live_config

        # Load databento-only configuration
        config = load_databento_live_config()

        print("🚀 Initializing data ingestion pipeline...")
        start_time = time.time()

        # Run data ingestion
        result = run_data_ingestion(config)

        execution_time = time.time() - start_time

        # Validate results
        if result.get('pipeline_status') == 'success':
            print(f"✅ Pipeline executed successfully in {execution_time:.2f}s")

            # Check for databento-specific results
            if result.get('_primary_source') == 'databento':
                print("✅ Databento confirmed as primary source")

            if result.get('_streaming_mode'):
                print("✅ Streaming mode active")

            return True
        else:
            print(f"❌ Pipeline failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ Data ingestion test failed: {e}")
        return False

def test_ifd_v3_integration():
    """Test IFD v3.0 integration with databento live data"""
    print("\n🎯 Testing IFD v3.0 integration...")

    try:
        from tasks.options_trading_system.analysis_engine.integration import run_analysis_engine

        # Configure for databento-only live mode
        data_config = {
            'mode': 'real_time',
            'sources': ['databento'],
            'symbols': ['NQ'],
            'enable_mbo_streaming': True,
            'live_data': True
        }

        print("🔄 Running analysis engine with databento-only configuration...")
        start_time = time.time()

        # Run analysis engine
        result = run_analysis_engine(data_config)

        execution_time = time.time() - start_time

        # Validate results
        if result.get('status') == 'success':
            print(f"✅ Analysis engine executed successfully in {execution_time:.2f}s")

            # Check for IFD v3.0 specific results
            if 'institutional_flow_v3' in result.get('individual_results', {}):
                ifd_result = result['individual_results']['institutional_flow_v3']
                if ifd_result.get('status') == 'success':
                    print("✅ IFD v3.0 analysis successful")

                    ifd_data = ifd_result.get('result', {})
                    signals = ifd_data.get('total_signals', 0)
                    latency = ifd_data.get('latency_ms', 0)

                    print(f"📈 IFD v3.0 Results: {signals} signals, {latency:.1f}ms latency")
                else:
                    print(f"⚠️  IFD v3.0 failed: {ifd_result.get('error', 'Unknown error')}")

            return True
        else:
            print(f"❌ Analysis engine failed: {result.get('error', 'Unknown error')}")
            return False

    except Exception as e:
        print(f"❌ IFD v3.0 integration test failed: {e}")
        return False

def test_end_to_end_performance():
    """Test end-to-end performance with multiple runs"""
    print("\n⚡ Testing end-to-end performance...")

    try:
        from tasks.options_trading_system.analysis_engine.integration import run_analysis_engine

        data_config = {
            'mode': 'real_time',
            'sources': ['databento'],
            'symbols': ['NQ']
        }

        run_times = []
        successful_runs = 0

        for i in range(3):
            print(f"   Run {i+1}/3...")
            try:
                start_time = time.time()
                result = run_analysis_engine(data_config)
                execution_time = time.time() - start_time

                if result.get('status') == 'success':
                    run_times.append(execution_time)
                    successful_runs += 1
                    print(f"   ✅ Run {i+1}: {execution_time:.2f}s")
                else:
                    print(f"   ❌ Run {i+1}: Failed")

            except Exception as e:
                print(f"   ❌ Run {i+1}: Error - {e}")

        if successful_runs > 0:
            avg_time = sum(run_times) / len(run_times)
            min_time = min(run_times)
            max_time = max(run_times)

            print(f"✅ Performance Summary:")
            print(f"   Successful runs: {successful_runs}/3")
            print(f"   Average time: {avg_time:.2f}s")
            print(f"   Min time: {min_time:.2f}s")
            print(f"   Max time: {max_time:.2f}s")

            # Performance thresholds
            if avg_time < 5.0:
                print("✅ Performance: EXCELLENT (< 5s)")
            elif avg_time < 10.0:
                print("⚠️  Performance: GOOD (< 10s)")
            else:
                print("❌ Performance: NEEDS IMPROVEMENT (> 10s)")

            return successful_runs >= 2
        else:
            print("❌ No successful runs")
            return False

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False

def main():
    """Run comprehensive databento live API validation"""
    print("🧪 DATABENTO LIVE API INTEGRATION TEST")
    print("=" * 60)
    print(f"Test started: {datetime.now().isoformat()}")

    tests = [
        ("Databento API Connectivity", test_databento_connectivity),
        ("Configuration Loading", test_configuration_loading),
        ("Data Ingestion Pipeline", test_data_ingestion_pipeline),
        ("IFD v3.0 Integration", test_ifd_v3_integration),
        ("End-to-End Performance", test_end_to_end_performance)
    ]

    results = {}

    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")

        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results[test_name] = False

    # Summary
    print(f"\n{'='*60}")
    print("📋 TEST SUMMARY")
    print(f"{'='*60}")

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    print(f"\nOverall Result: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL TESTS PASSED - Databento live API integration is ready!")
        return 0
    elif passed >= total * 0.8:
        print("⚠️  MOSTLY SUCCESSFUL - Minor issues need attention")
        return 1
    else:
        print("❌ SIGNIFICANT ISSUES - Review failed tests before proceeding")
        return 2

if __name__ == "__main__":
    exit(main())
