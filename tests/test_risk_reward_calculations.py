#!/usr/bin/env python3
"""
Risk-Reward Calculations Test
Verify risk-reward calculations and position sizing logic
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

def test_risk_reward_calculations():
    """Test risk-reward calculations and position sizing logic"""
    print("💰 Testing Risk-Reward Calculations and Position Sizing")
    print("=" * 60)
    
    test_results = {
        "test_timestamp": datetime.now().isoformat(),
        "risk_calculations": {},
        "reward_calculations": {},
        "position_sizing": {},
        "validation_results": {},
        "overall_status": "UNKNOWN"
    }
    
    # Test 1: Risk Calculation Methods
    print("\n1. Testing Risk Calculation Methods")
    
    risk_calculation_tests = {
        "maximum_loss": {},
        "probability_adjusted_risk": {},
        "portfolio_risk": {},
        "risk_per_trade": {}
    }
    
    # Define test scenarios
    test_scenarios = [
        {
            "id": "scenario_1",
            "option_premium": 2.50,
            "contracts": 10,
            "contract_multiplier": 100,
            "probability_of_loss": 0.35,
            "portfolio_value": 100000,
            "max_risk_per_trade": 0.02,  # 2%
            "expected_move": 0.05  # 5%
        },
        {
            "id": "scenario_2", 
            "option_premium": 5.75,
            "contracts": 5,
            "contract_multiplier": 100,
            "probability_of_loss": 0.45,
            "portfolio_value": 250000,
            "max_risk_per_trade": 0.015,  # 1.5%
            "expected_move": 0.08  # 8%
        },
        {
            "id": "scenario_3",
            "option_premium": 1.25,
            "contracts": 20,
            "contract_multiplier": 100,
            "probability_of_loss": 0.30,
            "portfolio_value": 50000,
            "max_risk_per_trade": 0.03,  # 3%
            "expected_move": 0.03  # 3%
        }
    ]
    
    # Test maximum loss calculation
    for scenario in test_scenarios:
        max_loss = scenario["option_premium"] * scenario["contracts"] * scenario["contract_multiplier"]
        
        risk_calculation_tests["maximum_loss"][scenario["id"]] = {
            "premium": scenario["option_premium"],
            "contracts": scenario["contracts"],
            "multiplier": scenario["contract_multiplier"],
            "max_loss": max_loss,
            "portfolio_percentage": (max_loss / scenario["portfolio_value"]) * 100
        }
        
        print(f"  {scenario['id']}: Max loss ${max_loss:,.0f} ({(max_loss/scenario['portfolio_value'])*100:.2f}% of portfolio)")
    
    # Test probability-adjusted risk
    for scenario in test_scenarios:
        max_loss = scenario["option_premium"] * scenario["contracts"] * scenario["contract_multiplier"]
        prob_adjusted_risk = max_loss * scenario["probability_of_loss"]
        
        risk_calculation_tests["probability_adjusted_risk"][scenario["id"]] = {
            "max_loss": max_loss,
            "probability_of_loss": scenario["probability_of_loss"],
            "adjusted_risk": prob_adjusted_risk,
            "risk_reduction": ((max_loss - prob_adjusted_risk) / max_loss) * 100
        }
        
        print(f"  {scenario['id']}: Prob-adjusted risk ${prob_adjusted_risk:,.0f} ({scenario['probability_of_loss']*100:.1f}% prob)")
    
    test_results["risk_calculations"] = risk_calculation_tests
    
    # Test 2: Reward Calculation Methods  
    print("\n2. Testing Reward Calculation Methods")
    
    reward_calculation_tests = {
        "maximum_profit": {},
        "expected_value": {},
        "risk_reward_ratio": {},
        "probability_weighted_return": {}
    }
    
    # Calculate rewards for each scenario
    for scenario in test_scenarios:
        premium = scenario["option_premium"]
        contracts = scenario["contracts"]
        multiplier = scenario["contract_multiplier"]
        expected_move = scenario["expected_move"]
        prob_loss = scenario["probability_of_loss"]
        
        # Maximum profit calculation (simplified - assuming unlimited upside for calls)
        max_profit_per_contract = expected_move * 100  # $100 per 1% move
        max_profit = max_profit_per_contract * contracts * multiplier
        
        # Expected value calculation
        prob_profit = 1 - prob_loss
        expected_profit = max_profit * prob_profit
        max_loss = premium * contracts * multiplier
        expected_loss = max_loss * prob_loss
        expected_value = expected_profit - expected_loss
        
        # Risk-reward ratio
        risk_reward_ratio = max_profit / max_loss if max_loss > 0 else 0
        
        reward_calculation_tests["maximum_profit"][scenario["id"]] = {
            "expected_move_pct": expected_move * 100,
            "profit_per_contract": max_profit_per_contract,
            "total_max_profit": max_profit
        }
        
        reward_calculation_tests["expected_value"][scenario["id"]] = {
            "expected_profit": expected_profit,
            "expected_loss": expected_loss,
            "net_expected_value": expected_value,
            "ev_percentage": (expected_value / max_loss) * 100 if max_loss > 0 else 0
        }
        
        reward_calculation_tests["risk_reward_ratio"][scenario["id"]] = {
            "max_profit": max_profit,
            "max_loss": max_loss,
            "ratio": risk_reward_ratio,
            "ratio_quality": "excellent" if risk_reward_ratio >= 3 else "good" if risk_reward_ratio >= 2 else "fair" if risk_reward_ratio >= 1 else "poor"
        }
        
        print(f"  {scenario['id']}: Max profit ${max_profit:,.0f}, R:R ratio {risk_reward_ratio:.2f}, EV ${expected_value:,.0f}")
    
    test_results["reward_calculations"] = reward_calculation_tests
    
    # Test 3: Position Sizing Logic
    print("\n3. Testing Position Sizing Logic")
    
    position_sizing_tests = {
        "kelly_criterion": {},
        "fixed_percentage": {},
        "risk_parity": {},
        "volatility_adjusted": {}
    }
    
    for scenario in test_scenarios:
        portfolio_value = scenario["portfolio_value"]
        max_risk_pct = scenario["max_risk_per_trade"]
        premium = scenario["option_premium"]
        multiplier = scenario["contract_multiplier"]
        prob_loss = scenario["probability_of_loss"]
        expected_move = scenario["expected_move"]
        
        # Fixed percentage sizing
        max_risk_dollars = portfolio_value * max_risk_pct
        max_contracts_risk = int(max_risk_dollars / (premium * multiplier))
        
        # Kelly Criterion sizing
        prob_win = 1 - prob_loss
        win_amount = expected_move * 100  # Profit per contract
        loss_amount = premium  # Loss per contract
        
        if loss_amount > 0:
            kelly_fraction = (prob_win * win_amount - prob_loss * loss_amount) / loss_amount
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%
        else:
            kelly_fraction = 0
        
        kelly_contracts = int((portfolio_value * kelly_fraction) / (premium * multiplier))
        
        # Risk parity sizing (equal risk allocation)
        target_risk = portfolio_value * 0.01  # 1% risk target
        risk_parity_contracts = int(target_risk / (premium * multiplier))
        
        # Volatility adjusted sizing
        vol_adjustment = 1.0 / (1.0 + expected_move)  # Reduce size for higher volatility
        vol_adjusted_contracts = int(max_contracts_risk * vol_adjustment)
        
        position_sizing_tests["fixed_percentage"][scenario["id"]] = {
            "max_risk_dollars": max_risk_dollars,
            "max_contracts": max_contracts_risk,
            "actual_risk": max_contracts_risk * premium * multiplier,
            "risk_percentage": (max_contracts_risk * premium * multiplier / portfolio_value) * 100
        }
        
        position_sizing_tests["kelly_criterion"][scenario["id"]] = {
            "kelly_fraction": kelly_fraction,
            "kelly_contracts": kelly_contracts,
            "kelly_risk": kelly_contracts * premium * multiplier,
            "kelly_percentage": (kelly_contracts * premium * multiplier / portfolio_value) * 100
        }
        
        position_sizing_tests["risk_parity"][scenario["id"]] = {
            "target_risk": target_risk,
            "contracts": risk_parity_contracts,
            "actual_risk": risk_parity_contracts * premium * multiplier,
            "risk_percentage": (risk_parity_contracts * premium * multiplier / portfolio_value) * 100
        }
        
        position_sizing_tests["volatility_adjusted"][scenario["id"]] = {
            "volatility_factor": expected_move,
            "adjustment_factor": vol_adjustment,
            "contracts": vol_adjusted_contracts,
            "actual_risk": vol_adjusted_contracts * premium * multiplier,
            "risk_percentage": (vol_adjusted_contracts * premium * multiplier / portfolio_value) * 100
        }
        
        print(f"  {scenario['id']}: Fixed={max_contracts_risk}, Kelly={kelly_contracts}, Risk-Parity={risk_parity_contracts}, Vol-Adj={vol_adjusted_contracts}")
    
    test_results["position_sizing"] = position_sizing_tests
    
    # Test 4: Risk Management Validation
    print("\n4. Validating Risk Management Rules")
    
    validation_tests = {
        "portfolio_risk_limits": {},
        "correlation_risk": {},
        "liquidity_risk": {},
        "concentration_risk": {}
    }
    
    # Portfolio risk limits validation
    total_portfolio_risk = 0
    for scenario in test_scenarios:
        scenario_risk = position_sizing_tests["fixed_percentage"][scenario["id"]]["actual_risk"]
        total_portfolio_risk += scenario_risk
    
    portfolio_risk_pct = (total_portfolio_risk / test_scenarios[0]["portfolio_value"]) * 100
    
    validation_tests["portfolio_risk_limits"] = {
        "total_risk": total_portfolio_risk,
        "risk_percentage": portfolio_risk_pct,
        "risk_limit": 10.0,  # 10% max portfolio risk
        "within_limits": portfolio_risk_pct <= 10.0,
        "risk_utilization": portfolio_risk_pct / 10.0
    }
    
    # Concentration risk validation
    max_single_position = max(
        position_sizing_tests["fixed_percentage"][scenario["id"]]["risk_percentage"]
        for scenario in test_scenarios
    )
    
    validation_tests["concentration_risk"] = {
        "max_single_position_pct": max_single_position,
        "concentration_limit": 5.0,  # 5% max per position
        "within_limits": max_single_position <= 5.0,
        "largest_position_id": max(
            test_scenarios,
            key=lambda s: position_sizing_tests["fixed_percentage"][s["id"]]["risk_percentage"]
        )["id"]
    }
    
    print(f"  Portfolio risk: {portfolio_risk_pct:.2f}% ({'✅ Within limits' if portfolio_risk_pct <= 10 else '❌ Exceeds limits'})")
    print(f"  Max position: {max_single_position:.2f}% ({'✅ Within limits' if max_single_position <= 5 else '❌ Exceeds limits'})")
    
    test_results["validation_results"] = validation_tests
    
    # Test 5: Performance Metrics Calculation
    print("\n5. Calculating Performance Metrics")
    
    performance_metrics = {
        "sharpe_ratio": {},
        "sortino_ratio": {},
        "max_drawdown": {},
        "win_rate_analysis": {}
    }
    
    # Calculate aggregate metrics across all scenarios
    total_expected_return = sum(
        reward_calculation_tests["expected_value"][scenario["id"]]["net_expected_value"]
        for scenario in test_scenarios
    )
    
    total_risk = sum(
        risk_calculation_tests["probability_adjusted_risk"][scenario["id"]]["adjusted_risk"]
        for scenario in test_scenarios
    )
    
    # Simplified Sharpe ratio calculation
    risk_free_rate = 0.02  # 2% risk-free rate
    if total_risk > 0:
        sharpe_ratio = (total_expected_return - risk_free_rate * sum(s["portfolio_value"] for s in test_scenarios)) / total_risk
    else:
        sharpe_ratio = 0
    
    # Win rate analysis
    positive_ev_scenarios = sum(
        1 for scenario in test_scenarios
        if reward_calculation_tests["expected_value"][scenario["id"]]["net_expected_value"] > 0
    )
    win_rate = (positive_ev_scenarios / len(test_scenarios)) * 100
    
    performance_metrics = {
        "total_expected_return": total_expected_return,
        "total_risk": total_risk,
        "sharpe_ratio": sharpe_ratio,
        "win_rate": win_rate,
        "average_rr_ratio": sum(
            reward_calculation_tests["risk_reward_ratio"][scenario["id"]]["ratio"]
            for scenario in test_scenarios
        ) / len(test_scenarios)
    }
    
    print(f"  Total expected return: ${total_expected_return:,.0f}")
    print(f"  Total risk: ${total_risk:,.0f}")
    print(f"  Sharpe ratio: {sharpe_ratio:.2f}")
    print(f"  Win rate: {win_rate:.1f}%")
    print(f"  Average R:R ratio: {performance_metrics['average_rr_ratio']:.2f}")
    
    # Calculate overall status
    criteria_met = 0
    total_criteria = 6
    
    # Check validation criteria
    if validation_tests["portfolio_risk_limits"]["within_limits"]:
        criteria_met += 1
    if validation_tests["concentration_risk"]["within_limits"]:
        criteria_met += 1
    if performance_metrics["win_rate"] >= 60:
        criteria_met += 1
    if performance_metrics["average_rr_ratio"] >= 1.5:
        criteria_met += 1
    if performance_metrics["sharpe_ratio"] >= 0.5:
        criteria_met += 1
    if total_expected_return > 0:
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
    print("RISK-REWARD CALCULATIONS TEST SUMMARY")
    print("=" * 60)
    
    print(f"\nScenarios Tested: {len(test_scenarios)}")
    print(f"Risk Calculation Methods: {len(risk_calculation_tests)}")
    print(f"Position Sizing Methods: {len(position_sizing_tests)}")
    print(f"Performance Metrics:")
    print(f"  Expected Return: ${total_expected_return:,.0f}")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Average R:R Ratio: {performance_metrics['average_rr_ratio']:.2f}")
    print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
    print(f"Risk Management:")
    print(f"  Portfolio Risk: {validation_tests['portfolio_risk_limits']['risk_percentage']:.2f}%")
    print(f"  Max Position: {validation_tests['concentration_risk']['max_single_position_pct']:.2f}%")
    print(f"Quality Score: {quality_score:.1f}%")
    print(f"Overall Status: {test_results['overall_status']}")
    
    print("\nPosition Sizing Comparison:")
    for scenario in test_scenarios:
        fixed = position_sizing_tests["fixed_percentage"][scenario["id"]]["max_contracts"]
        kelly = position_sizing_tests["kelly_criterion"][scenario["id"]]["kelly_contracts"]
        parity = position_sizing_tests["risk_parity"][scenario["id"]]["contracts"]
        print(f"  {scenario['id']}: Fixed={fixed}, Kelly={kelly}, Parity={parity}")
    
    print("\nRisk-Reward Analysis:")
    for scenario in test_scenarios:
        rr_data = reward_calculation_tests["risk_reward_ratio"][scenario["id"]]
        ev_data = reward_calculation_tests["expected_value"][scenario["id"]]
        print(f"  {scenario['id']}: R:R={rr_data['ratio']:.2f} ({rr_data['ratio_quality']}), EV=${ev_data['net_expected_value']:,.0f}")
    
    if test_results["overall_status"] in ["EXCELLENT", "GOOD"]:
        print("\n💰 RISK-REWARD CALCULATIONS VALIDATED")
    else:
        print("\n⚠️  RISK-REWARD CALCULATIONS NEED OPTIMIZATION")
    
    # Save results
    os.makedirs('outputs/live_trading_tests', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f'outputs/live_trading_tests/risk_reward_test_{timestamp}.json'
    
    with open(results_file, 'w') as f:
        json.dump(test_results, f, indent=2)
    
    print(f"\n📊 Test results saved to: {results_file}")
    
    return test_results

if __name__ == "__main__":
    test_risk_reward_calculations()