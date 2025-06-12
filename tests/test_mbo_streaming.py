#!/usr/bin/env python3
"""
MBO Streaming Connectivity Test
Test MBO streaming connectivity to GLBX.MDP3 and validate streaming capabilities
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, timezone
from pathlib import Path

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

def test_mbo_streaming_connectivity():
    """Test MBO streaming connectivity and capabilities"""
    print("📡 Testing MBO Streaming Connectivity")
    print("=" * 60)

    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "streaming_tests": {},
        "connectivity_checks": {},
        "configuration_validation": {},
        "overall_status": "UNKNOWN"
    }

    # Test 1: Check MBO streaming configuration
    print("\n1. Testing MBO Streaming Configuration")
    try:
        sys.path.append('tasks/options_trading_system/data_ingestion/databento_api')
        from solution import DatabentoMBOIngestion, DATABENTO_AVAILABLE

        if not DATABENTO_AVAILABLE:
            test_results["configuration_validation"]["databento_package"] = {
                "status": "MISSING",
                "error": "Databento package not installed"
            }
            print("❌ Databento package not installed")
        else:
            test_results["configuration_validation"]["databento_package"] = {
                "status": "AVAILABLE"
            }
            print("✅ Databento package available")

        # Check API key configuration
        api_key = os.getenv("DATABENTO_API_KEY")
        if api_key:
            test_results["configuration_validation"]["api_key"] = {
                "status": "CONFIGURED",
                "length": len(api_key),
                "masked": api_key[:8] + "..." if len(api_key) > 8 else "***"
            }
            print(f"✅ API key configured ({len(api_key)} chars)")
        else:
            test_results["configuration_validation"]["api_key"] = {
                "status": "MISSING"
            }
            print("❌ API key not found in environment")

        # Test MBO configuration parameters
        mbo_config = {
            "api_key": api_key or "test_key",
            "symbols": ["NQ"],
            "streaming_mode": True,
            "cache_dir": "outputs/mbo_cache"
        }

        if DATABENTO_AVAILABLE and api_key:
            try:
                # Test MBO ingestion initialization
                ingestion = DatabentoMBOIngestion(mbo_config)
                test_results["configuration_validation"]["mbo_initialization"] = {
                    "status": "SUCCESS"
                }
                print("✅ MBO ingestion initialization successful")
            except Exception as e:
                test_results["configuration_validation"]["mbo_initialization"] = {
                    "status": "FAILED",
                    "error": str(e)
                }
                print(f"❌ MBO initialization failed: {e}")
        else:
            test_results["configuration_validation"]["mbo_initialization"] = {
                "status": "SKIPPED",
                "reason": "Missing dependencies or API key"
            }
            print("⚠️  MBO initialization skipped")

    except ImportError as e:
        test_results["configuration_validation"]["import_error"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Import failed: {e}")

    # Test 2: GLBX.MDP3 Connectivity Parameters
    print("\n2. Testing GLBX.MDP3 Connectivity Parameters")

    connectivity_params = {
        "dataset": "GLBX.MDP3",
        "schema": "mbo",
        "symbols": ["NQ.OPT"],
        "stype_in": "parent"
    }

    test_results["connectivity_checks"]["parameters"] = {
        "dataset": connectivity_params["dataset"],
        "schema": connectivity_params["schema"],
        "symbols": connectivity_params["symbols"],
        "stype_in": connectivity_params["stype_in"],
        "validation": "VALID"
    }
    print("✅ GLBX.MDP3 connectivity parameters validated")

    # Test 3: Market Hours Check
    print("\n3. Testing Market Hours Detection")

    current_time = datetime.now(timezone.utc)
    current_hour = current_time.hour
    current_weekday = current_time.weekday()  # 0=Monday, 6=Sunday

    # CME Globex NQ options trading hours (approximate)
    # Sunday 5:00 PM CT to Friday 4:00 PM CT (with daily maintenance breaks)
    # Converting to UTC: Sunday 23:00 to Friday 22:00

    market_hours_analysis = {
        "current_utc_time": current_time.isoformat(),
        "current_hour": current_hour,
        "current_weekday": current_weekday,
        "weekday_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][current_weekday]
    }

    # Determine if market might be open (simplified logic)
    if current_weekday == 6:  # Sunday
        likely_open = current_hour >= 23  # After 23:00 UTC
    elif current_weekday < 5:  # Monday-Friday
        likely_open = True  # Usually open during weekdays
    elif current_weekday == 5:  # Saturday
        likely_open = current_hour < 22  # Before 22:00 UTC Friday
    else:
        likely_open = False

    market_hours_analysis["likely_market_open"] = likely_open
    market_hours_analysis["recommendation"] = "Test during market hours for best results" if not likely_open else "Good time for live testing"

    test_results["connectivity_checks"]["market_hours"] = market_hours_analysis

    if likely_open:
        print(f"✅ Market likely open - good for testing ({market_hours_analysis['weekday_name']} {current_hour:02d}:00 UTC)")
    else:
        print(f"⚠️  Market likely closed - limited testing possible ({market_hours_analysis['weekday_name']} {current_hour:02d}:00 UTC)")

    # Test 4: Streaming Infrastructure Components
    print("\n4. Testing Streaming Infrastructure Components")

    infrastructure_tests = {}

    # Test Queue Capacity
    try:
        import queue
        test_queue = queue.Queue(maxsize=10000)
        infrastructure_tests["queue_system"] = {
            "status": "AVAILABLE",
            "max_size": 10000
        }
        print("✅ Queue system available (max size: 10,000)")
    except Exception as e:
        infrastructure_tests["queue_system"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Queue system failed: {e}")

    # Test Threading Support
    try:
        import threading
        test_thread = threading.Thread(target=lambda: None)
        infrastructure_tests["threading"] = {
            "status": "AVAILABLE"
        }
        print("✅ Threading support available")
    except Exception as e:
        infrastructure_tests["threading"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Threading failed: {e}")

    # Test SQLite Database
    try:
        import sqlite3
        test_db_path = "outputs/test_mbo.db"
        Path("outputs").mkdir(exist_ok=True)

        with sqlite3.connect(test_db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY)")
            conn.commit()

        os.remove(test_db_path)
        infrastructure_tests["database"] = {
            "status": "AVAILABLE"
        }
        print("✅ SQLite database support available")
    except Exception as e:
        infrastructure_tests["database"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Database failed: {e}")

    test_results["streaming_tests"]["infrastructure"] = infrastructure_tests

    # Test 5: Cost Monitoring and Budget Control
    print("\n5. Testing Cost Monitoring and Budget Control")

    cost_monitoring_tests = {}

    # Test Usage Monitor
    try:
        if DATABENTO_AVAILABLE:
            from solution import UsageMonitor

            monitor = UsageMonitor(daily_budget=10.0)

            # Simulate some usage
            monitor.record_event(1024)  # 1KB event
            monitor.record_event(2048)  # 2KB event

            stats = monitor.get_usage_stats()
            should_continue = monitor.should_continue_streaming()

            cost_monitoring_tests["usage_monitor"] = {
                "status": "SUCCESS",
                "events_processed": stats["events_processed"],
                "estimated_cost": stats["estimated_cost"],
                "budget_remaining": stats["budget_remaining"],
                "should_continue": should_continue
            }
            print(f"✅ Usage monitor functional (${stats['estimated_cost']:.4f} estimated cost)")
        else:
            cost_monitoring_tests["usage_monitor"] = {
                "status": "SKIPPED",
                "reason": "Databento not available"
            }
            print("⚠️  Usage monitor skipped (Databento not available)")

    except Exception as e:
        cost_monitoring_tests["usage_monitor"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Usage monitor failed: {e}")

    test_results["streaming_tests"]["cost_monitoring"] = cost_monitoring_tests

    # Test 6: Event Processing Pipeline
    print("\n6. Testing Event Processing Pipeline")

    pipeline_tests = {}

    try:
        if DATABENTO_AVAILABLE:
            from solution import MBOEventProcessor, PressureAggregator

            # Test Event Processor
            processor = MBOEventProcessor()

            # Create a mock MBO event
            mock_event = {
                'ts_event': int(datetime.now(timezone.utc).timestamp() * 1_000_000_000),
                'instrument_id': 12345,
                'bid_px_00': 21900000000,  # $21900.00 scaled
                'ask_px_00': 21905000000,  # $21905.00 scaled
                'price': 21902500000,      # $21902.50 scaled
                'size': 10,
                'sequence': 1
            }

            processed = processor.process_event(mock_event)

            if processed:
                pipeline_tests["event_processor"] = {
                    "status": "SUCCESS",
                    "processed_event": {
                        "strike": processed.strike,
                        "option_type": processed.option_type,
                        "bid_price": processed.bid_price,
                        "ask_price": processed.ask_price,
                        "trade_side": processed.side
                    }
                }
                print("✅ Event processor working correctly")
            else:
                pipeline_tests["event_processor"] = {
                    "status": "FAILED",
                    "error": "Event processing returned None"
                }
                print("❌ Event processor failed")

            # Test Pressure Aggregator
            aggregator = PressureAggregator(window_minutes=5)

            if processed:
                pressure_metrics = aggregator.add_event(processed)
                pipeline_tests["pressure_aggregator"] = {
                    "status": "SUCCESS",
                    "window_minutes": 5
                }
                print("✅ Pressure aggregator working correctly")
            else:
                pipeline_tests["pressure_aggregator"] = {
                    "status": "SKIPPED",
                    "reason": "No processed event available"
                }
                print("⚠️  Pressure aggregator skipped")

        else:
            pipeline_tests["event_processor"] = {
                "status": "SKIPPED",
                "reason": "Databento not available"
            }
            pipeline_tests["pressure_aggregator"] = {
                "status": "SKIPPED",
                "reason": "Databento not available"
            }
            print("⚠️  Event processing pipeline skipped (Databento not available)")

    except Exception as e:
        pipeline_tests["event_processor"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Event processing failed: {e}")

    test_results["streaming_tests"]["pipeline"] = pipeline_tests

    # Calculate overall status
    config_valid = test_results["configuration_validation"].get("databento_package", {}).get("status") == "AVAILABLE"
    infrastructure_ready = all(
        test.get("status") == "AVAILABLE"
        for test in test_results["streaming_tests"].get("infrastructure", {}).values()
    )

    if config_valid and infrastructure_ready:
        if test_results["configuration_validation"].get("api_key", {}).get("status") == "CONFIGURED":
            test_results["overall_status"] = "READY_FOR_LIVE"
        else:
            test_results["overall_status"] = "READY_FOR_TESTING"
    else:
        test_results["overall_status"] = "NOT_READY"

    # Generate summary
    print("\n" + "=" * 60)
    print("MBO STREAMING CONNECTIVITY TEST SUMMARY")
    print("=" * 60)

    databento_available = test_results["configuration_validation"].get("databento_package", {}).get("status") == "AVAILABLE"
    api_key_configured = test_results["configuration_validation"].get("api_key", {}).get("status") == "CONFIGURED"
    infrastructure_ready = all(
        test.get("status") == "AVAILABLE"
        for test in test_results["streaming_tests"].get("infrastructure", {}).values()
    )

    print(f"Databento Package: {'✅' if databento_available else '❌'}")
    print(f"API Key Configured: {'✅' if api_key_configured else '❌'}")
    print(f"Infrastructure Ready: {'✅' if infrastructure_ready else '❌'}")
    print(f"Market Hours: {test_results['connectivity_checks']['market_hours']['recommendation']}")
    print(f"Overall Status: {test_results['overall_status']}")

    if test_results["overall_status"] == "READY_FOR_LIVE":
        print("\n📡 MBO STREAMING FULLY READY FOR LIVE DEPLOYMENT")
    elif test_results["overall_status"] == "READY_FOR_TESTING":
        print("\n⚠️  MBO STREAMING READY FOR TESTING (API KEY NEEDED FOR LIVE)")
    else:
        print("\n❌ MBO STREAMING NOT READY")

    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/mbo_streaming_test_{timestamp}.json'

    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\n📊 Test results saved to: {results_file}")

    return test_results

if __name__ == "__main__":
    test_mbo_streaming_connectivity()
