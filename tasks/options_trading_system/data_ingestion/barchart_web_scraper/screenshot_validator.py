#!/usr/bin/env python3
"""
Barchart Screenshot Validator
Takes screenshots of Barchart options pages for visual validation
Includes OCR text extraction and comparison with API data
"""

import os
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

# Import OCR components
try:
    from .ocr_extractor import OCRExtractor
    from .screenshot_data_normalizer import ScreenshotDataNormalizer
    from .screenshot_comparator import ScreenshotComparator
except ImportError:
    # Fallback for direct execution
    from ocr_extractor import OCRExtractor
    from screenshot_data_normalizer import ScreenshotDataNormalizer
    from screenshot_comparator import ScreenshotComparator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BarchartScreenshotValidator:
    """Validate Barchart data by taking screenshots of actual pages"""
    
    def __init__(self, headless: bool = False, output_dir: str = "outputs", enable_ocr: bool = True):
        self.headless = headless
        self.output_dir = Path(output_dir)
        self.screenshots_dir = self.output_dir / "screenshots" / "validation"
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        self.driver = None
        self.wait_time = 10
        self.enable_ocr = enable_ocr
        
        # Initialize OCR components
        if self.enable_ocr:
            self.ocr_extractor = OCRExtractor()
            self.data_normalizer = ScreenshotDataNormalizer()
            self.comparator = ScreenshotComparator(tolerance=0.02)  # 2% tolerance for OCR
        
    def setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with appropriate options"""
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless")
            
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        # User agent to avoid detection
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            return driver
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            raise
    
    def take_options_screenshot(self, symbol: str, underlying: str = "NQU25", full_page: bool = True) -> Dict[str, Any]:
        """
        Take screenshot of Barchart options page
        
        Args:
            symbol: Options symbol (e.g., "MQ6M25")
            underlying: Underlying futures symbol (e.g., "NQU25")
            full_page: If True, captures full scrollable page
            
        Returns:
            Dict with screenshot path and validation info
        """
        try:
            if not self.driver:
                self.driver = self.setup_driver()
            
            # Construct URL
            url = f"https://www.barchart.com/futures/quotes/{underlying}/options/{symbol}?futuresOptionsView=merged&moneyness=allRows"
            
            logger.info(f"📸 Taking screenshot of {symbol} options page...")
            logger.info(f"   URL: {url}")
            
            # Visit page
            self.driver.get(url)
            
            # Wait for options table to load
            try:
                WebDriverWait(self.driver, self.wait_time).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table.bc-table-scrollable-inner"))
                )
                logger.info("✅ Options table loaded")
            except TimeoutException:
                logger.warning("⚠️  Options table not found, page may still be loading")
            
            # Wait a bit more for data to populate
            time.sleep(2)
            
            # Create timestamped filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            date_dir = self.screenshots_dir / datetime.now().strftime('%Y%m%d')
            date_dir.mkdir(exist_ok=True)
            
            if full_page:
                # Capture full page with scrolling
                filename = f"{symbol}_validation_full_{timestamp}.png"
                filepath = date_dir / filename
                
                logger.info("📜 Capturing full page with scrolling...")
                self._capture_full_page_screenshot(str(filepath))
                logger.info(f"📸 Full page screenshot saved: {filepath}")
            else:
                # Regular screenshot
                filename = f"{symbol}_validation_{timestamp}.png"
                filepath = date_dir / filename
                
                # Take screenshot
                self.driver.save_screenshot(str(filepath))
                logger.info(f"📸 Screenshot saved: {filepath}")
            
            # Try to extract some data from the page
            validation_data = self._extract_page_data()
            
            result = {
                "success": True,
                "symbol": symbol,
                "underlying": underlying,
                "screenshot_path": str(filepath),
                "timestamp": datetime.now().isoformat(),
                "url": url,
                "page_data": validation_data
            }
            
            # Perform OCR if enabled
            if self.enable_ocr:
                logger.info("🔍 Performing OCR text extraction...")
                ocr_result = self._perform_ocr_validation(str(filepath), symbol)
                result["ocr_validation"] = ocr_result
                
                if ocr_result.get("success"):
                    logger.info(f"✅ OCR extracted {ocr_result.get('contracts_found', 0)} contracts")
                else:
                    logger.warning(f"⚠️  OCR failed: {ocr_result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Screenshot failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "symbol": symbol,
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_page_data(self) -> Dict[str, Any]:
        """Extract visible data from the page for validation"""
        try:
            data = {
                "page_title": self.driver.title,
                "has_options_table": False,
                "contract_count": 0,
                "underlying_price": None
            }
            
            # Check for options table
            try:
                table = self.driver.find_element(By.CSS_SELECTOR, "table.bc-table-scrollable-inner")
                data["has_options_table"] = True
                
                # Count rows
                rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
                data["contract_count"] = len(rows)
                
            except:
                pass
            
            # Try to get underlying price
            try:
                price_elem = self.driver.find_element(By.CSS_SELECTOR, "[data-ng-bind*='lastPrice']")
                data["underlying_price"] = price_elem.text
            except:
                pass
            
            return data
            
        except Exception as e:
            logger.warning(f"Could not extract page data: {e}")
            return {}
    
    def _capture_full_page_screenshot(self, filepath: str):
        """Capture full page screenshot by scrolling and stitching"""
        try:
            # Get page dimensions
            total_height = self.driver.execute_script("return document.body.scrollHeight")
            viewport_height = self.driver.execute_script("return window.innerHeight")
            total_width = self.driver.execute_script("return document.body.scrollWidth")
            
            logger.info(f"📏 Page dimensions: {total_width}x{total_height}px")
            logger.info(f"📏 Viewport height: {viewport_height}px")
            
            # Method 1: Try to set window size to full height (may be limited by OS)
            try:
                self.driver.set_window_size(total_width, min(total_height, 8000))  # Limit to 8000px
                time.sleep(1)
                self.driver.save_screenshot(filepath)
                logger.info("✅ Full page captured with single screenshot")
                return
            except:
                logger.info("⚠️  Single screenshot failed, using scroll method")
            
            # Method 2: Scroll and capture multiple screenshots
            from PIL import Image
            import io
            
            screenshots = []
            scroll_position = 0
            
            # Scroll to top
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(0.5)
            
            while scroll_position < total_height:
                # Take screenshot
                screenshot = self.driver.get_screenshot_as_png()
                image = Image.open(io.BytesIO(screenshot))
                screenshots.append({
                    'image': image,
                    'position': scroll_position
                })
                
                # Scroll down
                scroll_position += viewport_height - 100  # Overlap for continuity
                self.driver.execute_script(f"window.scrollTo(0, {scroll_position})")
                time.sleep(0.5)
                
                logger.info(f"📸 Captured section at position {scroll_position}/{total_height}")
            
            # Stitch screenshots together
            if len(screenshots) == 1:
                # Only one screenshot needed
                screenshots[0]['image'].save(filepath)
            else:
                # Create combined image
                combined_height = total_height
                combined_width = screenshots[0]['image'].width
                
                combined = Image.new('RGB', (combined_width, combined_height))
                
                for i, shot in enumerate(screenshots):
                    y_position = shot['position']
                    # For last screenshot, adjust position to avoid going beyond total height
                    if i == len(screenshots) - 1:
                        y_position = combined_height - shot['image'].height
                    
                    combined.paste(shot['image'], (0, y_position))
                
                # Save combined image
                combined.save(filepath)
                logger.info(f"✅ Stitched {len(screenshots)} screenshots into full page image")
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0)")
            
        except Exception as e:
            logger.error(f"Full page screenshot failed: {e}")
            # Fallback to regular screenshot
            self.driver.save_screenshot(filepath)
    
    def _perform_ocr_validation(self, screenshot_path: str, symbol: str) -> Dict[str, Any]:
        """Perform OCR extraction and validation"""
        try:
            # Extract text using OCR
            ocr_result = self.ocr_extractor.extract_text_from_screenshot(screenshot_path)
            
            if not ocr_result.get("success"):
                return {
                    "success": False,
                    "error": ocr_result.get("error", "OCR extraction failed")
                }
            
            # Get extracted contracts
            ocr_contracts = ocr_result.get("contracts", [])
            
            # Normalize the data
            normalized_data = self.data_normalizer.normalize_screenshot_data(ocr_contracts, symbol)
            
            # Extract summary statistics
            summary_stats = self.data_normalizer.extract_summary_stats(normalized_data)
            
            return {
                "success": True,
                "method": ocr_result.get("method"),
                "contracts_found": len(ocr_contracts),
                "normalized_data": normalized_data,
                "summary_stats": summary_stats,
                "raw_ocr_result": ocr_result
            }
            
        except Exception as e:
            logger.error(f"OCR validation error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def validate_with_screenshot(self, api_data_file: str) -> Dict[str, Any]:
        """
        Validate API data by taking screenshot of corresponding page
        
        Args:
            api_data_file: Path to API response JSON file
            
        Returns:
            Validation results with screenshot
        """
        try:
            # Load API data
            with open(api_data_file, 'r') as f:
                api_data = json.load(f)
            
            # Extract symbol from filename or data
            filename = Path(api_data_file).stem
            symbol = None
            for part in filename.split('_'):
                if part.startswith('M') and len(part) == 6:
                    symbol = part
                    break
            
            if not symbol:
                return {
                    "success": False,
                    "error": "Could not extract symbol from API data"
                }
            
            # Take screenshot
            screenshot_result = self.take_options_screenshot(symbol)
            
            # Compare data
            validation = {
                "api_data_file": api_data_file,
                "symbol": symbol,
                "screenshot": screenshot_result,
                "comparison": {}
            }
            
            if screenshot_result["success"] and "page_data" in screenshot_result:
                page_data = screenshot_result["page_data"]
                api_total = api_data.get("total", 0)
                
                validation["comparison"] = {
                    "api_contract_count": api_total,
                    "page_contract_count": page_data.get("contract_count", 0),
                    "counts_match": abs(api_total - page_data.get("contract_count", 0)) <= 5  # Allow small difference
                }
            
            # Perform OCR comparison if available
            if (screenshot_result.get("success") and 
                "ocr_validation" in screenshot_result and 
                screenshot_result["ocr_validation"].get("success")):
                
                logger.info("🔍 Comparing OCR data with API data...")
                
                ocr_normalized = screenshot_result["ocr_validation"]["normalized_data"]
                comparison_result = self.comparator.compare_data(ocr_normalized, api_data)
                
                validation["ocr_comparison"] = comparison_result
                validation["ocr_comparison_report"] = self.comparator.format_comparison_report(comparison_result)
                
                # Log the report
                logger.info("\n" + validation["ocr_comparison_report"])
            
            validation["success"] = screenshot_result["success"]
            
            return validation
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Validation failed: {str(e)}",
                "api_data_file": api_data_file
            }
    
    def cleanup(self):
        """Close the browser driver"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            logger.info("🧹 Browser closed")
    
    def print_validation_report(self, results: Dict[str, Any]):
        """Print formatted validation report"""
        print(f"\n{'='*60}")
        print(f"📸 SCREENSHOT VALIDATION REPORT")
        print(f"{'='*60}")
        
        print(f"\nSymbol: {results.get('symbol', 'Unknown')}")
        print(f"Status: {'✅ SUCCESS' if results.get('success') else '❌ FAILED'}")
        
        if "error" in results:
            print(f"\n❌ ERROR: {results['error']}")
            return
        
        if "screenshot" in results and results["screenshot"].get("success"):
            screenshot = results["screenshot"]
            print(f"\n📸 Screenshot Details:")
            print(f"   Path: {screenshot['screenshot_path']}")
            print(f"   URL: {screenshot['url']}")
            
            if "page_data" in screenshot:
                page = screenshot["page_data"]
                print(f"\n📊 Page Data:")
                print(f"   Title: {page.get('page_title', 'N/A')}")
                print(f"   Has Options Table: {'Yes' if page.get('has_options_table') else 'No'}")
                print(f"   Visible Contracts: {page.get('contract_count', 0)}")
        
        if "comparison" in results:
            comp = results["comparison"]
            print(f"\n🔍 Basic Comparison:")
            print(f"   API Contracts: {comp.get('api_contract_count', 'N/A')}")
            print(f"   Page Contracts: {comp.get('page_contract_count', 'N/A')}")
            print(f"   Counts Match: {'✅ YES' if comp.get('counts_match') else '❌ NO'}")
        
        # OCR Results
        if "screenshot" in results and "ocr_validation" in results["screenshot"]:
            ocr = results["screenshot"]["ocr_validation"]
            if ocr.get("success"):
                print(f"\n🔤 OCR Results:")
                print(f"   Method: {ocr.get('method', 'unknown')}")
                print(f"   Contracts Extracted: {ocr.get('contracts_found', 0)}")
                
                if "summary_stats" in ocr:
                    stats = ocr["summary_stats"]
                    print(f"   Contracts with Data: {stats.get('contracts_with_data', 0)}")
                    
                    if stats.get('call_oi_total') or stats.get('put_oi_total'):
                        print(f"\n   📊 OCR Statistics:")
                        print(f"      Call OI: {stats.get('call_oi_total', 0):,}")
                        print(f"      Put OI: {stats.get('put_oi_total', 0):,}")
                        print(f"      P/C Ratio: {stats.get('put_call_oi_ratio', 0):.3f}")
            else:
                print(f"\n🔤 OCR: ❌ Failed - {ocr.get('error', 'Unknown error')}")
        
        # OCR Comparison Report
        if "ocr_comparison_report" in results:
            print(f"\n{results['ocr_comparison_report']}")
        
        print(f"\n{'='*60}")


