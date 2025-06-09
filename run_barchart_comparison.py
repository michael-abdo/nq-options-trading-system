#!/usr/bin/env python3
"""
Run Barchart Web Scraper vs API Comparison from project root
"""

import sys
import os

# Add the barchart_web_scraper directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'tasks/options_trading_system/data_ingestion/barchart_web_scraper'))

# Import and run the main function
from solution import main

if __name__ == "__main__":
    print("Running Barchart Web Scraper vs API Comparison from project root...")
    print("=" * 60)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()