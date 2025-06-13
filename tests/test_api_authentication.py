#!/usr/bin/env python3
"""
API Authentication Test
Test API authentication with production API keys for all configured sources
"""

import os
import sys
import json
import time
from datetime import datetime
from utils.timezone_utils import get_eastern_time, get_utc_time

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

def test_api_authentication():
    """Test API authentication for all production data sources"""
    print("🔐 Testing API Authentication")
    print("=" * 50)

    test_results = {
        "test_timestamp": get_eastern_time().isoformat(),
        "authentication_tests": {},
        "environment_variables": {},
        "security_checks": {},
        "overall_status": "UNKNOWN"
    }

    # Test environment variable resolution
    print("\n1. Testing Environment Variable Resolution")
    env_vars_to_check = [
        "DATABENTO_API_KEY",
        "BARCHART_API_KEY",
        "POLYGON_API_KEY",
        "TRADOVATE_CID",
        "TRADOVATE_SECRET"
    ]

    for var_name in env_vars_to_check:
        value = os.getenv(var_name)
        if value:
            test_results["environment_variables"][var_name] = {
                "status": "FOUND",
                "length": len(value),
                "masked_value": value[:8] + "..." if len(value) > 8 else "***"
            }
            print(f"✅ {var_name}: Found ({len(value)} chars)")
        else:
            test_results["environment_variables"][var_name] = {
                "status": "MISSING",
                "length": 0,
                "masked_value": None
            }
            print(f"❌ {var_name}: Missing")

    # Test Databento API Authentication
    print("\n2. Testing Databento API Authentication")
    try:
        sys.path.append('tasks/options_trading_system/data_ingestion/databento_api')
        from solution import load_databento_mbo_data, DATABENTO_AVAILABLE

        if not DATABENTO_AVAILABLE:
            test_results["authentication_tests"]["databento"] = {
                "status": "UNAVAILABLE",
                "reason": "Databento package not installed"
            }
            print("⚠️  Databento API: Package not installed")
        else:
            databento_key = os.getenv("DATABENTO_API_KEY")
            if databento_key:
                # Test configuration with minimal request
                test_config = {
                    "api_key": databento_key,
                    "symbols": ["NQ"],
                    "streaming_mode": False,
                    "cache_dir": "outputs/databento_cache"
                }

                try:
                    # Test authentication by attempting to initialize loader
                    start_time = time.time()
                    result = load_databento_mbo_data(test_config)
                    elapsed = time.time() - start_time

                    if result.get('raw_data_available'):
                        test_results["authentication_tests"]["databento"] = {
                            "status": "SUCCESS",
                            "elapsed_time": elapsed,
                            "api_accessible": True,
                            "error": None
                        }
                        print(f"✅ Databento API: Authentication successful ({elapsed:.2f}s)")
                    else:
                        test_results["authentication_tests"]["databento"] = {
                            "status": "FAILED",
                            "elapsed_time": elapsed,
                            "api_accessible": False,
                            "error": result.get('metadata', {}).get('error', 'Unknown error')
                        }
                        print(f"❌ Databento API: Authentication failed")

                except Exception as e:
                    test_results["authentication_tests"]["databento"] = {
                        "status": "FAILED",
                        "elapsed_time": time.time() - start_time,
                        "api_accessible": False,
                        "error": str(e)
                    }
                    print(f"❌ Databento API: Authentication failed - {e}")
            else:
                test_results["authentication_tests"]["databento"] = {
                    "status": "SKIPPED",
                    "reason": "API key not found in environment"
                }
                print("⚠️  Databento API: Skipped (no API key)")

    except ImportError as e:
        test_results["authentication_tests"]["databento"] = {
            "status": "UNAVAILABLE",
            "reason": f"Module import failed: {e}"
        }
        print(f"⚠️  Databento API: Unavailable - {e}")

    # Test Barchart API Authentication
    print("\n3. Testing Barchart API Authentication")
    try:
        # Test via sources registry which handles imports properly
        from data_ingestion.sources_registry import get_sources_registry

        registry = get_sources_registry()
        barchart_available = registry.is_source_available("barchart_live")

        if barchart_available:
            barchart_key = os.getenv("BARCHART_API_KEY")
            if barchart_key:
                try:
                    # Test authentication through registry
                    start_time = time.time()
                    test_config = {
                        "use_live_api": True,
                        "futures_symbol": "NQM25",
                        "headless": True
                    }

                    # Test source loading (includes authentication)
                    result = registry.load_source("barchart_live", test_config)
                    elapsed = time.time() - start_time

                    if result and result.get('total_contracts', 0) > 0:
                        test_results["authentication_tests"]["barchart"] = {
                            "status": "SUCCESS",
                            "elapsed_time": elapsed,
                            "api_accessible": True,
                            "error": None
                        }
                        print(f"✅ Barchart API: Authentication successful ({elapsed:.2f}s)")
                    else:
                        test_results["authentication_tests"]["barchart"] = {
                            "status": "FAILED",
                            "elapsed_time": elapsed,
                            "api_accessible": False,
                            "error": "No data returned from API"
                        }
                        print(f"❌ Barchart API: Authentication failed - no data")

                except Exception as e:
                    test_results["authentication_tests"]["barchart"] = {
                        "status": "FAILED",
                        "elapsed_time": time.time() - start_time,
                        "api_accessible": False,
                        "error": str(e)
                    }
                    print(f"❌ Barchart API: Authentication failed - {e}")
            else:
                test_results["authentication_tests"]["barchart"] = {
                    "status": "SKIPPED",
                    "reason": "API key not found in environment"
                }
                print("⚠️  Barchart API: Skipped (no API key)")
        else:
            test_results["authentication_tests"]["barchart"] = {
                "status": "UNAVAILABLE",
                "reason": "Barchart live API not available in registry"
            }
            print("⚠️  Barchart API: Not available in registry")

    except ImportError as e:
        test_results["authentication_tests"]["barchart"] = {
            "status": "UNAVAILABLE",
            "reason": f"Module import failed: {e}"
        }
        print(f"⚠️  Barchart API: Unavailable - {e}")

    # Test Polygon API Authentication
    print("\n4. Testing Polygon API Authentication")
    try:
        # Test via sources registry
        from data_ingestion.sources_registry import get_sources_registry

        registry = get_sources_registry()
        polygon_available = registry.is_source_available("polygon")

        if polygon_available:
            polygon_key = os.getenv("POLYGON_API_KEY")
            if polygon_key:
                try:
                    # Test authentication with minimal request
                    start_time = time.time()
                    test_config = {
                        "api_key": polygon_key
                    }

                    # Test API access through registry
                    result = registry.load_source("polygon", test_config)
                    elapsed = time.time() - start_time

                    if result and result.get('total_contracts', 0) >= 0:
                        test_results["authentication_tests"]["polygon"] = {
                            "status": "SUCCESS",
                            "elapsed_time": elapsed,
                            "api_accessible": True,
                            "error": None
                        }
                        print(f"✅ Polygon API: Authentication successful ({elapsed:.2f}s)")
                    else:
                        test_results["authentication_tests"]["polygon"] = {
                            "status": "FAILED",
                            "elapsed_time": elapsed,
                            "api_accessible": False,
                            "error": "No valid response from API"
                        }
                        print(f"❌ Polygon API: Authentication failed - no valid response")

                except Exception as e:
                    test_results["authentication_tests"]["polygon"] = {
                        "status": "FAILED",
                        "elapsed_time": time.time() - start_time,
                        "api_accessible": False,
                        "error": str(e)
                    }
                    print(f"❌ Polygon API: Authentication failed - {e}")
            else:
                test_results["authentication_tests"]["polygon"] = {
                    "status": "SKIPPED",
                    "reason": "API key not found in environment"
                }
                print("⚠️  Polygon API: Skipped (no API key)")
        else:
            test_results["authentication_tests"]["polygon"] = {
                "status": "UNAVAILABLE",
                "reason": "Polygon API not available in registry"
            }
            print("⚠️  Polygon API: Not available in registry")

    except ImportError as e:
        test_results["authentication_tests"]["polygon"] = {
            "status": "UNAVAILABLE",
            "reason": f"Module import failed: {e}"
        }
        print(f"⚠️  Polygon API: Unavailable - {e}")

    # Test credential security
    print("\n5. Testing Credential Security")
    security_checks = {}

    # Check for hardcoded credentials in configuration files
    config_files = [
        "config/databento_only.json",
        "config/barchart_only.json",
        "config/all_sources.json",
        "config/testing.json"
    ]

    for config_file in config_files:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                content = f.read()

            # Check for potential hardcoded credentials
            security_issues = []
            if "api_key" in content and not "${" in content:
                security_issues.append("Potential hardcoded API key")
            if "secret" in content and not "${" in content:
                security_issues.append("Potential hardcoded secret")
            if "password" in content and not "${" in content:
                security_issues.append("Potential hardcoded password")

            security_checks[config_file] = {
                "issues": security_issues,
                "secure": len(security_issues) == 0
            }

            if security_issues:
                print(f"⚠️  {config_file}: {len(security_issues)} security issues")
                for issue in security_issues:
                    print(f"     - {issue}")
            else:
                print(f"✅ {config_file}: Secure (no hardcoded credentials)")

    test_results["security_checks"] = security_checks

    # Calculate overall status
    auth_successes = sum(1 for test in test_results["authentication_tests"].values()
                        if test.get("status") == "SUCCESS")
    auth_total = len([test for test in test_results["authentication_tests"].values()
                     if test.get("status") in ["SUCCESS", "FAILED"]])

    env_found = sum(1 for env in test_results["environment_variables"].values()
                   if env["status"] == "FOUND")

    security_secure = sum(1 for check in security_checks.values() if check["secure"])
    security_total = len(security_checks)

    if auth_total > 0 and auth_successes == auth_total and security_secure == security_total:
        test_results["overall_status"] = "FULLY_READY"
    elif auth_successes > 0 and security_secure == security_total:
        test_results["overall_status"] = "PARTIALLY_READY"
    else:
        test_results["overall_status"] = "NOT_READY"

    # Generate summary
    print("\n" + "=" * 50)
    print("API AUTHENTICATION TEST SUMMARY")
    print("=" * 50)
    print(f"Environment Variables Found: {env_found}/{len(env_vars_to_check)}")
    print(f"API Authentication Tests: {auth_successes}/{auth_total} passed")
    print(f"Security Checks: {security_secure}/{security_total} secure")
    print(f"Overall Status: {test_results['overall_status']}")

    if test_results["overall_status"] == "FULLY_READY":
        print("\n🔐 ALL API AUTHENTICATION TESTS PASSED")
    elif test_results["overall_status"] == "PARTIALLY_READY":
        print("\n⚠️  SOME APIS AUTHENTICATED SUCCESSFULLY")
    else:
        print("\n❌ API AUTHENTICATION TESTS FAILED")

    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = get_eastern_time().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/api_auth_test_{timestamp}.json'

    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\n📊 Test results saved to: {results_file}")

    return test_results

if __name__ == "__main__":
    test_api_authentication()
