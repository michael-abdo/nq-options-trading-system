#!/usr/bin/env python3
"""
Generalized Options Metrics Calculator
Calculates premium totals, OI totals, and ratios for any options data
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptionsMetricsCalculator:
    """Calculate standard options metrics from Barchart API data"""
    
    def __init__(self, output_base_dir: str = "outputs"):
        self.output_base_dir = output_base_dir
        
    def calculate_metrics(self, data: Dict[str, Any], symbol: str = None) -> Dict[str, Any]:
        """
        Calculate options metrics from API data
        
        Args:
            data: API response data with 'data' containing 'Call' and 'Put' arrays
            symbol: Optional symbol name for metadata
            
        Returns:
            Dictionary with calculated metrics
        """
        if 'data' not in data or 'Call' not in data['data'] or 'Put' not in data['data']:
            raise ValueError("Invalid data format - missing Call/Put data")
            
        calls = data['data']['Call']
        puts = data['data']['Put']
        
        logger.info(f"Processing {len(calls)} calls and {len(puts)} puts for {symbol or 'unknown symbol'}")
        
        # Calculate call metrics
        call_metrics = self._calculate_option_type_metrics(calls, "Call")
        
        # Calculate put metrics  
        put_metrics = self._calculate_option_type_metrics(puts, "Put")
        
        # Calculate totals and ratios
        total_premium = call_metrics['premium_total'] + put_metrics['premium_total']
        total_oi = call_metrics['oi_total'] + put_metrics['oi_total']
        
        put_call_premium_ratio = (put_metrics['premium_total'] / call_metrics['premium_total'] 
                                 if call_metrics['premium_total'] > 0 else 0)
        put_call_oi_ratio = (put_metrics['oi_total'] / call_metrics['oi_total'] 
                            if call_metrics['oi_total'] > 0 else 0)
        
        # Compile results
        results = {
            # Raw values
            'call_premium_total': call_metrics['premium_total'],
            'put_premium_total': put_metrics['premium_total'],
            'total_premium': total_premium,
            'put_call_premium_ratio': put_call_premium_ratio,
            
            'call_oi_total': call_metrics['oi_total'],
            'put_oi_total': put_metrics['oi_total'],
            'total_oi': total_oi,
            'put_call_oi_ratio': put_call_oi_ratio,
            
            # Contract counts
            'call_contracts_total': len(calls),
            'put_contracts_total': len(puts),
            'total_contracts': len(calls) + len(puts),
            'call_contracts_with_premium': call_metrics['contracts_with_premium'],
            'put_contracts_with_premium': put_metrics['contracts_with_premium'],
            'call_contracts_with_oi': call_metrics['contracts_with_oi'],
            'put_contracts_with_oi': put_metrics['contracts_with_oi'],
            
            # Formatted values for display
            'formatted': {
                'call_premium_total': f"${call_metrics['premium_total']:,.2f}",
                'put_premium_total': f"${put_metrics['premium_total']:,.2f}",
                'total_premium': f"${total_premium:,.2f}",
                'put_call_premium_ratio': f"{put_call_premium_ratio:.3f}",
                
                'call_oi_total': f"{call_metrics['oi_total']:,}",
                'put_oi_total': f"{put_metrics['oi_total']:,}",
                'total_oi': f"{total_oi:,}",
                'put_call_oi_ratio': f"{put_call_oi_ratio:.3f}",
            },
            
            # Metadata
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'data_source': 'barchart_api',
            'calculation_version': '1.0'
        }
        
        return results
    
    def _calculate_option_type_metrics(self, contracts: List[Dict], option_type: str) -> Dict[str, Any]:
        """Calculate metrics for a single option type (Call or Put)"""
        
        premium_total = 0
        oi_total = 0
        contracts_with_premium = 0
        contracts_with_oi = 0
        
        for contract in contracts:
            raw = contract.get('raw', {})
            
            # Premium calculation
            premium = raw.get('premium', 0)
            if premium and premium > 0:
                premium_total += premium
                contracts_with_premium += 1
            
            # Open Interest calculation
            open_interest = raw.get('openInterest', 0)
            if open_interest and open_interest > 0:
                oi_total += open_interest
                contracts_with_oi += 1
        
        return {
            'premium_total': premium_total,
            'oi_total': oi_total,
            'contracts_with_premium': contracts_with_premium,
            'contracts_with_oi': contracts_with_oi
        }
    
    def save_timestamped_data(self, data: Dict[str, Any], symbol: str, 
                             data_type: str = "api_data") -> str:
        """
        Save data with timestamp in organized directory structure
        
        Args:
            data: Data to save
            symbol: Symbol name for filename
            data_type: Type of data (api_data, metrics, etc.)
            
        Returns:
            Path to saved file
        """
        # Create timestamped directory structure
        date_str = datetime.now().strftime('%Y%m%d')
        timestamp = datetime.now().strftime('%H%M%S')
        
        output_dir = Path(self.output_base_dir) / date_str / data_type
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        filename = f"{symbol}_{data_type}_{timestamp}.json"
        filepath = output_dir / filename
        
        # Save data
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"💾 {data_type.title()} saved to: {filepath}")
        return str(filepath)
    
    def calculate_and_save_metrics(self, api_data: Dict[str, Any], symbol: str) -> tuple[Dict[str, Any], str]:
        """
        Calculate metrics and save both data and metrics with timestamps
        
        Args:
            api_data: Raw API response data
            symbol: Symbol name
            
        Returns:
            Tuple of (metrics_dict, metrics_file_path)
        """
        # Calculate metrics
        metrics = self.calculate_metrics(api_data, symbol)
        
        # Save metrics with timestamp
        metrics_file = self.save_timestamped_data(metrics, symbol, "metrics")
        
        # Also save the raw API data if not already saved
        api_file = self.save_timestamped_data(api_data, symbol, "api_data")
        
        return metrics, metrics_file
    
    def print_metrics_summary(self, metrics: Dict[str, Any]):
        """Print formatted metrics summary"""
        fmt = metrics['formatted']
        symbol = metrics.get('symbol', 'Unknown')
        
        print(f"\n{'='*60}")
        print(f"📈 {symbol} OPTIONS METRICS")
        print(f"{'='*60}")
        
        print(f"\n💰 PREMIUM ANALYSIS:")
        print(f"   Call Premium Total:     {fmt['call_premium_total']}")
        print(f"   Put Premium Total:      {fmt['put_premium_total']}")
        print(f"   Total Premium:          {fmt['total_premium']}")
        print(f"   Put/Call Premium Ratio: {fmt['put_call_premium_ratio']}")
        
        print(f"\n📊 OPEN INTEREST (OI) ANALYSIS:")
        print(f"   Call OI Total:          {fmt['call_oi_total']}")
        print(f"   Put OI Total:           {fmt['put_oi_total']}")
        print(f"   Total OI:               {fmt['total_oi']}")
        print(f"   Put/Call OI Ratio:      {fmt['put_call_oi_ratio']}")
        
        print(f"\n📋 CONTRACT COUNTS:")
        print(f"   Total Calls:            {metrics['call_contracts_total']}")
        print(f"   Total Puts:             {metrics['put_contracts_total']}")
        print(f"   Total Contracts:        {metrics['total_contracts']}")
        print(f"   Calls with Premium:     {metrics['call_contracts_with_premium']}")
        print(f"   Puts with Premium:      {metrics['put_contracts_with_premium']}")
        
        print(f"\n⏰ TIMESTAMP: {metrics['timestamp']}")
        print(f"{'='*60}")


def calculate_from_file(file_path: str, symbol: str = None) -> Dict[str, Any]:
    """
    Calculate metrics from a saved API data file
    
    Args:
        file_path: Path to JSON file with API data
        symbol: Optional symbol override
        
    Returns:
        Calculated metrics
    """
    calculator = OptionsMetricsCalculator()
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    # Extract symbol from filename if not provided
    if not symbol:
        symbol = Path(file_path).stem.split('_')[0]
    
    metrics = calculator.calculate_metrics(data, symbol)
    calculator.print_metrics_summary(metrics)
    
    # Save metrics
    metrics_file = calculator.save_timestamped_data(metrics, symbol, "metrics")
    
    return metrics


def main():
    """Example usage and CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate options metrics')
    parser.add_argument('--file', help='JSON file with API data')
    parser.add_argument('--symbol', help='Symbol name override')
    
    args = parser.parse_args()
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ File not found: {args.file}")
            return 1
        
        calculate_from_file(args.file, args.symbol)
        return 0
    
    # Example with MQ4M25 data
    example_file = "tasks/options_trading_system/data_ingestion/barchart_web_scraper/outputs/20250626/api_data/barchart_api_MQ4M25_234556.json"
    
    if os.path.exists(example_file):
        print("📊 Calculating metrics for MQ4M25 example...")
        calculate_from_file(example_file, "MQ4M25")
    else:
        print("No example file found. Use --file to specify a data file.")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())