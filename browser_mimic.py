#!/usr/bin/env python3
"""
Mimic browser behavior exactly
"""

import requests
import logging

logging.basicConfig(level=logging.DEBUG)

# Your browser cookies
cookie_string = 'OTGPPConsent=DBABLA~BAQCAAAACZA.QA; _gcl_au=1.1.1116205833.1748870379; _admrla=2.2-f8ff83d09d38bc20-94092ad0-3fb3-11f0-820c-8806f0aed666; OptanonAlertBoxClosed=2025-06-04T13:36:15.066Z; _hjSessionUser_2563157=eyJpZCI6IjNjNDVkNWIyLWVjNGMtNTY1YS05ZGE3LTFhZjViZGQ3Yzg2YiIsImNyZWF0ZWQiOjE3NDkwNDQ3MDc4MzYsImV4aXN0aW5nIjp0cnVlfQ==; _ga=GA1.1.1317851658.1748870380; bcFreeUserPageView=0; isDarkTheme=true; webinarClosed=249; ic_tagmanager=AY; XSRF-TOKEN=eyJpdiI6ImltSWRBeU92eW5OVlBCS3Zrbmpyanc9PSIsInZhbHVlIjoibEluci8vaFpkTUxpMWd2eDltY3JCanBLdG8zZHBUMGhjWkxqcHc4Z0IzZDhUOFNZMWx6U01Xbko2TGY2SVRiblFRM0VWd2pkSm1menNlR1lsUWw3bVVIZUJIZ016allMc0V6R292TTA5QWlsRnJXWGIxQnZrMzdzeVRrclpsck8iLCJtYWMiOiI4MTAyNWNiN2ZmY2ZjNDQ0NDc0NGZkMzgxMTY0N2FjM2Y5YzRjM2Q5M2M5ODU0ODBmMjYyNWEyMWIzOGM4ODZkIiwidGFnIjoiIn0%3D; IC_ViewCounter_www.barchart.com=11; OptanonConsent=isGpcEnabled=0&datestamp=Thu+Jun+26+2025+08%3A57%3A57+GMT-0500+(Central+Daylight+Time)&version=202501.2.0&browserGpcFlag=0&isIABGlobal=false&hosts=&consentId=ca062816-ba35-4e3b-9dc3-9761f00fa0a1&interactionCount=2&isAnonUser=1&landingPath=NotLandingPage&GPPCookiesCount=1&groups=C0001%3A1%2CC0003%3A1%2COSSTA_BG%3A1%2CC0004%3A1%2CC0002%3A1&AwaitingReconsent=false&intType=3&geolocation=US%3BOR; _ga_PE0FK9V6VN=GS2.1.s1750942389$o38$g1$t1750946277$j58$l0$h0; _awl=2.1750946279.5-19abf227c83bc86866e5aaa0b22bedfe-6763652d75732d7765737431-1'

# Parse cookies
cookies = {}
for cookie in cookie_string.split('; '):
    if '=' in cookie:
        name, value = cookie.split('=', 1)
        cookies[name] = value

print(f"Found {len(cookies)} cookies")
print(f"Essential cookies: {[k for k in cookies.keys() if 'laravel' in k.lower() or 'xsrf' in k.lower()]}")

# The EXACT request the browser makes
url = "https://www.barchart.com/proxies/core-api/v1/quotes/get"
params = {
    'symbol': 'MM9M25',
    'list': 'futures.options',
    'fields': 'strike,openPrice,highPrice,lowPrice,lastPrice,priceChange,bidPrice,askPrice,volume,openInterest,premium,tradeTime,longSymbol,optionType,symbol',
    'meta': 'field.shortName,field.description,field.type',
    'groupBy': 'optionType',
    'orderBy': 'strike',
    'orderDir': 'asc'
}

headers = {
    'Accept': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://www.barchart.com/futures/quotes/NQU25/options/MM9M25?futuresOptionsView=merged',
}

# Add XSRF token
if 'XSRF-TOKEN' in cookies:
    import urllib.parse
    headers['X-XSRF-TOKEN'] = urllib.parse.unquote(cookies['XSRF-TOKEN'])

session = requests.Session()
for name, value in cookies.items():
    session.cookies.set(name, value)

response = session.get(url, params=params, headers=headers)
print(f"\nStatus: {response.status_code}")
print(f"Response length: {len(response.text)}")

if response.status_code == 200:
    data = response.json()
    print(f"count: {data.get('count')}")
    print(f"total: {data.get('total')}")
    print(f"data type: {type(data.get('data'))}")
    
    if isinstance(data.get('data'), dict):
        print(f"data keys: {list(data['data'].keys())}")
    elif isinstance(data.get('data'), list):
        print(f"data is list with {len(data['data'])} items")
else:
    print(f"Error response: {response.text[:200]}")

# Also try without groupBy to see if that's the issue
print("\n--- Testing without groupBy ---")
params2 = params.copy()
del params2['groupBy']
response2 = session.get(url, params=params2, headers=headers)
print(f"Status: {response2.status_code}")
if response2.status_code == 200:
    data2 = response2.json()
    print(f"count: {data2.get('count')}")
    print(f"total: {data2.get('total')}")