#!/usr/bin/env python3
"""
Stealth Scraper with Anti-Bot Detection
Bypasses Barchart's bot detection by mimicking real browser behavior
"""

import asyncio
import logging
import random
from typing import Dict, List, Optional, Any
from pathlib import Path
from bs4 import BeautifulSoup
from .manual_html_parser import extract_from_shadow_dom
from .feedback_loop_scraper import wait_for_shadow_dom_ready

logger = logging.getLogger(__name__)

class StealthScraper:
    """Advanced scraper that bypasses bot detection"""
    
    def __init__(self):
        self.user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
        ]
    
    async def setup_stealth_page(self, page):
        """Configure page to bypass bot detection"""
        logger.info("🥷 Setting up stealth mode...")
        
        # 1. Set realistic user agent
        user_agent = random.choice(self.user_agents)
        await page.setUserAgent(user_agent)
        logger.info(f"Set user agent: {user_agent[:50]}...")
        
        # 2. Set realistic viewport
        await page.setViewport({
            'width': random.randint(1200, 1920), 
            'height': random.randint(800, 1080)
        })
        
        # 3. Override webdriver detection
        await page.evaluateOnNewDocument('''() => {
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            
            // Override chrome runtime
            window.chrome = {
                runtime: {},
            };
            
            // Mock permissions
            const getParameter = WebGLRenderingContext.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) {
                    return 'Intel Inc.';
                }
                if (parameter === 37446) {
                    return 'Intel Iris OpenGL Engine';
                }
                return getParameter(parameter);
            };
        }''')
        
        # 4. Set extra headers
        await page.setExtraHTTPHeaders({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("✅ Stealth configuration complete")
    
    async def human_like_navigation(self, page, url: str):
        """Navigate with human-like behavior"""
        logger.info(f"🧑 Navigating like a human to: {url}")
        
        # Human-like delay before navigation
        await asyncio.sleep(random.uniform(1, 3))
        
        # Navigate with realistic options
        response = await page.goto(url, {
            'waitUntil': 'networkidle2',
            'timeout': 30000
        })
        
        logger.info(f"Navigation response: {response.status}")
        
        # Random scroll and mouse movements to mimic human behavior
        await self.simulate_human_behavior(page)
        
        return response
    
    async def simulate_human_behavior(self, page):
        """Simulate realistic human interactions"""
        logger.info("🎭 Simulating human behavior...")
        
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 800)
            y = random.randint(100, 600)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.5))
        
        # Random scrolling
        for _ in range(random.randint(1, 3)):
            await page.evaluate(f'''
                window.scrollTo({{
                    top: {random.randint(0, 1000)},
                    behavior: 'smooth'
                }});
            ''')
            await asyncio.sleep(random.uniform(1, 2))
        
        # Wait like a human reading
        await asyncio.sleep(random.uniform(2, 5))
    
    async def wait_for_real_data(self, page, max_attempts: int = 10):
        """Wait for real options data to load (not bot-blocked content)"""
        logger.info("⏳ Waiting for real options data to load...")
        
        # First use our improved Shadow DOM wait function
        shadow_ready = await wait_for_shadow_dom_ready(page, max_wait_time=30)
        if shadow_ready:
            logger.info("✅ Shadow DOM data is ready!")
            return True
        
        # Fallback to other checks if Shadow DOM isn't ready
        for attempt in range(max_attempts):
            logger.info(f"Attempt {attempt + 1}/{max_attempts}")
            
            # Check if we have actual options data
            has_data = await page.evaluate('''() => {
                // First check for Shadow DOM components
                const textBindings = document.querySelectorAll('text-binding');
                if (textBindings.length > 0) {
                    // Check if Shadow DOM has actual strike data
                    let validStrikes = 0;
                    for (const binding of textBindings) {
                        const shadowRoot = binding.shadowRoot;
                        if (shadowRoot) {
                            const text = shadowRoot.textContent || '';
                            // Check for strike prices like 21450.00C
                            if (/2[01][0-9]{3}\\.?[0-9]*[CP]/.test(text)) {
                                validStrikes++;
                            }
                        }
                        // Also check for template elements
                        const template = binding.querySelector('template[shadowrootmode="open"]');
                        if (template && template.textContent) {
                            const text = template.textContent;
                            if (/2[01][0-9]{3}\\.?[0-9]*[CP]/.test(text)) {
                                validStrikes++;
                            }
                        }
                    }
                    if (validStrikes >= 5) { // At least 5 strikes
                        return true;
                    }
                }
                
                // Look for actual table data
                const tables = document.querySelectorAll('table');
                for (const table of tables) {
                    const rows = table.querySelectorAll('tr');
                    if (rows.length > 5) { // Likely has real data
                        const text = table.textContent;
                        if (text.includes('Strike') || 
                            text.includes('Call') || 
                            text.includes('Put') ||
                            /2[01][0-9]{3}/.test(text)) { // Strike prices like 20000-21999
                            return true;
                        }
                    }
                }
                
                // Also check for Angular data being populated
                try {
                    const element = document.querySelector('[data-ng-controller*="futuresOptionsQuotes"]');
                    if (element) {
                        const scope = angular.element(element).scope();
                        if (scope && scope.data && scope.data.calls && scope.data.calls.data) {
                            return scope.data.calls.data.length > 0;
                        }
                    }
                } catch (e) {
                    // Angular not ready
                }
                
                return false;
            }''')
            
            if has_data:
                logger.info("✅ Real options data detected!")
                return True
            
            logger.info("⏳ No real data yet, waiting...")
            await asyncio.sleep(3)
            
            # Try some more human-like interactions
            if attempt % 3 == 0:
                await self.simulate_human_behavior(page)
        
        logger.warning("❌ No real data found after all attempts")
        return False
    
    async def extract_options_data_stealth(self, page) -> List[Dict[str, Any]]:
        """Extract options data using stealth techniques"""
        logger.info("🔍 Extracting options data with stealth methods...")
        
        # First try Shadow DOM extraction
        try:
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            shadow_data = extract_from_shadow_dom(soup)
            
            if shadow_data and len(shadow_data) > 0:
                logger.info(f"✅ Extracted {len(shadow_data)} options via Shadow DOM")
                return shadow_data
        except Exception as e:
            logger.debug(f"Shadow DOM extraction failed: {e}")
        
        # Then try Angular scope extraction
        angular_data = await page.evaluate('''() => {
            try {
                const element = document.querySelector('[data-ng-controller*="futuresOptionsQuotes"]');
                if (element) {
                    const scope = angular.element(element).scope();
                    if (scope && scope.data) {
                        const options = [];
                        
                        // Extract calls
                        if (scope.data.calls && scope.data.calls.data) {
                            for (const call of scope.data.calls.data) {
                                const strike = parseFloat(call.strike);
                                if (!isNaN(strike)) {
                                    options.push({
                                        strike: strike,
                                        call_volume: parseInt(call.volume || 0),
                                        call_oi: parseInt(call.openInterest || 0),
                                        call_premium: parseFloat(call.lastPrice || 0),
                                        put_premium: 0,
                                        put_oi: 0,
                                        put_volume: 0
                                    });
                                }
                            }
                        }
                        
                        // Extract puts
                        if (scope.data.puts && scope.data.puts.data) {
                            for (const put of scope.data.puts.data) {
                                const strike = parseFloat(put.strike);
                                if (!isNaN(strike)) {
                                    let existing = options.find(opt => opt.strike === strike);
                                    if (existing) {
                                        existing.put_volume = parseInt(put.volume || 0);
                                        existing.put_oi = parseInt(put.openInterest || 0);
                                        existing.put_premium = parseFloat(put.lastPrice || 0);
                                    } else {
                                        options.push({
                                            strike: strike,
                                            call_volume: 0,
                                            call_oi: 0,
                                            call_premium: 0,
                                            put_premium: parseFloat(put.lastPrice || 0),
                                            put_oi: parseInt(put.openInterest || 0),
                                            put_volume: parseInt(put.volume || 0)
                                        });
                                    }
                                }
                            }
                        }
                        
                        return options.sort((a, b) => a.strike - b.strike);
                    }
                }
            } catch (e) {
                console.log('Angular extraction failed:', e);
            }
            return [];
        }''')
        
        if angular_data and len(angular_data) > 0:
            logger.info(f"✅ Extracted {len(angular_data)} options via Angular")
            return angular_data
        
        # Fallback to table extraction
        table_data = await page.evaluate('''() => {
            const options = [];
            const tables = document.querySelectorAll('table');
            
            for (const table of tables) {
                const rows = table.querySelectorAll('tr');
                if (rows.length > 5) { // Skip tiny tables
                    for (let i = 1; i < rows.length; i++) {
                        const cells = rows[i].querySelectorAll('td');
                        if (cells.length >= 7) {
                            const strike = parseFloat(cells[3]?.innerText.replace(/,/g, ''));
                            if (strike && !isNaN(strike) && strike > 15000 && strike < 30000) {
                                options.push({
                                    strike: strike,
                                    call_volume: parseInt(cells[0]?.innerText.replace(/,/g, '') || '0'),
                                    call_oi: parseInt(cells[1]?.innerText.replace(/,/g, '') || '0'),
                                    call_premium: parseFloat(cells[2]?.innerText.replace(/,/g, '') || '0'),
                                    put_premium: parseFloat(cells[4]?.innerText.replace(/,/g, '') || '0'),
                                    put_oi: parseInt(cells[5]?.innerText.replace(/,/g, '') || '0'),
                                    put_volume: parseInt(cells[6]?.innerText.replace(/,/g, '') || '0')
                                });
                            }
                        }
                    }
                }
            }
            
            return options.sort((a, b) => a.strike - b.strike);
        }''')
        
        if table_data and len(table_data) > 0:
            logger.info(f"✅ Extracted {len(table_data)} options via table")
            return table_data
        
        logger.warning("❌ No options data found")
        return []

