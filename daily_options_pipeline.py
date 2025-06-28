#!/usr/bin/env python3
"""
Daily Options Data Pipeline
Orchestrates: Symbol Generation → Authentication → Data Retrieval → Metrics Calculation

Features:
- Cookie persistence between sessions
- Comprehensive error handling with retries
- Progress tracking and partial recovery
- Timestamped data organization
- Detailed logging and monitoring
"""

import os
import sys
import json
import pickle
import logging
import time
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict

# Add path to import our modules
sys.path.append("tasks/options_trading_system/data_ingestion/barchart_web_scraper")

from solution import BarchartAPIComparator
from hybrid_scraper import HybridBarchartScraper
from scripts.utilities.options_metrics_calculator import OptionsMetricsCalculator

@dataclass
class PipelineState:
    """Track pipeline execution state"""
    timestamp: str
    symbol_generated: bool = False
    symbol: Optional[str] = None
    option_type: Optional[str] = None
    authenticated: bool = False
    cookies_saved: bool = False
    cookie_file: Optional[str] = None
    data_retrieved: bool = False
    data_file: Optional[str] = None
    metrics_calculated: bool = False
    metrics_file: Optional[str] = None
    total_contracts: int = 0
    errors: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []

class DailyOptionsPipeline:
    """Orchestrates daily options data collection and analysis"""
    
    def __init__(self, output_dir: str = "outputs", cookie_dir: str = "cookies"):
        self.output_dir = Path(output_dir)
        self.cookie_dir = Path(cookie_dir)
        self.date_str = datetime.now().strftime('%Y%m%d')
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create directories
        self.output_dir.mkdir(exist_ok=True)
        self.cookie_dir.mkdir(exist_ok=True)
        (self.output_dir / self.date_str).mkdir(exist_ok=True)
        
        # Setup logging
        self.setup_logging()
        
        # Initialize state
        self.state = PipelineState(timestamp=self.timestamp)
        self.state_file = self.output_dir / self.date_str / f"pipeline_state_{self.timestamp}.json"
        
        # Initialize components
        self.symbol_generator = None
        self.scraper = None
        self.calculator = OptionsMetricsCalculator(str(self.output_dir))
        
        self.logger.info(f"🚀 Daily Options Pipeline initialized")
        self.logger.info(f"   Output: {self.output_dir / self.date_str}")
        self.logger.info(f"   Cookies: {self.cookie_dir}")
        self.logger.info(f"   State: {self.state_file}")
    
    def setup_logging(self):
        """Configure comprehensive logging"""
        log_dir = self.output_dir / self.date_str / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # File handler
        log_file = log_dir / f"pipeline_{self.timestamp}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        self.logger.info(f"📝 Logging configured: {log_file}")
    
    def save_state(self):
        """Save current pipeline state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(asdict(self.state), f, indent=2)
            self.logger.debug(f"💾 State saved to {self.state_file}")
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def load_cookies(self) -> Optional[Dict[str, str]]:
        """Load persisted cookies from most recent session"""
        try:
            # Find most recent cookie file
            cookie_files = list(self.cookie_dir.glob("barchart_cookies_*.pkl"))
            if not cookie_files:
                self.logger.info("🍪 No persisted cookies found")
                return None
            
            latest_cookie_file = max(cookie_files, key=os.path.getctime)
            cookie_age = datetime.now() - datetime.fromtimestamp(os.path.getctime(latest_cookie_file))
            
            # Check if cookies are too old (older than 24 hours)
            if cookie_age > timedelta(hours=24):
                self.logger.info(f"🍪 Cookies too old ({cookie_age}), will re-authenticate")
                return None
            
            with open(latest_cookie_file, 'rb') as f:
                cookies = pickle.load(f)
            
            self.logger.info(f"🍪 Loaded {len(cookies)} cookies from {latest_cookie_file.name}")
            self.logger.info(f"   Age: {cookie_age}")
            
            # Validate essential cookies
            essential_cookies = ['laravel_session', 'XSRF-TOKEN', 'laravel_token']
            missing = [c for c in essential_cookies if c not in cookies]
            
            if missing:
                self.logger.warning(f"🍪 Missing essential cookies: {missing}")
                return None
            
            return cookies
            
        except Exception as e:
            self.logger.error(f"Failed to load cookies: {e}")
            return None
    
    def save_cookies(self, cookies: Dict[str, str]) -> str:
        """Save cookies with timestamp"""
        try:
            cookie_file = self.cookie_dir / f"barchart_cookies_{self.timestamp}.pkl"
            
            with open(cookie_file, 'wb') as f:
                pickle.dump(cookies, f)
            
            self.logger.info(f"🍪 Saved {len(cookies)} cookies to {cookie_file.name}")
            
            # Clean up old cookie files (keep last 5)
            cookie_files = sorted(
                self.cookie_dir.glob("barchart_cookies_*.pkl"),
                key=os.path.getctime,
                reverse=True
            )
            
            for old_file in cookie_files[5:]:
                old_file.unlink()
                self.logger.debug(f"🗑️  Cleaned up old cookie file: {old_file.name}")
            
            return str(cookie_file)
            
        except Exception as e:
            self.logger.error(f"Failed to save cookies: {e}")
            raise
    
    def retry_with_backoff(self, func, max_retries: int = 3, base_delay: float = 1.0):
        """Execute function with exponential backoff retry"""
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                
                delay = base_delay * (2 ** attempt)
                self.logger.warning(f"⚠️  Attempt {attempt + 1} failed: {e}")
                self.logger.info(f"🔄 Retrying in {delay:.1f}s...")
                time.sleep(delay)
    
    def step1_generate_symbol(self, option_type: str = "weekly", year_format: str = "2digit") -> bool:
        """Step 1: Generate today's options symbol"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📅 STEP 1: SYMBOL GENERATION")
        self.logger.info("="*60)
        
        try:
            def _generate():
                from tasks.options_trading_system.data_ingestion.barchart_web_scraper.symbol_generator import BarchartSymbolGenerator
                self.symbol_generator = BarchartSymbolGenerator()
                symbol = self.symbol_generator.get_eod_contract_symbol(option_type=option_type, year_format=year_format)
                return symbol
            
            symbol = self.retry_with_backoff(_generate)
            
            self.state.symbol = symbol
            self.state.option_type = option_type
            self.state.symbol_generated = True
            
            self.logger.info(f"✅ Generated {option_type} symbol: {symbol}")
            
            # Test with known working symbols as fallbacks
            fallback_symbols = {
                'weekly': ['MM1N25', 'MM2N25', 'MM3N25'],
                'monthly': ['MM6N25', 'MM6Q25'],
                'daily': ['MC4N25', 'MC5N25']
            }
            
            if symbol in fallback_symbols.get(option_type, []):
                self.logger.info("✅ Generated symbol matches known working symbols")
            
            self.save_state()
            return True
            
        except Exception as e:
            error_msg = f"Symbol generation failed: {e}"
            self.logger.error(f"❌ {error_msg}")
            self.state.errors.append(error_msg)
            
            # Try fallback symbols
            fallback_symbols = ['MM1N25', 'MM6N25', 'MC4N25']
            for fallback in fallback_symbols:
                try:
                    self.logger.info(f"🔄 Trying fallback symbol: {fallback}")
                    self.state.symbol = fallback
                    self.state.option_type = "fallback"
                    self.state.symbol_generated = True
                    self.save_state()
                    return True
                except Exception:
                    continue
            
            self.save_state()
            return False
    
    def step2_authenticate_and_extract_cookies(self, force_refresh: bool = False) -> bool:
        """Step 2: Authenticate and extract/save cookies"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🔐 STEP 2: AUTHENTICATION & COOKIE MANAGEMENT")
        self.logger.info("="*60)
        
        try:
            # Try to load existing cookies first
            cookies = None
            if not force_refresh:
                cookies = self.load_cookies()
            
            if cookies:
                self.logger.info("✅ Using existing cookies")
                self.state.authenticated = True
                self.state.cookies_saved = True
                self.save_state()
                return True
            
            # Fresh authentication needed
            self.logger.info("🔄 Fresh authentication required")
            
            def _authenticate():
                scraper = HybridBarchartScraper(headless=True)
                
                # Authenticate and extract cookies
                if not scraper.authenticate("NQU25"):
                    raise Exception("Authentication failed")
                
                if not scraper.cookies or len(scraper.cookies) < 10:
                    raise Exception(f"Insufficient cookies extracted: {len(scraper.cookies) if scraper.cookies else 0}")
                
                return scraper.cookies
            
            cookies = self.retry_with_backoff(_authenticate, max_retries=2)
            
            # Save cookies
            cookie_file = self.save_cookies(cookies)
            
            self.state.authenticated = True
            self.state.cookies_saved = True
            self.state.cookie_file = cookie_file
            
            self.logger.info(f"✅ Authentication successful")
            self.logger.info(f"   Extracted: {len(cookies)} cookies")
            self.logger.info(f"   Saved to: {Path(cookie_file).name}")
            
            self.save_state()
            return True
            
        except Exception as e:
            error_msg = f"Authentication failed: {e}"
            self.logger.error(f"❌ {error_msg}")
            self.state.errors.append(error_msg)
            self.save_state()
            return False
    
    def step3_retrieve_data(self) -> bool:
        """Step 3: Retrieve options data using authenticated session"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 STEP 3: DATA RETRIEVAL")
        self.logger.info("="*60)
        
        try:
            # Load cookies
            cookies = self.load_cookies()
            if not cookies:
                raise Exception("No cookies available for data retrieval")
            
            def _retrieve_data():
                scraper = HybridBarchartScraper(headless=True)
                
                # Set cookies directly
                scraper.cookies = cookies
                
                # Initialize API client with cookies
                from tasks.options_trading_system.data_ingestion.barchart_web_scraper.barchart_api_client import BarchartAPIClient
                api_client = BarchartAPIClient()
                api_client.set_cookies(cookies)
                
                # Fetch data
                data = api_client.get_options_data(self.state.symbol, "NQU25")
                
                if not data or data.get('total', 0) == 0:
                    raise Exception(f"No data returned for symbol {self.state.symbol}")
                
                return data, api_client
            
            data, api_client = self.retry_with_backoff(_retrieve_data)
            
            # Save data
            data_file = api_client.save_api_response(data, self.state.symbol)
            
            self.state.data_retrieved = True
            self.state.data_file = data_file
            self.state.total_contracts = data.get('total', 0)
            
            self.logger.info(f"✅ Data retrieval successful")
            self.logger.info(f"   Symbol: {self.state.symbol}")
            self.logger.info(f"   Contracts: {self.state.total_contracts}")
            self.logger.info(f"   Saved to: {Path(data_file).name}")
            
            # Log data breakdown
            if 'data' in data and isinstance(data['data'], dict):
                calls = len(data['data'].get('Call', []))
                puts = len(data['data'].get('Put', []))
                self.logger.info(f"   Breakdown: {calls} calls, {puts} puts")
            
            self.save_state()
            return True
            
        except Exception as e:
            error_msg = f"Data retrieval failed: {e}"
            self.logger.error(f"❌ {error_msg}")
            self.state.errors.append(error_msg)
            
            # Try alternative symbols
            alternative_symbols = ['MM6N25', 'MM1N25', 'MC4N25']
            for alt_symbol in alternative_symbols:
                if alt_symbol == self.state.symbol:
                    continue
                
                try:
                    self.logger.info(f"🔄 Trying alternative symbol: {alt_symbol}")
                    
                    cookies = self.load_cookies()
                    if cookies:
                        from barchart_api_client import BarchartAPIClient
                        api_client = BarchartAPIClient()
                        api_client.set_cookies(cookies)
                        
                        data = api_client.get_options_data(alt_symbol, "NQU25")
                        
                        if data and data.get('total', 0) > 0:
                            data_file = api_client.save_api_response(data, alt_symbol)
                            
                            self.state.symbol = alt_symbol  # Update symbol
                            self.state.data_retrieved = True
                            self.state.data_file = data_file
                            self.state.total_contracts = data.get('total', 0)
                            
                            self.logger.info(f"✅ Alternative symbol worked: {alt_symbol}")
                            self.save_state()
                            return True
                            
                except Exception as alt_e:
                    self.logger.warning(f"Alternative symbol {alt_symbol} failed: {alt_e}")
                    continue
            
            self.save_state()
            return False
    
    def step4_calculate_metrics(self) -> bool:
        """Step 4: Calculate options metrics"""
        self.logger.info("\n" + "="*60)
        self.logger.info("📈 STEP 4: METRICS CALCULATION")
        self.logger.info("="*60)
        
        try:
            if not self.state.data_file:
                raise Exception("No data file available for metrics calculation")
            
            def _calculate_metrics():
                # Load data
                with open(self.state.data_file, 'r') as f:
                    data = json.load(f)
                
                # Calculate metrics
                metrics, metrics_file = self.calculator.calculate_and_save_metrics(
                    data, self.state.symbol
                )
                
                return metrics, metrics_file
            
            metrics, metrics_file = self.retry_with_backoff(_calculate_metrics)
            
            self.state.metrics_calculated = True
            self.state.metrics_file = metrics_file
            
            # Print metrics summary
            self.calculator.print_metrics_summary(metrics)
            
            self.logger.info(f"✅ Metrics calculation successful")
            self.logger.info(f"   Saved to: {Path(metrics_file).name}")
            
            # Log key metrics
            fmt = metrics['formatted']
            self.logger.info(f"📊 Key Metrics:")
            self.logger.info(f"   Call Premium: {fmt['call_premium_total']}")
            self.logger.info(f"   Put Premium: {fmt['put_premium_total']}")
            self.logger.info(f"   P/C Premium Ratio: {fmt['put_call_premium_ratio']}")
            self.logger.info(f"   Call OI: {fmt['call_oi_total']}")
            self.logger.info(f"   Put OI: {fmt['put_oi_total']}")
            self.logger.info(f"   P/C OI Ratio: {fmt['put_call_oi_ratio']}")
            
            self.save_state()
            return True
            
        except Exception as e:
            error_msg = f"Metrics calculation failed: {e}"
            self.logger.error(f"❌ {error_msg}")
            self.state.errors.append(error_msg)
            
            # Even if metrics fail, we still have the raw data
            self.logger.info("⚠️  Raw data is still available for manual analysis")
            
            self.save_state()
            return False
    
    def run_full_pipeline(self, option_type: str = "weekly", force_refresh_cookies: bool = False, year_format: str = "2digit") -> Dict[str, Any]:
        """Execute the complete pipeline"""
        start_time = datetime.now()
        
        self.logger.info("🚀 STARTING DAILY OPTIONS PIPELINE")
        self.logger.info("="*80)
        self.logger.info(f"   Timestamp: {self.timestamp}")
        self.logger.info(f"   Option Type: {option_type}")
        self.logger.info(f"   Force Refresh: {force_refresh_cookies}")
        self.logger.info("="*80)
        
        pipeline_success = True
        steps_completed = 0
        
        try:
            # Step 1: Generate Symbol
            if self.step1_generate_symbol(option_type, year_format):
                steps_completed += 1
            else:
                pipeline_success = False
                if not self.state.symbol:  # Complete failure
                    raise Exception("Cannot proceed without a symbol")
            
            # Step 2: Authentication
            if self.step2_authenticate_and_extract_cookies(force_refresh_cookies):
                steps_completed += 1
            else:
                pipeline_success = False
                raise Exception("Cannot proceed without authentication")
            
            # Step 3: Data Retrieval
            if self.step3_retrieve_data():
                steps_completed += 1
            else:
                pipeline_success = False
                raise Exception("Cannot proceed without data")
            
            # Step 4: Metrics Calculation
            if self.step4_calculate_metrics():
                steps_completed += 1
            else:
                pipeline_success = False
                # Don't raise exception - we have data even if metrics failed
            
        except Exception as e:
            self.logger.error(f"💥 Pipeline stopped: {e}")
            pipeline_success = False
        
        # Final results
        execution_time = datetime.now() - start_time
        
        self.logger.info("\n" + "="*80)
        if pipeline_success and steps_completed == 4:
            self.logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY")
        elif steps_completed > 0:
            self.logger.info(f"⚠️  PIPELINE PARTIALLY COMPLETED ({steps_completed}/4 steps)")
        else:
            self.logger.error("❌ PIPELINE FAILED")
        
        self.logger.info("="*80)
        self.logger.info(f"📊 EXECUTION SUMMARY:")
        self.logger.info(f"   Steps Completed: {steps_completed}/4")
        self.logger.info(f"   Symbol: {self.state.symbol}")
        self.logger.info(f"   Total Contracts: {self.state.total_contracts}")
        self.logger.info(f"   Execution Time: {execution_time}")
        self.logger.info(f"   Errors: {len(self.state.errors)}")
        
        if self.state.errors:
            self.logger.info(f"⚠️  Errors encountered:")
            for i, error in enumerate(self.state.errors, 1):
                self.logger.info(f"   {i}. {error}")
        
        # File locations
        if self.state.data_file:
            self.logger.info(f"📄 Data File: {self.state.data_file}")
        if self.state.metrics_file:
            self.logger.info(f"📊 Metrics File: {self.state.metrics_file}")
        if self.state.cookie_file:
            self.logger.info(f"🍪 Cookie File: {self.state.cookie_file}")
        
        self.logger.info(f"💾 State File: {self.state_file}")
        self.save_state()
        
        return {
            'success': pipeline_success,
            'steps_completed': steps_completed,
            'execution_time': execution_time.total_seconds(),
            'state': asdict(self.state),
            'files': {
                'data': self.state.data_file,
                'metrics': self.state.metrics_file,
                'cookies': self.state.cookie_file,
                'state': str(self.state_file)
            }
        }

