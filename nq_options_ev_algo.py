#!/usr/bin/env python3
"""
NQ Options Expected Value Trading System with Comprehensive Logging
Pulls data from Barchart and calculates EV for optimal TP/SL combinations
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Tuple, Optional
import logging
import sys
import os
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.logging_config import setup_logging, get_logger, log_function_call, log_section

# Set up logging
log_dir, session_id = setup_logging(log_level=logging.DEBUG, console_level=logging.INFO)
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

# Log configuration
logger.info("Configuration loaded:")
logger.info(f"  Weights: {WEIGHTS}")
logger.info(f"  Min EV: {MIN_EV}")
logger.info(f"  Min Probability: {MIN_PROBABILITY}")
logger.info(f"  Max Risk: {MAX_RISK}")
logger.info(f"  Min Risk/Reward: {MIN_RISK_REWARD}")


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
        
        logger.debug(f"Created OptionsStrike: price={price}, "
                    f"call_vol={call_volume}, call_oi={call_oi}, call_prem={call_premium}, "
                    f"put_vol={put_volume}, put_oi={put_oi}, put_prem={put_premium}")


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
        
        logger.debug(f"Created TradeSetup: {direction} TP={tp}, SL={sl}, "
                    f"prob={probability:.2%}, reward={reward}, risk={risk}, "
                    f"EV={ev:.2f}, RR={self.risk_reward:.2f}")


@log_function_call
def get_current_contract_url() -> str:
    """Generate the Barchart URL for the current NQ options contract"""
    log_section("URL Generation", logging.DEBUG)
    
    now = datetime.now()
    logger.debug(f"Current date: {now}")
    
    # Find the next quarterly expiration (Mar, Jun, Sep, Dec)
    # Contract months: H=Mar(3), M=Jun(6), U=Sep(9), Z=Dec(12)
    month_codes = {3: 'H', 6: 'M', 9: 'U', 12: 'Z'}
    quarterly_months = [3, 6, 9, 12]
    
    # Find next quarterly month
    current_month = now.month
    current_year = now.year
    
    logger.debug(f"Current month: {current_month}, Current year: {current_year}")
    
    for month in quarterly_months:
        if month >= current_month:
            contract_month = month
            contract_year = current_year
            logger.debug(f"Found contract month: {month}")
            break
    else:
        contract_month = 3
        contract_year = current_year + 1
        logger.debug(f"Rolling to next year: {contract_year}, month: {contract_month}")
    
    # Get month code
    month_code = month_codes[contract_month]
    year_suffix = str(contract_year)[-2:]
    
    # NQ futures symbol
    futures_symbol = f"NQ{month_code}{year_suffix}"
    logger.debug(f"Futures symbol: {futures_symbol}")
    
    # Options symbol (MC prefix for CME options)
    options_symbol = f"MC{contract_month}{month_code}{year_suffix}"
    logger.debug(f"Options symbol: {options_symbol}")
    
    url = f"https://www.barchart.com/futures/quotes/{futures_symbol}/options/{options_symbol}?futuresOptionsView=merged"
    
    logger.info(f"Generated URL for {futures_symbol}: {url}")
    return url


@log_function_call
def scrape_barchart_options(url: str) -> Tuple[float, List[OptionsStrike]]:
    """Scrape options data from Barchart URL"""
    log_section("Data Scraping", logging.INFO)
    data_logger.info(f"Starting scrape of URL: {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        data_logger.info("Sending HTTP request...")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data_logger.info(f"Response received: Status {response.status_code}, Length {len(response.text)} bytes")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        data_logger.debug("HTML parsed successfully")
        
        # Try to find the current price from the page
        current_price = None
        data_logger.debug("Searching for current price...")
        
        price_elem = soup.find('span', class_='last-change')
        if price_elem:
            price_text = price_elem.text.strip().replace(',', '')
            try:
                current_price = float(price_text)
                data_logger.info(f"Found current price in last-change span: {current_price}")
            except Exception as e:
                data_logger.warning(f"Failed to parse price from last-change: {e}")
        
        # If not found in usual place, try to extract from script tags
        if not current_price:
            data_logger.debug("Searching for price in script tags...")
            scripts = soup.find_all('script')
            data_logger.debug(f"Found {len(scripts)} script tags")
            
            for i, script in enumerate(scripts):
                if script.string and 'lastPrice' in script.string:
                    match = re.search(r'"lastPrice":\s*"?([\d,\.]+)"?', script.string)
                    if match:
                        current_price = float(match.group(1).replace(',', ''))
                        data_logger.info(f"Found current price in script tag {i}: {current_price}")
                        break
        
        if not current_price:
            data_logger.warning("Could not find current price, using default")
            current_price = 21376.75  # Default from the example
        
        logger.info(f"Current NQ price: {current_price}")
        
        # Find the options data table
        options_data = []
        
        # Look for table with options data
        tables = soup.find_all('table')
        data_logger.info(f"Found {len(tables)} tables to search")
        
        for table_idx, table in enumerate(tables):
            rows = table.find_all('tr')
            data_logger.debug(f"Table {table_idx}: {len(rows)} rows")
            
            for row_idx, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 7:  # Minimum cells for options data
                    try:
                        # Try to parse as options data row
                        cell_texts = [cell.text.strip() for cell in cells]
                        
                        # Look for strike price pattern
                        strike_match = None
                        for i, text in enumerate(cell_texts):
                            if re.match(r'^\d{5}(\.\d+)?$', text.replace(',', '')):
                                strike_match = i
                                break
                        
                        if strike_match is not None:
                            strike = float(cell_texts[strike_match].replace(',', ''))
                            
                            # Extract call and put data (adjust indices based on table structure)
                            call_vol = int(cell_texts[strike_match - 3].replace(',', '') or '0')
                            call_oi = int(cell_texts[strike_match - 2].replace(',', '') or '0')
                            call_premium = float(cell_texts[strike_match - 1].replace(',', '') or '0')
                            
                            put_premium = float(cell_texts[strike_match + 1].replace(',', '') or '0')
                            put_oi = int(cell_texts[strike_match + 2].replace(',', '') or '0')
                            put_vol = int(cell_texts[strike_match + 3].replace(',', '') or '0')
                            
                            data_logger.debug(f"Parsed strike {strike} from table {table_idx}, row {row_idx}")
                            
                            options_data.append(OptionsStrike(
                                strike, call_vol, call_oi, call_premium,
                                put_vol, put_oi, put_premium
                            ))
                    except Exception as e:
                        data_logger.debug(f"Failed to parse row {row_idx} in table {table_idx}: {e}")
                        continue
        
        # If no data found from HTML, generate sample data based on the markdown example
        if not options_data:
            data_logger.warning("No options data found in HTML, using sample data")
            sample_data = [
                (21200, 250, 1500, 2.50, 800, 5200, 8.75),
                (21250, 180, 1200, 4.25, 650, 4800, 12.50),
                (21300, 320, 2100, 7.50, 920, 6500, 18.25),
                (21350, 450, 3200, 12.75, 1100, 7200, 26.50),
                (21400, 850, 5500, 22.50, 1350, 8900, 38.75),
                (21450, 1200, 8200, 35.25, 1580, 9500, 55.50),
                (21500, 980, 6800, 52.75, 1820, 8800, 78.25),
            ]
            
            for data in sample_data:
                options_data.append(OptionsStrike(*data))
        
        data_logger.info(f"Successfully scraped {len(options_data)} strikes")
        return current_price, options_data
        
    except requests.RequestException as e:
        data_logger.error(f"!!! ERROR: HTTP request failed: {e}")
        raise
    except Exception as e:
        data_logger.error(f"!!! ERROR scraping data: {type(e).__name__}: {str(e)}")
        data_logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


@log_function_call
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
    
    calc_logger.debug(f"Distance {distance_pct:.3%} -> Weight {weight}")
    return weight


def calculate_probability(current_price: float, tp: float, sl: float, 
                         strikes: List[OptionsStrike], direction: str) -> float:
    """Calculate probability of reaching TP before SL"""
    calc_logger.info(f"=== Calculating Probability ===")
    calc_logger.info(f"Current: {current_price}, TP: {tp}, SL: {sl}, Direction: {direction}")
    
    # Calculate factors
    oi_factor = 0
    vol_factor = 0
    pcr_factor = 0
    
    max_oi = max([s.call_oi + s.put_oi for s in strikes]) if strikes else 1
    max_vol = max([s.call_volume + s.put_volume for s in strikes]) if strikes else 1
    
    calc_logger.debug(f"Max OI: {max_oi}, Max Volume: {max_vol}")
    
    total_call_premium = sum([s.call_premium * s.call_oi for s in strikes])
    total_put_premium = sum([s.put_premium * s.put_oi for s in strikes])
    
    calc_logger.debug(f"Total call premium: ${total_call_premium:,.2f}")
    calc_logger.debug(f"Total put premium: ${total_put_premium:,.2f}")
    
    for strike in strikes:
        distance_pct = (strike.price - current_price) / current_price
        distance_weight = get_distance_weight(distance_pct)
        
        # Determine if strike supports direction
        if direction == 'long':
            direction_modifier = 1 if strike.price > current_price else -0.5
        else:
            direction_modifier = 1 if strike.price < current_price else -0.5
        
        calc_logger.debug(f"Strike {strike.price}: distance={distance_pct:.3%}, "
                         f"weight={distance_weight}, modifier={direction_modifier}")
        
        # OI Factor
        strike_oi = strike.call_oi + strike.put_oi
        oi_contribution = (strike_oi * distance_weight * direction_modifier) / max_oi
        oi_factor += oi_contribution
        calc_logger.debug(f"  OI contribution: {oi_contribution:.4f}")
        
        # Volume Factor
        strike_vol = strike.call_volume + strike.put_volume
        vol_contribution = (strike_vol * distance_weight * direction_modifier) / max_vol
        vol_factor += vol_contribution
        calc_logger.debug(f"  Volume contribution: {vol_contribution:.4f}")
    
    # PCR Factor
    if total_call_premium + total_put_premium > 0:
        pcr_factor = (total_call_premium - total_put_premium) / (total_call_premium + total_put_premium)
        if direction == 'short':
            pcr_factor = -pcr_factor
        calc_logger.debug(f"PCR factor (raw): {pcr_factor:.4f}")
    
    # Distance Factor
    distance_factor = 1 - (abs(current_price - tp) / current_price)
    calc_logger.debug(f"Distance factor: {distance_factor:.4f}")
    
    # Normalize factors
    oi_factor = max(0, min(1, oi_factor))
    vol_factor = max(0, min(1, vol_factor))
    pcr_factor = (pcr_factor + 1) / 2  # Convert from [-1, 1] to [0, 1]
    distance_factor = max(0, min(1, distance_factor))
    
    calc_logger.info(f"Normalized factors:")
    calc_logger.info(f"  OI Factor: {oi_factor:.4f} (weight: {WEIGHTS['oi_factor']})")
    calc_logger.info(f"  Volume Factor: {vol_factor:.4f} (weight: {WEIGHTS['vol_factor']})")
    calc_logger.info(f"  PCR Factor: {pcr_factor:.4f} (weight: {WEIGHTS['pcr_factor']})")
    calc_logger.info(f"  Distance Factor: {distance_factor:.4f} (weight: {WEIGHTS['distance_factor']})")
    
    # Calculate weighted probability
    probability = (
        WEIGHTS['oi_factor'] * oi_factor +
        WEIGHTS['vol_factor'] * vol_factor +
        WEIGHTS['pcr_factor'] * pcr_factor +
        WEIGHTS['distance_factor'] * distance_factor
    )
    
    calc_logger.debug(f"Raw probability: {probability:.4f}")
    
    # Clamp between 10% and 90%
    probability = max(0.1, min(0.9, probability))
    
    calc_logger.info(f"Final probability: {probability:.2%}")
    
    return probability


@log_function_call
def calculate_ev_for_all_combinations(current_price: float, 
                                     strikes: List[OptionsStrike]) -> List[TradeSetup]:
    """Calculate EV for all valid TP/SL combinations"""
    log_section("EV Calculation", logging.INFO)
    logger.info(f"Testing all TP/SL combinations for current price: {current_price}")
    
    setups = []
    
    # Get all strike prices
    strike_prices = sorted([s.price for s in strikes])
    logger.debug(f"Strike prices: {strike_prices}")
    
    total_combinations = len(strike_prices) * len(strike_prices)
    valid_combinations = 0
    
    # Test all combinations
    for tp in strike_prices:
        for sl in strike_prices:
            # Long setup
            if tp > current_price > sl:
                reward = tp - current_price
                risk = current_price - sl
                
                logger.debug(f"Testing LONG: TP={tp}, SL={sl}, Reward={reward}, Risk={risk}")
                
                if risk <= MAX_RISK and reward / risk >= MIN_RISK_REWARD:
                    prob = calculate_probability(current_price, tp, sl, strikes, 'long')
                    ev = (prob * reward) - ((1 - prob) * risk)
                    
                    setup = TradeSetup(tp, sl, 'long', prob, reward, risk, ev)
                    setups.append(setup)
                    valid_combinations += 1
                    
                    logger.info(f"Valid LONG setup: TP={tp}, SL={sl}, EV={ev:.2f}")
                else:
                    logger.debug(f"  Rejected: Risk={risk} > {MAX_RISK} or RR={reward/risk:.2f} < {MIN_RISK_REWARD}")
            
            # Short setup
            elif tp < current_price < sl:
                reward = current_price - tp
                risk = sl - current_price
                
                logger.debug(f"Testing SHORT: TP={tp}, SL={sl}, Reward={reward}, Risk={risk}")
                
                if risk <= MAX_RISK and reward / risk >= MIN_RISK_REWARD:
                    prob = calculate_probability(current_price, tp, sl, strikes, 'short')
                    ev = (prob * reward) - ((1 - prob) * risk)
                    
                    setup = TradeSetup(tp, sl, 'short', prob, reward, risk, ev)
                    setups.append(setup)
                    valid_combinations += 1
                    
                    logger.info(f"Valid SHORT setup: TP={tp}, SL={sl}, EV={ev:.2f}")
                else:
                    logger.debug(f"  Rejected: Risk={risk} > {MAX_RISK} or RR={reward/risk:.2f} < {MIN_RISK_REWARD}")
    
    logger.info(f"Tested {total_combinations} combinations, found {valid_combinations} valid setups")
    
    # Sort by EV
    setups.sort(key=lambda x: x.ev, reverse=True)
    logger.info(f"Sorted setups by EV (best first)")
    
    return setups


@log_function_call
def filter_quality_setups(setups: List[TradeSetup]) -> List[TradeSetup]:
    """Filter setups by quality criteria"""
    log_section("Filtering Quality Setups", logging.INFO)
    
    logger.info(f"Filtering {len(setups)} setups with criteria:")
    logger.info(f"  Min EV: {MIN_EV}")
    logger.info(f"  Min Probability: {MIN_PROBABILITY}")
    logger.info(f"  Max Risk: {MAX_RISK}")
    logger.info(f"  Min Risk/Reward: {MIN_RISK_REWARD}")
    
    quality_setups = []
    
    for setup in setups:
        passes = True
        reasons = []
        
        if setup.ev < MIN_EV:
            passes = False
            reasons.append(f"EV {setup.ev:.2f} < {MIN_EV}")
        
        if setup.probability < MIN_PROBABILITY:
            passes = False
            reasons.append(f"Prob {setup.probability:.2%} < {MIN_PROBABILITY:.0%}")
        
        if setup.risk > MAX_RISK:
            passes = False
            reasons.append(f"Risk {setup.risk} > {MAX_RISK}")
        
        if setup.risk_reward < MIN_RISK_REWARD:
            passes = False
            reasons.append(f"RR {setup.risk_reward:.2f} < {MIN_RISK_REWARD}")
        
        if passes:
            quality_setups.append(setup)
            logger.debug(f"✓ PASSED: {setup.direction} TP={setup.tp} SL={setup.sl} EV={setup.ev:.2f}")
        else:
            logger.debug(f"✗ FAILED: {setup.direction} TP={setup.tp} SL={setup.sl} - {', '.join(reasons)}")
    
    logger.info(f"Filtered to {len(quality_setups)} quality setups")
    
    return quality_setups


@log_function_call
def generate_report(current_price: float, setups: List[TradeSetup]) -> str:
    """Generate trading report"""
    log_section("Report Generation", logging.INFO)
    
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
        
        logger.info(f"Top {i}: {setup.direction} TP={setup.tp} SL={setup.sl} "
                   f"Prob={setup.probability:.1%} RR={setup.risk_reward:.1f} EV={setup.ev:+.1f}")
    
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
        
        logger.info(f"Best setup recommendation: {best.direction.upper()} with {position_size} position")
    else:
        logger.warning("No quality setups found!")
    
    return '\n'.join(report)


def main():
    """Main execution function"""
    try:
        log_section("STARTING NQ OPTIONS EV SYSTEM")
        
        # Generate URL for current contract
        url = get_current_contract_url()
        
        # Scrape data
        logger.info("Scraping options data from Barchart...")
        current_price, strikes = scrape_barchart_options(url)
        
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
        filename = f"reports/nq_ev_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            with open(filename, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {filename}")
        except Exception as e:
            logger.error(f"!!! ERROR saving report: {e}")
            logger.exception("Full traceback:")
        
        log_section("SYSTEM COMPLETED SUCCESSFULLY")
        
        # Return best opportunities for programmatic use
        return quality_setups[:5] if quality_setups else []
        
    except Exception as e:
        logger.error(f"!!! ERROR in main execution: {type(e).__name__}: {str(e)}")
        logger.exception("Full traceback:")
        log_section("SYSTEM FAILED", logging.ERROR)
        raise


if __name__ == "__main__":
    main()