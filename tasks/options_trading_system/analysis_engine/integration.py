#!/usr/bin/env python3
"""
TASK: analysis_engine
TYPE: Parent Task Integration
PURPOSE: Coordinate all analysis strategies including your actual NQ EV algorithm
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add current directory to path for child task imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import child task modules - using your actual NQ EV algorithm
from expected_value_analysis.solution import analyze_expected_value
from risk_analysis.solution import run_risk_analysis
from volume_shock_analysis.solution import analyze_volume_shocks


class AnalysisEngine:
    """Unified analysis engine coordinating your NQ EV algorithm with risk analysis"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the analysis engine
        
        Args:
            config: Configuration containing analysis settings for each strategy
        """
        self.config = config
        self.analysis_results = {}
        
    def run_nq_ev_analysis(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run your actual NQ Options Expected Value analysis"""
        print("  Running NQ Options EV Analysis (Your Algorithm)...")
        
        # Use your algorithm's configuration with strict quality criteria
        ev_config = self.config.get("expected_value", {
            "weights": {
                "oi_factor": 0.35,
                "vol_factor": 0.25,
                "pcr_factor": 0.25,
                "distance_factor": 0.15
            },
            "min_ev": 15,  # Your algorithm's strict threshold
            "min_probability": 0.60,  # Your algorithm's strict threshold
            "max_risk": 150,  # Your algorithm's strict threshold
            "min_risk_reward": 1.0  # Your algorithm's strict threshold
        })
        
        try:
            result = analyze_expected_value(data_config, ev_config)
            print(f"    ✓ NQ EV Analysis: {result['quality_setups']} quality setups found")
            
            if result.get("trading_report", {}).get("execution_recommendation"):
                rec = result["trading_report"]["execution_recommendation"]
                print(f"    ✓ Best trade: {rec['trade_direction']} EV={rec['expected_value']:+.1f} points")
            
            return {
                "status": "success",
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"    ✗ NQ EV Analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_risk_analysis(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run risk analysis (institutional positioning)"""
        print("  Running Risk Analysis...")
        
        risk_config = self.config.get("risk", {
            "multiplier": 20,
            "immediate_threat_distance": 10,
            "near_term_distance": 25,
            "medium_term_distance": 50
        })
        
        try:
            result = run_risk_analysis(data_config, risk_config)
            
            if result["status"] == "success":
                print(f"    ✓ Risk Analysis: {result['metrics']['total_positions_at_risk']} positions at risk, "
                      f"bias: {result['summary']['bias']}")
                return {
                    "status": "success",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"    ✗ Risk Analysis failed: {result.get('error', 'Unknown error')}")
                return {
                    "status": "failed",
                    "error": result.get('error', 'Unknown error'),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            print(f"    ✗ Risk Analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def run_volume_shock_analysis(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run volume shock analysis (The Egg Rush Strategy)"""
        print("  Running Volume Shock Analysis (Front-Running Market Makers)...")
        
        volume_shock_config = self.config.get("volume_shock", {
            "volume_ratio_threshold": 4.0,
            "min_volume_threshold": 100,
            "pressure_threshold": 50.0,
            "high_delta_threshold": 2000,
            "emergency_delta_threshold": 5000,
            "validation_mode": True
        })
        
        try:
            result = analyze_volume_shocks(data_config, volume_shock_config)
            
            if result["status"] == "success":
                alerts = result.get("alerts", [])
                recommendations = result.get("execution_recommendations", [])
                
                print(f"    ✓ Volume Shock Analysis: {len(alerts)} alerts, {len(recommendations)} signals")
                
                if recommendations:
                    primary_signal = recommendations[0]
                    print(f"    ✓ Primary signal: {primary_signal['trade_direction']} "
                          f"EV={primary_signal['expected_value']:+.1f} points "
                          f"({primary_signal['flow_type']})")
                
                return {
                    "status": "success",
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                print(f"    ✗ Volume Shock Analysis failed: {result.get('error', 'Unknown error')}")
                return {
                    "status": "failed",
                    "error": result.get('error', 'Unknown error'),
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            print(f"    ✗ Volume Shock Analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def synthesize_analysis_results(self) -> Dict[str, Any]:
        """Synthesize results prioritizing your NQ EV algorithm"""
        print("  Synthesizing Analysis Results (NQ EV Algorithm Priority)...")
        
        synthesis = {
            "timestamp": datetime.now().isoformat(),
            "primary_algorithm": "nq_ev_analysis",
            "analysis_summary": {},
            "trading_recommendations": [],
            "market_context": {},
            "execution_priorities": []
        }
        
        # Extract key insights from each analysis
        successful_analyses = [name for name, result in self.analysis_results.items() 
                             if result["status"] == "success"]
        
        synthesis["analysis_summary"] = {
            "total_analyses": len(self.analysis_results),
            "successful_analyses": len(successful_analyses),
            "failed_analyses": len(self.analysis_results) - len(successful_analyses),
            "analysis_types": list(self.analysis_results.keys())
        }
        
        # Prioritize your NQ EV algorithm results
        primary_recommendations = []
        
        # Your NQ EV algorithm (highest priority)
        if "expected_value" in successful_analyses:
            nq_result = self.analysis_results["expected_value"]["result"]
            
            # Extract trading recommendations from your algorithm
            if nq_result.get("trading_report", {}).get("execution_recommendation"):
                rec = nq_result["trading_report"]["execution_recommendation"]
                primary_recommendations.append({
                    "source": "nq_ev_algorithm",
                    "priority": "PRIMARY",
                    "trade_direction": rec["trade_direction"],
                    "entry_price": rec["entry_price"],
                    "target": rec["target"],
                    "stop": rec["stop"],
                    "expected_value": rec["expected_value"],
                    "probability": rec["probability"],
                    "position_size": rec["position_size"],
                    "confidence": "HIGH",
                    "reasoning": f"Your NQ EV algorithm found high-quality setup with EV={rec['expected_value']:+.1f} points"
                })
            
            # Add top opportunities from your algorithm
            for i, opp in enumerate(nq_result.get("trading_report", {}).get("top_opportunities", [])[:3], 1):
                if i > 1:  # Skip first one as it's already in primary recommendation
                    primary_recommendations.append({
                        "source": "nq_ev_algorithm",
                        "priority": "SECONDARY",
                        "rank": i,
                        "trade_direction": opp["direction"].upper(),
                        "target": opp["tp"],
                        "stop": opp["sl"],
                        "expected_value": opp["expected_value"],
                        "probability": opp["probability"],
                        "confidence": "MEDIUM",
                        "reasoning": f"Your NQ EV algorithm setup #{i} with EV={opp['expected_value']:+.1f}"
                    })
        
        # Volume Shock Analysis (High Priority - Time Sensitive)
        if "volume_shock" in successful_analyses:
            volume_result = self.analysis_results["volume_shock"]["result"]
            volume_recommendations = volume_result.get("execution_recommendations", [])
            
            for i, rec in enumerate(volume_recommendations[:2]):  # Top 2 volume shock signals
                primary_recommendations.append({
                    "source": "volume_shock_analysis",
                    "priority": "IMMEDIATE" if rec["priority"] == "PRIMARY" else "HIGH",
                    "rank": i + 1,
                    "trade_direction": rec["trade_direction"],
                    "entry_price": rec["entry_price"],
                    "target": rec["target_price"],
                    "stop": rec["stop_price"],
                    "expected_value": rec["expected_value"],
                    "probability": rec["confidence"],
                    "position_size": rec["position_size"],
                    "confidence": rec["execution_urgency"],
                    "max_hold_time": rec["max_hold_time_minutes"],
                    "flow_type": rec["flow_type"],
                    "reasoning": rec["reasoning"]
                })
        
        synthesis["trading_recommendations"] = primary_recommendations
        
        # Market context from analyses
        market_context = {}
        
        if "risk" in successful_analyses:
            risk_result = self.analysis_results["risk"]["result"]
            market_context["risk_bias"] = risk_result["summary"]["bias"]
            market_context["risk_verdict"] = risk_result["summary"]["verdict"]
            market_context["critical_zones"] = len(risk_result.get("battle_zones", []))
            market_context["total_risk_exposure"] = risk_result["metrics"]["total_risk_exposure"]
        
        if "expected_value" in successful_analyses:
            nq_result = self.analysis_results["expected_value"]["result"]
            market_context["nq_price"] = nq_result["underlying_price"]
            market_context["quality_setups"] = nq_result["quality_setups"]
            market_context["best_ev"] = nq_result["metrics"]["best_ev"]
        
        if "volume_shock" in successful_analyses:
            volume_result = self.analysis_results["volume_shock"]["result"]
            market_context["volume_shock_alerts"] = len(volume_result.get("alerts", []))
            market_context["volume_shock_intensity"] = volume_result.get("market_context", {}).get("volume_shock_intensity", {})
            market_context["execution_window"] = volume_result.get("market_context", {}).get("optimal_trading_window", {})
        
        synthesis["market_context"] = market_context
        
        # Execution priorities (your NQ EV algorithm gets highest priority)
        execution_priorities = []
        
        for i, rec in enumerate(primary_recommendations):
            if rec["priority"] == "PRIMARY":
                priority_level = "IMMEDIATE"
                reasoning = f"Your NQ EV algorithm's top recommendation with EV={rec['expected_value']:+.1f}"
            elif rec["priority"] == "SECONDARY" and i < 3:
                priority_level = "HIGH"
                reasoning = f"Your NQ EV algorithm's alternative setup #{rec.get('rank', i)}"
            else:
                priority_level = "MEDIUM"
                reasoning = f"Additional opportunity from {rec['source']}"
            
            execution_priorities.append({
                "recommendation": rec,
                "priority": priority_level,
                "reasoning": reasoning
            })
        
        synthesis["execution_priorities"] = execution_priorities
        
        print(f"    ✓ Synthesis complete: {len(primary_recommendations)} NQ EV recommendations prioritized")
        return synthesis
    
    def run_full_analysis(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run complete analysis engine with NQ EV, Risk Analysis, and Volume Shock"""
        print("EXECUTING ANALYSIS ENGINE (NQ EV + Risk + Volume Shock)")
        print("-" * 50)
        
        start_time = datetime.now()
        
        # Run all analyses in parallel for speed
        print("  Running all analyses simultaneously...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all analyses to run concurrently
            futures = {
                executor.submit(self.run_nq_ev_analysis, data_config): "expected_value",
                executor.submit(self.run_risk_analysis, data_config): "risk",
                executor.submit(self.run_volume_shock_analysis, data_config): "volume_shock"
            }
            
            # Collect results as they complete
            for future in as_completed(futures):
                analysis_name = futures[future]
                try:
                    self.analysis_results[analysis_name] = future.result()
                    if self.analysis_results[analysis_name]["status"] == "success":
                        print(f"    ✓ {analysis_name.replace('_', ' ').title()} completed")
                except Exception as e:
                    print(f"    ✗ {analysis_name} failed: {str(e)}")
                    self.analysis_results[analysis_name] = {
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
        
        print("  All analyses complete. Synthesizing results...")
        
        # Synthesize results with NQ EV priority
        synthesis = self.synthesize_analysis_results()
        
        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Final results
        final_results = {
            "timestamp": datetime.now().isoformat(),
            "execution_time_seconds": execution_time,
            "primary_algorithm": "nq_ev_analysis",
            "analysis_config": self.config,
            "individual_results": self.analysis_results,
            "synthesis": synthesis,
            "status": "success",
            "summary": {
                "successful_analyses": len([r for r in self.analysis_results.values() if r["status"] == "success"]),
                "primary_recommendations": len([r for r in synthesis["trading_recommendations"] if r["priority"] == "PRIMARY"]),
                "market_context": synthesis["market_context"],
                "execution_priorities": len(synthesis["execution_priorities"])
            }
        }
        
        print(f"\nANALYSIS ENGINE COMPLETE")
        print(f"✓ Execution time: {execution_time:.2f}s")
        print(f"✓ Successful analyses: {final_results['summary']['successful_analyses']}/3")
        print(f"✓ Primary recommendations: {final_results['summary']['primary_recommendations']}")
        
        # Show best NQ EV recommendation
        if synthesis["trading_recommendations"]:
            best = synthesis["trading_recommendations"][0]
            print(f"✓ Best NQ EV trade: {best['trade_direction']} EV={best['expected_value']:+.1f} points")
        
        return final_results


# Module-level function for easy integration
def run_analysis_engine(data_config: Dict[str, Any], analysis_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run the complete analysis engine with your NQ EV algorithm as primary
    
    Args:
        data_config: Configuration for data sources
        analysis_config: Configuration for analysis strategies (optional)
        
    Returns:
        Dict with comprehensive analysis results prioritizing your NQ EV algorithm
    """
    if analysis_config is None:
        analysis_config = {
            "expected_value": {
                # Your algorithm's configuration
                "weights": {
                    "oi_factor": 0.35,
                    "vol_factor": 0.25,
                    "pcr_factor": 0.25,
                    "distance_factor": 0.15
                },
                "min_ev": 15,
                "min_probability": 0.60,
                "max_risk": 150,
                "min_risk_reward": 1.0
            },
            "risk": {
                "multiplier": 20,
                "immediate_threat_distance": 10,
                "near_term_distance": 25,
                "medium_term_distance": 50
            },
            "volume_shock": {
                "volume_ratio_threshold": 4.0,
                "min_volume_threshold": 100,
                "pressure_threshold": 50.0,
                "high_delta_threshold": 2000,
                "emergency_delta_threshold": 5000,
                "validation_mode": True
            }
        }
    
    engine = AnalysisEngine(analysis_config)
    return engine.run_full_analysis(data_config)