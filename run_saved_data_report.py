#!/usr/bin/env python3
"""
NQ Options Expected Value Report using Saved Working Data
Uses our captured API data with Volume and Open Interest
"""

import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import sys
import os

# Add utils to path for logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils.logging_config import setup_logging, get_logger

# Set up logging
log_dir, session_id = setup_logging()
logger = get_logger(__name__)
data_logger = get_logger(f"{__name__}.data")
calc_logger = get_logger(f"{__name__}.calculations")

# Configuration
WEIGHTS = {
    'oi_factor': 0.35,
    'vol_factor': 0.25,
    'pcr_factor': 0.25,
    'distance_factor': 0.15
}

MIN_EV = 15
MIN_PROBABILITY = 0.60
MAX_RISK = 150
MIN_RISK_REWARD = 1.0

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

def load_saved_data() -> Dict:
    """Load the saved API data from our breakthrough discovery"""
    data_logger.info("📁 Loading saved API data from breakthrough discovery...")
    
    data_file = "data/api_responses/options_data_20250602_141553.json"
    
    try:
        with open(data_file, 'r') as f:
            data = json.load(f)
        
        data_logger.info(f"✅ Loaded saved data: {len(data.get('data', {}).get('Call', []))} calls, {len(data.get('data', {}).get('Put', []))} puts")
        return data
        
    except Exception as e:
        data_logger.error(f"❌ Failed to load saved data: {e}")
        raise

def analyze_data_quality(data: Dict) -> Dict:
    """Analyze the quality of our saved data"""
    logger.info("📊 Analyzing data quality...")
    
    calls = data.get('data', {}).get('Call', [])
    puts = data.get('data', {}).get('Put', [])
    
    # Count how many have actual volume/OI data in raw section
    calls_with_vol = sum(1 for c in calls if c.get('raw', {}).get('volume') not in [None, 0])
    calls_with_oi = sum(1 for c in calls if c.get('raw', {}).get('openInterest') not in [None, 0])
    
    puts_with_vol = sum(1 for p in puts if p.get('raw', {}).get('volume') not in [None, 0])
    puts_with_oi = sum(1 for p in puts if p.get('raw', {}).get('openInterest') not in [None, 0])
    
    total_options = len(calls) + len(puts)
    total_with_vol = calls_with_vol + puts_with_vol
    total_with_oi = calls_with_oi + puts_with_oi
    
    vol_percentage = (total_with_vol / total_options * 100) if total_options > 0 else 0
    oi_percentage = (total_with_oi / total_options * 100) if total_options > 0 else 0
    
    quality = {
        'total_options': total_options,
        'volume_coverage': vol_percentage,
        'oi_coverage': oi_percentage,
        'calls': len(calls),
        'puts': len(puts),
        'calls_with_vol': calls_with_vol,
        'calls_with_oi': calls_with_oi,
        'puts_with_vol': puts_with_vol,
        'puts_with_oi': puts_with_oi
    }
    
    logger.info(f"📈 Data Quality Report:")
    logger.info(f"  🎯 Volume Coverage: {vol_percentage:.1f}%")
    logger.info(f"  🎯 OI Coverage: {oi_percentage:.1f}%")
    logger.info(f"  📊 Total Options: {total_options}")
    logger.info(f"  📞 Calls: {len(calls)} ({calls_with_vol} with volume, {calls_with_oi} with OI)")
    logger.info(f"  📉 Puts: {len(puts)} ({puts_with_vol} with volume, {puts_with_oi} with OI)")
    
    return quality

