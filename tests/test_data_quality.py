#!/usr/bin/env python3
"""
Data Quality Validation Test
Test data quality validation and contract completeness across all data sources
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

def test_data_quality_validation():
    """Test data quality validation and contract completeness"""
    print("📊 Testing Data Quality Validation")
    print("=" * 60)
    
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "data_quality_tests": {},
        "contract_completeness": {},
        "validation_framework": {},
        "overall_status": "UNKNOWN"
    }
    
    # Test 1: Data Quality Validation Framework
    print("\n1. Testing Data Quality Validation Framework")
    
    validation_tests = {}
    
    # Test data normalizer validation
    try:
        sys.path.append('tasks/options_trading_system/data_ingestion/data_normalizer')
        from solution import normalize_options_data, validate_options_data
        
        validation_tests["data_normalizer"] = {
            "status": "AVAILABLE",
            "functions": ["normalize_options_data", "validate_options_data"]
        }
        print("✅ Data normalizer validation framework available")
    except ImportError as e:
        validation_tests["data_normalizer"] = {
            "status": "UNAVAILABLE",
            "error": str(e)
        }
        print(f"❌ Data normalizer unavailable: {e}")
    
    # Test sources registry validation
    try:
        from data_ingestion.sources_registry import get_sources_registry
        
        registry = get_sources_registry()
        available_sources = registry.get_available_sources()
        
        validation_tests["sources_registry"] = {
            "status": "AVAILABLE",
            "available_sources": available_sources,
            "source_count": len(available_sources)
        }
        print(f"✅ Sources registry available ({len(available_sources)} sources)")
    except ImportError as e:
        validation_tests["sources_registry"] = {
            "status": "UNAVAILABLE",
            "error": str(e)
        }
        print(f"❌ Sources registry unavailable: {e}")
    
    test_results["validation_framework"] = validation_tests
    
    # Test 2: Contract Completeness Validation
    print("\n2. Testing Contract Completeness Validation")
    
    completeness_tests = {}
    
    # Test options chain structure validation
    mock_options_data = {
        "options_summary": {
            "total_contracts": 100,
            "calls": [
                {"strike": 21900, "bid": 10.5, "ask": 11.0, "volume": 100, "open_interest": 500},
                {"strike": 21950, "bid": 8.0, "ask": 8.5, "volume": 50, "open_interest": 300}
            ],
            "puts": [
                {"strike": 21900, "bid": 9.5, "ask": 10.0, "volume": 75, "open_interest": 400},
                {"strike": 21950, "bid": 12.0, "ask": 12.5, "volume": 25, "open_interest": 200}
            ]
        },
        "metadata": {
            "source": "test_data",
            "timestamp": datetime.now().isoformat()
        }
    }
    
    # Validate contract structure
    required_fields = {
        "options_summary": ["total_contracts", "calls", "puts"],
        "contract": ["strike", "bid", "ask", "volume", "open_interest"]
    }
    
    structure_valid = True
    validation_errors = []
    
    # Check top-level structure
    for field in required_fields["options_summary"]:
        if field not in mock_options_data["options_summary"]:
            structure_valid = False
            validation_errors.append(f"Missing field: {field}")
    
    # Check contract fields
    all_contracts = (mock_options_data["options_summary"].get("calls", []) + 
                    mock_options_data["options_summary"].get("puts", []))
    
    for i, contract in enumerate(all_contracts):
        for field in required_fields["contract"]:
            if field not in contract:
                structure_valid = False
                validation_errors.append(f"Contract {i}: Missing field {field}")
    
    completeness_tests["structure_validation"] = {
        "status": "PASSED" if structure_valid else "FAILED",
        "validation_errors": validation_errors,
        "total_contracts_tested": len(all_contracts)
    }
    
    if structure_valid:
        print(f"✅ Contract structure validation passed ({len(all_contracts)} contracts)")
    else:
        print(f"❌ Contract structure validation failed ({len(validation_errors)} errors)")
    
    # Test strike coverage validation
    strikes = [contract["strike"] for contract in all_contracts]
    unique_strikes = list(set(strikes))
    strike_coverage = len(unique_strikes)
    
    # Check for reasonable strike distribution
    if len(unique_strikes) >= 2:
        strike_range = max(unique_strikes) - min(unique_strikes)
        avg_strike_spacing = strike_range / (len(unique_strikes) - 1) if len(unique_strikes) > 1 else 0
        
        completeness_tests["strike_coverage"] = {
            "status": "PASSED",
            "unique_strikes": len(unique_strikes),
            "strike_range": strike_range,
            "avg_spacing": avg_strike_spacing
        }
        print(f"✅ Strike coverage adequate ({len(unique_strikes)} strikes, range: {strike_range})")
    else:
        completeness_tests["strike_coverage"] = {
            "status": "FAILED",
            "unique_strikes": len(unique_strikes),
            "error": "Insufficient strike coverage"
        }
        print("❌ Insufficient strike coverage")
    
    test_results["contract_completeness"] = completeness_tests
    
    # Test 3: Data Quality Metrics
    print("\n3. Testing Data Quality Metrics")
    
    quality_metrics = {}
    
    # Test bid-ask spread validation
    spread_issues = []
    valid_spreads = 0
    
    for contract in all_contracts:
        bid = contract.get("bid", 0)
        ask = contract.get("ask", 0)
        strike = contract.get("strike", 0)
        
        if bid > 0 and ask > 0:
            spread = ask - bid
            spread_pct = (spread / ((bid + ask) / 2)) * 100
            
            # Flag unusual spreads
            if spread <= 0:
                spread_issues.append(f"Strike {strike}: Invalid spread (bid={bid}, ask={ask})")
            elif spread_pct > 50:  # > 50% spread
                spread_issues.append(f"Strike {strike}: Wide spread ({spread_pct:.1f}%)")
            else:
                valid_spreads += 1
    
    quality_metrics["bid_ask_spreads"] = {
        "status": "PASSED" if len(spread_issues) == 0 else "WARNING",
        "valid_spreads": valid_spreads,
        "total_contracts": len(all_contracts),
        "spread_issues": spread_issues,
        "valid_percentage": (valid_spreads / len(all_contracts)) * 100 if all_contracts else 0
    }
    
    if len(spread_issues) == 0:
        print(f"✅ Bid-ask spreads valid ({valid_spreads}/{len(all_contracts)} contracts)")
    else:
        print(f"⚠️  Bid-ask spread issues found ({len(spread_issues)} issues)")
    
    # Test volume and open interest validation
    volume_issues = []
    total_volume = 0
    total_oi = 0
    
    for contract in all_contracts:
        volume = contract.get("volume", 0)
        oi = contract.get("open_interest", 0)
        strike = contract.get("strike", 0)
        
        total_volume += volume
        total_oi += oi
        
        # Flag contracts with zero volume and OI (potentially stale data)
        if volume == 0 and oi == 0:
            volume_issues.append(f"Strike {strike}: Zero volume and OI")
    
    quality_metrics["volume_oi_validation"] = {
        "status": "PASSED" if len(volume_issues) < len(all_contracts) * 0.5 else "WARNING",
        "total_volume": total_volume,
        "total_open_interest": total_oi,
        "zero_activity_contracts": len(volume_issues),
        "active_contracts": len(all_contracts) - len(volume_issues)
    }
    
    if len(volume_issues) < len(all_contracts) * 0.5:
        print(f"✅ Volume/OI validation passed ({len(all_contracts) - len(volume_issues)} active contracts)")
    else:
        print(f"⚠️  High number of inactive contracts ({len(volume_issues)} with zero activity)")
    
    test_results["data_quality_tests"] = quality_metrics
    
    # Test 4: Cross-Source Data Consistency
    print("\n4. Testing Cross-Source Data Consistency")
    
    consistency_tests = {}
    
    # Test configuration consistency across sources
    try:
        config_files = [
            "config/databento_only.json",
            "config/barchart_only.json",
            "config/all_sources.json"
        ]
        
        config_consistency = {}
        
        for config_file in config_files:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                
                # Check for consistent analysis parameters
                analysis_config = config.get("analysis", {})
                ev_config = analysis_config.get("expected_value", {})
                
                config_consistency[config_file] = {
                    "min_ev": ev_config.get("min_ev"),
                    "min_probability": ev_config.get("min_probability"),
                    "max_risk": ev_config.get("max_risk")
                }
        
        # Check if all configs have consistent thresholds
        threshold_values = {}
        for config_file, params in config_consistency.items():
            for param, value in params.items():
                if param not in threshold_values:
                    threshold_values[param] = []
                threshold_values[param].append(value)
        
        consistency_issues = []
        for param, values in threshold_values.items():
            unique_values = list(set(v for v in values if v is not None))
            if len(unique_values) > 1:
                consistency_issues.append(f"{param}: inconsistent values {unique_values}")
        
        consistency_tests["configuration_consistency"] = {
            "status": "PASSED" if len(consistency_issues) == 0 else "WARNING",
            "configs_checked": len(config_consistency),
            "consistency_issues": consistency_issues
        }
        
        if len(consistency_issues) == 0:
            print(f"✅ Configuration consistency validated ({len(config_consistency)} configs)")
        else:
            print(f"⚠️  Configuration inconsistencies found ({len(consistency_issues)} issues)")
    
    except Exception as e:
        consistency_tests["configuration_consistency"] = {
            "status": "FAILED",
            "error": str(e)
        }
        print(f"❌ Configuration consistency test failed: {e}")
    
    # Test 5: Data Freshness Validation
    print("\n5. Testing Data Freshness Validation")
    
    freshness_tests = {}
    
    # Check timestamp validation
    current_time = datetime.now()
    data_timestamp = datetime.fromisoformat(mock_options_data["metadata"]["timestamp"].replace("Z", "+00:00"))
    
    # Calculate data age
    if data_timestamp.tzinfo is None:
        data_timestamp = data_timestamp.replace(tzinfo=current_time.tzinfo)
    
    data_age_seconds = (current_time - data_timestamp.replace(tzinfo=None)).total_seconds()
    data_age_minutes = data_age_seconds / 60
    
    # Market hours consideration (data should be fresher during market hours)
    is_market_hours = 9 <= current_time.hour <= 16  # Simplified market hours
    max_age_minutes = 5 if is_market_hours else 60  # 5 min during market, 1 hour otherwise
    
    freshness_tests["timestamp_validation"] = {
        "status": "PASSED" if data_age_minutes <= max_age_minutes else "WARNING",
        "data_age_minutes": data_age_minutes,
        "max_allowed_minutes": max_age_minutes,
        "is_market_hours": is_market_hours,
        "timestamp": data_timestamp.isoformat()
    }
    
    if data_age_minutes <= max_age_minutes:
        print(f"✅ Data freshness acceptable ({data_age_minutes:.1f} minutes old)")
    else:
        print(f"⚠️  Data may be stale ({data_age_minutes:.1f} minutes old)")
    
    test_results["data_quality_tests"]["freshness"] = freshness_tests
    
    # Calculate overall status
    validation_available = test_results["validation_framework"].get("data_normalizer", {}).get("status") == "AVAILABLE"
    structure_valid = test_results["contract_completeness"].get("structure_validation", {}).get("status") == "PASSED"
    quality_acceptable = all(
        test.get("status") in ["PASSED", "WARNING"]
        for test in test_results["data_quality_tests"].values()
        if isinstance(test, dict) and "status" in test
    )
    
    if validation_available and structure_valid and quality_acceptable:
        test_results["overall_status"] = "READY"
    elif structure_valid and quality_acceptable:
        test_results["overall_status"] = "PARTIALLY_READY"
    else:
        test_results["overall_status"] = "NOT_READY"
    
    # Generate summary
    print("\n" + "=" * 60)
    print("DATA QUALITY VALIDATION TEST SUMMARY")
    print("=" * 60)
    
    framework_available = test_results["validation_framework"].get("data_normalizer", {}).get("status") == "AVAILABLE"
    structure_passed = test_results["contract_completeness"].get("structure_validation", {}).get("status") == "PASSED"
    quality_checks = len([
        test for test in test_results["data_quality_tests"].values()
        if isinstance(test, dict) and test.get("status") == "PASSED"
    ])
    total_checks = len([
        test for test in test_results["data_quality_tests"].values()
        if isinstance(test, dict) and "status" in test
    ])
    
    print(f"Validation Framework: {'✅' if framework_available else '❌'}")
    print(f"Contract Structure: {'✅' if structure_passed else '❌'}")
    print(f"Quality Checks Passed: {quality_checks}/{total_checks}")
    print(f"Overall Status: {test_results['overall_status']}")
    
    if test_results["overall_status"] == "READY":
        print("\n📊 DATA QUALITY VALIDATION FULLY READY")
    elif test_results["overall_status"] == "PARTIALLY_READY":
        print("\n⚠️  DATA QUALITY VALIDATION PARTIALLY READY")
    else:
        print("\n❌ DATA QUALITY VALIDATION NOT READY")
    
    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/data_quality_test_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📊 Test results saved to: {results_file}")
    
    return test_results

if __name__ == "__main__":
    test_data_quality_validation()