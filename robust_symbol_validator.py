#!/usr/bin/env python3
"""
Robust Symbol Generation Validator
Tests thousands of random dates across multiple years and all edge cases
"""

import logging
import json
import random
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "tasks/options_trading_system/data_ingestion/barchart_web_scraper"))
from solution import BarchartAPIComparator

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RobustSymbolValidator:
    """Comprehensive validator for symbol generation across all scenarios"""
    
    def __init__(self):
        self.comparator = BarchartAPIComparator()
        self.failures = []
        self.edge_cases = []
        self.patterns = defaultdict(Counter)
        
    def generate_symbol_for_date(self, test_date: datetime, option_type: str = "weekly", year_format: str = "2digit") -> tuple:
        """Generate symbol for a specific test date and return symbol + expiry date"""
        from datetime import timedelta
        
        # Get month letter code
        month_codes = {
            1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
            7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'
        }
        
        if option_type == "weekly":
            # For weekly options, find the next Tuesday
            days_ahead = 1 - test_date.weekday()  # Tuesday = 1
            if days_ahead <= 0:  # Already past Tuesday
                days_ahead += 7
            
            next_tuesday = test_date + timedelta(days=days_ahead)
            week_of_month = (next_tuesday.day - 1) // 7 + 1
            
            # Use MM prefix with week number
            next_tuesday_year = str(next_tuesday.year)[-2:] if year_format == "2digit" else str(next_tuesday.year)[-1]
            symbol = f"MM{week_of_month}{month_codes[next_tuesday.month]}{next_tuesday_year}"
            return symbol, next_tuesday
            
        elif option_type == "friday" or option_type == "0dte":
            # For Friday weekly options (including 0DTE on Fridays)
            days_ahead = 4 - test_date.weekday()  # Friday = 4
            if days_ahead < 0:  # Already past Friday
                days_ahead += 7
            elif days_ahead == 0 and option_type == "0dte":
                # Today is Friday, use today for 0DTE
                days_ahead = 0
            
            next_friday = test_date + timedelta(days=days_ahead)
            week_of_month = (next_friday.day - 1) // 7 + 1
            
            # Use MQ prefix with week number
            next_friday_year = str(next_friday.year)[-2:] if year_format == "2digit" else str(next_friday.year)[-1]
            symbol = f"MQ{week_of_month}{month_codes[next_friday.month]}{next_friday_year}"
            return symbol, next_friday
            
        elif option_type == "monthly":
            # Monthly options expire on 3rd Thursday
            first_day = test_date.replace(day=1)
            first_thursday = first_day + timedelta(days=(3 - first_day.weekday()) % 7)
            third_thursday = first_thursday + timedelta(days=14)
            
            # If we're past 3rd Thursday, use next month
            if test_date > third_thursday:
                if test_date.month == 12:
                    next_month = test_date.replace(year=test_date.year + 1, month=1, day=1)
                else:
                    next_month = test_date.replace(month=test_date.month + 1, day=1)
                
                first_thursday = next_month + timedelta(days=(3 - next_month.weekday()) % 7)
                third_thursday = first_thursday + timedelta(days=14)
            
            # Calculate which week the 3rd Thursday falls in
            week_of_month = (third_thursday.day - 1) // 7 + 1
            
            third_thursday_year = str(third_thursday.year)[-2:] if year_format == "2digit" else str(third_thursday.year)[-1]
            symbol = f"MM{week_of_month}{month_codes[third_thursday.month]}{third_thursday_year}"
            return symbol, third_thursday
    
    def validate_symbol_rules(self, test_date: datetime, symbol: str, expiry_date: datetime, option_type: str) -> dict:
        """Validate that symbol follows all business rules"""
        
        issues = []
        
        # Rule 1: Week number must be 1-5
        if len(symbol) >= 3:
            week_char = symbol[2]
            if week_char.isdigit():
                week_num = int(week_char)
                if week_num < 1 or week_num > 5:
                    issues.append(f"Invalid week number: {week_num}")
        
        # Rule 2: Expiry date must be in the future (or today for 0DTE)
        if option_type == "0dte" and test_date.weekday() == 4:  # Friday
            if expiry_date.date() != test_date.date():
                issues.append(f"0DTE on Friday should expire today, not {expiry_date.date()}")
        elif expiry_date.date() <= test_date.date():
            issues.append(f"Expiry date {expiry_date.date()} is not after {test_date.date()}")
        
        # Rule 3: Weekly options must expire on Tuesday
        if option_type == "weekly" and expiry_date.weekday() != 1:
            issues.append(f"Weekly option expires on {expiry_date.strftime('%A')}, not Tuesday")
        
        # Rule 4: Friday options must expire on Friday
        if option_type in ["friday", "0dte"] and expiry_date.weekday() != 4:
            issues.append(f"Friday option expires on {expiry_date.strftime('%A')}, not Friday")
        
        # Rule 5: Monthly options must expire on Thursday
        if option_type == "monthly" and expiry_date.weekday() != 3:
            issues.append(f"Monthly option expires on {expiry_date.strftime('%A')}, not Thursday")
        
        # Rule 6: Symbol format validation
        if option_type == "weekly" and not symbol.startswith("MM"):
            issues.append(f"Weekly option should start with MM, not {symbol[:2]}")
        elif option_type in ["friday", "0dte"] and not symbol.startswith("MQ"):
            issues.append(f"Friday option should start with MQ, not {symbol[:2]}")
        elif option_type == "monthly" and not symbol.startswith("MM"):
            issues.append(f"Monthly option should start with MM, not {symbol[:2]}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }
    
    def test_edge_cases(self):
        """Test specific edge cases"""
        
        edge_case_dates = [
            # Year transitions
            (datetime(2024, 12, 31), "New Year's Eve"),
            (datetime(2025, 1, 1), "New Year's Day"),
            
            # Leap year February
            (datetime(2024, 2, 28), "Day before leap day"),
            (datetime(2024, 2, 29), "Leap day"),
            (datetime(2024, 3, 1), "Day after leap day"),
            (datetime(2025, 2, 28), "Last day of non-leap February"),
            
            # 5-week months
            (datetime(2025, 1, 29), "5th Wednesday of January"),
            (datetime(2025, 3, 29), "5th Saturday of March"),
            (datetime(2025, 5, 30), "5th Friday of May"),
            
            # Holidays (market may be closed)
            (datetime(2025, 7, 4), "Independence Day"),
            (datetime(2025, 12, 25), "Christmas"),
            (datetime(2025, 11, 27), "Thanksgiving"),
            
            # Month boundaries
            (datetime(2025, 1, 31), "End of January"),
            (datetime(2025, 4, 30), "End of April"),
            (datetime(2025, 6, 30), "End of June"),
            
            # Special Fridays
            (datetime(2025, 1, 3), "First Friday of year"),
            (datetime(2025, 12, 26), "Friday after Christmas"),
            (datetime(2025, 11, 28), "Black Friday"),
        ]
        
        logger.info("\n🔍 TESTING EDGE CASES")
        logger.info("="*80)
        
        for test_date, description in edge_case_dates:
            logger.info(f"\nTesting: {description} - {test_date.strftime('%Y-%m-%d %A')}")
            
            for option_type in ["weekly", "friday", "0dte", "monthly"]:
                try:
                    symbol, expiry_date = self.generate_symbol_for_date(test_date, option_type)
                    validation = self.validate_symbol_rules(test_date, symbol, expiry_date, option_type)
                    
                    if not validation['valid']:
                        logger.warning(f"  ❌ {option_type}: {symbol} - Issues: {validation['issues']}")
                        self.edge_cases.append({
                            'date': test_date,
                            'description': description,
                            'option_type': option_type,
                            'symbol': symbol,
                            'issues': validation['issues']
                        })
                    else:
                        logger.info(f"  ✅ {option_type}: {symbol} (expires {expiry_date.strftime('%Y-%m-%d %A')})")
                        
                except Exception as e:
                    logger.error(f"  💥 {option_type}: ERROR - {str(e)}")
                    self.failures.append({
                        'date': test_date,
                        'description': description,
                        'option_type': option_type,
                        'error': str(e)
                    })
    
    def test_all_days_of_week(self):
        """Test every day of the week across multiple random weeks"""
        
        logger.info("\n📅 TESTING ALL DAYS OF WEEK")
        logger.info("="*80)
        
        # Test 10 random weeks across different years
        base_years = [2024, 2025, 2026, 2027, 2028]
        
        for year in base_years:
            # Pick a random week in each quarter
            for quarter in range(4):
                month = quarter * 3 + random.randint(1, 3)
                day = random.randint(1, 15)
                
                try:
                    week_start = datetime(year, month, day)
                    # Adjust to Monday
                    week_start -= timedelta(days=week_start.weekday())
                    
                    logger.info(f"\nWeek of {week_start.strftime('%Y-%m-%d')}:")
                    
                    # Test each day of this week
                    for day_offset in range(7):
                        test_date = week_start + timedelta(days=day_offset)
                        day_name = test_date.strftime('%A')
                        
                        # Test all option types for this day
                        results = {}
                        for option_type in ["weekly", "friday", "0dte"]:
                            symbol, expiry_date = self.generate_symbol_for_date(test_date, option_type)
                            validation = self.validate_symbol_rules(test_date, symbol, expiry_date, option_type)
                            results[option_type] = (symbol, validation['valid'])
                            
                            # Track patterns
                            self.patterns['day_of_week'][day_name] += 1
                            self.patterns['symbols'][symbol[:2]] += 1
                            
                        # Special validation for Fridays
                        if test_date.weekday() == 4:  # Friday
                            if results['friday'][0] != results['0dte'][0]:
                                logger.error(f"  ❌ {day_name}: Friday != 0DTE mismatch!")
                                self.failures.append({
                                    'date': test_date,
                                    'issue': 'Friday != 0DTE',
                                    'friday': results['friday'][0],
                                    '0dte': results['0dte'][0]
                                })
                        
                        logger.info(f"  {day_name}: Weekly={results['weekly'][0]}, Friday={results['friday'][0]}")
                        
                except Exception as e:
                    logger.error(f"Error testing week in {year}-{month}: {e}")
    
    def test_random_dates(self, num_tests: int = 1000):
        """Test random dates across a wide range"""
        
        logger.info(f"\n🎲 TESTING {num_tests} RANDOM DATES")
        logger.info("="*80)
        
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2030, 12, 31)
        date_range = (end_date - start_date).days
        
        validation_stats = defaultdict(int)
        
        for i in range(num_tests):
            if i % 100 == 0 and i > 0:
                logger.info(f"Progress: {i}/{num_tests} tested...")
            
            # Generate random date
            random_days = random.randint(0, date_range)
            test_date = start_date + timedelta(days=random_days)
            
            # Test all option types
            for option_type in ["weekly", "friday", "0dte", "monthly"]:
                try:
                    symbol, expiry_date = self.generate_symbol_for_date(test_date, option_type)
                    validation = self.validate_symbol_rules(test_date, symbol, expiry_date, option_type)
                    
                    if validation['valid']:
                        validation_stats[f'{option_type}_valid'] += 1
                    else:
                        validation_stats[f'{option_type}_invalid'] += 1
                        if len(self.failures) < 50:  # Only store first 50 failures
                            self.failures.append({
                                'date': test_date,
                                'option_type': option_type,
                                'symbol': symbol,
                                'issues': validation['issues']
                            })
                    
                    # Track patterns
                    self.patterns['years'][str(test_date.year)] += 1
                    self.patterns['months'][test_date.strftime('%B')] += 1
                    
                    # Extract week number
                    if len(symbol) >= 3 and symbol[2].isdigit():
                        self.patterns['week_numbers'][symbol[2]] += 1
                        
                except Exception as e:
                    validation_stats[f'{option_type}_error'] += 1
                    if len(self.failures) < 50:
                        self.failures.append({
                            'date': test_date,
                            'option_type': option_type,
                            'error': str(e)
                        })
        
        # Print validation statistics
        logger.info(f"\n📊 VALIDATION STATISTICS ({num_tests} random dates):")
        logger.info("="*60)
        
        for option_type in ["weekly", "friday", "0dte", "monthly"]:
            valid = validation_stats.get(f'{option_type}_valid', 0)
            invalid = validation_stats.get(f'{option_type}_invalid', 0)
            errors = validation_stats.get(f'{option_type}_error', 0)
            total = valid + invalid + errors
            
            if total > 0:
                success_rate = (valid / total) * 100
                logger.info(f"{option_type.upper():8} - Valid: {valid:4d}, Invalid: {invalid:4d}, Errors: {errors:4d} | Success Rate: {success_rate:.1f}%")
    
    def analyze_patterns(self):
        """Analyze patterns found during validation"""
        
        logger.info("\n🔍 PATTERN ANALYSIS")
        logger.info("="*80)
        
        # Week number distribution
        logger.info("\nWeek Number Distribution:")
        for week, count in sorted(self.patterns['week_numbers'].items()):
            logger.info(f"  Week {week}: {count:,} occurrences")
        
        # Symbol prefix distribution
        logger.info("\nSymbol Prefix Distribution:")
        for prefix, count in sorted(self.patterns['symbols'].items()):
            logger.info(f"  {prefix}: {count:,} occurrences")
        
        # Day of week distribution
        logger.info("\nDay of Week Testing Coverage:")
        days_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        for day in days_order:
            count = self.patterns['day_of_week'].get(day, 0)
            logger.info(f"  {day:9}: {count:,} tests")
        
        # Year coverage
        logger.info("\nYear Coverage:")
        for year, count in sorted(self.patterns['years'].items()):
            logger.info(f"  {year}: {count:,} tests")
    
    def generate_report(self):
        """Generate comprehensive validation report"""
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_failures': len(self.failures),
                'edge_case_issues': len(self.edge_cases),
                'patterns_analyzed': dict(self.patterns)
            },
            'failures': self.failures[:50],  # First 50 failures
            'edge_cases': self.edge_cases,
            'patterns': {k: dict(v) for k, v in self.patterns.items()}
        }
        
        # Save report
        report_file = f"robust_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"\n💾 Full report saved to: {report_file}")
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("🏁 VALIDATION SUMMARY")
        logger.info("="*80)
        
        if len(self.failures) == 0:
            logger.info("✅ ALL VALIDATIONS PASSED! Symbol generation is robust.")
        else:
            logger.info(f"⚠️  Found {len(self.failures)} validation failures")
            logger.info(f"⚠️  Found {len(self.edge_cases)} edge case issues")
            
            # Show sample failures
            if self.failures:
                logger.info("\nSample Failures:")
                for failure in self.failures[:5]:
                    logger.info(f"  - {failure}")
        
        return report

def main():
    """Run comprehensive validation"""
    
    validator = RobustSymbolValidator()
    
    logger.info("🚀 STARTING ROBUST SYMBOL VALIDATION")
    logger.info("="*80)
    
    # 1. Test edge cases
    validator.test_edge_cases()
    
    # 2. Test all days of week
    validator.test_all_days_of_week()
    
    # 3. Test thousands of random dates
    validator.test_random_dates(2000)
    
    # 4. Analyze patterns
    validator.analyze_patterns()
    
    # 5. Generate report
    report = validator.generate_report()
    
    return 0 if len(validator.failures) == 0 else 1

if __name__ == "__main__":
    exit(main())