async def run_stealth_scraper(page, url: str) -> Dict[str, Any]:
    """Run the stealth scraper on a page"""
    scraper = StealthScraper()
    
    try:
        # Setup stealth mode
        await scraper.setup_stealth_page(page)
        
        # Navigate like a human
        await scraper.human_like_navigation(page, url)
        
        # Wait for real data
        has_real_data = await scraper.wait_for_real_data(page)
        
        if not has_real_data:
            return {
                "success": False,
                "error": "No real options data found - likely bot detected"
            }
        
        # Extract options data
        options_data = await scraper.extract_options_data_stealth(page)
        
        # Extract current price
        current_price = await page.evaluate('''() => {
            try {
                // Try multiple price selectors
                const selectors = [
                    '.last-change.ng-binding',
                    '[data-ng-bind*="lastPrice"]',
                    '.pricechangerow .last-change'
                ];
                
                for (const selector of selectors) {
                    const elem = document.querySelector(selector);
                    if (elem && elem.textContent) {
                        const price = parseFloat(elem.textContent.replace(/,/g, ''));
                        if (!isNaN(price) && price > 15000 && price < 30000) {
                            return price;
                        }
                    }
                }
                
                // Try regex on page content
                const content = document.body.textContent;
                const match = content.match(/"lastPrice":\s*"?([0-9,]+\.?[0-9]*)"?/);
                if (match) {
                    const price = parseFloat(match[1].replace(/,/g, ''));
                    if (!isNaN(price) && price > 15000 && price < 30000) {
                        return price;
                    }
                }
            } catch (e) {
                console.log('Price extraction error:', e);
            }
            return null;
        }''')
        
        return {
            "success": bool(current_price and options_data and len(options_data) > 0),
            "current_price": current_price,
            "options_data": options_data,
            "method": "stealth_scraper"
        }
        
    except Exception as e:
        logger.error(f"Stealth scraper error: {e}")
        return {
            "success": False,
            "error": str(e)
        }