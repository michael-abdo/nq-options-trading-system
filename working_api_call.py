#!/usr/bin/env python3
"""
Working API call with complete cookies including httpOnly
"""

import requests
import json
import logging
import urllib.parse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Complete cookies including httpOnly ones
cookies = {
    'laravel_session': 'eyJpdiI6ImdLYTJicUxsa09JZmVZbmFHNU96Z3c9PSIsInZhbHVlIjoidkF1T0VFNHY0MjAra3dSOTNncGNkTXY2QTBjTnY3L0VLR1cvZkVWbFIvRmRRMTdPeDJoL2IrWGcyV2FLVzlXc1M1RlhPN1JZS0NqSk1wS2pUa0xVRmlTb2g5RStsL1BkcmdzTzNuNEp4RmJYVmJDcGJLZ3QyTm9BV3luOFpiRmQiLCJtYWMiOiIzYTM0NTQzYzg2ZjU4MDFlZDdiZWVmMzRmNDZhY2U4NmUyZGVkYzgzZmM0NmZjYmQwZTA4MDc3Zjk0ZmM4ZDAyIiwidGFnIjoiIn0%3D',
    'laravel_token': 'eyJpdiI6IlorMkpiODhVK1EvQ2ZTcENOblRWc0E9PSIsInZhbHVlIjoiWkhzbnJleGVFeFl5SGlGWFhJeWRLdHg5NVdDYjJ4anNEczI5aURJczhWWFcyMGdSaHRqcUdKdlZLSndGWEw2LzhQdTQrKzgxc0JpSU1VYm5XUUFpdnRHanRMcEJYcFpSTkFJQWVRWG1SeENzci8xRkcxSHRySHlPUGlLVFVmdVlhOENkTnhFUkxGZVg4SU4yTVcrdGIrem5oZGZybVpaaHpSTVN6LytVdVg0T3VQRDJIMDlqZW4wMlZ4OEJZSlRxZFM5ZlZoNVZoK2dlKzRwaGhLVGlDdnZlaWJUOFE5Z2RIZDc1MmhPUEJRd3pmckUyVFRTYkpLMEtLQWZsaXluOEZmb00xbnBHbk01bm43SnhwcnZmYnF6aTRyMFkyU0hBSGFHaTFTclhGeUprMzFNZ3BweWEvN1lCMy8vQjIzSXYiLCJtYWMiOiJiYWFkMWM2MzI3NDhlYzg3ZDAwYTMxYjBjOGJiMDdiZDFmNTgwOTU1YjJhNWNhNWEwNTg5YTM0YzM1MWVkMjg3IiwidGFnIjoiIn0%3D',
    'XSRF-TOKEN': 'eyJpdiI6Ik9OekFza09seVlycXFpUk0yUzBFVGc9PSIsInZhbHVlIjoicUNtaDVUelNQckpYck9hSHl5OTNBbzhZemdLYkc5Z2xvL0xPNTZOWEM1SWk0Vjlwd2NEV004UkpiejhaY2JkSW9PQWc1RmMwVFBHL0dYUnVHbjhlZnFrVFR1akdNOFhKNGU4cW9abzFIVWVqdmhiUUFTU3B1MUs4aTlGT1BIZTIiLCJtYWMiOiJkN2JlODA0MDM3Y2IwNjBhNDM5MmJjNjVjMjhlZDM1NGE4NWYzNjE1MDhiM2M3YTA4YmY2Njk3MzRjOTcwZWY0IiwidGFnIjoiIn0%3D',
    'market': 'eyJpdiI6Im9jUGZSdHZEK0V1aEdRWGJmRHd2K1E9PSIsInZhbHVlIjoiSjBqSWtadDQ5ZkRFcDVKbXpaRml4WnBud01hVVF0TngyeHhHZk0zTDlMeHUwdFRVTGN6aG5PaDROMFNxZkZsTSIsIm1hYyI6IjdmZmIzMzYwNzU0OGFlMDRlY2I2YTI1ZDhiZjk5NWFlMDllNWFkNTNjNGI2NTg5NGI4MzEyMmNjOGZiOWM4NTciLCJ0YWciOiIifQ%3D%3D',
    'isDarkTheme': 'true',
    'bcFreeUserPageView': '0',
    'ic_tagmanager': 'AY',
    'IC_ViewCounter_www.barchart.com': '5',
    'webinarClosed': '249'
}

