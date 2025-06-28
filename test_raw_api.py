#!/usr/bin/env python3
"""
Test raw API response to understand what's happening
"""

import requests
import json
import logging

logging.basicConfig(level=logging.DEBUG)

# Let's make a completely raw request to see what happens
url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"

# Exact params from working request
params = {
    'symbol': 'MC7M5',
    'list': 'futures.options',
    'fields': 'strike,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,longSymbol,optionType,symbol,symbolCode,symbolType',
    'meta': 'field.shortName,field.description,field.type,lists.lastUpdate',
    'groupBy': 'optionType',
    'orderBy': 'strike',
    'orderDir': 'asc',
    'raw': '1'
}

# No auth, just to see the error
response = requests.get(url, params=params)
print(f"No auth status: {response.status_code}")
print(f"Response: {response.text[:500]}")

# Try without groupBy - maybe that's the issue?
params2 = params.copy()
del params2['groupBy']
response2 = requests.get(url, params=params2)
print(f"\nNo groupBy status: {response2.status_code}")
print(f"Response: {response2.text[:500]}")

# Try a different list parameter
params3 = params.copy()
params3['list'] = 'options'
response3 = requests.get(url, params=params3)
print(f"\nDifferent list status: {response3.status_code}")
print(f"Response: {response3.text[:500]}")