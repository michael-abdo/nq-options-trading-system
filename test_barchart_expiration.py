#!/usr/bin/env python3
"""
Test Barchart options expiration date validation
"""

import requests
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_symbol_expiration(symbol: str):
    """Test if a symbol exists and get its expiration info"""
    
    # Load cookies from our successful pipeline run
    import pickle
    
    try:
        with open('cookies/barchart_cookies_20250627_135620.pkl', 'rb') as f:
            cookies = pickle.load(f)
        
        logger.info(f"Testing symbol: {symbol}")
        
        # Create session
        session = requests.Session()
        for name, value in cookies.items():
            session.cookies.set(name, value)
        
        # Headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': f'https://www.barchart.com/futures/quotes/NQU25/options/{symbol}',
            'X-Requested-With': 'XMLHttpRequest'
        })
        
        if 'XSRF-TOKEN' in cookies:
            session.headers['X-XSRF-TOKEN'] = cookies['XSRF-TOKEN'].replace('%3D', '=')
        
        # Try to fetch data
        params = {
            'symbol': symbol,
            'list': 'futures.options',
            'fields': 'strike,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,longSymbol,optionType,symbol,symbolCode,symbolType',
            'meta': 'field.shortName,field.description,field.type,lists.lastUpdate',
            'groupBy': 'optionType',
            'orderBy': 'strike',
            'orderDir': 'asc',
            'raw': '1'
        }
        
        url = 'https://www.barchart.com/proxies/core-api/v1/quotes/get'
        response = session.get(url, params=params, timeout=10)
        
        logger.info(f"API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            total = data.get('total', 0)
            
            if total > 0:
                logger.info(f"✅ {symbol} EXISTS - Found {total} contracts")
                
                # Try to get expiration info from the data
                if 'data' in data and 'Call' in data['data'] and len(data['data']['Call']) > 0:
                    first_contract = data['data']['Call'][0]
                    logger.info(f"First contract: {first_contract.get('longSymbol', 'N/A')}")
                    
                return True
            else:
                logger.info(f"❌ {symbol} - No contracts found")
                return False
        else:
            logger.info(f"❌ {symbol} - API error: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error testing {symbol}: {e}")
        return False

def main():
    """Test various symbol formats"""
    
    symbols_to_test = [
        ('MQ4M25', 'Friday 0DTE (4th Friday June)'),
        ('MM1N25', 'Tuesday weekly (1st Tuesday July)'),
        ('MM6N25', 'Monthly (3rd Thursday July)'),
        ('MC4M25', 'Daily option (Thursday June)'),
        ('MC5M25', 'Daily option (Friday June)'),
        ('MQ1N25', 'Friday weekly (1st Friday July)'),
        ('MQ2N25', 'Friday weekly (2nd Friday July)'),
        ('MQ3N25', 'Friday weekly (3rd Friday July)'),
    ]
    
    logger.info("Testing Barchart options symbols...")
    logger.info("=" * 60)
    
    results = []
    
    for symbol, description in symbols_to_test:
        logger.info(f"\nTesting: {symbol} - {description}")
        exists = test_symbol_expiration(symbol)
        results.append((symbol, description, exists))
    
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY:")
    logger.info("=" * 60)
    
    for symbol, description, exists in results:
        status = "✅ EXISTS" if exists else "❌ NOT FOUND"
        logger.info(f"{symbol}: {status} - {description}")

if __name__ == "__main__":
    main()