def main():
    """Example usage and CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate Barchart data with screenshots')
    parser.add_argument('--symbol', help='Options symbol to screenshot (e.g., MQ6M25)')
    parser.add_argument('--underlying', default='NQU25', help='Underlying futures symbol')
    parser.add_argument('--api-file', help='API data file to validate with screenshot')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    
    args = parser.parse_args()
    
    validator = BarchartScreenshotValidator(headless=args.headless)
    
    try:
        if args.api_file:
            # Validate API data with screenshot
            results = validator.validate_with_screenshot(args.api_file)
            validator.print_validation_report(results)
            
        elif args.symbol:
            # Just take a screenshot
            result = validator.take_options_screenshot(args.symbol, args.underlying)
            
            if result["success"]:
                print(f"\n✅ Screenshot saved: {result['screenshot_path']}")
                if "page_data" in result:
                    print(f"📊 Page has {result['page_data'].get('contract_count', 0)} visible contracts")
            else:
                print(f"\n❌ Screenshot failed: {result.get('error')}")
        
        else:
            print("Usage: python screenshot_validator.py --symbol MQ6M25 [--underlying NQU25] [--headless]")
            print("   or: python screenshot_validator.py --api-file path/to/api_data.json [--headless]")
            
    finally:
        validator.cleanup()


if __name__ == "__main__":
    main()