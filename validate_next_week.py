#!/usr/bin/env python3
"""
Validate symbol generation for the next 7 days
Shows exactly what symbols will be generated each day
"""

from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "tasks/options_trading_system/data_ingestion/barchart_web_scraper"))
from solution import BarchartAPIComparator

def main():
    comp = BarchartAPIComparator()
    
    print("📅 SYMBOL GENERATION FOR NEXT 7 DAYS")
    print("="*80)
    
    start_date = datetime.now()
    
    for i in range(7):
        test_date = start_date + timedelta(days=i)
        day_name = test_date.strftime('%A')
        date_str = test_date.strftime('%Y-%m-%d')
        
        print(f"\n{date_str} ({day_name}):")
        print("-"*40)
        
        # Create a custom comparator for this specific date
        # We'll use the same logic but with the test date
        from robust_symbol_validator import RobustSymbolValidator
        validator = RobustSymbolValidator()
        
        weekly_sym, weekly_exp = validator.generate_symbol_for_date(test_date, "weekly")
        friday_sym, friday_exp = validator.generate_symbol_for_date(test_date, "friday")
        monthly_sym, monthly_exp = validator.generate_symbol_for_date(test_date, "monthly")
        
        # Special handling for 0DTE
        if test_date.weekday() == 4:  # Friday
            dte0_sym, dte0_exp = validator.generate_symbol_for_date(test_date, "0dte")
            print(f"  Weekly:  {weekly_sym} → expires {weekly_exp.strftime('%Y-%m-%d %a')}")
            print(f"  Friday:  {friday_sym} → expires {friday_exp.strftime('%Y-%m-%d %a')}")
            print(f"  0DTE:    {dte0_sym} → expires TODAY!")
            print(f"  Monthly: {monthly_sym} → expires {monthly_exp.strftime('%Y-%m-%d %a')}")
            
            if friday_sym == dte0_sym:
                print("  ✅ Friday = 0DTE confirmed!")
            else:
                print("  ❌ ERROR: Friday != 0DTE")
        else:
            print(f"  Weekly:  {weekly_sym} → expires {weekly_exp.strftime('%Y-%m-%d %a')}")
            print(f"  Friday:  {friday_sym} → expires {friday_exp.strftime('%Y-%m-%d %a')}")
            print(f"  0DTE:    N/A (only on Fridays)")
            print(f"  Monthly: {monthly_sym} → expires {monthly_exp.strftime('%Y-%m-%d %a')}")
        
        # Decode the symbols
        if len(weekly_sym) >= 5:
            week_num = weekly_sym[2]
            month_code = weekly_sym[3]
            month_names = {'F': 'Jan', 'G': 'Feb', 'H': 'Mar', 'J': 'Apr', 'K': 'May', 'M': 'Jun',
                          'N': 'Jul', 'Q': 'Aug', 'U': 'Sep', 'V': 'Oct', 'X': 'Nov', 'Z': 'Dec'}
            print(f"\n  Decoded: Week {week_num} of {month_names.get(month_code, month_code)}")

if __name__ == "__main__":
    main()