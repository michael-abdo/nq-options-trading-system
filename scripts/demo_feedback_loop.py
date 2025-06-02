#!/usr/bin/env python3
"""
Demo script for the Feedback Loop Scraper System
Demonstrates all features step by step
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.chrome_connection_manager import get_chrome_page, close_chrome_page
from utils.feedback_loop_scraper import FeedbackLoopScraper
from utils.logging_config import setup_logging
from nq_options_ev_algo import get_current_contract_url

async def demo_feedback_loop():
    """Demonstrate the feedback loop system step by step"""
    page = None
    
    try:
        # Setup logging
        logger = setup_logging()
        logger.info("=" * 80)
        logger.info("FEEDBACK LOOP SCRAPER SYSTEM DEMO")
        logger.info("=" * 80)
        
        # Get URL
        url = get_current_contract_url()
        logger.info(f"Demo URL: {url}")
        
        # Create feedback loop scraper
        scraper = FeedbackLoopScraper(debug_dir="data/debug")
        
        # Connect to Chrome
        logger.info("\n1. Connecting to Chrome...")
        page = await get_chrome_page(9222)
        
        # Navigate to page
        logger.info("\n2. Navigating to Barchart...")
        await page.goto(url, waitUntil='networkidle2', timeout=30000)
        await asyncio.sleep(3)
        
        # Check for CAPTCHA
        recaptcha_present = await page.evaluate('''() => {
            return document.querySelector('iframe[src*="recaptcha"]') !== null;
        }''')
        
        if recaptcha_present:
            logger.warning("⚠️  reCAPTCHA detected! Please solve manually in Chrome")
            logger.info("Waiting 60 seconds for manual intervention...")
            await asyncio.sleep(60)
        
        logger.info("\n3. Demonstrating individual feedback loop steps...")
        
        # Step 1: Save HTML snapshot
        logger.info("\n   Step 1: Saving HTML snapshot...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_path = await scraper.save_page_html(page, timestamp)
        logger.info(f"   ✓ HTML saved to: {html_path}")
        
        # Step 2: Analyze HTML structure
        logger.info("\n   Step 2: Analyzing HTML structure...")
        analysis = scraper.analyze_html_structure(html_path)
        logger.info(f"   ✓ Found {len(analysis['findings']['price']['elements_with_price_pattern'])} price-like elements")
        logger.info(f"   ✓ Found {len(analysis['findings']['table']['tables'])} tables")
        logger.info(f"   ✓ Generated {len(analysis['potential_selectors']['current_price'])} new price selectors")
        logger.info(f"   ✓ Generated {len(analysis['potential_selectors']['options_table'])} new table selectors")
        
        # Step 3: Test current strategies
        logger.info("\n   Step 3: Testing current selector strategies...")
        test_results = await scraper.test_selectors(page, scraper.selector_strategies)
        
        if test_results["current_price"]:
            logger.info(f"   ✓ Current price found: ${test_results['current_price']:,.2f}")
        else:
            logger.warning("   ✗ Current price not found")
        
        if test_results["options_data"]:
            logger.info(f"   ✓ Options data found: {len(test_results['options_data'])} strikes")
        else:
            logger.warning("   ✗ Options data not found")
        
        # Step 4: Update and test improved strategies
        logger.info("\n   Step 4: Updating strategies with analysis results...")
        improved_results = await scraper.update_scraping_logic(page, analysis)
        
        logger.info("\n4. Full Feedback Loop Demo...")
        
        # Reset attempt counter for clean demo
        scraper.current_attempt = 0
        scraper.attempts_log = []
        
        # Run full feedback loop
        final_results = await scraper.iterate_until_successful(page, max_attempts=5)
        
        # Display results
        logger.info("\n" + "=" * 60)
        logger.info("DEMO RESULTS")
        logger.info("=" * 60)
        
        if final_results["success"]:
            logger.info("🎉 SUCCESS! Feedback loop completed successfully")
            logger.info(f"💰 Current Price: ${final_results['current_price']:,.2f}")
            logger.info(f"📊 Options Found: {len(final_results['options_data'])} strikes")
            logger.info(f"🔄 Attempts Required: {scraper.current_attempt}")
            
            # Show successful selectors
            logger.info("\n🎯 Successful Selectors:")
            for data_type, selector in final_results.get("successful_selectors", {}).items():
                logger.info(f"   {data_type}: {selector['method']} - {selector['selector']}")
            
            # Show sample data
            if final_results['options_data']:
                logger.info("\n📈 Sample Options Data (first 3 strikes):")
                for i, opt in enumerate(final_results['options_data'][:3]):
                    logger.info(f"   Strike {opt['strike']:,.0f}: "
                              f"Call ${opt['call_premium']:.2f}, "
                              f"Put ${opt['put_premium']:.2f}")
        else:
            logger.error("❌ FAILED: Could not extract data after all attempts")
            logger.error(f"🔄 Attempts Made: {scraper.current_attempt}")
        
        # Generate and display final report
        logger.info("\n5. Generating final report...")
        report = scraper.generate_final_report()
        
        # Show debug files created
        debug_dir = Path("data/debug")
        if debug_dir.exists():
            debug_files = list(debug_dir.glob("*"))
            logger.info(f"\n📁 Debug files created ({len(debug_files)} files):")
            for file in sorted(debug_files)[-10:]:  # Show last 10 files
                logger.info(f"   {file.name}")
        
        logger.info("\n" + "=" * 60)
        logger.info("DEMO COMPLETED")
        logger.info("=" * 60)
        logger.info("Check data/debug/ directory for:")
        logger.info("• HTML snapshots of each attempt")
        logger.info("• Analysis reports with detailed findings")
        logger.info("• Attempts log with all test results")
        logger.info("• Final report summary")
        logger.info("• Successful selectors (if found)")
        
        return final_results
        
    except Exception as e:
        logging.error(f"Demo error: {e}")
        logging.exception("Full traceback:")
        return {"success": False, "error": str(e)}
    
    finally:
        if page:
            await close_chrome_page(page)


def main():
    """Main entry point for demo"""
    print("🚀 Starting Feedback Loop Scraper Demo")
    print("=" * 50)
    print("This demo will:")
    print("1. Connect to Chrome and navigate to Barchart")
    print("2. Show each step of the feedback loop process")
    print("3. Demonstrate automatic selector improvement")
    print("4. Generate detailed debug reports")
    print("5. Save all artifacts for analysis")
    print()
    print("Make sure Chrome is running with:")
    print("/Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222")
    print()
    
    input("Press Enter to start the demo...")
    
    # Run the demo
    results = asyncio.run(demo_feedback_loop())
    
    # Exit with appropriate code
    if results.get("success"):
        print("\n✅ Demo completed successfully!")
        print("Check the logs above and data/debug/ directory for detailed results.")
    else:
        print("\n❌ Demo encountered issues.")
        print("Check the logs above for details.")
    
    sys.exit(0 if results.get("success") else 1)


if __name__ == "__main__":
    main()