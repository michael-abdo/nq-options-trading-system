#!/usr/bin/env python3
"""
Screenshot Data Comparator
Compares normalized screenshot data with API data to validate accuracy
"""

import logging
from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ScreenshotComparator:
    """Compare screenshot OCR data with API data"""
    
    def __init__(self, tolerance: float = 0.01):
        """
        Initialize comparator
        
        Args:
            tolerance: Price comparison tolerance (default 1%)
        """
        self.tolerance = tolerance
    
    def compare_data(self, screenshot_data: Dict[str, Any], 
                    api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compare normalized screenshot data with API data
        
        Returns:
            Comparison results with discrepancies and match statistics
        """
        try:
            results = {
                "timestamp": datetime.now().isoformat(),
                "success": True,
                "summary": {},
                "discrepancies": [],
                "match_stats": {},
                "warnings": []
            }
            
            # Extract contracts
            screenshot_calls = screenshot_data.get("data", {}).get("Call", [])
            screenshot_puts = screenshot_data.get("data", {}).get("Put", [])
            api_calls = api_data.get("data", {}).get("Call", [])
            api_puts = api_data.get("data", {}).get("Put", [])
            
            # Compare totals
            results["summary"] = {
                "screenshot_total": len(screenshot_calls) + len(screenshot_puts),
                "api_total": api_data.get("total", 0),
                "screenshot_calls": len(screenshot_calls),
                "api_calls": len(api_calls),
                "screenshot_puts": len(screenshot_puts),
                "api_puts": len(api_puts),
                "coverage_ratio": (len(screenshot_calls) + len(screenshot_puts)) / api_data.get("total", 1) if api_data.get("total", 0) > 0 else 0
            }
            
            # Check if screenshot captured all data
            if results["summary"]["screenshot_total"] < results["summary"]["api_total"]:
                results["warnings"].append(
                    f"Screenshot shows only {results['summary']['screenshot_total']} of {results['summary']['api_total']} contracts - may be paginated"
                )
            
            # Compare individual contracts
            call_comparison = self._compare_contract_sets(screenshot_calls, api_calls, "Call")
            put_comparison = self._compare_contract_sets(screenshot_puts, api_puts, "Put")
            
            results["discrepancies"].extend(call_comparison["discrepancies"])
            results["discrepancies"].extend(put_comparison["discrepancies"])
            
            # Calculate match statistics
            results["match_stats"] = {
                "calls": call_comparison["stats"],
                "puts": put_comparison["stats"],
                "overall": self._calculate_overall_stats(call_comparison["stats"], put_comparison["stats"])
            }
            
            # Determine if validation passed
            overall_match_rate = results["match_stats"]["overall"]["match_rate"]
            results["validation_passed"] = overall_match_rate >= 0.90  # 90% match threshold
            
            if not results["validation_passed"]:
                results["warnings"].append(
                    f"Low match rate: {overall_match_rate:.1%} - check OCR accuracy or data freshness"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _compare_contract_sets(self, screenshot_contracts: List[Dict], 
                              api_contracts: List[Dict], 
                              option_type: str) -> Dict[str, Any]:
        """Compare sets of contracts (calls or puts)"""
        
        discrepancies = []
        matches = 0
        total_fields_compared = 0
        fields_matched = 0
        
        # Create lookup by strike
        api_by_strike = {}
        for contract in api_contracts:
            if contract and "raw" in contract:
                strike = contract["raw"].get("strike")
                if strike:
                    api_by_strike[strike] = contract
        
        # Compare each screenshot contract
        for sc_contract in screenshot_contracts:
            if not sc_contract or "raw" not in sc_contract:
                continue
                
            strike = sc_contract["raw"].get("strike")
            if not strike:
                continue
            
            api_contract = api_by_strike.get(strike)
            if not api_contract:
                discrepancies.append({
                    "type": "missing_in_api",
                    "option_type": option_type,
                    "strike": strike,
                    "message": f"{option_type} strike {strike} found in screenshot but not in API"
                })
                continue
            
            # Compare contract fields
            contract_discrepancies = self._compare_contracts(sc_contract, api_contract, strike, option_type)
            
            if contract_discrepancies:
                discrepancies.extend(contract_discrepancies)
            else:
                matches += 1
            
            # Track field-level statistics
            field_stats = self._compare_contract_fields(sc_contract["raw"], api_contract["raw"])
            total_fields_compared += field_stats["total"]
            fields_matched += field_stats["matched"]
        
        # Check for contracts in API but not screenshot
        for api_strike, api_contract in api_by_strike.items():
            found = any(sc["raw"].get("strike") == api_strike for sc in screenshot_contracts if sc)
            if not found:
                discrepancies.append({
                    "type": "missing_in_screenshot",
                    "option_type": option_type,
                    "strike": api_strike,
                    "message": f"{option_type} strike {api_strike} in API but not found in screenshot"
                })
        
        stats = {
            "total_screenshot": len(screenshot_contracts),
            "total_api": len(api_contracts),
            "matches": matches,
            "match_rate": matches / len(api_contracts) if api_contracts else 0,
            "field_match_rate": fields_matched / total_fields_compared if total_fields_compared > 0 else 0
        }
        
        return {
            "discrepancies": discrepancies,
            "stats": stats
        }
    
    def _compare_contracts(self, sc_contract: Dict, api_contract: Dict, 
                          strike: float, option_type: str) -> List[Dict]:
        """Compare individual contracts and return discrepancies"""
        
        discrepancies = []
        sc_raw = sc_contract.get("raw", {})
        api_raw = api_contract.get("raw", {})
        
        # Fields to compare with tolerances
        price_fields = ["lastPrice", "bidPrice", "askPrice", "openPrice", "highPrice", "lowPrice"]
        
        for field in price_fields:
            sc_value = sc_raw.get(field)
            api_value = api_raw.get(field)
            
            # Skip if either is None/0
            if not sc_value or not api_value:
                continue
            
            # Compare with tolerance
            if not self._prices_match(sc_value, api_value):
                discrepancies.append({
                    "type": "price_mismatch",
                    "option_type": option_type,
                    "strike": strike,
                    "field": field,
                    "screenshot_value": sc_value,
                    "api_value": api_value,
                    "difference": abs(sc_value - api_value),
                    "difference_pct": abs((sc_value - api_value) / api_value) * 100 if api_value else 0
                })
        
        # Compare volume and OI (exact match expected)
        for field in ["volume", "openInterest"]:
            sc_value = sc_raw.get(field)
            api_value = api_raw.get(field)
            
            # Both None is ok
            if sc_value is None and api_value is None:
                continue
            
            # If one has data and other doesn't
            if (sc_value is None) != (api_value is None):
                discrepancies.append({
                    "type": "data_availability",
                    "option_type": option_type,
                    "strike": strike,
                    "field": field,
                    "screenshot_value": sc_value,
                    "api_value": api_value,
                    "message": f"{field} available in {'API' if sc_value is None else 'screenshot'} but not the other"
                })
            elif sc_value != api_value:
                discrepancies.append({
                    "type": "volume_mismatch",
                    "option_type": option_type,
                    "strike": strike,
                    "field": field,
                    "screenshot_value": sc_value,
                    "api_value": api_value,
                    "difference": abs((sc_value or 0) - (api_value or 0))
                })
        
        return discrepancies
    
    def _compare_contract_fields(self, sc_raw: Dict, api_raw: Dict) -> Dict[str, int]:
        """Count matching vs total fields compared"""
        
        fields_to_check = ["lastPrice", "bidPrice", "askPrice", "volume", "openInterest"]
        total = 0
        matched = 0
        
        for field in fields_to_check:
            sc_value = sc_raw.get(field)
            api_value = api_raw.get(field)
            
            # Skip if both None
            if sc_value is None and api_value is None:
                continue
            
            total += 1
            
            if field in ["lastPrice", "bidPrice", "askPrice"]:
                if sc_value and api_value and self._prices_match(sc_value, api_value):
                    matched += 1
            else:
                if sc_value == api_value:
                    matched += 1
        
        return {"total": total, "matched": matched}
    
    def _prices_match(self, price1: float, price2: float) -> bool:
        """Check if two prices match within tolerance"""
        if price1 == price2:
            return True
        
        if price1 == 0 or price2 == 0:
            return False
        
        # Calculate percentage difference
        diff_pct = abs((price1 - price2) / price2)
        return diff_pct <= self.tolerance
    
    def _calculate_overall_stats(self, call_stats: Dict, put_stats: Dict) -> Dict:
        """Calculate overall match statistics"""
        
        total_contracts = call_stats["total_api"] + put_stats["total_api"]
        total_matches = call_stats["matches"] + put_stats["matches"]
        
        total_field_comparisons = (call_stats.get("field_match_rate", 0) * call_stats["total_api"] + 
                                  put_stats.get("field_match_rate", 0) * put_stats["total_api"])
        
        return {
            "total_contracts": total_contracts,
            "total_matches": total_matches,
            "match_rate": total_matches / total_contracts if total_contracts > 0 else 0,
            "avg_field_match_rate": total_field_comparisons / total_contracts if total_contracts > 0 else 0
        }
    
    def format_comparison_report(self, comparison_results: Dict[str, Any]) -> str:
        """Format comparison results as readable report"""
        
        report = []
        report.append("=" * 60)
        report.append("📊 SCREENSHOT vs API COMPARISON REPORT")
        report.append("=" * 60)
        
        summary = comparison_results.get("summary", {})
        report.append(f"\n📈 Contract Summary:")
        report.append(f"   Screenshot Total: {summary.get('screenshot_total', 0)}")
        report.append(f"   API Total: {summary.get('api_total', 0)}")
        report.append(f"   Coverage: {summary.get('coverage_ratio', 0):.1%}")
        
        stats = comparison_results.get("match_stats", {})
        if "overall" in stats:
            overall = stats["overall"]
            report.append(f"\n✅ Match Statistics:")
            report.append(f"   Overall Match Rate: {overall.get('match_rate', 0):.1%}")
            report.append(f"   Field Match Rate: {overall.get('avg_field_match_rate', 0):.1%}")
        
        # Warnings
        warnings = comparison_results.get("warnings", [])
        if warnings:
            report.append(f"\n⚠️  Warnings:")
            for warning in warnings:
                report.append(f"   - {warning}")
        
        # Discrepancies summary
        discrepancies = comparison_results.get("discrepancies", [])
        if discrepancies:
            report.append(f"\n❌ Discrepancies Found: {len(discrepancies)}")
            
            # Group by type
            by_type = {}
            for disc in discrepancies[:10]:  # Show first 10
                disc_type = disc.get("type", "unknown")
                if disc_type not in by_type:
                    by_type[disc_type] = []
                by_type[disc_type].append(disc)
            
            for disc_type, items in by_type.items():
                report.append(f"\n   {disc_type}: {len(items)} issues")
                for item in items[:3]:  # Show first 3 of each type
                    if disc_type == "price_mismatch":
                        report.append(f"     - {item['option_type']} {item['strike']}: "
                                    f"{item['field']} {item['screenshot_value']:.2f} vs {item['api_value']:.2f} "
                                    f"({item['difference_pct']:.1f}% diff)")
                    else:
                        report.append(f"     - {item.get('message', str(item))}")
        
        # Validation result
        report.append(f"\n🏁 Validation Result: {'✅ PASSED' if comparison_results.get('validation_passed') else '❌ FAILED'}")
        
        report.append("=" * 60)
        
        return "\n".join(report)


# Module-level convenience functions
def compare_screenshot_to_api(screenshot_data: Dict[str, Any], 
                             api_data: Dict[str, Any],
                             tolerance: float = 0.01) -> Dict[str, Any]:
    """Compare screenshot data to API data"""
    comparator = ScreenshotComparator(tolerance=tolerance)
    return comparator.compare_data(screenshot_data, api_data)


if __name__ == "__main__":
    # Test comparison
    print("Screenshot Comparator Test")
    
    # Sample data
    screenshot_data = {
        "total": 2,
        "data": {
            "Call": [{
                "raw": {
                    "strike": 3500.0,
                    "lastPrice": 19244.75,
                    "bidPrice": 19300.0,
                    "askPrice": 19358.75,
                    "volume": None,
                    "openInterest": None
                }
            }],
            "Put": []
        }
    }
    
    api_data = {
        "total": 2,
        "data": {
            "Call": [{
                "raw": {
                    "strike": 3500.0,
                    "lastPrice": 19245.00,  # Slightly different
                    "bidPrice": 19300.00,
                    "askPrice": 19360.00,
                    "volume": 10,
                    "openInterest": 100
                }
            }],
            "Put": []
        }
    }
    
    results = compare_screenshot_to_api(screenshot_data, api_data)
    
    comparator = ScreenshotComparator()
    report = comparator.format_comparison_report(results)
    print(report)