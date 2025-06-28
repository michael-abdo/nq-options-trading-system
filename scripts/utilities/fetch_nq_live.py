#!/usr/bin/env python3
"""
Fetch live NQ futures price and volume from Yahoo Finance
"""

import requests
import json
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_nq_live_data():
    """Get current NQ futures price and volume from Yahoo Finance"""
    
    url = "https://query1.finance.yahoo.com/v8/finance/chart/NQ=F"
    params = {
        'interval': '1m',
        'range': '1d',
        'includePrePost': 'true'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        result = data['chart']['result'][0]
        meta = result['meta']
        
        # Extract key data
        current_price = meta['regularMarketPrice']
        previous_close = meta['previousClose']
        volume = meta['regularMarketVolume']
        change = current_price - previous_close
        change_pct = (change / previous_close) * 100
        
        # Market status
        market_state = meta.get('marketState', 'UNKNOWN')
        
        # Get latest timestamp
        timestamps = result['timestamp']
        latest_time = datetime.fromtimestamp(timestamps[-1])
        
        return {
            'symbol': 'NQ=F',
            'price': current_price,
            'change': change,
            'change_percent': change_pct,
            'volume': volume,
            'previous_close': previous_close,
            'market_state': market_state,
            'timestamp': latest_time.strftime('%Y-%m-%d %H:%M:%S'),
            'is_real_time': market_state == 'REGULAR'
        }
        
    except Exception as e:
        logger.error(f"Error fetching NQ data: {e}")
        return None

def main():
    """Test the NQ data fetcher"""
    
    logger.info("🎯 Fetching live NQ futures data from Yahoo Finance...")
    
    data = get_nq_live_data()
    
    if data:
        logger.info("✅ SUCCESS! NQ Futures Data:")
        logger.info(f"   Price: {data['price']:,.2f}")
        logger.info(f"   Change: {data['change']:+.2f} ({data['change_percent']:+.2f}%)")
        logger.info(f"   Volume: {data['volume']:,}")
        logger.info(f"   Market: {data['market_state']}")
        logger.info(f"   Time: {data['timestamp']}")
        logger.info(f"   Real-time: {'Yes' if data['is_real_time'] else 'Delayed'}")
        
        return data
    else:
        logger.error("❌ Failed to fetch NQ data")
        return None

if __name__ == "__main__":
    main()