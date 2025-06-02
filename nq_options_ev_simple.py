#!/usr/bin/env python3
"""
Simplified NQ Options Expected Value Trading System
Works without pandas/numpy dependencies
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import json
import re
from typing import Dict, List, Tuple, Optional
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Configuration
WEIGHTS = {
    'oi_factor': 0.35,
    'vol_factor': 0.25,
    'pcr_factor': 0.25,
    'distance_factor': 0.15
}

# Quality thresholds
MIN_EV = 15
MIN_PROBABILITY = 0.60
MAX_RISK = 150
MIN_RISK_REWARD = 1.0

# Distance weighting brackets
DISTANCE_WEIGHTS = {
    0.01: 1.0,  # 0-1%
    0.02: 0.8,  # 1-2%
    0.05: 0.5,  # 2-5%
    1.00: 0.2   # 5%+
}


class OptionsStrike:
    """Represents a single options strike with call and put data"""
    def __init__(self, price: float, call_volume: int, call_oi: int, call_premium: float,
                 put_volume: int, put_oi: int, put_premium: float):
        self.price = price
        self.call_volume = call_volume
        self.call_oi = call_oi
        self.call_premium = call_premium
        self.put_volume = put_volume
        self.put_oi = put_oi
        self.put_premium = put_premium


class TradeSetup:
    """Represents a potential trade setup with calculated metrics"""
    def __init__(self, tp: float, sl: float, direction: str, probability: float,
                 reward: float, risk: float, ev: float):
        self.tp = tp
        self.sl = sl
        self.direction = direction
        self.probability = probability
        self.reward = reward
        self.risk = risk
        self.ev = ev
        self.risk_reward = reward / risk if risk > 0 else 0


def get_current_contract_url() -> str:
    """Generate the Barchart URL for the current NQ options contract"""
    now = datetime.now()
    
    # Find the next quarterly expiration (Mar, Jun, Sep, Dec)
    # Contract months: H=Mar(3), M=Jun(6), U=Sep(9), Z=Dec(12)
    month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
    quarterly_months = [3, 6, 9, 12]
    
    # Find next quarterly month
    current_month = now.month
    current_year = now.year
    
    for month in quarterly_months:
        if month >= current_month:
            contract_month = month
            contract_year = current_year
            break
    else:
        contract_month = 3
        contract_year = current_year + 1
    
    # Get month code
    month_code = month_codes[contract_month]
    year_suffix = str(contract_year)[-2:]
    
    # NQ futures symbol
    futures_symbol = f"NQ{month_code}{year_suffix}"
    
    # Options symbol (MC prefix for CME options)
    # For June 2025: MC6M25
    options_symbol = f"MC{contract_month}{month_code}{year_suffix}"
    
    url = f"https://www.barchart.com/futures/quotes/{futures_symbol}/options/{options_symbol}?futuresOptionsView=merged"
    
    logger.info(f"Generated URL for {futures_symbol}: {url}")
    return url


def get_sample_data() -> List[OptionsStrike]:
    """Return sample data from the markdown example"""
    sample_data = [
        (21200, 250, 1500, 2.50, 800, 5200, 8.75),
        (21250, 180, 1200, 4.25, 650, 4800, 12.50),
        (21300, 320, 2100, 7.50, 920, 6500, 18.25),
        (21350, 450, 3200, 12.75, 1100, 7200, 26.50),
        (21400, 850, 5500, 22.50, 1350, 8900, 38.75),
        (21450, 1200, 8200, 35.25, 1580, 9500, 55.50),
        (21500, 980, 6800, 52.75, 1820, 8800, 78.25),
    ]
    
    return [OptionsStrike(*data) for data in sample_data]


def get_distance_weight(distance_pct: float) -> float:
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


def calculate_probability(current_price: float, tp: float, sl: float, 
                         strikes: List[OptionsStrike], direction: str) -> float:
    """Calculate probability of reaching TP before SL"""
    
    # Calculate factors
    oi_factor = 0
    vol_factor = 0
    pcr_factor = 0
    
    max_oi = max([s.call_oi + s.put_oi for s in strikes]) if strikes else 1
    max_vol = max([s.call_volume + s.put_volume for s in strikes]) if strikes else 1
    
    total_call_premium = sum([s.call_premium * s.call_oi for s in strikes])
    total_put_premium = sum([s.put_premium * s.put_oi for s in strikes])
    
    for strike in strikes:
        distance_pct = (strike.price - current_price) / current_price
        distance_weight = get_distance_weight(distance_pct)
        
        # Determine if strike supports direction
        if direction == 'long':
            direction_modifier = 1 if strike.price > current_price else -0.5
        else:
            direction_modifier = 1 if strike.price < current_price else -0.5
        
        # OI Factor
        strike_oi = strike.call_oi + strike.put_oi
        oi_factor += (strike_oi * distance_weight * direction_modifier) / max_oi
        
        # Volume Factor
        strike_vol = strike.call_volume + strike.put_volume
        vol_factor += (strike_vol * distance_weight * direction_modifier) / max_vol
    
    # PCR Factor
    if total_call_premium + total_put_premium > 0:
        pcr_factor = (total_call_premium - total_put_premium) / (total_call_premium + total_put_premium)
        if direction == 'short':
            pcr_factor = -pcr_factor
    
    # Distance Factor
    distance_factor = 1 - (abs(current_price - tp) / current_price)
    
    # Normalize factors
    oi_factor = max(0, min(1, oi_factor))
    vol_factor = max(0, min(1, vol_factor))
    pcr_factor = (pcr_factor + 1) / 2  # Convert from [-1, 1] to [0, 1]
    distance_factor = max(0, min(1, distance_factor))
    
    # Calculate weighted probability
    probability = (
        WEIGHTS['oi_factor'] * oi_factor +
        WEIGHTS['vol_factor'] * vol_factor +
        WEIGHTS['pcr_factor'] * pcr_factor +
        WEIGHTS['distance_factor'] * distance_factor
    )
    
    # Clamp between 10% and 90%
    probability = max(0.1, min(0.9, probability))
    
    return probability


def calculate_ev_for_all_combinations(current_price: float, 
                                     strikes: List[OptionsStrike]) -> List[TradeSetup]:
    """Calculate EV for all valid TP/SL combinations"""
    setups = []
    
    # Get all strike prices
    strike_prices = sorted([s.price for s in strikes])
    
    # Test all combinations
    for tp in strike_prices:
        for sl in strike_prices:
            # Long setup
            if tp > current_price > sl:
                reward = tp - current_price
                risk = current_price - sl
                
                if risk <= MAX_RISK and reward / risk >= MIN_RISK_REWARD:
                    prob = calculate_probability(current_price, tp, sl, strikes, 'long')
                    ev = (prob * reward) - ((1 - prob) * risk)
                    
                    setups.append(TradeSetup(tp, sl, 'long', prob, reward, risk, ev))
            
            # Short setup
            elif tp < current_price < sl:
                reward = current_price - tp
                risk = sl - current_price
                
                if risk <= MAX_RISK and reward / risk >= MIN_RISK_REWARD:
                    prob = calculate_probability(current_price, tp, sl, strikes, 'short')
                    ev = (prob * reward) - ((1 - prob) * risk)
                    
                    setups.append(TradeSetup(tp, sl, 'short', prob, reward, risk, ev))
    
    # Sort by EV
    setups.sort(key=lambda x: x.ev, reverse=True)
    
    return setups


def filter_quality_setups(setups: List[TradeSetup]) -> List[TradeSetup]:
    """Filter setups by quality criteria"""
    return [s for s in setups if 
            s.ev >= MIN_EV and 
            s.probability >= MIN_PROBABILITY and 
            s.risk <= MAX_RISK and 
            s.risk_reward >= MIN_RISK_REWARD]


def generate_report(current_price: float, setups: List[TradeSetup]) -> str:
    """Generate trading report"""
    report = []
    report.append(f"\n{'='*80}")
    report.append(f"NQ OPTIONS EV TRADING SYSTEM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"{'='*80}")
    report.append(f"\nCurrent NQ Price: {current_price:,.2f}")
    report.append(f"\nTop 5 Trading Opportunities:")
    report.append("-" * 80)
    report.append(f"{'Rank':<5} {'Direction':<10} {'TP':<10} {'SL':<10} {'Prob':<8} {'RR':<8} {'EV':<10}")
    report.append("-" * 80)
    
    for i, setup in enumerate(setups[:5], 1):
        report.append(
            f"{i:<5} {setup.direction:<10} {setup.tp:<10.0f} {setup.sl:<10.0f} "
            f"{setup.probability:<8.1%} {setup.risk_reward:<8.1f} {setup.ev:+10.1f}"
        )
    
    if setups:
        best = setups[0]
        position_size = "LARGE (15-20%)" if best.ev > 50 else "MEDIUM (10-15%)" if best.ev > 30 else "SMALL (5-10%)"
        
        report.append(f"\n{'='*80}")
        report.append("EXECUTION RECOMMENDATION:")
        report.append(f"Recommended Trade: {best.direction.upper()} NQ")
        report.append(f"Entry: Current price ({current_price:,.2f})")
        report.append(f"Target: {best.tp:,.0f} ({best.reward:+.0f} points)")
        report.append(f"Stop: {best.sl:,.0f} ({-best.risk:.0f} points)")
        report.append(f"Position Size: {position_size}")
        report.append(f"Expected Value: {best.ev:+.1f} points per trade")
        report.append(f"{'='*80}\n")
    
    return '\n'.join(report)


def main():
    """Main execution function"""
    try:
        # Use sample data for demonstration
        logger.info("Using sample data for demonstration...")
        current_price = 21376.75
        strikes = get_sample_data()
        
        # Calculate EV for all combinations
        logger.info("Calculating EV for all TP/SL combinations...")
        all_setups = calculate_ev_for_all_combinations(current_price, strikes)
        
        # Filter quality setups
        quality_setups = filter_quality_setups(all_setups)
        logger.info(f"Found {len(quality_setups)} quality setups")
        
        # Generate report
        report = generate_report(current_price, quality_setups)
        print(report)
        
        # Save report to file
        filename = f"nq_ev_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        logger.info(f"Report saved to {filename}")
        
        # Return best opportunities for programmatic use
        return quality_setups[:5] if quality_setups else []
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")
        raise


if __name__ == "__main__":
    main()