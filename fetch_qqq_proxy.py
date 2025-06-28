#!/usr/bin/env python3
"""
Fetch QQQ as NQ proxy - should be real-time
"""

import requests
import json

def get_qqq_proxy():
    """Get QQQ as NQ proxy"""
    
    url = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ"
    params = {'interval': '1m', 'range': '1d'}
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        meta = data['chart']['result'][0]['meta']
        
        price = meta['regularMarketPrice']
        market_state = meta.get('marketState', 'UNKNOWN')
        
        # Convert QQQ to approximate NQ equivalent
        # QQQ tracks Nasdaq 100 index, NQ is 20x the index
        # Rough conversion: NQ ≈ QQQ * 45-50 (approximate multiplier)
        nq_equivalent = price * 46.5  # Rough estimate
        
        return {
            'qqq_price': price,
            'nq_equivalent': nq_equivalent,
            'market_state': market_state,
            'is_real_time': market_state in ['REGULAR', 'PRE', 'POST']
        }
        
    except Exception as e:
        print(f"Error: {e}")
        return None

if __name__ == "__main__":
    data = get_qqq_proxy()
    if data:
        print(f"QQQ Price: ${data['qqq_price']:.2f}")
        print(f"NQ Equivalent: ~{data['nq_equivalent']:.0f}")
        print(f"Market State: {data['market_state']}")
        print(f"Real-time: {data['is_real_time']}")