def main():
    """Main execution with CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Daily Options Data Pipeline')
    parser.add_argument('--option-type', choices=['weekly', 'monthly', 'daily', 'friday', '0dte'], 
                       default='weekly', help='Type of options to fetch (weekly=Tuesday, friday=Friday weekly, 0dte=today if Friday)')
    parser.add_argument('--force-refresh-cookies', action='store_true',
                       help='Force fresh authentication (ignore cached cookies)')
    parser.add_argument('--output-dir', default='outputs',
                       help='Output directory for data and logs')
    parser.add_argument('--cookie-dir', default='cookies',
                       help='Directory for cookie storage')
    parser.add_argument('--year-format', choices=['2digit', '1digit'], 
                       default='2digit', help='Year format: 2digit (25) or 1digit (5)')
    
    args = parser.parse_args()
    
    # Initialize pipeline
    pipeline = DailyOptionsPipeline(
        output_dir=args.output_dir,
        cookie_dir=args.cookie_dir
    )
    
    # Run pipeline
    result = pipeline.run_full_pipeline(
        option_type=args.option_type,
        force_refresh_cookies=args.force_refresh_cookies,
        year_format=args.year_format
    )
    
    # Exit code based on success
    return 0 if result['success'] else 1

if __name__ == "__main__":
    exit(main())