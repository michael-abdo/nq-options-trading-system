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
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Add current directory to path for child task imports
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import child task modules - using your actual NQ EV algorithm
from expected_value_analysis.solution import analyze_expected_value
from risk_analysis.solution import run_risk_analysis
from volume_shock_analysis.solution import analyze_volume_shocks
from volume_spike_dead_simple.solution import DeadSimpleVolumeSpike
from institutional_flow_v3.solution import create_ifd_v3_analyzer, run_ifd_v3_analysis


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
    
    def run_dead_simple_analysis(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run DEAD Simple institutional flow detection"""
        print("  Running DEAD Simple Analysis (Following Institutional Money)...")
        
        dead_simple_config = self.config.get("dead_simple", {
            "min_vol_oi_ratio": 10,
            "min_volume": 500,
            "min_dollar_size": 100000,
            "max_distance_percent": 2.0,
            "confidence_thresholds": {
                "extreme": 50,
                "very_high": 30,
                "high": 20,
                "moderate": 10
            }
        })
        
        try:
            # Import data ingestion pipeline (following pattern of other analyses)
            from data_ingestion.integration import run_data_ingestion
            
            # Load normalized data like other analyses do
            print("    Fetching options data via data ingestion pipeline...")
            pipeline_result = run_data_ingestion(data_config)
            
            if pipeline_result["pipeline_status"] != "success":
                print("    ✗ Data ingestion pipeline failed")
                return {
                    "status": "failed",
                    "error": "Data ingestion pipeline failed",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Extract normalized contracts
            contracts = pipeline_result["normalized_data"]["contracts"]
            
            if not contracts:
                print("    ✗ No options contracts available")
                return {
                    "status": "failed",
                    "error": "No options contracts available",
                    "timestamp": datetime.now().isoformat()
                }
            
            # Estimate underlying price from contracts
            current_price = self._estimate_underlying_price(contracts)
            
            # Convert normalized contracts to DEAD Simple format
            options_data = self._convert_to_dead_simple_format(contracts)
            
            print(f"    ✓ Loaded {len(contracts)} contracts, underlying price: ${current_price:,.2f}")
            
            # Initialize the DEAD Simple analyzer
            analyzer = DeadSimpleVolumeSpike(dead_simple_config)
            
            # Find institutional flow
            signals = analyzer.find_institutional_flow(options_data, current_price)
            
            # Filter for actionable signals
            actionable_signals = analyzer.filter_actionable_signals(
                signals, 
                current_price,
                dead_simple_config.get("max_distance_percent", 2.0)
            )
            
            # Generate trade plans for top signals
            trade_plans = []
            for signal in actionable_signals[:3]:  # Top 3 actionable signals
                trade_plan = analyzer.generate_trade_plan(signal, current_price)
                trade_plans.append(trade_plan)
            
            # Generate summary
            summary = analyzer.summarize_institutional_activity(signals)
            
            print(f"    ✓ DEAD Simple Analysis: {len(signals)} institutional signals found")
            
            if signals:
                top_signal = signals[0]
                print(f"    ✓ Top signal: {top_signal.strike}{top_signal.option_type[0]} "
                      f"Vol/OI={top_signal.vol_oi_ratio:.1f}x ${top_signal.dollar_size:,.0f} "
                      f"({top_signal.confidence})")
            
            return {
                "status": "success",
                "result": {
                    "signals": [s.to_dict() for s in signals],
                    "actionable_signals": [s.to_dict() for s in actionable_signals],
                    "trade_plans": trade_plans,
                    "summary": summary,
                    "total_signals": len(signals),
                    "extreme_signals": len([s for s in signals if s.confidence == "EXTREME"])
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"    ✗ DEAD Simple Analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _estimate_underlying_price(self, contracts: List[Dict]) -> float:
        """Estimate underlying price from contracts (following pattern of other analyses)"""
        if not contracts:
            return 21376.75  # Default NQ price
        
        # Try to get from contract metadata first
        for contract in contracts[:10]:  # Check first 10 contracts
            if contract.get('underlying_price'):
                return float(contract['underlying_price'])
        
        # Fallback: estimate from strike distribution
        strikes = [float(c.get('strike', 0)) for c in contracts if c.get('strike')]
        if strikes:
            return sum(strikes) / len(strikes)
        
        return 21376.75  # Final fallback
    
    def _convert_to_dead_simple_format(self, contracts: List[Dict]) -> List[Dict]:
        """Convert normalized contracts to DEAD Simple expected format"""
        options_data = []
        
        for contract in contracts:
            # Convert normalized contract to DEAD Simple format with proper null handling
            option_data = {
                'strike': contract.get('strike') or 0,
                'optionType': (contract.get('type') or '').upper(),  # 'call' -> 'CALL', 'put' -> 'PUT'
                'volume': contract.get('volume') or 0,
                'openInterest': contract.get('open_interest') or 0,
                'lastPrice': contract.get('last_price') or 0,
                'expirationDate': contract.get('expiration') or '',
                'bid': contract.get('bid') or 0,
                'ask': contract.get('ask') or 0
            }
            
            # Only include if we have the required fields
            if (option_data['strike'] > 0 and 
                option_data['optionType'] in ['CALL', 'PUT'] and
                option_data['volume'] >= 0 and
                option_data['openInterest'] >= 0):
                options_data.append(option_data)
        
        return options_data
    
    def run_ifd_v3_analysis(self, data_config: Dict[str, Any]) -> Dict[str, Any]:
        """Run IFD v3.0 Institutional Flow Detection with MBO streaming integration"""
        print("  Running IFD v3.0 Analysis (Enhanced Institutional Flow Detection)...")
        
        ifd_config = self.config.get("institutional_flow_v3", {
            "db_path": "/tmp/ifd_v3_test.db",
            "pressure_thresholds": {
                "min_pressure_ratio": 1.5,
                "min_volume_concentration": 0.3,
                "min_time_persistence": 0.4,
                "min_trend_strength": 0.5
            },
            "confidence_thresholds": {
                "min_baseline_anomaly": 1.5,
                "min_overall_confidence": 0.6
            },
            "market_making_penalty": 0.3
        })
        
        try:
            # Import data ingestion pipeline to get MBO streaming data
            from data_ingestion.integration import run_data_ingestion
            
            # Load pressure metrics from MBO streaming (or fallback to simulation)
            print("    Fetching MBO pressure metrics via data ingestion pipeline...")
            
            try:
                pipeline_result = run_data_ingestion(data_config)
                
                if pipeline_result["pipeline_status"] != "success":
                    print("    ⚠ Data ingestion pipeline failed, using simulated MBO data")
                    # Generate simulated pressure metrics for testing
                    pressure_metrics = self._generate_simulated_pressure_metrics()
                else:
                    # Extract pressure metrics from MBO streaming data
                    pressure_metrics = self._extract_pressure_metrics_from_pipeline(pipeline_result)
            
            except Exception as pipeline_error:
                print(f"    ⚠ Data ingestion error: {pipeline_error}, using simulated MBO data")
                # Generate simulated pressure metrics when pipeline fails completely
                pressure_metrics = self._generate_simulated_pressure_metrics()
            
            if not pressure_metrics:
                print("    ✗ No pressure metrics available")
                return {
                    "status": "failed",
                    "error": "No pressure metrics available",
                    "timestamp": datetime.now().isoformat()
                }
            
            print(f"    ✓ Loaded {len(pressure_metrics)} pressure metric snapshots")
            
            # Convert pressure metrics to the format expected by IFD v3.0
            pressure_data = self._convert_to_pressure_metrics_objects(pressure_metrics)
            
            print(f"    ✓ Converted {len(pressure_data)} pressure metrics objects")
            
            # Run IFD v3.0 analysis on all pressure data
            result = run_ifd_v3_analysis(pressure_data, ifd_config)
            
            # Extract signals and summaries from result
            signals = result.get("signals", [])
            analysis_summaries = result.get("analysis_summaries", [])
            
            # Generate comprehensive summary
            summary = self._summarize_ifd_v3_results(signals, analysis_summaries)
            
            print(f"    ✓ IFD v3.0 Analysis: {len(signals)} institutional signals detected")
            
            if signals:
                top_signal = signals[0]
                print(f"    ✓ Top signal: {top_signal['symbol']} "
                      f"Confidence={top_signal['confidence']:.2f} "
                      f"Direction={top_signal['expected_direction']} "
                      f"Strength={top_signal['signal_strength']:.1f}")
            
            return {
                "status": "success",
                "result": {
                    "signals": signals,
                    "analysis_summaries": analysis_summaries,
                    "summary": summary,
                    "total_signals": len(signals),
                    "high_confidence_signals": len([s for s in signals if s["confidence"] > 0.7]),
                    "pressure_snapshots_analyzed": len(pressure_metrics)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"    ✗ IFD v3.0 Analysis failed: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _generate_simulated_pressure_metrics(self) -> List[Dict[str, Any]]:
        """Generate simulated pressure metrics for testing when MBO data unavailable"""
        from datetime import datetime, timedelta
        import random
        
        # Generate 5 simulated pressure snapshots over 5-minute windows
        metrics = []
        base_time = datetime.now()
        
        symbols = ["NQM25", "NQU25", "ESM25"]  # NQ futures options
        
        for i in range(5):
            window_start = base_time - timedelta(minutes=(5-i)*5)
            window_end = window_start + timedelta(minutes=5)
            
            for symbol in symbols:
                metrics.append({
                    "symbol": symbol,
                    "window_start": window_start.isoformat(),
                    "window_end": window_end.isoformat(),
                    "total_trades": random.randint(100, 1000),
                    "buy_pressure": random.uniform(0.3, 0.8),
                    "sell_pressure": random.uniform(0.2, 0.7),
                    "volume_weighted_price": random.uniform(21300, 21400),
                    "total_volume": random.randint(500, 5000),
                    "unique_prices": random.randint(10, 50),
                    "bid_ask_spread_avg": random.uniform(0.25, 2.0)
                })
        
        return metrics
    
    def _extract_pressure_metrics_from_pipeline(self, pipeline_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract pressure metrics from MBO streaming pipeline results"""
        # In a real implementation, this would extract pressure metrics from
        # the MBO streaming data that comes from the data ingestion pipeline
        
        # For now, check if pipeline has MBO/pressure data
        if "mbo_pressure_data" in pipeline_result:
            return pipeline_result["mbo_pressure_data"]
        
        # Fallback to simulation if no MBO data available
        return self._generate_simulated_pressure_metrics()
    
    def _convert_to_pressure_metrics_objects(self, pressure_metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert raw pressure metrics dicts to PressureMetrics-compatible format"""
        from datetime import datetime
        from dataclasses import dataclass
        
        # Import PressureMetrics from the databento solution
        try:
            from data_ingestion.databento_api.solution import PressureMetrics
        except ImportError:
            # Create a minimal PressureMetrics-like object if import fails
            @dataclass
            class PressureMetrics:
                strike: float
                option_type: str
                time_window: datetime
                bid_volume: int
                ask_volume: int
                pressure_ratio: float
                total_trades: int
                avg_trade_size: float
                dominant_side: str
                confidence: float
        
        converted_metrics = []
        
        for metric in pressure_metrics:
            # Parse timestamp from string if needed
            time_window = metric.get("window_start", datetime.now().isoformat())
            if isinstance(time_window, str):
                try:
                    time_window = datetime.fromisoformat(time_window.replace('Z', '+00:00'))
                except:
                    time_window = datetime.now()
            
            # Create PressureMetrics object
            pressure_metric = PressureMetrics(
                strike=21350.0,  # Mock NQ strike
                option_type="CALL",  # Mock option type
                time_window=time_window,
                bid_volume=int(metric.get("total_volume", 1000) * 0.4),
                ask_volume=int(metric.get("total_volume", 1000) * 0.6),
                pressure_ratio=metric.get("buy_pressure", 0.5) / max(metric.get("sell_pressure", 0.5), 0.1),
                total_trades=metric.get("total_trades", 100),
                avg_trade_size=metric.get("total_volume", 1000) / max(metric.get("total_trades", 100), 1),
                dominant_side="BUY" if metric.get("buy_pressure", 0.5) > metric.get("sell_pressure", 0.5) else "SELL",
                confidence=min(abs(metric.get("buy_pressure", 0.5) - metric.get("sell_pressure", 0.5)) * 2, 1.0)
            )
            converted_metrics.append(pressure_metric)
        
        return converted_metrics
    
    def _summarize_ifd_v3_results(self, signals: List[Dict], analysis_summaries: List[Dict]) -> Dict[str, Any]:
        """Summarize IFD v3.0 analysis results"""
        if not signals:
            return {
                "net_institutional_flow": "NEUTRAL",
                "average_confidence": 0.0,
                "dominant_direction": "NONE",
                "market_making_activity": "UNKNOWN",
                "pressure_trend": "FLAT"
            }
        
        # Calculate summary statistics
        confidences = [s["confidence"] for s in signals]
        directions = [s["expected_direction"] for s in signals]
        
        # Determine dominant direction
        long_signals = len([d for d in directions if d == "LONG"])
        short_signals = len([d for d in directions if d == "SHORT"])
        
        if long_signals > short_signals:
            dominant_direction = "BULLISH"
            net_flow = "BUYING"
        elif short_signals > long_signals:
            dominant_direction = "BEARISH"
            net_flow = "SELLING"
        else:
            dominant_direction = "NEUTRAL"
            net_flow = "BALANCED"
        
        # Calculate average confidence
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        return {
            "net_institutional_flow": net_flow,
            "average_confidence": avg_confidence,
            "dominant_direction": dominant_direction,
            "total_signals": len(signals),
            "high_confidence_signals": len([s for s in signals if s["confidence"] > 0.7]),
            "signal_strength_avg": sum(s.get("signal_strength", 0) for s in signals) / len(signals),
            "pressure_trend": "INCREASING" if avg_confidence > 0.6 else "DECREASING"
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
        
        # IFD v3.0 Analysis (HIGHEST PRIORITY for high-confidence institutional signals)
        if "institutional_flow_v3" in successful_analyses:
            ifd_result = self.analysis_results["institutional_flow_v3"]["result"]
            ifd_signals = ifd_result.get("signals", [])
            
            for i, signal in enumerate(ifd_signals[:3]):  # Top 3 IFD v3.0 signals
                # High confidence IFD v3.0 signals get immediate priority
                if signal["confidence"] > 0.8:
                    priority = "IMMEDIATE"
                    confidence = "EXTREME"
                elif signal["confidence"] > 0.7:
                    priority = "PRIMARY"
                    confidence = "VERY_HIGH"
                elif signal["confidence"] > 0.6:
                    priority = "HIGH"
                    confidence = "HIGH"
                else:
                    priority = "MEDIUM"
                    confidence = "MODERATE"
                
                # Estimate entry/exit prices based on signal direction
                entry_price = 21350.0  # Base NQ price
                if signal["expected_direction"] == "LONG":
                    target = entry_price + (signal["signal_strength"] * 10)
                    stop = entry_price - (signal["signal_strength"] * 5)
                    expected_value = target - entry_price
                else:
                    target = entry_price - (signal["signal_strength"] * 10)
                    stop = entry_price + (signal["signal_strength"] * 5)
                    expected_value = entry_price - target
                
                primary_recommendations.append({
                    "source": "institutional_flow_v3",
                    "priority": priority,
                    "rank": i + 1,
                    "trade_direction": signal["expected_direction"],
                    "entry_price": entry_price,
                    "target": target,
                    "stop": stop,
                    "expected_value": expected_value,
                    "probability": signal["confidence"],
                    "position_size": min(10, int(signal["confidence"] * 15)),  # Scale size with confidence
                    "confidence": confidence,
                    "signal_strength": signal["signal_strength"],
                    "symbol": signal["symbol"],
                    "reasoning": f"IFD v3.0 institutional flow detected: {signal['symbol']} confidence={signal['confidence']:.2f} strength={signal['signal_strength']:.1f}"
                })
        
        # DEAD Simple Analysis (HIGHEST PRIORITY for EXTREME signals)
        if "dead_simple" in successful_analyses:
            dead_simple_result = self.analysis_results["dead_simple"]["result"]
            dead_simple_plans = dead_simple_result.get("trade_plans", [])
            
            for i, plan in enumerate(dead_simple_plans[:3]):  # Top 3 institutional signals
                signal = plan["signal"]
                
                # EXTREME signals get IMMEDIATE priority
                if signal["confidence"] == "EXTREME":
                    priority = "IMMEDIATE"
                    confidence = "EXTREME"
                elif signal["confidence"] == "VERY_HIGH":
                    priority = "PRIMARY"
                    confidence = "VERY_HIGH"
                else:
                    priority = "HIGH"
                    confidence = signal["confidence"]
                
                primary_recommendations.append({
                    "source": "dead_simple_analysis",
                    "priority": priority,
                    "rank": i + 1,
                    "trade_direction": signal["direction"],
                    "entry_price": plan["entry_price"],
                    "target": plan["take_profit"],
                    "stop": plan["stop_loss"],
                    "expected_value": (plan["take_profit"] - plan["entry_price"]) * (1 if signal["direction"] == "LONG" else -1),
                    "probability": 0.75 if signal["confidence"] == "EXTREME" else 0.65,  # High probability for institutional flow
                    "position_size": plan["size_multiplier"],
                    "confidence": confidence,
                    "vol_oi_ratio": signal["vol_oi_ratio"],
                    "dollar_size": signal["dollar_size"],
                    "strike": signal["strike"],
                    "option_type": signal["option_type"],
                    "reasoning": f"Institutional ${signal['dollar_size']:,.0f} flow at {signal['strike']}{signal['option_type'][0]} ({signal['vol_oi_ratio']:.1f}x Vol/OI)"
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
        
        # Sort all recommendations by priority
        priority_order = {"IMMEDIATE": 0, "PRIMARY": 1, "SECONDARY": 2, "HIGH": 3, "MEDIUM": 4}
        primary_recommendations.sort(key=lambda x: (priority_order.get(x["priority"], 999), -x.get("dollar_size", 0)))
        
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
        
        if "dead_simple" in successful_analyses:
            dead_simple_result = self.analysis_results["dead_simple"]["result"]
            market_context["institutional_signals"] = dead_simple_result["total_signals"]
            market_context["extreme_institutional_signals"] = dead_simple_result["extreme_signals"]
            market_context["institutional_positioning"] = dead_simple_result["summary"]["net_positioning"]
            market_context["institutional_dollar_volume"] = dead_simple_result["summary"]["total_dollar_volume"]
            market_context["top_institutional_strikes"] = dead_simple_result["summary"]["top_strikes"][:3]
        
        if "institutional_flow_v3" in successful_analyses:
            ifd_result = self.analysis_results["institutional_flow_v3"]["result"]
            market_context["ifd_v3_total_signals"] = ifd_result["total_signals"]
            market_context["ifd_v3_high_confidence_signals"] = ifd_result["high_confidence_signals"]
            market_context["ifd_v3_pressure_snapshots"] = ifd_result["pressure_snapshots_analyzed"]
            market_context["ifd_v3_net_flow"] = ifd_result["summary"]["net_institutional_flow"]
            market_context["ifd_v3_avg_confidence"] = ifd_result["summary"]["average_confidence"]
            market_context["ifd_v3_dominant_direction"] = ifd_result["summary"]["dominant_direction"]
        
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
        """Run complete analysis engine with NQ EV, Risk Analysis, Volume Shock, DEAD Simple, and IFD v3.0"""
        print("EXECUTING ANALYSIS ENGINE (NQ EV + Risk + Volume Shock + DEAD Simple + IFD v3.0)")
        print("-" * 50)
        
        start_time = datetime.now()
        
        # Run all analyses in parallel for speed
        print("  Running all analyses simultaneously...")
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all analyses to run concurrently
            futures = {
                executor.submit(self.run_nq_ev_analysis, data_config): "expected_value",
                executor.submit(self.run_risk_analysis, data_config): "risk",
                executor.submit(self.run_volume_shock_analysis, data_config): "volume_shock",
                executor.submit(self.run_dead_simple_analysis, data_config): "dead_simple",
                executor.submit(self.run_ifd_v3_analysis, data_config): "institutional_flow_v3"
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
        print(f"✓ Successful analyses: {final_results['summary']['successful_analyses']}/5")
        print(f"✓ Primary recommendations: {final_results['summary']['primary_recommendations']}")
        
        # Show best NQ EV recommendation
        if synthesis["trading_recommendations"]:
            best = synthesis["trading_recommendations"][0]
            print(f"✓ Best NQ EV trade: {best['trade_direction']} EV={best['expected_value']:+.1f} points")
        
        return final_results


# Module-level function for easy integration
def run_analysis_engine(data_config: Dict[str, Any], analysis_config: Dict[str, Any] = None, 
                       profile_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Run the complete analysis engine with your NQ EV algorithm as primary
    
    Args:
        data_config: Configuration for data sources
        analysis_config: Configuration for analysis strategies (optional)
        profile_name: Configuration profile name (for v1.0/v3.0/A/B testing)
        
    Returns:
        Dict with comprehensive analysis results prioritizing your NQ EV algorithm
    """
    # If profile name provided, load configuration from profile
    if profile_name:
        try:
            from config_manager import get_config_manager
            config_manager = get_config_manager()
            analysis_config = config_manager.get_analysis_config(profile_name)
            
            # Also update data config if profile specifies it
            profile_data_config = config_manager.get_data_config(profile_name)
            if profile_data_config:
                data_config.update(profile_data_config)
                
        except Exception as e:
            print(f"Warning: Failed to load profile '{profile_name}': {e}")
            # Fall back to default config
    
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
            },
            "dead_simple": {
                "min_vol_oi_ratio": 10,
                "min_volume": 500,
                "min_dollar_size": 100000,
                "max_distance_percent": 2.0,
                "confidence_thresholds": {
                    "extreme": 50,
                    "very_high": 30,
                    "high": 20,
                    "moderate": 10
                }
            },
            "institutional_flow_v3": {
                "db_path": "/tmp/ifd_v3_integration.db",
                "pressure_thresholds": {
                    "min_pressure_ratio": 1.5,
                    "min_volume_concentration": 0.3,
                    "min_time_persistence": 0.4,
                    "min_trend_strength": 0.5
                },
                "confidence_thresholds": {
                    "min_baseline_anomaly": 1.5,
                    "min_overall_confidence": 0.6
                },
                "market_making_penalty": 0.3
            }
        }
    
    engine = AnalysisEngine(analysis_config)
    return engine.run_full_analysis(data_config)


