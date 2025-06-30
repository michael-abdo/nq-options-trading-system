#!/usr/bin/env python3
"""
Screenshot Data Normalizer
Converts OCR-extracted data to match API data format for comparison
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScreenshotDataNormalizer:
    """Normalize screenshot data to match API format"""
    
    def __init__(self):
        self.multiplier = 20  # NQ multiplier for premium calculation
    
    def normalize_screenshot_data(self, ocr_contracts: List[Dict[str, Any]], 
                                 symbol: str) -> Dict[str, Any]:
        """
        Normalize OCR-extracted contracts to match API data structure
        
        Args:
            ocr_contracts: List of contracts from OCR
            symbol: Options symbol (e.g., "MQ6M25")
            
        Returns:
            Normalized data matching API structure
        """
        try:
            # Separate calls and puts
            calls = []
            puts = []
            
            for contract in ocr_contracts:
                if contract.get("type") == "Call":
                    calls.append(self._normalize_contract(contract, "Call"))
                elif contract.get("type") == "Put":
                    puts.append(self._normalize_contract(contract, "Put"))
            
            # Build response matching API structure
            normalized = {
                "count": 2,  # Call and Put sections
                "total": len(calls) + len(puts),
                "data": {
                    "Call": calls,
                    "Put": puts
                },
                "meta": {
                    "symbol": symbol,
                    "source": "screenshot_ocr",
                    "normalized_at": datetime.now().isoformat()
                }
            }
            
            return normalized
            
        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            return {
                "error": str(e),
                "data": {"Call": [], "Put": []}
            }
    
    def _normalize_contract(self, contract: Dict[str, Any], 
                           option_type: str) -> Dict[str, Any]:
        """Normalize a single contract to match API format"""
        
        strike = contract.get("strike")
        if not strike:
            return None
        
        # Format strike like API: "3,500.00C" or "3,500.00P"
        strike_str = f"{strike:,.2f}{option_type[0]}"
        
        # Get prices
        last_price = contract.get("last", 0) or 0
        bid_price = contract.get("bid", 0) or 0
        ask_price = contract.get("ask", 0) or 0
        open_price = contract.get("open", 0) or 0
        high_price = contract.get("high", 0) or 0
        low_price = contract.get("low", 0) or 0
        
        # Calculate premium (last_price * multiplier)
        premium = last_price * self.multiplier if last_price else 0
        
        # Build normalized contract
        normalized = {
            "strike": strike_str,
            "openPrice": "N/A" if not open_price else f"{open_price:,.2f}",
            "highPrice": "N/A" if not high_price else f"{high_price:,.2f}",
            "lowPrice": "N/A" if not low_price else f"{low_price:,.2f}",
            "lastPrice": "N/A" if not last_price else f"{last_price:,.2f}",
            "priceChange": contract.get("change", "N/A"),
            "bidPrice": "N/A" if not bid_price else f"{bid_price:,.2f}",
            "askPrice": "N/A" if not ask_price else f"{ask_price:,.2f}",
            "volume": contract.get("volume", "N/A"),
            "openInterest": contract.get("open_interest", "N/A"),
            "premium": f"{premium:,.2f}" if premium else "N/A",
            "tradeTime": contract.get("time", "N/A"),
            "optionType": option_type,
            "symbol": f"{contract.get('symbol', 'MQ6M5')}|{int(strike)}{option_type[0]}",
            "raw": {
                "strike": strike,
                "openPrice": open_price,
                "highPrice": high_price,
                "lowPrice": low_price,
                "lastPrice": last_price,
                "priceChange": self._parse_change(contract.get("change")),
                "bidPrice": bid_price,
                "askPrice": ask_price,
                "volume": contract.get("volume"),
                "openInterest": contract.get("open_interest"),
                "premium": premium,
                "optionType": option_type
            }
        }
        
        return normalized
    
    def _parse_change(self, change_str: Any) -> float:
        """Parse change string to float"""
        if not change_str or change_str == "N/A":
            return 0
        
        if isinstance(change_str, (int, float)):
            return float(change_str)
        
        # Remove + or - and parse
        try:
            return float(str(change_str).replace('+', '').replace(',', ''))
        except:
            return 0
    
    def extract_summary_stats(self, normalized_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary statistics from normalized data"""
        
        calls = normalized_data.get("data", {}).get("Call", [])
        puts = normalized_data.get("data", {}).get("Put", [])
        
        # Calculate totals
        call_oi_total = sum(c["raw"]["openInterest"] or 0 for c in calls if c)
        put_oi_total = sum(p["raw"]["openInterest"] or 0 for p in puts if p)
        
        call_volume_total = sum(c["raw"]["volume"] or 0 for c in calls if c)
        put_volume_total = sum(p["raw"]["volume"] or 0 for p in puts if p)
        
        call_premium_total = sum(c["raw"]["premium"] or 0 for c in calls if c)
        put_premium_total = sum(p["raw"]["premium"] or 0 for p in puts if p)
        
        # Count contracts with data
        calls_with_data = sum(1 for c in calls if c and c["raw"]["lastPrice"])
        puts_with_data = sum(1 for p in puts if p and p["raw"]["lastPrice"])
        
        return {
            "total_contracts": len(calls) + len(puts),
            "contracts_with_data": calls_with_data + puts_with_data,
            "call_contracts": len(calls),
            "put_contracts": len(puts),
            "call_oi_total": call_oi_total,
            "put_oi_total": put_oi_total,
            "call_volume_total": call_volume_total,
            "put_volume_total": put_volume_total,
            "call_premium_total": call_premium_total,
            "put_premium_total": put_premium_total,
            "put_call_oi_ratio": put_oi_total / call_oi_total if call_oi_total > 0 else 0,
            "put_call_volume_ratio": put_volume_total / call_volume_total if call_volume_total > 0 else 0
        }


# Module-level convenience function
def normalize_screenshot_data(ocr_contracts: List[Dict[str, Any]], 
                            symbol: str) -> Dict[str, Any]:
    """Normalize OCR contracts to API format"""
    normalizer = ScreenshotDataNormalizer()
    return normalizer.normalize_screenshot_data(ocr_contracts, symbol)


if __name__ == "__main__":
    # Test with sample OCR data
    sample_contracts = [
        {
            "strike": 3500.0,
            "type": "Call",
            "last": 19244.75,
            "bid": 19300.0,
            "ask": 19358.75,
            "volume": None,
            "open_interest": None,
            "premium": 384895.0
        },
        {
            "strike": 4000.0,
            "type": "Call", 
            "last": 18744.75,
            "bid": 18800.0,
            "ask": 18858.75,
            "volume": None,
            "open_interest": None,
            "premium": 374895.0
        }
    ]
    
    normalized = normalize_screenshot_data(sample_contracts, "MQ6M25")
    
    print(f"Normalized {normalized['total']} contracts")
    print(f"Calls: {len(normalized['data']['Call'])}")
    print(f"Puts: {len(normalized['data']['Put'])}")
    
    # Show first contract
    if normalized['data']['Call']:
        first_call = normalized['data']['Call'][0]
        print(f"\nFirst Call:")
        print(f"  Strike: {first_call['strike']}")
        print(f"  Last: {first_call['lastPrice']}")
        print(f"  Bid: {first_call['bidPrice']}")
        print(f"  Ask: {first_call['askPrice']}")