# Also add the tracking cookies
tracking_cookies = {
    'OTGPPConsent': 'DBABLA~BAQCAAAACZA.QA',
    '_gcl_au': '1.1.1116205833.1748870379',
    '_admrla': '2.2-f8ff83d09d38bc20-94092ad0-3fb3-11f0-820c-8806f0aed666',
    'OptanonAlertBoxClosed': '2025-06-04T13:36:15.066Z',
    '_hjSessionUser_2563157': 'eyJpZCI6IjNjNDVkNWIyLWVjNGMtNTY1YS05ZGE3LTFhZjViZGQ3Yzg2YiIsImNyZWF0ZWQiOjE3NDkwNDQ3MDc4MzYsImV4aXN0aW5nIjp0cnVlfQ==',
    '_ga': 'GA1.1.1317851658.1748870380',
    'OptanonConsent': 'isGpcEnabled=0&datestamp=Thu+Jun+26+2025+23%3A18%3A55+GMT-0500+(Central+Daylight+Time)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=ca062816-ba35-4e3b-9dc3-9761f00fa0a1&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&GPPCookiesCount=1&groups=C0001%3A1%2CC0003%3A1%2COSSTA_BG%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&intType=3&geolocation=US%3BOR',
    '_ga_PE0FK9V6VN': 'GS2.1.s1750995508$o40$g1$t1750997936$j56$l0$h0',
    '_awl': '2.1750997939.5-19abf227c83bc86866e5aaa0b22bedfe-6763652d75732d7765737431-1'
}

# Combine all cookies
all_cookies = {**cookies, **tracking_cookies}

logger.info(f"✅ Have all essential cookies: laravel_session, laravel_token, XSRF-TOKEN")

# Test multiple symbols
test_symbols = [
    ("MM9M25", "NQU25", "June 2025 - URL format"),
    ("MM9M5", "NQU25", "June 2025 - Single digit year"),
    ("MC7M5", "NQM25", "July 2025 - Original working format"),
    ("MC4M5", "NQU25", "Today's EOD - Single digit")
]

# Setup session
session = requests.Session()
for name, value in all_cookies.items():
    session.cookies.set(name, value)

# API endpoint
url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"

for symbol, futures, desc in test_symbols:
    logger.info(f"\n📊 Testing {desc}: {symbol}")
    
    # First try WITH groupBy (original method)
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
    
    headers = {
        'Accept': 'application/json',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': f'https://www.barchart.com/futures/quotes/{futures}/options/{symbol}?futuresOptionsView=merged',
        'X-XSRF-TOKEN': urllib.parse.unquote(cookies['XSRF-TOKEN'])
    }
    
    try:
        response = session.get(url, params=params, headers=headers)
        logger.info(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ SUCCESS! count={data.get('count')}, total={data.get('total')}")
            
            # Check data structure
            if 'data' in data:
                if isinstance(data['data'], dict):
                    logger.info(f"Data structure: dict with keys: {list(data['data'].keys())}")
                    for key, value in data['data'].items():
                        if isinstance(value, list):
                            logger.info(f"  {key}: {len(value)} contracts")
                            if len(value) > 0:
                                logger.info(f"    Sample: Strike={value[0].get('strike')}, Last={value[0].get('lastPrice')}")
                elif isinstance(data['data'], list):
                    logger.info(f"Data structure: list with {len(data['data'])} items")
            
            # If no data with groupBy, try WITHOUT groupBy
            if data.get('total', 0) == 0:
                logger.info("🔄 Retrying WITHOUT groupBy parameter...")
                params_no_group = params.copy()
                del params_no_group['groupBy']
                
                response2 = session.get(url, params=params_no_group, headers=headers)
                if response2.status_code == 200:
                    data2 = response2.json()
                    logger.info(f"Without groupBy: count={data2.get('count')}, total={data2.get('total')}")
                    
                    if data2.get('total', 0) > 0:
                        logger.info("✅ SUCCESS WITHOUT groupBy!")
                        with open(f'{symbol}_response_no_group.json', 'w') as f:
                            json.dump(data2, f, indent=2)
                        logger.info(f"💾 Saved to {symbol}_response_no_group.json")
                        data = data2  # Use this data
                        
            # Save successful response
            if data.get('total', 0) > 0:
                with open(f'{symbol}_response.json', 'w') as f:
                    json.dump(data, f, indent=2)
                logger.info(f"💾 Saved to {symbol}_response.json")
                break  # Found working symbol!
                
        else:
            logger.error(f"❌ Error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"❌ Exception: {e}")