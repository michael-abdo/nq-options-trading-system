#!/usr/bin/env python3
"""
Expected Value Strategy - Converted from original EV algorithm
Analyzes options data to find highest expected value trading opportunities
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from core.data_models import OptionsChain, AnalysisResult, DataRequirements, OptionType
from plugins.strategies.base import BaseStrategy


class ExpectedValueStrategy(BaseStrategy):
    """Expected Value analysis strategy"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Load configuration with defaults
        weights = config.get("weights", {})
        self.weights = {
            'oi_factor': weights.get('oi_factor', 0.35),
            'vol_factor': weights.get('vol_factor', 0.25),
            'pcr_factor': weights.get('pcr_factor', 0.25),
            'distance_factor': weights.get('distance_factor', 0.15)
        }
        
        self.min_ev = config.get("min_ev", 15)
        self.min_probability = config.get("min_probability", 0.60)
        self.max_risk = config.get("max_risk", 150)
        self.min_risk_reward = config.get("min_risk_reward", 1.0)
        
    def get_requirements(self) -> DataRequirements:
        """Define data requirements for EV strategy"""
        return DataRequirements(
            requires_volume=True,
            requires_open_interest=True,
            requires_prices=True,
            min_contracts=10,
            max_age_hours=24
        )
    
    def analyze(self, data: OptionsChain) -> AnalysisResult:
        """Perform Expected Value analysis"""
        self.log_analysis_start(data)
        result = self.create_result(data)
        
        # Filter to liquid contracts near current price
        price_range = data.underlying_price * 0.05  # ±5%
        liquid_contracts = self.filter_contracts(
            data.contracts,
            strike_min=data.underlying_price - price_range,
            strike_max=data.underlying_price + price_range,
            require_volume=False,  # Allow contracts without volume if they have OI
            require_oi=False
        )
        
        if len(liquid_contracts) < 10:
            result.add_warning(f"Limited liquid contracts: {len(liquid_contracts)}")
            liquid_contracts = data.contracts  # Use all contracts if too few liquid ones
        
        self.logger.info(f"🎯 Analyzing {len(liquid_contracts)} contracts within ±5% of current price")
        
        # Calculate EV for all valid combinations
        setups = self._calculate_ev_combinations(data.underlying_price, liquid_contracts)
        
        # Filter quality setups
        quality_setups = self._filter_quality_setups(setups)
        
        # Add top setups as signals
        for i, setup in enumerate(quality_setups[:5]):
            result.add_signal(
                signal_type="trade_opportunity",
                confidence=setup["probability"],
                rank=i + 1,
                direction=setup["direction"],
                target_price=setup["tp"],
                stop_loss=setup["sl"],
                reward=setup["reward"],
                risk=setup["risk"],
                risk_reward_ratio=setup["rr"],
                expected_value=setup["ev"]
            )
        
        # Add metrics
        if quality_setups:
            best_setup = quality_setups[0]
            result.add_metric("best_ev", best_setup["ev"])
            result.add_metric("best_probability", best_setup["probability"])
            result.add_metric("best_risk_reward", best_setup["rr"])
            result.add_metric("total_opportunities", len(quality_setups))
        
        # Calculate additional metrics
        calls = [c for c in liquid_contracts if c.option_type == OptionType.CALL]
        puts = [c for c in liquid_contracts if c.option_type == OptionType.PUT]
        
        result.add_metric("pcr_volume", self.calculate_pcr_ratio(calls, puts, "volume"))
        result.add_metric("pcr_oi", self.calculate_pcr_ratio(calls, puts, "open_interest"))
        result.add_metric("total_volume", sum(c.volume or 0 for c in liquid_contracts))
        result.add_metric("total_oi", sum(c.open_interest or 0 for c in liquid_contracts))
        
        self.log_analysis_complete(result)
        return result
    
    def _calculate_ev_combinations(self, current_price: float, contracts: List) -> List[Dict]:
        """Calculate EV for all valid TP/SL combinations"""
        self.logger.info("🧮 Calculating EV for all combinations...")
        
        setups = []
        strikes = sorted(set(c.strike for c in contracts))
        
        total_combinations = len(strikes) * len(strikes)
        valid_combinations = 0
        
        for tp in strikes:
            for sl in strikes:
                # Long setup: TP > current > SL
                if tp > current_price > sl:
                    reward = tp - current_price
                    risk = current_price - sl
                    
                    if risk <= self.max_risk and reward / risk >= self.min_risk_reward:
                        prob = self._calculate_probability(current_price, tp, sl, contracts, 'long')
                        ev = (prob * reward) - ((1 - prob) * risk)
                        
                        setup = {
                            "direction": "long",
                            "tp": tp,
                            "sl": sl,
                            "reward": reward,
                            "risk": risk,
                            "rr": reward / risk,
                            "probability": prob,
                            "ev": ev
                        }
                        setups.append(setup)
                        valid_combinations += 1
                
                # Short setup: SL > current > TP
                elif tp < current_price < sl:
                    reward = current_price - tp
                    risk = sl - current_price
                    
                    if risk <= self.max_risk and reward / risk >= self.min_risk_reward:
                        prob = self._calculate_probability(current_price, tp, sl, contracts, 'short')
                        ev = (prob * reward) - ((1 - prob) * risk)
                        
                        setup = {
                            "direction": "short",
                            "tp": tp,
                            "sl": sl,
                            "reward": reward,
                            "risk": risk,
                            "rr": reward / risk,
                            "probability": prob,
                            "ev": ev
                        }
                        setups.append(setup)
                        valid_combinations += 1
        
        self.logger.info(f"📊 Tested {total_combinations} combinations, found {valid_combinations} valid setups")
        
        # Sort by EV (best first)
        setups.sort(key=lambda x: x["ev"], reverse=True)
        return setups
    
    def _calculate_probability(self, current_price: float, tp: float, sl: float, 
                              contracts: List, direction: str) -> float:
        """Calculate probability using Volume/OI weighted factors"""
        
        if not contracts:
            return 0.5  # Default if no data
        
        # Calculate factors
        max_oi = max((c.open_interest or 0) + (c.open_interest or 0) for c in contracts)
        max_vol = max((c.volume or 0) + (c.volume or 0) for c in contracts)
        
        if max_oi == 0:
            max_oi = 1
        if max_vol == 0:
            max_vol = 1
        
        # Calculate weighted factors
        oi_factor = 0
        vol_factor = 0
        
        calls = [c for c in contracts if c.option_type == OptionType.CALL]
        puts = [c for c in contracts if c.option_type == OptionType.PUT]
        
        # Process each contract
        for contract in contracts:
            distance_pct = (contract.strike - current_price) / current_price
            distance_weight = self._get_distance_weight(distance_pct)
            
            # Determine if strike supports direction
            if direction == 'long':
                direction_modifier = 1 if contract.strike > current_price else -0.5
            else:
                direction_modifier = 1 if contract.strike < current_price else -0.5
            
            # OI Factor
            contract_oi = contract.open_interest or 0
            oi_contribution = (contract_oi * distance_weight * direction_modifier) / max_oi
            oi_factor += oi_contribution
            
            # Volume Factor
            contract_vol = contract.volume or 0
            vol_contribution = (contract_vol * distance_weight * direction_modifier) / max_vol
            vol_factor += vol_contribution
        
        # PCR Factor
        total_call_premium = sum((c.last_price or 0) * (c.open_interest or 0) for c in calls)
        total_put_premium = sum((p.last_price or 0) * (p.open_interest or 0) for p in puts)
        
        pcr_factor = 0
        if total_call_premium + total_put_premium > 0:
            pcr_factor = (total_call_premium - total_put_premium) / (total_call_premium + total_put_premium)
            if direction == 'short':
                pcr_factor = -pcr_factor
        
        # Distance Factor
        distance_factor = 1 - (abs(current_price - tp) / current_price)
        
        # Normalize factors to [0, 1] range
        oi_factor = max(0, min(1, oi_factor))
        vol_factor = max(0, min(1, vol_factor))
        pcr_factor = (pcr_factor + 1) / 2  # Convert from [-1, 1] to [0, 1]
        distance_factor = max(0, min(1, distance_factor))
        
        # Calculate weighted probability
        probability = (
            self.weights['oi_factor'] * oi_factor +
            self.weights['vol_factor'] * vol_factor +
            self.weights['pcr_factor'] * pcr_factor +
            self.weights['distance_factor'] * distance_factor
        )
        
        # Clamp between 10% and 90% for realistic probability range
        probability = max(0.1, min(0.9, probability))
        
        return probability
    
    def _get_distance_weight(self, distance_pct: float) -> float:
        """Get weight based on distance from current price"""
        distance_pct = abs(distance_pct)
        
        if distance_pct <= 0.01:
            return 1.0
        elif distance_pct <= 0.02:
            return 0.8
        elif distance_pct <= 0.05:
            return 0.5
        else:
            return 0.2
    
    def _filter_quality_setups(self, setups: List[Dict]) -> List[Dict]:
        """Filter setups by quality criteria"""
        self.logger.info("🔍 Filtering setups by quality criteria...")
        
        quality_setups = []
        
        for setup in setups:
            if (setup["ev"] >= self.min_ev and 
                setup["probability"] >= self.min_probability and 
                setup["risk"] <= self.max_risk and 
                setup["rr"] >= self.min_risk_reward):
                quality_setups.append(setup)
        
        self.logger.info(f"✅ Filtered to {len(quality_setups)} quality setups")
        return quality_setups