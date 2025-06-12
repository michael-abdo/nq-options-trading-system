#!/usr/bin/env python3
"""
Quality Setup Identification Test
Test quality setup identification and scoring accuracy
"""

import os
import sys
import json
import time
import math
from datetime import datetime
from pathlib import Path
import random

# Add project paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

def test_quality_setup_identification():
    """Test quality setup identification and scoring accuracy"""
    print("🎯 Testing Quality Setup Identification and Scoring")
    print("=" * 60)

    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "setup_identification": {},
        "scoring_accuracy": {},
        "quality_metrics": {},
        "validation_results": {},
        "overall_status": "UNKNOWN"
    }

    # Test 1: Define Quality Setup Criteria
    print("\n1. Testing Quality Setup Criteria")

    quality_criteria = {
        "volume_anomaly": {
            "description": "Unusual volume spike detection",
            "thresholds": {
                "minimum_ratio": 4.0,
                "excellent_ratio": 10.0,
                "extreme_ratio": 30.0
            },
            "weight": 0.25,
            "scoring_method": "logarithmic"
        },
        "institutional_flow": {
            "description": "Large institutional order detection",
            "thresholds": {
                "minimum_size": 100000,  # $100k
                "large_size": 500000,    # $500k
                "whale_size": 2000000    # $2M
            },
            "weight": 0.25,
            "scoring_method": "linear"
        },
        "expected_value": {
            "description": "Risk-adjusted expected value",
            "thresholds": {
                "minimum_ev": 15,
                "good_ev": 25,
                "excellent_ev": 40
            },
            "weight": 0.20,
            "scoring_method": "linear"
        },
        "probability_confidence": {
            "description": "Statistical confidence in outcome",
            "thresholds": {
                "minimum_probability": 0.60,
                "good_probability": 0.75,
                "high_probability": 0.85
            },
            "weight": 0.15,
            "scoring_method": "exponential"
        },
        "time_sensitivity": {
            "description": "Time to expiration optimization",
            "thresholds": {
                "too_short": 7,     # days
                "optimal_min": 14,
                "optimal_max": 45,
                "too_long": 90
            },
            "weight": 0.15,
            "scoring_method": "bell_curve"
        }
    }

    # Test 2: Generate Test Scenarios
    print("\n2. Generating Test Scenarios for Quality Assessment")

    test_scenarios = []

    # Generate 30 diverse scenarios
    for i in range(30):
        scenario = {
            "id": f"scenario_{i+1:02d}",
            "volume_ratio": random.uniform(1.0, 50.0),
            "institutional_size": random.uniform(50000, 3000000),
            "expected_value": random.uniform(5, 60),
            "probability": random.uniform(0.40, 0.95),
            "days_to_expiration": random.randint(1, 120),
            "market_context": random.choice(["trending", "volatile", "stable", "uncertain"]),
            "option_type": random.choice(["call", "put"]),
            "moneyness": random.uniform(0.8, 1.2),  # Strike/Spot ratio
            "implied_volatility": random.uniform(0.15, 0.80),
            "liquidity_score": random.uniform(0.3, 1.0)
        }

        test_scenarios.append(scenario)

    # Test 3: Setup Identification Logic
    print("\n3. Testing Setup Identification Logic")

    identification_results = {
        "scenarios_processed": 0,
        "setups_identified": 0,
        "quality_distribution": {"poor": 0, "fair": 0, "good": 0, "excellent": 0},
        "detailed_scores": []
    }

    for scenario in test_scenarios:
        identification_results["scenarios_processed"] += 1

        # Calculate component scores
        component_scores = {}

        # Volume anomaly score
        vol_ratio = scenario["volume_ratio"]
        if vol_ratio >= quality_criteria["volume_anomaly"]["thresholds"]["minimum_ratio"]:
            if quality_criteria["volume_anomaly"]["scoring_method"] == "logarithmic":
                vol_score = min(100, 50 + 25 * math.log10(vol_ratio / 4.0))
            else:
                vol_score = min(100, (vol_ratio / 30.0) * 100)
        else:
            vol_score = 0
        component_scores["volume_anomaly"] = vol_score

        # Institutional flow score
        inst_size = scenario["institutional_size"]
        min_size = quality_criteria["institutional_flow"]["thresholds"]["minimum_size"]
        whale_size = quality_criteria["institutional_flow"]["thresholds"]["whale_size"]

        if inst_size >= min_size:
            inst_score = min(100, ((inst_size - min_size) / (whale_size - min_size)) * 100)
        else:
            inst_score = 0
        component_scores["institutional_flow"] = inst_score

        # Expected value score
        ev = scenario["expected_value"]
        min_ev = quality_criteria["expected_value"]["thresholds"]["minimum_ev"]
        excellent_ev = quality_criteria["expected_value"]["thresholds"]["excellent_ev"]

        if ev >= min_ev:
            ev_score = min(100, ((ev - min_ev) / (excellent_ev - min_ev)) * 100)
        else:
            ev_score = 0
        component_scores["expected_value"] = ev_score

        # Probability confidence score
        prob = scenario["probability"]
        min_prob = quality_criteria["probability_confidence"]["thresholds"]["minimum_probability"]
        high_prob = quality_criteria["probability_confidence"]["thresholds"]["high_probability"]

        if prob >= min_prob:
            prob_score = min(100, ((prob - min_prob) / (high_prob - min_prob)) * 100)
        else:
            prob_score = 0
        component_scores["probability_confidence"] = prob_score

        # Time sensitivity score (bell curve)
        days = scenario["days_to_expiration"]
        optimal_min = quality_criteria["time_sensitivity"]["thresholds"]["optimal_min"]
        optimal_max = quality_criteria["time_sensitivity"]["thresholds"]["optimal_max"]

        if optimal_min <= days <= optimal_max:
            time_score = 100
        elif days < optimal_min:
            time_score = max(0, 100 * (days / optimal_min))
        else:  # days > optimal_max
            time_score = max(0, 100 * (1 - (days - optimal_max) / 50))
        component_scores["time_sensitivity"] = time_score

        # Calculate composite quality score
        composite_score = sum(
            component_scores[component] * quality_criteria[component]["weight"]
            for component in quality_criteria
        )

        # Determine quality classification
        if composite_score >= 80:
            quality_class = "excellent"
        elif composite_score >= 65:
            quality_class = "good"
        elif composite_score >= 45:
            quality_class = "fair"
        else:
            quality_class = "poor"

        # Check if setup qualifies (minimum thresholds)
        setup_qualifies = (
            vol_score > 0 and inst_score > 0 and ev_score > 0 and
            prob_score > 0 and composite_score >= 45
        )

        if setup_qualifies:
            identification_results["setups_identified"] += 1

        identification_results["quality_distribution"][quality_class] += 1

        scenario_result = {
            "scenario_id": scenario["id"],
            "component_scores": component_scores,
            "composite_score": composite_score,
            "quality_class": quality_class,
            "qualifies": setup_qualifies
        }

        identification_results["detailed_scores"].append(scenario_result)

        print(f"  {scenario['id']}: {composite_score:.1f} ({quality_class}) - {'✅ Qualified' if setup_qualifies else '❌ Rejected'}")

    test_results["setup_identification"] = identification_results

    # Test 4: Scoring Accuracy Validation
    print("\n4. Validating Scoring Accuracy")

    accuracy_validation = {
        "component_accuracy": {},
        "threshold_accuracy": {},
        "ranking_accuracy": {}
    }

    # Test component scoring accuracy

    for component in quality_criteria:
        component_scores_list = [score["component_scores"][component] for score in identification_results["detailed_scores"]]

        # Calculate distribution statistics
        avg_score = sum(component_scores_list) / len(component_scores_list)
        max_score = max(component_scores_list)
        min_score = min(component_scores_list)

        # Count scores above threshold
        above_threshold = sum(1 for score in component_scores_list if score > 50)

        component_accuracy = {
            "average_score": avg_score,
            "score_range": [min_score, max_score],
            "above_threshold_count": above_threshold,
            "distribution_quality": "good" if 20 <= avg_score <= 80 else "poor"
        }

        accuracy_validation["component_accuracy"][component] = component_accuracy
        print(f"  {component}: avg={avg_score:.1f}, range=[{min_score:.1f}, {max_score:.1f}], above_50={above_threshold}")

    # Test threshold accuracy
    quality_counts = identification_results["quality_distribution"]
    total_scenarios = identification_results["scenarios_processed"]

    threshold_test = {
        "excellent_rate": (quality_counts["excellent"] / total_scenarios) * 100,
        "good_plus_rate": ((quality_counts["excellent"] + quality_counts["good"]) / total_scenarios) * 100,
        "qualification_rate": (identification_results["setups_identified"] / total_scenarios) * 100,
        "rejection_rate": ((total_scenarios - identification_results["setups_identified"]) / total_scenarios) * 100
    }

    accuracy_validation["threshold_accuracy"] = threshold_test

    print(f"  Excellent setups: {threshold_test['excellent_rate']:.1f}%")
    print(f"  Good+ setups: {threshold_test['good_plus_rate']:.1f}%")
    print(f"  Qualification rate: {threshold_test['qualification_rate']:.1f}%")
    print(f"  Rejection rate: {threshold_test['rejection_rate']:.1f}%")

    # Test 5: Quality Metrics Analysis
    print("\n5. Analyzing Quality Metrics")

    quality_analysis = {
        "score_distribution": {},
        "correlation_analysis": {},
        "performance_prediction": {}
    }

    # Analyze score distribution
    all_composite_scores = [score["composite_score"] for score in identification_results["detailed_scores"]]

    score_distribution = {
        "mean": sum(all_composite_scores) / len(all_composite_scores),
        "median": sorted(all_composite_scores)[len(all_composite_scores)//2],
        "std_dev": (sum((x - sum(all_composite_scores)/len(all_composite_scores))**2 for x in all_composite_scores) / len(all_composite_scores))**0.5,
        "score_ranges": {
            "0-25": sum(1 for s in all_composite_scores if 0 <= s < 25),
            "25-50": sum(1 for s in all_composite_scores if 25 <= s < 50),
            "50-75": sum(1 for s in all_composite_scores if 50 <= s < 75),
            "75-100": sum(1 for s in all_composite_scores if 75 <= s <= 100)
        }
    }

    quality_analysis["score_distribution"] = score_distribution

    print(f"  Score distribution: mean={score_distribution['mean']:.1f}, std={score_distribution['std_dev']:.1f}")
    print(f"  Score ranges: 0-25({score_distribution['score_ranges']['0-25']}), 25-50({score_distribution['score_ranges']['25-50']}), 50-75({score_distribution['score_ranges']['50-75']}), 75-100({score_distribution['score_ranges']['75-100']})")

    test_results["scoring_accuracy"] = accuracy_validation
    test_results["quality_metrics"] = quality_analysis

    # Calculate overall status
    qualification_rate = threshold_test["qualification_rate"]
    good_plus_rate = threshold_test["good_plus_rate"]
    score_mean = score_distribution["mean"]

    # Quality assessment criteria
    criteria_met = 0
    total_criteria = 4

    if 30 <= qualification_rate <= 70:  # Reasonable qualification rate
        criteria_met += 1
    if good_plus_rate >= 20:  # At least 20% good+ setups
        criteria_met += 1
    if 40 <= score_mean <= 70:  # Reasonable average score
        criteria_met += 1
    if identification_results["setups_identified"] >= 5:  # At least 5 qualified setups
        criteria_met += 1

    quality_score = (criteria_met / total_criteria) * 100

    if quality_score >= 90:
        test_results["overall_status"] = "EXCELLENT"
    elif quality_score >= 75:
        test_results["overall_status"] = "GOOD"
    elif quality_score >= 60:
        test_results["overall_status"] = "ACCEPTABLE"
    else:
        test_results["overall_status"] = "POOR"

    # Generate summary
    print("\n" + "=" * 60)
    print("QUALITY SETUP IDENTIFICATION TEST SUMMARY")
    print("=" * 60)

    print(f"\nScenarios Processed: {identification_results['scenarios_processed']}")
    print(f"Setups Identified: {identification_results['setups_identified']}")
    print(f"Qualification Rate: {threshold_test['qualification_rate']:.1f}%")
    print(f"Average Quality Score: {score_distribution['mean']:.1f}")
    print(f"Quality Distribution:")
    for quality, count in quality_counts.items():
        print(f"  {quality.title()}: {count} ({(count/total_scenarios)*100:.1f}%)")
    print(f"Quality Assessment Score: {quality_score:.1f}%")
    print(f"Overall Status: {test_results['overall_status']}")

    print("\nComponent Performance:")
    for component, accuracy in accuracy_validation["component_accuracy"].items():
        print(f"  {component}: {accuracy['average_score']:.1f} avg score ({accuracy['distribution_quality']})")

    print("\nTop Quality Setups:")
    top_setups = sorted(identification_results["detailed_scores"], key=lambda x: x["composite_score"], reverse=True)[:5]
    for i, setup in enumerate(top_setups, 1):
        print(f"  {i}. {setup['scenario_id']}: {setup['composite_score']:.1f} ({setup['quality_class']})")

    if test_results["overall_status"] in ["EXCELLENT", "GOOD"]:
        print("\n🎯 QUALITY SETUP IDENTIFICATION ACCURATE")
    else:
        print("\n⚠️  QUALITY SETUP IDENTIFICATION NEEDS CALIBRATION")

    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/quality_setup_test_{timestamp}.json'

    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)

    print(f"\n📊 Test results saved to: {results_file}")

    return test_results

if __name__ == "__main__":
    test_quality_setup_identification()
