#!/usr/bin/env python3
"""
Fetch MC4M25 options data using cookies from Chrome browser session
"""

import logging
import json
from datetime import datetime
import os
import sys

# Add the task directory to path
sys.path.append('/Users/Mike/trading/algos/EOD/tasks/options_trading_system/data_ingestion/barchart_web_scraper')

from barchart_api_client import BarchartAPIClient

def main():
    # Setup logging with debug level
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Cookie string from Chrome browser (updated with MM9M25 page)
    cookie_string = 'OTGPPConsent=DBABLA~BAQCAAAACZA.QA; _gcl_au=1.1.1116205833.1748870379; _admrla=2.2-f8ff83d09d38bc20-94092ad0-3fb3-11f0-820c-8806f0aed666; OptanonAlertBoxClosed=2025-06-04T13:36:15.066Z; _hjSessionUser_2563157=eyJpZCI6IjNjNDVkNWIyLWVjNGMtNTY1YS05ZGE3LTFhZjViZGQ3Yzg2YiIsImNyZWF0ZWQiOjE3NDkwNDQ3MDc4MzYsImV4aXN0aW5nIjp0cnVlfQ==; _ga=GA1.1.1317851658.1748870380; bcFreeUserPageView=0; isDarkTheme=true; webinarClosed=249; ic_tagmanager=AY; XSRF-TOKEN=eyJpdiI6ImltSWRBeU92eW5OVlBCS3Zrbmpyanc9PSIsInZhbHVlIjoibEluci8vaFpkTUxpMWd2eDltY3JCanBLdG8zZHBUMGhjWkxqcHc4Z0IzZDhUOFNZMWx6U01Xbko2TGY2SVRiblFRM0VWd2pkSm1menNlR1lsUWw3bVVIZUJIZ016allMc0V6R292TTA5QWlsRnJXWGIxQnZrMzdzeVRrclpsck8iLCJtYWMiOiI4MTAyNWNiN2ZmY2ZjNDQ0NDc0NGZkMzgxMTY0N2FjM2Y5YzRjM2Q5M2M5ODU0ODBmMjYyNWEyMWIzOGM4ODZkIiwidGFnIjoiIn0%3D; IC_ViewCounter_www.barchart.com=11; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Jun+26+2025+08%3A57%3A57+GMT-0500+(Central+Daylight+Time)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=ca062816-ba35-4e3b-9dc3-9761f00fa0a1&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&GPPCookiesCount=1&groups=C0001%3A1%2CC0003%3A1%2COSSTA_BG%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&intType=3&geolocation=US%3BOR; _ga_PE0FK9V6VN=GS2.1.s1750942389$o38$g1$t1750946277$j58$l0$h0; _awl=2.1750946279.5-19abf227c83bc86866e5aaa0b22bedfe-6763652d75732d7765737431-1'
    
    logger.info("🔐 Parsing cookies from Chrome browser session...")
    
    # Parse cookies
    cookies = {}
    for cookie in cookie_string.split('; '):
        if '=' in cookie:
            name, value = cookie.split('=', 1)
            cookies[name] = value
    
    logger.info(f"✅ Parsed {len(cookies)} cookies")
    
    # Check for essential cookies
    essential_cookies = ['laravel_session', 'XSRF-TOKEN', 'laravel_token']
    found_cookies = [c for c in essential_cookies if c in cookies]
    logger.info(f"Found {len(found_cookies)}/{len(essential_cookies)} essential cookies: {found_cookies}")
    
    # Debug: Show all cookie names
    logger.info(f"All cookies: {list(cookies.keys())}")
    
    # Look for any Laravel session-related cookies
    session_cookies = [name for name in cookies.keys() if 'session' in name.lower() or 'laravel' in name.lower()]
    logger.info(f"Session-related cookies: {session_cookies}")
    
    # Initialize API client
    logger.info("📡 Initializing Barchart API client...")
    client = BarchartAPIClient()
    client.set_cookies(cookies)
    
    # First, let's try to get cookies by making a simple request to the page
    logger.info("🔄 Testing authentication with a simple page request...")
    test_url = "https://www.barchart.com/futures/quotes/NQU25/options/MM9M25?futuresOptionsView=merged&moneyness=allRows"
    
    try:
        response = client.session.get(test_url, headers=client.headers)
        logger.info(f"Page request status: {response.status_code}")
        
        # Check if we got any new cookies
        new_cookies = {}
        for cookie in client.session.cookies:
            new_cookies[cookie.name] = cookie.value
        logger.info(f"After page request, we have {len(new_cookies)} total cookies")
        
        # Look for Laravel session cookies again
        session_cookies = [name for name in new_cookies.keys() if 'laravel' in name.lower()]
        logger.info(f"Laravel cookies after page request: {session_cookies}")
        
    except Exception as e:
        logger.warning(f"Page request failed: {e}")
    
    # Test MC7M25 - the EXACT symbol that worked on June 8th
    symbol_full = "MC7M25"  # What worked on June 8th
    symbol_api = "MC7M5"    # Single digit format that appeared in successful response
    futures_symbol = "NQM25"  # July 2025 futures (what was used on June 8th)
    
    # Try single-digit year format first (this should work based on git history analysis)
    for symbol in [symbol_api, symbol_full]:
        logger.info(f"📊 Trying symbol: {symbol} (underlying: {futures_symbol})...")
        
        try:
            # Let's debug the request first
            logger.info("🔍 Debugging API request...")
            
            # Show current cookies
            current_cookies = {}
            for cookie in client.session.cookies:
                current_cookies[cookie.name] = cookie.value
            logger.info(f"Current cookies for API call: {list(current_cookies.keys())}")
            
            # Check if we have essential cookies now
            essential_now = [name for name in ['laravel_session', 'XSRF-TOKEN', 'laravel_token'] if name in current_cookies]
            logger.info(f"Essential cookies available: {essential_now}")
            
            data = client.get_options_data(symbol, futures_symbol)
            
            if data and data.get('total', 0) > 0:
                logger.info(f"✅ Successfully retrieved {data.get('total', 0)} contracts with symbol {symbol}!")
                
                # Save the data
                saved_path = client.save_api_response(data, symbol)
                logger.info(f"💾 Data saved to: {saved_path}")
                
                # Display summary
                print(f"\n📊 Options Data Summary for {symbol}:")
                print(f"   Total contracts: {data.get('total', 0)}")
                print(f"   Returned count: {data.get('count', 0)}")
                
                # Show sample data
                if 'data' in data:
                    if 'Call' in data['data'] and data['data']['Call']:
                        calls = data['data']['Call']
                        print(f"   Call options: {len(calls)}")
                        if calls:
                            sample_call = calls[0]
                            print(f"   Sample call - Strike: {sample_call.get('strike')}, Last: ${sample_call.get('lastPrice')}")
                    
                    if 'Put' in data['data'] and data['data']['Put']:
                        puts = data['data']['Put']
                        print(f"   Put options: {len(puts)}")
                        if puts:
                            sample_put = puts[0]
                            print(f"   Sample put - Strike: {sample_put.get('strike')}, Last: ${sample_put.get('lastPrice')}")
                
                print(f"\n✅ Success! Data retrieved and saved to: {saved_path}")
                return 0
                
            else:
                logger.warning(f"⚠️  No data returned for symbol {symbol}")
                continue  # Try next symbol
                
        except Exception as e:
            logger.warning(f"⚠️  Error with symbol {symbol}: {e}")
            continue  # Try next symbol
    
    # If we get here, both symbols failed
    logger.error("❌ Failed to fetch data with both symbol formats")
    return 1

if __name__ == "__main__":
    exit(main())