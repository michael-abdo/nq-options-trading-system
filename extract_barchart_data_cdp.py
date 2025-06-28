#!/usr/bin/env python3
"""
Extract Barchart options data using Chrome DevTools Protocol
"""

import requests
import json
import logging
from datetime import datetime
import os

def main():
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    # Chrome DevTools tab info
    tab_id = "955B966DC8930B45EB481241CDA0BE78"  # From barchart_tab_info.json
    cdp_url = f"http://localhost:9222/json/runtime/evaluate"
    
    logger.info("🌐 Connecting to Chrome DevTools Protocol...")
    
    # JavaScript to extract options data from the page
    js_code = """
    // Function to extract options data from Barchart page
    function extractOptionsData() {
        const data = {
            symbol: null,
            underlying: null,
            timestamp: new Date().toISOString(),
            options: []
        };
        
        // Try to get the symbol from the page title or URL
        const title = document.title;
        const urlMatch = window.location.pathname.match(/options\/([^?]+)/);
        if (urlMatch) {
            data.symbol = urlMatch[1];
        }
        
        // Try to get underlying symbol
        const underlyingMatch = window.location.pathname.match(/quotes\/([^/]+)\/options/);
        if (underlyingMatch) {
            data.underlying = underlyingMatch[1];
        }
        
        // Look for options table rows
        const rows = document.querySelectorAll('tr[data-ng-repeat*="option"], tbody tr');
        
        rows.forEach((row, index) => {
            const cells = row.querySelectorAll('td, .ng-binding');
            
            if (cells.length >= 7) {
                // Extract data from cells - this may need adjustment based on page structure
                const optionData = {
                    strike: null,
                    call_last: null,
                    call_bid: null,
                    call_ask: null,
                    call_volume: null,
                    put_last: null,
                    put_bid: null,
                    put_ask: null,
                    put_volume: null
                };
                
                // Try to extract numerical values from cells
                for (let i = 0; i < cells.length && i < 10; i++) {
                    const text = cells[i].textContent.trim();
                    const value = parseFloat(text.replace(/[$,]/g, ''));
                    
                    // Map based on typical Barchart column order
                    switch(i) {
                        case 0: optionData.strike = isNaN(value) ? text : value; break;
                        case 1: optionData.call_last = isNaN(value) ? null : value; break;
                        case 2: optionData.call_bid = isNaN(value) ? null : value; break;
                        case 3: optionData.call_ask = isNaN(value) ? null : value; break;
                        case 4: optionData.call_volume = isNaN(value) ? null : value; break;
                        case 5: optionData.put_last = isNaN(value) ? null : value; break;
                        case 6: optionData.put_bid = isNaN(value) ? null : value; break;
                        case 7: optionData.put_ask = isNaN(value) ? null : value; break;
                        case 8: optionData.put_volume = isNaN(value) ? null : value; break;
                    }
                }
                
                // Only add if we have meaningful data
                if (optionData.strike !== null) {
                    data.options.push(optionData);
                }
            }
        });
        
        // Alternative: Try to extract from any data attributes or Angular scope
        try {
            // Look for Angular scope data
            const ngElements = document.querySelectorAll('[ng-controller]');
            if (ngElements.length > 0) {
                const scope = angular.element(ngElements[0]).scope();
                if (scope && scope.options) {
                    data.angular_options = scope.options;
                }
            }
        } catch (e) {
            // Angular may not be available
        }
        
        // Try to get data from any visible table
        const tables = document.querySelectorAll('table');
        tables.forEach((table, tableIndex) => {
            const tableRows = table.querySelectorAll('tbody tr');
            if (tableRows.length > 0) {
                data[`table_${tableIndex}_rows`] = tableRows.length;
            }
        });
        
        return data;
    }
    
    // Execute the extraction
    extractOptionsData();
    """
    
    # Prepare the request to Chrome DevTools
    payload = {
        "id": 1,
        "method": "Runtime.evaluate",
        "params": {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": False
        }
    }
    
    # Use the tab-specific endpoint
    tab_cdp_url = f"http://localhost:9222/json/runtime/evaluate"
    
    try:
        logger.info("📊 Executing JavaScript to extract options data...")
        
        # Try direct HTTP request to DevTools API
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Try using the tab ID in the URL
        response = requests.post(f"http://localhost:9222/json/runtime/evaluate", 
                               json=payload, 
                               headers=headers,
                               timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            
            if 'result' in result and 'value' in result['result']:
                data = result['result']['value']
                logger.info(f"✅ Successfully extracted data!")
                logger.info(f"   Symbol: {data.get('symbol', 'Unknown')}")
                logger.info(f"   Underlying: {data.get('underlying', 'Unknown')}")
                logger.info(f"   Options count: {len(data.get('options', []))}")
                
                # Save the extracted data
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_dir = f"outputs/{datetime.now().strftime('%Y%m%d')}/extracted_data"
                os.makedirs(output_dir, exist_ok=True)
                
                filename = f"barchart_extracted_{data.get('symbol', 'unknown')}_{timestamp}.json"
                filepath = os.path.join(output_dir, filename)
                
                with open(filepath, 'w') as f:
                    json.dump(data, f, indent=2)
                
                logger.info(f"💾 Data saved to: {filepath}")
                
                # Show sample data
                if data.get('options'):
                    sample = data['options'][0]
                    logger.info(f"   Sample option - Strike: {sample.get('strike')}, Call Last: {sample.get('call_last')}")
                
                return 0
            else:
                logger.error(f"❌ No data in response: {result}")
                return 1
        else:
            logger.error(f"❌ HTTP error {response.status_code}: {response.text}")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error connecting to Chrome DevTools: {e}")
        
        # Fallback: Provide manual instructions
        logger.info("📋 Manual extraction method:")
        logger.info("1. Go to Chrome DevTools (F12)")
        logger.info("2. Click Console tab")
        logger.info("3. Paste and run this JavaScript:")
        
        print("\n" + "="*80)
        print("JAVASCRIPT CODE TO RUN IN CONSOLE:")
        print("="*80)
        print(js_code)
        print("="*80)
        
        return 1

if __name__ == "__main__":
    exit(main())