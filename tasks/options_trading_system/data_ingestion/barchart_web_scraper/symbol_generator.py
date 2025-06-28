#!/usr/bin/env python3
"""
Barchart Options Symbol Generator
Generates EOD (End of Day) contract symbols for Barchart options
"""

from datetime import datetime, timedelta
from typing import Tuple


class BarchartSymbolGenerator:
    """Generate Barchart options contract symbols for various expiry types"""
    
    def get_eod_contract_symbol(self, base_symbol: str = "NQ", option_type: str = "weekly", year_format: str = "2digit") -> str:
        """
        Generate the EOD (End of Day) contract symbol for today.
        
        Args:
            base_symbol: Base futures symbol (default: "NQ")
            option_type: Type of option - "weekly", "friday", "0dte", "daily", or "monthly"
            year_format: Year format - "2digit" or "4digit"
            
        Returns:
            str: Contract symbol (e.g., "MM1N25" for weekly, "MQ1N25" for Friday)
        """
        now = datetime.now()
        
        # Determine expiry date based on option type
        if option_type == "weekly":
            # Weekly options expire on Tuesday
            # Find next Tuesday
            days_ahead = 1 - now.weekday()  # Tuesday is 1
            if days_ahead <= 0:  # Today is Tuesday or later
                days_ahead += 7
            expiry_date = now + timedelta(days=days_ahead)
            prefix = "MM"
            
        elif option_type in ["friday", "0dte"]:
            # Friday options expire on Friday
            # For 0DTE on Friday, use today; otherwise next Friday
            days_ahead = 4 - now.weekday()  # Friday is 4
            if days_ahead < 0:  # Past Friday this week
                days_ahead += 7
            elif days_ahead == 0 and option_type == "0dte":
                # It's Friday and we want 0DTE, use today
                days_ahead = 0
            expiry_date = now + timedelta(days=days_ahead)
            prefix = "MQ"
            
        elif option_type == "daily":
            # Daily options typically use "MC" prefix
            # Get next business day
            if now.weekday() == 4:  # Friday
                days_ahead = 3  # Monday
            elif now.weekday() == 5:  # Saturday
                days_ahead = 2  # Monday
            else:
                days_ahead = 1  # Next day
            expiry_date = now + timedelta(days=days_ahead)
            prefix = "MC"
            
        elif option_type == "monthly":
            # Monthly options expire on 3rd Thursday
            # Find the 3rd Thursday of the next month if we're past this month's
            
            # Check if we're past the 3rd Thursday of current month
            first_day = now.replace(day=1)
            first_thursday = first_day + timedelta(days=(3 - first_day.weekday()) % 7)
            third_thursday = first_thursday + timedelta(days=14)
            
            if now.date() > third_thursday.date():
                # Move to next month
                if now.month == 12:
                    first_day = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    first_day = now.replace(month=now.month + 1, day=1)
                first_thursday = first_day + timedelta(days=(3 - first_day.weekday()) % 7)
                third_thursday = first_thursday + timedelta(days=14)
                
            expiry_date = third_thursday
            prefix = "MM"
            
        else:
            raise ValueError(f"Unknown option type: {option_type}")
        
        # Get week of month (1-5)
        week_of_month = ((expiry_date.day - 1) // 7) + 1
        
        # For monthly options, use week 6 to differentiate
        if option_type == "monthly":
            week_of_month = 6
        
        # Month codes
        month_codes = {
            1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
            7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
        }
        
        month_code = month_codes[expiry_date.month]
        
        # Year suffix
        if year_format == "4digit":
            year_suffix = str(expiry_date.year)
        else:  # 2digit
            year_suffix = str(expiry_date.year)[-2:]
        
        # Construct symbol
        symbol = f"{prefix}{week_of_month}{month_code}{year_suffix}"
        
        return symbol
    
    def parse_symbol(self, symbol: str) -> dict:
        """
        Parse a Barchart options symbol to extract its components
        
        Args:
            symbol: The symbol to parse (e.g., "MM1N25")
            
        Returns:
            dict: Parsed components including type, week, month, year
        """
        if len(symbol) < 5:
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        prefix = symbol[:2]
        week = symbol[2]
        month_code = symbol[3]
        year = symbol[4:]
        
        # Determine option type from prefix
        option_types = {
            "MM": "weekly" if week != "6" else "monthly",
            "MQ": "friday",
            "MC": "daily"
        }
        
        option_type = option_types.get(prefix, "unknown")
        
        # Month code to number
        month_numbers = {
            'F': 1, 'G': 2, 'H': 3, 'J': 4, 'K': 5, 'M': 6,
            'N': 7, 'Q': 8, 'U': 9, 'V': 10, 'X': 11, 'Z': 12
        }
        
        month = month_numbers.get(month_code, 0)
        
        return {
            "symbol": symbol,
            "prefix": prefix,
            "option_type": option_type,
            "week": int(week) if week.isdigit() else 0,
            "month": month,
            "month_code": month_code,
            "year": year
        }


# Module-level function for backward compatibility
def get_eod_contract_symbol(base_symbol: str = "NQ", option_type: str = "weekly", year_format: str = "2digit") -> str:
    """Generate EOD contract symbol - convenience function"""
    generator = BarchartSymbolGenerator()
    return generator.get_eod_contract_symbol(base_symbol, option_type, year_format)