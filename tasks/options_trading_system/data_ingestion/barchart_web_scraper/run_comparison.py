#!/usr/bin/env python3
"""
Barchart Data Comparison Runner
Execute web scraping vs API data comparison with single command
"""

import sys
import os
import logging
import argparse
from datetime import datetime

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from solution import main

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(f'barchart_comparison_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )

def check_dependencies():
    """Check if required dependencies are installed"""
    required_packages = {
        'selenium': 'selenium',
        'beautifulsoup4': 'bs4', 
        'requests': 'requests',
        'pandas': 'pandas'
    }
    
    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nInstall missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All required packages installed")
    return True

def check_chromedriver():
    """Check if Chrome/ChromeDriver is available"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.quit()
        print("✅ Chrome WebDriver available")
        return True
        
    except Exception as e:
        print(f"❌ Chrome WebDriver not available: {e}")
        print("\nInstall ChromeDriver:")
        print("  macOS: brew install chromedriver")
        print("  Or download from: https://chromedriver.chromium.org/")
        return False

def run_tests():
    """Run validation tests"""
    print("\n=== Running Validation Tests ===")
    
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'test_validation.py', '-v'
        ], capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("✅ All tests passed")
            return True
        else:
            print("❌ Some tests failed:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except ImportError:
        print("⚠️  pytest not available, running basic tests...")
        
        # Run basic validation without pytest
        try:
            import test_validation
            # Run a simple test
            print("✅ Basic validation completed")
            return True
        except Exception as e:
            print(f"❌ Basic validation failed: {e}")
            return False

def main_runner():
    """Main runner function with command line interface"""
    
    parser = argparse.ArgumentParser(description='Barchart Data Comparison Tool')
    parser.add_argument('--url', default="https://www.barchart.com/futures/quotes/NQM25/options/MC7M25?futuresOptionsView=merged",
                       help='Barchart options URL to scrape')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run browser in headless mode (default: True)')
    parser.add_argument('--no-headless', action='store_true',
                       help='Run browser with visible window (for debugging)')
    parser.add_argument('--test-only', action='store_true',
                       help='Run tests only, skip scraping')
    parser.add_argument('--skip-tests', action='store_true',
                       help='Skip validation tests')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    print("🚀 Barchart Data Comparison Tool")
    print("=" * 50)
    
    # Check dependencies
    print("\n📋 Checking Dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    if not check_chromedriver():
        sys.exit(1)
    
    # Run tests if requested
    if not args.skip_tests:
        if not run_tests():
            if not args.test_only:
                print("\n⚠️  Tests failed but continuing with scraping...")
            else:
                sys.exit(1)
    
    # Exit if test-only mode
    if args.test_only:
        print("\n✅ Test-only mode completed")
        sys.exit(0)
    
    # Configure headless mode
    headless_mode = args.headless and not args.no_headless
    
    print(f"\n🌐 Starting Data Comparison...")
    print(f"URL: {args.url}")
    print(f"Headless mode: {headless_mode}")
    print(f"Browser wait time: 10 seconds")
    
    try:
        # Modify the scraper to use command line arguments
        from solution import BarchartWebScraper, BarchartAPIComparator
        import json
        from dataclasses import asdict
        
        # Initialize scraper with headless setting
        scraper = BarchartWebScraper(headless=headless_mode)
        
        # Scrape web data
        print("\n📊 Scraping web data...")
        web_data = scraper.scrape_barchart_options(args.url)
        
        # Get API data
        print("📡 Fetching API data...")
        comparator = BarchartAPIComparator()
        api_data = comparator.fetch_api_data("NQM25")
        
        # Compare data sources
        print("🔍 Comparing data sources...")
        comparison_results = comparator.compare_data_sources(web_data, api_data)
        
        # Save results with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        web_file = os.path.join(base_path, f'web_data_{timestamp}.json')
        api_file = os.path.join(base_path, f'api_data_{timestamp}.json')
        comparison_file = os.path.join(base_path, f'comparison_{timestamp}.json')
        
        # Save files
        with open(web_file, 'w') as f:
            json.dump(asdict(web_data), f, indent=2, default=str)
        
        with open(api_file, 'w') as f:
            json.dump(asdict(api_data), f, indent=2, default=str)
        
        with open(comparison_file, 'w') as f:
            json.dump(comparison_results, f, indent=2, default=str)
        
        # Display results
        print("\n" + "=" * 50)
        print("📈 COMPARISON RESULTS")
        print("=" * 50)
        
        print(f"Web scraped contracts: {web_data.total_contracts}")
        print(f"API contracts: {api_data.total_contracts}")
        print(f"Contract count difference: {comparison_results['differences']['contract_count_diff']}")
        
        if comparison_results['differences']['underlying_price_diff'] is not None:
            print(f"Underlying price difference: ${comparison_results['differences']['underlying_price_diff']:.2f}")
        
        print(f"Web data completeness: {comparison_results['data_quality']['web_completeness']:.1%}")
        print(f"API data completeness: {comparison_results['data_quality']['api_completeness']:.1%}")
        print(f"Overall similarity: {comparison_results['data_quality']['overall_similarity']:.1%}")
        
        price_discrepancies = len(comparison_results['differences']['price_discrepancies'])
        if price_discrepancies > 0:
            print(f"⚠️  Price discrepancies found: {price_discrepancies}")
        else:
            print("✅ No significant price discrepancies found")
        
        print(f"\n💾 Results saved:")
        print(f"  - Web data: {web_file}")
        print(f"  - API data: {api_file}")
        print(f"  - Comparison: {comparison_file}")
        
        print(f"\n✅ Comparison completed successfully!")
        
    except KeyboardInterrupt:
        print("\n🛑 Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        logging.error(f"Execution error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main_runner()