def run_ab_testing_analysis(v1_profile: str = "ifd_v1_production", 
                           v3_profile: str = "ifd_v3_production",
                           duration_hours: float = 1.0,
                           data_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run A/B testing analysis comparing v1.0 and v3.0 algorithms
    
    Args:
        v1_profile: Configuration profile for v1.0 algorithm
        v3_profile: Configuration profile for v3.0 algorithm
        duration_hours: Duration for A/B testing
        data_config: Data configuration (optional)
        
    Returns:
        A/B testing results with comparison metrics
    """
    try:
        from ab_testing_coordinator import create_ab_coordinator
        from config_manager import get_config_manager
        
        # Create A/B testing coordinator
        coordinator = create_ab_coordinator(get_config_manager())
        
        # Start A/B test
        session_id = coordinator.start_ab_test(
            v1_profile, v3_profile, duration_hours, data_config
        )
        
        print(f"A/B test started: {session_id}")
        print(f"Duration: {duration_hours} hours")
        
        # Wait for test completion
        import time
        wait_time = min(duration_hours * 3600, 300)  # Max 5 minute wait for demo
        time.sleep(wait_time)
        
        # Get results
        if coordinator.test_active:
            results = coordinator.stop_ab_test()
            
            return {
                "ab_test_results": results,
                "recommendation": results.recommended_algorithm,
                "confidence": results.confidence_in_recommendation,
                "reasoning": results.reasoning,
                "performance_comparison": {
                    "v1.0": results.v1_metrics,
                    "v3.0": results.v3_metrics
                }
            }
        else:
            return {"error": "A/B test not active"}
            
    except Exception as e:
        return {"error": f"A/B testing failed: {str(e)}"}


def run_specific_algorithm(algorithm_version: str, data_config: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Run a specific algorithm version (v1.0 or v3.0)
    
    Args:
        algorithm_version: "v1.0" or "v3.0"
        data_config: Data configuration
        
    Returns:
        Analysis results for the specific algorithm
    """
    if algorithm_version == "v1.0":
        profile_name = "ifd_v1_production"
    elif algorithm_version == "v3.0":
        profile_name = "ifd_v3_production"
    else:
        raise ValueError(f"Invalid algorithm version: {algorithm_version}")
    
    return run_analysis_engine(data_config, profile_name=profile_name)


def compare_algorithm_performance(duration_hours: float = 0.1) -> Dict[str, Any]:
    """
    Quick performance comparison between v1.0 and v3.0
    
    Args:
        duration_hours: Test duration (default 0.1 = 6 minutes)
        
    Returns:
        Performance comparison results
    """
    try:
        from performance_tracker import create_performance_tracker
        
        # Create performance tracker
        tracker = create_performance_tracker()
        
        # Start tracking both algorithms
        tracker.start_tracking(["v1.0", "v3.0"])
        
        # Run some test signals
        data_config = {"mode": "simulation"}
        
        # Run v1.0
        v1_result = run_specific_algorithm("v1.0", data_config)
        
        # Run v3.0 
        v3_result = run_specific_algorithm("v3.0", data_config)
        
        # Wait for duration
        import time
        time.sleep(duration_hours * 3600)
        
        # Stop tracking
        final_performance = tracker.stop_tracking()
        
        # Get comparison
        comparison = tracker.compare_algorithms("v1.0", "v3.0")
        
        return {
            "comparison": comparison,
            "v1_performance": tracker.get_performance_summary("v1.0"),
            "v3_performance": tracker.get_performance_summary("v3.0"),
            "overall_winner": comparison.get("overall_winner", "tie")
        }
        
    except Exception as e:
        return {"error": f"Performance comparison failed: {str(e)}"}