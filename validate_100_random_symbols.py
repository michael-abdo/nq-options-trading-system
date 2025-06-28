#!/usr/bin/env python3
"""
Generate 100 random dates and validate their symbols
Logs EVERYTHING for comprehensive analysis
"""

import json
import random
import os
from datetime import datetime, timedelta
import sys
from pathlib import Path
import logging
import subprocess
import time

sys.path.append(str(Path(__file__).parent / "tasks/options_trading_system/data_ingestion/barchart_web_scraper"))
from robust_symbol_validator import RobustSymbolValidator

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('validation_100_detailed.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ComprehensiveSymbolValidator:
    """Validate 100 random symbols with full logging"""
    
    def __init__(self):
        self.validator = RobustSymbolValidator()
        self.results = []
        self.output_dir = "validation_100_results"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def generate_puppeteer_script(self, symbol: str, test_date: datetime, expiry_date: datetime, option_type: str) -> str:
        """Generate a Puppeteer validation script"""
        
        script = f'''const puppeteer = require('puppeteer');

(async () => {{
    const result = {{
        symbol: '{symbol}',
        test_date: '{test_date.strftime("%Y-%m-%d")}',
        option_type: '{option_type}',
        expected_expiry: '{expiry_date.strftime("%m/%d/%y")}',
        validation_start: new Date().toISOString()
    }};
    
    console.log('🔍 Validating', result.symbol, 'for', result.test_date);
    
    const browser = await puppeteer.launch({{
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }});
    
    const page = await browser.newPage();
    
    try {{
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36');
        
        const url = 'https://www.barchart.com/futures/quotes/NQU25/options/{symbol}?futuresOptionsView=merged';
        await page.goto(url, {{ waitUntil: 'networkidle2', timeout: 30000 }});
        
        // Wait for content
        await page.waitForTimeout(3000);
        
        // Get page text
        const pageText = await page.evaluate(() => document.body.innerText);
        
        // Look for expiration info
        const expirationMatch = pageText.match(/(\\d+)\\s+Days?\\s+to\\s+expiration\\s+on\\s+([\\d\\/]+)/i);
        
        if (expirationMatch) {{
            result.found_expiration = true;
            result.days_to_expiry = parseInt(expirationMatch[1]);
            result.actual_expiry = expirationMatch[2];
            result.match = expirationMatch[2] === '{expiry_date.strftime("%m/%d/%y")}' || 
                          expirationMatch[2] === '{expiry_date.strftime("%-m/%-d/%y")}';
            
            // Check for options data
            result.has_options_data = pageText.includes('Call') && pageText.includes('Put');
        }} else {{
            result.found_expiration = false;
            result.match = false;
            
            // Check if redirected or error
            result.current_url = page.url();
            result.page_title = await page.title();
        }}
        
        result.validation_end = new Date().toISOString();
        result.success = result.found_expiration && result.match;
        
    }} catch (error) {{
        result.error = error.message;
        result.success = false;
    }} finally {{
        await browser.close();
        console.log(JSON.stringify(result));
    }}
}})();'''
        
        return script
    
    def run_validation_script(self, script_path: str) -> dict:
        """Run a Puppeteer script and capture results"""
        
        try:
            # Run the script and capture output
            process = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Parse the JSON output (last line should be JSON)
            output_lines = process.stdout.strip().split('\n')
            for line in reversed(output_lines):
                if line.strip().startswith('{'):
                    return json.loads(line)
            
            # If no JSON found, return error
            return {
                'success': False,
                'error': 'No JSON output found',
                'stdout': process.stdout,
                'stderr': process.stderr
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Script timeout'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'JSON parse error: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def validate_single_date(self, test_date: datetime, test_num: int) -> dict:
        """Validate all option types for a single date"""
        
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST {test_num}: {test_date.strftime('%Y-%m-%d %A')}")
        logger.info(f"{'='*80}")
        
        date_result = {
            'test_num': test_num,
            'test_date': test_date.strftime('%Y-%m-%d'),
            'weekday': test_date.strftime('%A'),
            'day_of_month': test_date.day,
            'week_of_month': (test_date.day - 1) // 7 + 1,
            'validations': {}
        }
        
        # Test each option type
        option_types = ['weekly', 'friday', 'monthly']
        if test_date.weekday() == 4:  # Friday
            option_types.append('0dte')
        
        for option_type in option_types:
            logger.info(f"\nValidating {option_type.upper()} option...")
            
            # Generate symbol
            try:
                symbol, expiry_date = self.validator.generate_symbol_for_date(test_date, option_type)
                days_to_expiry = (expiry_date - test_date).days
                
                logger.info(f"  Generated: {symbol}")
                logger.info(f"  Expires: {expiry_date.strftime('%Y-%m-%d %A')}")
                logger.info(f"  Days to expiry: {days_to_expiry}")
                
                # Log symbol breakdown
                if len(symbol) >= 4:
                    prefix = symbol[:2]
                    week = symbol[2]
                    month = symbol[3]
                    year = symbol[4:]
                    logger.debug(f"  Breakdown: {prefix} (prefix), Week {week}, Month {month}, Year 20{year}")
                
                # Create validation script
                script_name = f"validate_{test_num}_{option_type}_{symbol}.js"
                script_path = os.path.join(self.output_dir, script_name)
                
                script_content = self.generate_puppeteer_script(symbol, test_date, expiry_date, option_type)
                with open(script_path, 'w') as f:
                    f.write(script_content)
                
                logger.debug(f"  Created script: {script_name}")
                
                # Run validation
                logger.info(f"  Running Puppeteer validation...")
                validation_result = self.run_validation_script(script_path)
                
                # Log results
                if validation_result.get('success'):
                    logger.info(f"  ✅ VALIDATION SUCCESSFUL!")
                    logger.info(f"     Actual expiry: {validation_result.get('actual_expiry')}")
                    logger.info(f"     Days to expiry: {validation_result.get('days_to_expiry')}")
                else:
                    logger.warning(f"  ❌ VALIDATION FAILED!")
                    if validation_result.get('found_expiration'):
                        logger.warning(f"     Expected: {expiry_date.strftime('%m/%d/%y')}")
                        logger.warning(f"     Actual: {validation_result.get('actual_expiry')}")
                    else:
                        logger.warning(f"     Symbol may not exist or page didn't load")
                        logger.debug(f"     Error: {validation_result.get('error', 'Unknown')}")
                
                # Store results
                date_result['validations'][option_type] = {
                    'symbol': symbol,
                    'expected_expiry': expiry_date.strftime('%Y-%m-%d'),
                    'days_to_expiry': days_to_expiry,
                    'validation': validation_result
                }
                
                # Clean up script file to save space
                if os.path.exists(script_path):
                    os.remove(script_path)
                    
            except Exception as e:
                logger.error(f"  💥 ERROR generating/validating {option_type}: {e}")
                date_result['validations'][option_type] = {
                    'error': str(e)
                }
            
            # Small delay between validations
            time.sleep(0.5)
        
        # Special validation for Fridays
        if test_date.weekday() == 4 and 'friday' in date_result['validations'] and '0dte' in date_result['validations']:
            friday_symbol = date_result['validations']['friday'].get('symbol')
            dte_symbol = date_result['validations']['0dte'].get('symbol')
            
            if friday_symbol == dte_symbol:
                logger.info(f"\n✅ Friday = 0DTE consistency check PASSED")
            else:
                logger.error(f"\n❌ Friday = 0DTE consistency check FAILED")
                logger.error(f"   Friday: {friday_symbol}")
                logger.error(f"   0DTE: {dte_symbol}")
        
        return date_result
    
    def run_comprehensive_validation(self, num_tests: int = 100):
        """Run validation on random dates"""
        
        logger.info("🚀 STARTING 100 RANDOM SYMBOL VALIDATIONS")
        logger.info("="*80)
        
        # Generate random dates across next 6 months
        start_date = datetime.now()
        end_date = start_date + timedelta(days=180)
        date_range = (end_date - start_date).days
        
        # Track statistics
        stats = {
            'total_tests': 0,
            'total_validations': 0,
            'successful_validations': 0,
            'failed_validations': 0,
            'errors': 0,
            'by_type': {
                'weekly': {'success': 0, 'fail': 0},
                'friday': {'success': 0, 'fail': 0},
                '0dte': {'success': 0, 'fail': 0},
                'monthly': {'success': 0, 'fail': 0}
            }
        }
        
        # Run tests
        for i in range(1, num_tests + 1):
            # Generate random date
            random_days = random.randint(0, date_range)
            test_date = start_date + timedelta(days=random_days)
            
            # Run validation
            result = self.validate_single_date(test_date, i)
            self.results.append(result)
            
            # Update statistics
            stats['total_tests'] += 1
            
            for option_type, validation in result['validations'].items():
                if 'validation' in validation:
                    stats['total_validations'] += 1
                    
                    if validation['validation'].get('success'):
                        stats['successful_validations'] += 1
                        stats['by_type'][option_type]['success'] += 1
                    else:
                        stats['failed_validations'] += 1
                        stats['by_type'][option_type]['fail'] += 1
                elif 'error' in validation:
                    stats['errors'] += 1
            
            # Progress update every 10 tests
            if i % 10 == 0:
                success_rate = (stats['successful_validations'] / stats['total_validations'] * 100) if stats['total_validations'] > 0 else 0
                logger.info(f"\nPROGRESS: {i}/{num_tests} tests completed")
                logger.info(f"Current success rate: {success_rate:.1f}%")
        
        # Save detailed results
        self.save_results(stats)
        
        # Print final summary
        self.print_summary(stats)
        
        return stats
    
    def save_results(self, stats: dict):
        """Save all results to files"""
        
        # Save detailed results
        detailed_results = {
            'run_timestamp': datetime.now().isoformat(),
            'statistics': stats,
            'test_results': self.results
        }
        
        with open(os.path.join(self.output_dir, 'validation_results.json'), 'w') as f:
            json.dump(detailed_results, f, indent=2)
        
        # Save summary report
        self.generate_report(stats)
    
    def generate_report(self, stats: dict):
        """Generate a human-readable report"""
        
        report_path = os.path.join(self.output_dir, 'validation_report.txt')
        
        with open(report_path, 'w') as f:
            f.write("BARCHART SYMBOL VALIDATION REPORT\n")
            f.write("="*80 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Tests: {stats['total_tests']}\n")
            f.write(f"Total Validations: {stats['total_validations']}\n\n")
            
            f.write("OVERALL RESULTS:\n")
            f.write("-"*40 + "\n")
            success_rate = (stats['successful_validations'] / stats['total_validations'] * 100) if stats['total_validations'] > 0 else 0
            f.write(f"Success Rate: {success_rate:.2f}%\n")
            f.write(f"Successful: {stats['successful_validations']}\n")
            f.write(f"Failed: {stats['failed_validations']}\n")
            f.write(f"Errors: {stats['errors']}\n\n")
            
            f.write("BY OPTION TYPE:\n")
            f.write("-"*40 + "\n")
            for option_type, type_stats in stats['by_type'].items():
                total = type_stats['success'] + type_stats['fail']
                if total > 0:
                    type_success_rate = (type_stats['success'] / total) * 100
                    f.write(f"{option_type.upper():8} - Success: {type_stats['success']:3d}, Fail: {type_stats['fail']:3d}, Rate: {type_success_rate:.1f}%\n")
            
            f.write("\nFAILED VALIDATIONS:\n")
            f.write("-"*40 + "\n")
            
            # List failed validations
            fail_count = 0
            for result in self.results:
                for option_type, validation in result['validations'].items():
                    if 'validation' in validation and not validation['validation'].get('success'):
                        fail_count += 1
                        f.write(f"\n{fail_count}. Date: {result['test_date']} ({result['weekday']})\n")
                        f.write(f"   Type: {option_type}\n")
                        f.write(f"   Symbol: {validation['symbol']}\n")
                        f.write(f"   Expected: {validation['expected_expiry']}\n")
                        
                        if validation['validation'].get('found_expiration'):
                            f.write(f"   Actual: {validation['validation'].get('actual_expiry')}\n")
                        else:
                            f.write(f"   Error: Symbol not found or page didn't load\n")
                        
                        if fail_count >= 20:  # Limit to first 20 failures
                            f.write(f"\n... and {stats['failed_validations'] - 20} more failures\n")
                            break
                
                if fail_count >= 20:
                    break
    
    def print_summary(self, stats: dict):
        """Print summary to console"""
        
        logger.info("\n" + "="*80)
        logger.info("🏁 VALIDATION COMPLETE - FINAL SUMMARY")
        logger.info("="*80)
        
        success_rate = (stats['successful_validations'] / stats['total_validations'] * 100) if stats['total_validations'] > 0 else 0
        
        logger.info(f"\n📊 OVERALL RESULTS:")
        logger.info(f"   Total Tests: {stats['total_tests']}")
        logger.info(f"   Total Validations: {stats['total_validations']}")
        logger.info(f"   Success Rate: {success_rate:.2f}%")
        logger.info(f"   ✅ Successful: {stats['successful_validations']}")
        logger.info(f"   ❌ Failed: {stats['failed_validations']}")
        logger.info(f"   💥 Errors: {stats['errors']}")
        
        logger.info(f"\n📈 BY OPTION TYPE:")
        for option_type, type_stats in stats['by_type'].items():
            total = type_stats['success'] + type_stats['fail']
            if total > 0:
                type_success_rate = (type_stats['success'] / total) * 100
                logger.info(f"   {option_type.upper():8} - Success: {type_stats['success']:3d}, Fail: {type_stats['fail']:3d}, Rate: {type_success_rate:.1f}%")
        
        logger.info(f"\n📁 Results saved to: {self.output_dir}/")
        logger.info(f"   - validation_results.json (detailed results)")
        logger.info(f"   - validation_report.txt (summary report)")
        logger.info(f"   - validation_100_detailed.log (full log)")

def main():
    """Run the comprehensive validation"""
    
    # First check if we have node and puppeteer
    try:
        subprocess.run(['node', '--version'], capture_output=True, check=True)
    except:
        logger.error("Node.js not found. Please install Node.js first.")
        return 1
    
    # Check for puppeteer
    if not os.path.exists('node_modules/puppeteer'):
        logger.info("Installing Puppeteer...")
        subprocess.run(['npm', 'install', 'puppeteer'], check=True)
    
    # Run validation
    validator = ComprehensiveSymbolValidator()
    stats = validator.run_comprehensive_validation(100)
    
    return 0 if stats['failed_validations'] == 0 else 1

if __name__ == "__main__":
    exit(main())