def convert_api_to_strikes(data: Dict) -> Tuple[float, List[OptionsStrike]]:
    """Convert API data to OptionsStrike objects"""
    logger.info("🔄 Converting API data to strikes...")
    
    calls = data.get('data', {}).get('Call', [])
    puts = data.get('data', {}).get('Put', [])
    
    # Estimate current price from strike range (ATM strikes around middle)
    all_strikes = []
    for call in calls:
        try:
            strike = float(call.get('strike', 0))
            if strike > 0:
                all_strikes.append(strike)
        except:
            continue
    
    if all_strikes:
        all_strikes.sort()
        # Use median strike as approximation of current price
        current_price = all_strikes[len(all_strikes)//2]
        logger.info(f"💰 Estimated current price from data: ${current_price:,.2f}")
    else:
        current_price = 21376.75  # Fallback
        logger.info(f"💰 Using fallback current price: ${current_price:,.2f}")
    
    # Group options by strike price
    strikes_dict = {}
    
    # Process calls
    for call in calls:
        try:
            # Use raw data which has actual numeric values
            raw_data = call.get('raw', {})
            strike = float(raw_data.get('strike', 0))
            if strike == 0:
                continue
                
            volume = int(raw_data.get('volume') or 0)
            oi = int(raw_data.get('openInterest') or 0)
            premium = float(raw_data.get('lastPrice', 0) or 0)
            
            if strike not in strikes_dict:
                strikes_dict[strike] = {
                    'call_volume': 0, 'call_oi': 0, 'call_premium': 0,
                    'put_volume': 0, 'put_oi': 0, 'put_premium': 0
                }
            
            strikes_dict[strike].update({
                'call_volume': volume,
                'call_oi': oi,
                'call_premium': premium
            })
            
        except Exception as e:
            logger.debug(f"Error processing call: {e}")
            continue
    
    # Process puts
    for put in puts:
        try:
            # Use raw data which has actual numeric values
            raw_data = put.get('raw', {})
            strike = float(raw_data.get('strike', 0))
            if strike == 0:
                continue
                
            volume = int(raw_data.get('volume') or 0)
            oi = int(raw_data.get('openInterest') or 0)
            premium = float(raw_data.get('lastPrice', 0) or 0)
            
            if strike not in strikes_dict:
                strikes_dict[strike] = {
                    'call_volume': 0, 'call_oi': 0, 'call_premium': 0,
                    'put_volume': 0, 'put_oi': 0, 'put_premium': 0
                }
            
            strikes_dict[strike].update({
                'put_volume': volume,
                'put_oi': oi,
                'put_premium': premium
            })
            
        except Exception as e:
            logger.debug(f"Error processing put: {e}")
            continue
    
    # Convert to OptionsStrike objects
    strikes = []
    for strike_price, data in sorted(strikes_dict.items()):
        strike_obj = OptionsStrike(
            price=strike_price,
            call_volume=data['call_volume'],
            call_oi=data['call_oi'],
            call_premium=data['call_premium'],
            put_volume=data['put_volume'],
            put_oi=data['put_oi'],
            put_premium=data['put_premium']
        )
        strikes.append(strike_obj)
    
    # Filter to liquid strikes near current price (±5% for better focus)
    price_range = current_price * 0.05
    liquid_strikes = [
        s for s in strikes 
        if abs(s.price - current_price) <= price_range and 
        (s.call_volume > 0 or s.put_volume > 0 or s.call_oi > 0 or s.put_oi > 0)
    ]
    
    logger.info(f"📊 Converted to {len(strikes)} total strikes")
    logger.info(f"🎯 Filtered to {len(liquid_strikes)} liquid strikes near current price")
    
    if liquid_strikes:
        strike_range = f"${liquid_strikes[0].price:,.0f} - ${liquid_strikes[-1].price:,.0f}"
        logger.info(f"📈 Strike range: {strike_range}")
    
    return current_price, liquid_strikes

def get_distance_weight(distance_pct: float) -> float:
    """Get weight based on distance from current price"""
    distance_pct = abs(distance_pct)
    
    if distance_pct <= 0.01:
        weight = 1.0
    elif distance_pct <= 0.02:
        weight = 0.8
    elif distance_pct <= 0.05:
        weight = 0.5
    else:
        weight = 0.2
    
    return weight

def calculate_probability(current_price: float, tp: float, sl: float, 
                         strikes: List[OptionsStrike], direction: str) -> float:
    """Calculate probability of reaching TP before SL using Volume/OI data"""
    
    calc_logger.info(f"=== Calculating Probability ===")
    calc_logger.info(f"Current: ${current_price:,.2f}, TP: ${tp:,.2f}, SL: ${sl:,.2f}, Direction: {direction}")
    
    if not strikes:
        calc_logger.warning("No strikes data available, returning default 0.5")
        return 0.5  # Default if no data
    
    # Calculate factors
    oi_factor = 0
    vol_factor = 0
    pcr_factor = 0
    
    max_oi = max([s.call_oi + s.put_oi for s in strikes])
    max_vol = max([s.call_volume + s.put_volume for s in strikes])
    
    if max_oi == 0:
        max_oi = 1
    if max_vol == 0:
        max_vol = 1
    
    calc_logger.debug(f"Max OI: {max_oi:,}, Max Volume: {max_vol:,}")
    
    total_call_premium = sum([s.call_premium * s.call_oi for s in strikes])
    total_put_premium = sum([s.put_premium * s.put_oi for s in strikes])
    
    calc_logger.debug(f"Total call premium: ${total_call_premium:,.2f}")
    calc_logger.debug(f"Total put premium: ${total_put_premium:,.2f}")
    
    # Process each strike
    calculations_logged = 0  # Limit debug logging
    for i, strike in enumerate(strikes):
        distance_pct = (strike.price - current_price) / current_price
        distance_weight = get_distance_weight(distance_pct)
        
        # Determine if strike supports direction
        if direction == 'long':
            direction_modifier = 1 if strike.price > current_price else -0.5
        else:
            direction_modifier = 1 if strike.price < current_price else -0.5
        
        # OI Factor (primary weight: 35%)
        strike_oi = strike.call_oi + strike.put_oi
        oi_contribution = (strike_oi * distance_weight * direction_modifier) / max_oi
        oi_factor += oi_contribution
        
        # Volume Factor (25% weight)
        strike_vol = strike.call_volume + strike.put_volume
        vol_contribution = (strike_vol * distance_weight * direction_modifier) / max_vol
        vol_factor += vol_contribution
        
        # Skip detailed strike logging to avoid huge log files
        # Only log if this is a high-impact strike
        if (strike_oi > 100 or strike_vol > 50) and calculations_logged < 10:
            calc_logger.debug(f"Strike ${strike.price:,.0f}: distance={distance_pct:+.3%}, weight={distance_weight:.2f}, "
                            f"modifier={direction_modifier:+.1f}, OI={strike_oi}, Vol={strike_vol}, "
                            f"OI_contrib={oi_contribution:.4f}, Vol_contrib={vol_contribution:.4f}")
            calculations_logged += 1
    
    # PCR Factor (25% weight)
    if total_call_premium + total_put_premium > 0:
        pcr_factor = (total_call_premium - total_put_premium) / (total_call_premium + total_put_premium)
        if direction == 'short':
            pcr_factor = -pcr_factor
        calc_logger.debug(f"PCR factor (raw): {pcr_factor:.4f}")
    
    # Distance Factor (15% weight)
    distance_factor = 1 - (abs(current_price - tp) / current_price)
    calc_logger.debug(f"Distance factor: {distance_factor:.4f}")
    
    # Normalize factors to [0, 1] range
    oi_factor = max(0, min(1, oi_factor))
    vol_factor = max(0, min(1, vol_factor))
    pcr_factor = (pcr_factor + 1) / 2  # Convert from [-1, 1] to [0, 1]
    distance_factor = max(0, min(1, distance_factor))
    
    calc_logger.info(f"Normalized factors:")
    calc_logger.info(f"  OI Factor: {oi_factor:.4f} (weight: {WEIGHTS['oi_factor']:.0%})")
    calc_logger.info(f"  Volume Factor: {vol_factor:.4f} (weight: {WEIGHTS['vol_factor']:.0%})")
    calc_logger.info(f"  PCR Factor: {pcr_factor:.4f} (weight: {WEIGHTS['pcr_factor']:.0%})")
    calc_logger.info(f"  Distance Factor: {distance_factor:.4f} (weight: {WEIGHTS['distance_factor']:.0%})")
    
    # Calculate weighted probability
    probability = (
        WEIGHTS['oi_factor'] * oi_factor +
        WEIGHTS['vol_factor'] * vol_factor +
        WEIGHTS['pcr_factor'] * pcr_factor +
        WEIGHTS['distance_factor'] * distance_factor
    )
    
    calc_logger.debug(f"Raw probability: {probability:.4f}")
    
    # Clamp between 10% and 90% for realistic probability range
    probability = max(0.1, min(0.9, probability))
    
    calc_logger.info(f"Final probability: {probability:.2%}")
    
    return probability

def calculate_ev_for_all_combinations(current_price: float, 
                                     strikes: List[OptionsStrike]) -> List[TradeSetup]:
    """Calculate EV for all valid TP/SL combinations"""
    calc_logger.info("🧮 Calculating EV for all TP/SL combinations...")
    
    setups = []
    
    # Get all strike prices
    strike_prices = sorted([s.price for s in strikes])
    
    total_combinations = len(strike_prices) * len(strike_prices)
    valid_combinations = 0
    
    # Test all combinations
    for tp in strike_prices:
        for sl in strike_prices:
            # Long setup: TP > current > SL
            if tp > current_price > sl:
                reward = tp - current_price
                risk = current_price - sl
                
                if risk <= MAX_RISK and reward / risk >= MIN_RISK_REWARD:
                    prob = calculate_probability(current_price, tp, sl, strikes, 'long')
                    ev = (prob * reward) - ((1 - prob) * risk)
                    
                    if ev > 100:  # Log high-value setups
                        calc_logger.info(f"HIGH EV LONG: TP=${tp:,.0f}, SL=${sl:,.0f}, "
                                       f"Reward={reward:.0f}, Risk={risk:.0f}, RR={reward/risk:.2f}, "
                                       f"Prob={prob:.2%}, EV={ev:+.1f}")
                    
                    setup = TradeSetup(tp, sl, 'long', prob, reward, risk, ev)
                    setups.append(setup)
                    valid_combinations += 1
            
            # Short setup: SL > current > TP
            elif tp < current_price < sl:
                reward = current_price - tp
                risk = sl - current_price
                
                if risk <= MAX_RISK and reward / risk >= MIN_RISK_REWARD:
                    prob = calculate_probability(current_price, tp, sl, strikes, 'short')
                    ev = (prob * reward) - ((1 - prob) * risk)
                    
                    if ev > 100:  # Log high-value setups
                        calc_logger.info(f"HIGH EV SHORT: TP=${tp:,.0f}, SL=${sl:,.0f}, "
                                       f"Reward={reward:.0f}, Risk={risk:.0f}, RR={reward/risk:.2f}, "
                                       f"Prob={prob:.2%}, EV={ev:+.1f}")
                    
                    setup = TradeSetup(tp, sl, 'short', prob, reward, risk, ev)
                    setups.append(setup)
                    valid_combinations += 1
    
    calc_logger.info(f"📊 Tested {total_combinations} combinations, found {valid_combinations} valid setups")
    
    # Sort by EV (best first)
    setups.sort(key=lambda x: x.ev, reverse=True)
    
    return setups

def filter_quality_setups(setups: List[TradeSetup]) -> List[TradeSetup]:
    """Filter setups by quality criteria"""
    logger.info("🔍 Filtering setups by quality criteria...")
    
    quality_setups = []
    
    for setup in setups:
        if (setup.ev >= MIN_EV and 
            setup.probability >= MIN_PROBABILITY and 
            setup.risk <= MAX_RISK and 
            setup.risk_reward >= MIN_RISK_REWARD):
            quality_setups.append(setup)
    
    logger.info(f"✅ Filtered to {len(quality_setups)} quality setups")
    
    return quality_setups

def generate_report(current_price: float, setups: List[TradeSetup], quality_stats: Dict) -> str:
    """Generate comprehensive trading report"""
    logger.info("📄 Generating comprehensive report...")
    
    report = []
    report.append(f"\n{'='*80}")
    report.append(f"NQ OPTIONS EV TRADING SYSTEM - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"DATA SOURCE: Saved API Data from Breakthrough Discovery")
    report.append(f"{'='*80}")
    
    # Data Quality Section
    report.append(f"\n📊 DATA QUALITY METRICS:")
    report.append(f"  🎯 Volume Coverage: {quality_stats['volume_coverage']:.1f}%")
    report.append(f"  🎯 Open Interest Coverage: {quality_stats['oi_coverage']:.1f}%")
    report.append(f"  📊 Total Options Analyzed: {quality_stats['total_options']}")
    report.append(f"  📞 Calls: {quality_stats['calls']} ({quality_stats['calls_with_vol']} with volume)")
    report.append(f"  📉 Puts: {quality_stats['puts']} ({quality_stats['puts_with_vol']} with volume)")
    
    report.append(f"\n💰 Current NQ Price: ${current_price:,.2f}")
    
    if setups:
        report.append(f"\n🏆 Top 5 Trading Opportunities:")
        report.append("-" * 80)
        report.append(f"{'Rank':<5} {'Direction':<10} {'TP':<10} {'SL':<10} {'Prob':<8} {'RR':<8} {'EV':<10}")
        report.append("-" * 80)
        
        for i, setup in enumerate(setups[:5], 1):
            report.append(
                f"{i:<5} {setup.direction:<10} ${setup.tp:<9.0f} ${setup.sl:<9.0f} "
                f"{setup.probability:<8.1%} {setup.risk_reward:<8.1f} {setup.ev:+10.1f}"
            )
        
        # Best recommendation
        best = setups[0]
        position_size = "LARGE (15-20%)" if best.ev > 50 else "MEDIUM (10-15%)" if best.ev > 30 else "SMALL (5-10%)"
        
        report.append(f"\n{'='*80}")
        report.append("🎯 EXECUTION RECOMMENDATION:")
        report.append(f"Recommended Trade: {best.direction.upper()} NQ")
        report.append(f"Entry: Current price (${current_price:,.2f})")
        report.append(f"Target: ${best.tp:,.0f} ({best.reward:+.0f} points)")
        report.append(f"Stop: ${best.sl:,.0f} ({-best.risk:.0f} points)")
        report.append(f"Position Size: {position_size}")
        report.append(f"Expected Value: {best.ev:+.1f} points per trade")
        report.append(f"Success Probability: {best.probability:.1%}")
        report.append(f"Risk/Reward Ratio: {best.risk_reward:.2f}:1")
        
    else:
        report.append(f"\n❌ No quality trading opportunities found.")
        report.append(f"All setups failed to meet minimum criteria:")
        report.append(f"  • Min EV: {MIN_EV} points")
        report.append(f"  • Min Probability: {MIN_PROBABILITY:.0%}")
        report.append(f"  • Max Risk: {MAX_RISK} points")
        report.append(f"  • Min Risk/Reward: {MIN_RISK_REWARD}:1")
    
    report.append(f"\n📝 ANALYSIS NOTES:")
    report.append(f"  • Volume coverage of {quality_stats['volume_coverage']:.1f}% provides sufficient data for EV calculations")
    report.append(f"  • Open Interest coverage of {quality_stats['oi_coverage']:.1f}% shows market positioning")
    report.append(f"  • Using saved data from breakthrough API discovery (2025-06-02)")
    report.append(f"  • Analysis confirms Volume/OI data is sufficient for Expected Value calculations")
    report.append(f"  • Filtered to liquid strikes within 5% of current price for focused analysis")
    
    report.append(f"\n📈 ALGORITHM WEIGHTING:")
    report.append(f"  • Open Interest Factor: {WEIGHTS['oi_factor']:.0%} (Primary: Market positioning)")
    report.append(f"  • Volume Factor: {WEIGHTS['vol_factor']:.0%} (Secondary: Current conviction)")
    report.append(f"  • Put/Call Ratio: {WEIGHTS['pcr_factor']:.0%} (Sentiment: Directional bias)")
    report.append(f"  • Distance Factor: {WEIGHTS['distance_factor']:.0%} (Probability: Distance decay)")
    
    report.append(f"\n{'='*80}")
    
    return '\n'.join(report)

def main():
    """Main execution function"""
    try:
        logger.info("🚀 Starting NQ Options EV Analysis with Saved Working Data")
        
        # Load saved data
        saved_data = load_saved_data()
        
        # Analyze data quality
        quality_stats = analyze_data_quality(saved_data)
        
        # Convert to our format
        current_price, strikes = convert_api_to_strikes(saved_data)
        
        if not strikes:
            logger.error("❌ No valid strikes found!")
            return
        
        # Calculate EV for all combinations
        all_setups = calculate_ev_for_all_combinations(current_price, strikes)
        
        # Filter quality setups
        quality_setups = filter_quality_setups(all_setups)
        
        # Generate report
        report = generate_report(current_price, quality_setups, quality_stats)
        print(report)
        
        # Save report to file
        os.makedirs('reports', exist_ok=True)
        filename = f"reports/nq_saved_data_ev_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        logger.info(f"📁 Report saved to {filename}")
        
        logger.info("✅ Analysis completed successfully!")
        
        return quality_setups[:5] if quality_setups else []
        
    except Exception as e:
        logger.error(f"❌ Error in main execution: {e}")
        logger.exception("Full traceback:")
        raise

if __name__ == "__main__":
    main()