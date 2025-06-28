#!/usr/bin/env python3
"""
Debug why we're getting empty responses
"""

import requests
import json
import logging
import urllib.parse
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Complete cookies
cookies = {
    'laravel_session': 'eyJpdiI6ImdLYTJicUxsa09JZmVZbmFHNU96Z3c9PSIsInZhbHVlIjoidkF1T0VFNHY0MjAra3dSOTNncGNkTXY2QTBjTnY3L0VLR1cvZkVWbFIvRmRRMTdPeDJoL2IrWGcyV2FLVzlXc1M1RlhPN1JZS0NqSk1wS2pUa0xVRmlTb2g5RStsL1BkcmdzTzNuNEp4RmJYVmJDcGJLZ3QyTm9BV3luOFpiRmQiLCJtYWMiOiIzYTM0NTQzYzg2ZjU4MDFlZDdiZWVmMzRmNDZhY2U4NmUyZGVkYzgzZmM0NmZjYmQwZTA4MDc3Zjk0ZmM4ZDAyIiwidGFnIjoiIn0%3D',
    'laravel_token': 'eyJpdiI6IlorMkpiODhVK1EvQ2ZTcENOblRWc0E9PSIsInZhbHVlIjoiWkhzbnJleGVFeFl5SGlGWFhJeWRLdHg5NVdDYjJ4anNEczI5aURJczhWWFcyMGdSaHRqcUdKdlZLSndGWEw2LzhQdTQrKzgxc0JpSU1VYm5XUUFpdnRHanRMcEJYcFpSTkFJQWVRWG1SeENzci8xRkcxSHRySHlPUGlLVFVmdVlhOENkTnhFUkxGZVg4SU4yTVcrdGIrem5oZGZybVpaaHpSTVN6LytVdVg0T3VQRDJIMDlqZW4wMlZ4OEJZSlRxZFM5ZlZoNVZoK2dlKzRwaGhLVGlDdnZlaWJUOFE5Z2RIZDc1MmhPUEJRd3pmckUyVFRTYkpLMEtLQWZsaXluOEZmb00xbnBHbk01bm43SnhwcnZmYnF6aTRyMFkyU0hBSGFHaTFTclhGeUprMzFNZ3BweWEvN1lCMy8vQjIzSXYiLCJtYWMiOiJiYWFkMWM2MzI3NDhlYzg3ZDAwYTMxYjBjOGJiMDdiZDFmNTgwOTU1YjJhNWNhNWEwNTg5YTM0YzM1MWVkMjg3IiwidGFnIjoiIn0%3D',
    'XSRF-TOKEN': 'eyJpdiI6Ik9OekFza09seVlycXFpUk0yUzBFVGc9PSIsInZhbHVlIjoicUNtaDVUelNQckpYck9hSHl5OTNBbzhZemdLYkc5Z2xvL0xPNTZOWEM1SWk0Vjlwd2NEV004UkpiejhaY2JkSW9PQWc1RmMwVFBHL0dYUnVHbjhlZnFrVFR1akdNOFhKNGU4cW9abzFIVWVqdmhiUUFTU3B1MUs4aTlGT1BIZTIiLCJtYWMiOiJkN2JlODA0MDM3Y2IwNjBhNDM5MmJjNjVjMjhlZDM1NGE4NWYzNjE1MDhiM2M3YTA4YmY2Njk3MzRjOTcwZWY0IiwidGFnIjoiIn0%3D',
}

session = requests.Session()
for name, value in cookies.items():
    session.cookies.set(name, value)

url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"

# Test 1: Try different list values
logger.info("🔍 Test 1: Different list parameters")
list_options = ['futures.options', 'options', 'futures', 'all']
symbol = 'MM9M25'

for list_param in list_options:
    params = {
        'symbol': symbol,
        'list': list_param,
        'fields': 'symbol,lastPrice,strike',
        'raw': '1'
    }
    
    headers = {
        'Accept': 'application/json',
        'X-XSRF-TOKEN': urllib.parse.unquote(cookies['XSRF-TOKEN']),
        'Referer': 'https://www.barchart.com/futures/quotes/NQU25/options/MM9M25'
    }
    
    try:
        response = session.get(url, params=params, headers=headers)
        logger.info(f"  list='{list_param}': status={response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"    count={data.get('count')}, total={data.get('total')}")
    except Exception as e:
        logger.error(f"  Error: {e}")

# Test 2: Try just the futures contract
logger.info("\n🔍 Test 2: Futures contracts")
futures_symbols = ['NQU25', 'NQM25', 'NQZ25']

for fut_symbol in futures_symbols:
    params = {
        'symbol': fut_symbol,
        'fields': 'symbol,lastPrice,contract',
        'raw': '1'
    }
    
    response = session.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        logger.info(f"  {fut_symbol}: count={data.get('count')}, total={data.get('total')}")
        if data.get('count', 0) > 0:
            logger.info(f"    ✅ Futures data exists!")

# Test 3: Check specific option format
logger.info("\n🔍 Test 3: Specific option contract formats")
option_formats = [
    'MM9M25',
    'MM9M5',
    'OQU25|19000C',  # Full option format
    'NQU25|MM9M25',  # Futures|Option format
]

for opt in option_formats:
    params = {
        'symbol': opt,
        'list': 'futures.options',
        'fields': 'symbol,strike,lastPrice',
        'raw': '1'
    }
    
    response = session.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        logger.info(f"  {opt}: count={data.get('count')}, total={data.get('total')}")

# Test 4: Get available expiration dates
logger.info("\n🔍 Test 4: Available expirations")
params = {
    'root': 'NQ',
    'list': 'futures.expirations',
    'fields': 'symbol,contract,expirationDate',
    'raw': '1'
}

response = session.get(url, params=params, headers=headers)
if response.status_code == 200:
    data = response.json()
    logger.info(f"  Expirations: count={data.get('count')}, total={data.get('total')}")