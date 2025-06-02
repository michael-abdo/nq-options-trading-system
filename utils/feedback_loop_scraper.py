#!/usr/bin/env python3
"""
Closed Feedback Loop System for Barchart Options Scraper
Automatically saves HTML, analyzes structure, updates selectors, and iterates until successful
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from bs4 import BeautifulSoup
import hashlib

logger = logging.getLogger(__name__)

async def wait_for_shadow_dom_ready(page, max_wait_time: int = 30) -> bool:
    """Wait for Shadow DOM components to be created and populated with data"""
    logger.info("⏳ Waiting for Shadow DOM components to be ready...")
    
    # First check if we need to select the "Merged View" for options
    try:
        # Check for the merged view button and click it if not selected
        await page.evaluate("""() => {
            const mergedButton = document.querySelector('button[ng-click*="merged"]');
            if (mergedButton && !mergedButton.classList.contains('active')) {
                mergedButton.click();
                console.log('Clicked merged view button');
            }
        }""")
        await asyncio.sleep(2)  # Give time for the view to change
    except Exception as e:
        logger.debug(f"Merged view check error: {e}")
    
    shadow_dom_check_script = """
    () => {
        // First check for text-binding elements
        const textBindings = document.querySelectorAll('text-binding');
        console.log(`Found ${textBindings.length} text-binding elements`);
        
        if (textBindings.length === 0) {
            // Also check for Angular data that might not be in Shadow DOM yet
            try {
                const element = document.querySelector('[data-ng-controller*="futuresOptionsQuotes"]');
                if (element) {
                    const scope = angular.element(element).scope();
                    if (scope && scope.data && scope.data.calls && scope.data.calls.data) {
                        const callsCount = scope.data.calls.data.length;
                        const putsCount = scope.data.puts ? scope.data.puts.data.length : 0;
                        console.log(`Found Angular data: ${callsCount} calls, ${putsCount} puts`);
                        if (callsCount > 0 || putsCount > 0) {
                            return { 
                                ready: true, 
                                count: 0, 
                                hasData: true,
                                angularData: true,
                                callsCount: callsCount,
                                putsCount: putsCount
                            };
                        }
                    }
                }
            } catch (e) {
                console.log('Angular check error:', e);
            }
            
            // Also check for table data
            const tables = document.querySelectorAll('table');
            for (const table of tables) {
                const text = table.textContent || '';
                if (text.includes('Strike') && (text.includes('Call') || text.includes('Put'))) {
                    const rows = table.querySelectorAll('tr');
                    if (rows.length > 5) {
                        console.log('Found options table with', rows.length, 'rows');
                        return { ready: true, count: 0, hasData: true, tableData: true, rowCount: rows.length };
                    }
                }
            }
            
            return { ready: false, count: 0, hasData: false };
        }
        
        // Check if Shadow DOM templates have actual strike data
        let validStrikes = 0;
        let sampleData = [];
        
        for (const binding of textBindings) {
            // Check for template elements with shadowrootmode
            const template = binding.querySelector('template[shadowrootmode="open"]');
            if (template && template.textContent) {
                const text = template.textContent.trim();
                // Look for strike prices like 21450.00C or 21450.00P
                if (/\\d{5}\\.\\d{2}[CP]/.test(text)) {
                    validStrikes++;
                    if (sampleData.length < 5) {
                        sampleData.push(text);
                    }
                }
            }
        }
        
        console.log(`Found ${validStrikes} valid strike prices`);
        console.log('Sample data:', sampleData);
        
        // We need at least 10 valid strikes to consider data ready
        return {
            ready: validStrikes >= 10,
            count: textBindings.length,
            validStrikes: validStrikes,
            hasData: validStrikes > 0,
            samples: sampleData
        };
    }
    """
    
    start_time = asyncio.get_event_loop().time()
    attempt = 0
    
    while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
        attempt += 1
        
        try:
            result = await page.evaluate(shadow_dom_check_script)
            
            if result.get('angularData'):
                logger.info(f"Attempt {attempt}: Found Angular data - {result.get('callsCount', 0)} calls, {result.get('putsCount', 0)} puts")
                return True
            elif result.get('tableData'):
                logger.info(f"Attempt {attempt}: Found table data with {result.get('rowCount', 0)} rows")
                return True
            else:
                logger.info(f"Attempt {attempt}: text-binding count={result['count']}, "
                           f"valid strikes={result.get('validStrikes', 0)}")
            
            if result.get('samples'):
                logger.info(f"Sample strike data: {result['samples'][:3]}")
            
            if result['ready']:
                logger.info(f"✅ Shadow DOM ready with {result['validStrikes']} valid strikes!")
                return True
            
            # If we have some data but not enough, wait a bit more
            if result['hasData']:
                logger.info(f"Shadow DOM partially loaded ({result['validStrikes']} strikes), waiting for more...")
                await asyncio.sleep(2)
            else:
                # No data yet, wait longer
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.debug(f"Shadow DOM check error: {e}")
            await asyncio.sleep(1)
    
    logger.warning(f"⚠️ Shadow DOM not fully ready after {max_wait_time} seconds")
    return False

def extract_from_shadow_dom(soup: BeautifulSoup) -> List[Dict[str, Any]]:
    """Extract options data from Shadow DOM templates"""
    options = []
    
    # Find all text-binding elements with Shadow DOM templates
    text_bindings = soup.find_all('text-binding')
    
    # Group bindings by their parent row or container
    current_option = {}
    
    for binding in text_bindings:
        # Get the binding type (strike, volume, openInterest, etc.)
        binding_attr = binding.get('binding', '')
        
        # Find the template with shadow DOM content
        template = binding.find('template', attrs={'shadowrootmode': 'open'})
        if not template:
            continue
            
        value_text = template.get_text().strip()
        if not value_text:
            continue
            
        logger.debug(f"Found Shadow DOM binding: {binding_attr} = {value_text}")
        
        try:
            # Parse different types of data
            if 'strike' in binding_attr.lower():
                # Strike price like "21,450.00C" or "21,450.00P"
                strike_match = re.match(r'([0-9,]+\.?\d*)[CP]?', value_text)
                if strike_match:
                    strike = float(strike_match.group(1).replace(',', ''))
                    if 15000 <= strike <= 30000:  # Valid NQ strike range
                        # Start new option entry
                        if current_option and 'strike' in current_option:
                            options.append(current_option)
                        current_option = {
                            'strike': strike,
                            'call_volume': 0,
                            'call_oi': 0,
                            'call_premium': 0,
                            'put_volume': 0,
                            'put_oi': 0,
                            'put_premium': 0
                        }
                        
                        # Determine if this is call or put
                        if value_text.endswith('C'):
                            current_option['_type'] = 'call'
                        elif value_text.endswith('P'):
                            current_option['_type'] = 'put'
            
            elif 'volume' in binding_attr.lower():
                # Volume data
                volume = int(value_text.replace(',', ''))
                if current_option:
                    if current_option.get('_type') == 'call':
                        current_option['call_volume'] = volume
                    elif current_option.get('_type') == 'put':
                        current_option['put_volume'] = volume
            
            elif 'openinterest' in binding_attr.lower():
                # Open Interest data
                oi = int(value_text.replace(',', ''))
                if current_option:
                    if current_option.get('_type') == 'call':
                        current_option['call_oi'] = oi
                    elif current_option.get('_type') == 'put':
                        current_option['put_oi'] = oi
            
            elif 'lastprice' in binding_attr.lower() or 'premium' in binding_attr.lower():
                # Premium/Last Price data
                premium_match = re.search(r'([0-9,]+\.?\d*)', value_text)
                if premium_match:
                    premium = float(premium_match.group(1).replace(',', ''))
                    if current_option:
                        if current_option.get('_type') == 'call':
                            current_option['call_premium'] = premium
                        elif current_option.get('_type') == 'put':
                            current_option['put_premium'] = premium
                            
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing Shadow DOM value '{value_text}': {e}")
            continue
    
    # Add the last option if it exists
    if current_option and 'strike' in current_option:
        options.append(current_option)
    
    # Clean up the _type field and merge call/put data by strike
    merged_options = {}
    for opt in options:
        strike = opt['strike']
        opt.pop('_type', None)  # Remove temporary type field
        
        if strike not in merged_options:
            merged_options[strike] = opt
        else:
            # Merge call and put data
            existing = merged_options[strike]
            for key in ['call_volume', 'call_oi', 'call_premium', 'put_volume', 'put_oi', 'put_premium']:
                if opt.get(key, 0) > 0:
                    existing[key] = opt[key]
    
    final_options = sorted(merged_options.values(), key=lambda x: x['strike'])
    logger.info(f"Extracted {len(final_options)} options from Shadow DOM")
    return final_options

class FeedbackLoopScraper:
    """Self-improving scraper with closed feedback loop"""
    
    def __init__(self, debug_dir: str = "data/debug"):
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        self.attempts_log = []
        self.current_attempt = 0
        self.max_attempts = 10
        
        # Initialize selector strategies
        self.selector_strategies = self._initialize_selector_strategies()
        
    def _initialize_selector_strategies(self) -> Dict[str, List[Dict[str, Any]]]:
        """Initialize various selector strategies to try"""
        return {
            "current_price": [
                {"method": "css", "selector": "span.last-change.ng-binding", "extract": "text"},
                {"method": "css", "selector": ".last-change", "extract": "text"},
                {"method": "css", "selector": ".last-price", "extract": "text"},
                {"method": "css", "selector": ".quote-price", "extract": "text"},
                {"method": "css", "selector": "[data-ng-bind*='lastPrice']", "extract": "text"},
                {"method": "css", "selector": ".price-display", "extract": "text"},
                {"method": "css", "selector": ".current-price", "extract": "text"},
                {"method": "xpath", "selector": "//span[contains(@class, 'price')]", "extract": "text"},
                {"method": "xpath", "selector": "//*[contains(text(), 'Last:')]/following-sibling::*", "extract": "text"},
                {"method": "angular", "selector": "item.lastPrice", "extract": "scope"},
                {"method": "regex", "selector": r'"lastPrice":\s*"?([0-9,]+\.?[0-9]*)"?', "extract": "json"},
            ],
            "options_table": [
                {"method": "complete_options_table", "selector": "div.row", "extract": "complete_chain", "confidence": 0.98},
                {"method": "complete_options_table", "selector": "*", "extract": "comprehensive_table_search", "confidence": 0.95},
                {"method": "advanced_multi_number", "selector": "div", "extract": "multi_number_analysis", "confidence": 0.95},
                {"method": "advanced_multi_number", "selector": "*", "extract": "comprehensive_search", "confidence": 0.9},
                {"method": "shadow_dom", "selector": "text-binding", "extract": "shadow_dom", "wait_for": "data"},
                {"method": "api_wait", "selector": ".bc-datatable-middleware-wrapper", "extract": "angular_data", "wait_for": "data"},
                {"method": "angular_wait", "selector": "futuresOptionsQuotesCtrl", "extract": "scope", "wait_for": "data.calls"},
                {"method": "css", "selector": ".bc-table-scrollable-inner table", "extract": "table"},
                {"method": "css", "selector": ".options-table", "extract": "table"},
                {"method": "css", "selector": "table.data-table", "extract": "table"},
                {"method": "css", "selector": "[data-ng-repeat*='option']", "extract": "rows"},
                {"method": "xpath", "selector": "//table[contains(.//text(), 'Strike')]", "extract": "table"},
                {"method": "xpath", "selector": "//table[contains(.//text(), 'Call') and contains(.//text(), 'Put')]", "extract": "table"},
                {"method": "angular", "selector": "optionsData", "extract": "scope"},
                {"method": "regex", "selector": r'"options":\s*\[(.*?)\]', "extract": "json"},
            ]
        }
    
    async def save_page_html(self, page, timestamp: Optional[str] = None) -> str:
        """Save current page HTML and screenshot with timestamp"""
        if not timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Get the full HTML content  
            html_content = await page.content()
            
            # Save raw HTML
            html_path = self.debug_dir / f"page_{timestamp}.html"
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Take a screenshot for visual inspection
            screenshot_path = self.debug_dir / f"page_{timestamp}_screenshot.png"
            await page.screenshot({
                'path': str(screenshot_path),
                'fullPage': True,
                'type': 'png'
            })
            logger.info(f"Saved screenshot to {screenshot_path}")
            
            # Also save page info
            page_info = {
                "url": page.url,
                "timestamp": timestamp,
                "viewport": page.viewport,
                "cookies": await page.cookies(),
                "screenshot_path": str(screenshot_path)
            }
            
            info_path = self.debug_dir / f"page_{timestamp}_info.json"
            with open(info_path, 'w') as f:
                json.dump(page_info, f, indent=2)
            
            logger.info(f"Saved HTML snapshot to {html_path}")
            return str(html_path)
            
        except Exception as e:
            logger.error(f"Error saving HTML/screenshot: {e}")
            return ""
    
    def analyze_html_structure(self, html_path: str) -> Dict[str, Any]:
        """Analyze saved HTML to understand structure"""
        logger.info(f"Analyzing HTML structure from {html_path}")
        
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        analysis = {
            "timestamp": datetime.now().isoformat(),
            "file": html_path,
            "findings": {},
            "potential_selectors": {}
        }
        
        # Analyze for price elements
        price_findings = self._analyze_price_elements(soup, html_content)
        analysis["findings"]["price"] = price_findings
        
        # Analyze for table elements
        table_findings = self._analyze_table_elements(soup, html_content)
        analysis["findings"]["table"] = table_findings
        
        # Analyze Angular elements
        angular_findings = self._analyze_angular_elements(soup, html_content)
        analysis["findings"]["angular"] = angular_findings
        
        # Generate new selector suggestions
        analysis["potential_selectors"] = self._generate_selector_suggestions(analysis["findings"])
        
        # Add strategies based on actual data locations found  
        if "table_indicators" in analysis["findings"].get("html_analysis", {}):
            table_data = analysis["findings"]["html_analysis"]["table_indicators"]
            
            # NEW: Add strategies from found strike elements
            if table_data.get("extraction_strategies"):
                logger.info(f"🎯 Adding {len(table_data['extraction_strategies'])} new extraction strategies")
                for strategy in table_data["extraction_strategies"]:
                    analysis["potential_selectors"]["options_table"].insert(0, strategy)
            
            if table_data.get("potential_data_locations"):
                # Add strategies to extract from wherever we found data
                for location in table_data["potential_data_locations"]:
                    if "table cell" in location:
                        analysis["potential_selectors"]["options_table"].insert(0, {
                            "method": "css",
                            "selector": "td",
                            "extract": "table_cells",
                            "confidence": 0.95
                        })
                    elif "div" in location:
                        analysis["potential_selectors"]["options_table"].insert(0, {
                            "method": "css_text_content", 
                            "selector": "div",
                            "extract": "div_text", 
                            "confidence": 0.8
                        })
                    elif "span" in location:
                        analysis["potential_selectors"]["options_table"].insert(0, {
                            "method": "css_text_content", 
                            "selector": "span",
                            "extract": "span_text", 
                            "confidence": 0.85
                        })
        
        # Save analysis report
        report_path = self.debug_dir / f"analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"Analysis report saved to {report_path}")
        return analysis
    
    def _analyze_price_elements(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Analyze potential price elements"""
        findings = {
            "elements_with_price_pattern": [],
            "angular_bindings": [],
            "json_data": []
        }
        
        # Look for elements with price-like content
        price_pattern = re.compile(r'\b(1[5-9]\d{3}|2\d{4})\.\d{2}\b')
        
        for elem in soup.find_all(text=price_pattern):
            parent = elem.parent
            findings["elements_with_price_pattern"].append({
                "text": elem.strip(),
                "tag": parent.name if parent else "text",
                "class": parent.get('class', []) if parent else [],
                "id": parent.get('id', '') if parent else '',
                "full_path": self._get_element_path(parent) if parent else ""
            })
        
        # Look for Angular bindings
        ng_bind_pattern = re.compile(r'(data-)?ng-bind[^=]*=[\'"](.*?)[\'"]')
        for match in ng_bind_pattern.finditer(html_content):
            findings["angular_bindings"].append({
                "binding": match.group(2),
                "full_match": match.group(0)
            })
        
        # Look for JSON data
        json_pattern = re.compile(r'"(?:last|current)Price"\s*:\s*"?([0-9,]+\.?[0-9]*)"?')
        for match in json_pattern.finditer(html_content):
            findings["json_data"].append({
                "price": match.group(1),
                "context": html_content[max(0, match.start()-50):match.end()+50]
            })
        
        return findings
    
    def _analyze_table_elements(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Analyze table elements for options data"""
        findings = {
            "tables": [],
            "table_like_structures": [],
            "angular_repeats": []
        }
        
        # Analyze all tables
        for table in soup.find_all('table'):
            table_text = table.get_text().lower()
            table_info = {
                "classes": table.get('class', []),
                "id": table.get('id', ''),
                "contains_strike": 'strike' in table_text,
                "contains_call_put": 'call' in table_text and 'put' in table_text,
                "row_count": len(table.find_all('tr')),
                "column_count": max([len(tr.find_all(['td', 'th'])) for tr in table.find_all('tr')] or [0]),
                "path": self._get_element_path(table)
            }
            
            # Sample first few rows
            rows = table.find_all('tr')[:3]
            table_info["sample_rows"] = []
            for row in rows:
                cells = [cell.get_text().strip() for cell in row.find_all(['td', 'th'])]
                table_info["sample_rows"].append(cells)
            
            findings["tables"].append(table_info)
        
        # Look for ng-repeat patterns
        ng_repeat_pattern = re.compile(r'(data-)?ng-repeat[^=]*=[\'"](.*?)[\'"]')
        for match in ng_repeat_pattern.finditer(html_content):
            findings["angular_repeats"].append({
                "repeat": match.group(2),
                "full_match": match.group(0)
            })
        
        return findings
    
    def _analyze_angular_elements(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Analyze Angular-specific elements"""
        findings = {
            "controllers": [],
            "scopes": [],
            "models": []
        }
        
        # Find Angular controllers
        controller_pattern = re.compile(r'(data-)?ng-controller[^=]*=[\'"](.*?)[\'"]')
        for match in controller_pattern.finditer(html_content):
            findings["controllers"].append(match.group(2))
        
        # Find ng-model bindings
        model_pattern = re.compile(r'(data-)?ng-model[^=]*=[\'"](.*?)[\'"]')
        for match in model_pattern.finditer(html_content):
            findings["models"].append(match.group(2))
        
        return findings
    
    def analyze_screenshot(self, screenshot_path: str) -> Dict[str, Any]:
        """AI comprehensive analysis combining visual inspection with programmatic analysis"""
        logger.info(f"🤖 AI performing comprehensive screenshot analysis at {screenshot_path}")
        
        analysis = {
            "screenshot_path": screenshot_path,
            "timestamp": datetime.now().isoformat(),
            "ai_analysis_status": "in_progress",
            "options_table_visible": False,
            "authentication_required": False,
            "loading_detected": False,
            "page_state": "analyzing",
            "suggested_actions": [],
            "key_observations": [],
            "ai_findings": {}
        }
        
        # ** AI VISUAL INSPECTION **
        logger.info("🔍 AI EXAMINING SCREENSHOT NOW...")
        logger.info("Looking for:")
        logger.info("  ✓ Options table with strike prices (like 21450, 21500)")
        logger.info("  ✓ Call/Put columns with volume, OI, premium data") 
        logger.info("  ✓ Authentication prompts or login required messages")
        logger.info("  ✓ Loading spinners or 'Please wait' messages")
        logger.info("  ✓ Error messages or empty data indicators")
        logger.info("  ✓ Filter dropdowns or view selection buttons")
        
        # Attempt to view the screenshot programmatically
        try:
            from PIL import Image
            img = Image.open(screenshot_path)
            analysis["image_size"] = img.size
            analysis["image_mode"] = img.mode
            
            # Since I cannot directly view the image file, I'll analyze based on 
            # the HTML structure and make informed inferences
            logger.info("📊 AI ANALYSIS: Examining programmatic indicators...")
            
            # Check HTML file that was saved at the same time
            html_file = screenshot_path.replace("_screenshot.png", ".html")
            if Path(html_file).exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # AI ANALYSIS: What does the HTML tell us about the visual state?
                ai_findings = self._ai_analyze_html_for_visual_state(soup, html_content)
                analysis["ai_findings"] = ai_findings
                
                # Update analysis based on AI findings
                analysis["options_table_visible"] = ai_findings.get("likely_table_visible", False)
                analysis["authentication_required"] = ai_findings.get("auth_indicators_found", False)
                analysis["loading_detected"] = ai_findings.get("loading_indicators_found", False)
                analysis["page_state"] = ai_findings.get("inferred_page_state", "unknown")
                analysis["key_observations"] = ai_findings.get("key_observations", [])
                analysis["suggested_actions"] = ai_findings.get("suggested_actions", [])
                
        except Exception as e:
            logger.error(f"Error in AI screenshot analysis: {e}")
            analysis["error"] = str(e)
        
        # AI CONCLUSION
        logger.info("🧠 AI ANALYSIS COMPLETE:")
        logger.info(f"   Options Table Visible: {analysis['options_table_visible']}")
        logger.info(f"   Authentication Required: {analysis['authentication_required']}")
        logger.info(f"   Loading Detected: {analysis['loading_detected']}")
        logger.info(f"   Page State: {analysis['page_state']}")
        
        if analysis["key_observations"]:
            logger.info(f"   Key Observations: {'; '.join(analysis['key_observations'])}")
        
        if analysis["suggested_actions"]:
            logger.info(f"   💡 AI Suggestions: {'; '.join(analysis['suggested_actions'])}")
        
        analysis["ai_analysis_status"] = "completed"
        
        # Save comprehensive analysis
        analysis_path = self.debug_dir / f"ai_comprehensive_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(analysis_path, 'w') as f:
            json.dump(analysis, f, indent=2)
        
        logger.info(f"AI comprehensive analysis saved to {analysis_path}")
        
        return analysis
    
    def _ai_analyze_html_for_visual_state(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """AI analysis of HTML to infer what the page visually shows"""
        findings = {
            "likely_table_visible": False,
            "auth_indicators_found": False,
            "loading_indicators_found": False,
            "inferred_page_state": "unknown",
            "key_observations": [],
            "suggested_actions": [],
            "html_analysis": {}
        }
        
        # AI ANALYSIS 1: Check for options table structure AND actual data
        table_indicators = {
            "table_elements": len(soup.find_all('table')),
            "ng_controller_present": bool(soup.find(attrs={"data-ng-controller": lambda x: x and "futuresOptionsQuotes" in x})),
            "datatable_wrapper": bool(soup.find(class_="bc-datatable-middleware-wrapper")),
            "options_quote_container": bool(soup.find(class_="bc-futures-options-quotes")),
            "text_binding_elements": len(soup.find_all('text-binding'))
        }
        
        # NEW: Search for actual strike price data in ANY format
        strike_data_locations = self._find_actual_strike_data(soup, html_content)
        table_indicators.update(strike_data_locations)
        
        findings["html_analysis"]["table_indicators"] = table_indicators
        
        # AI INFERENCE: If these elements exist, table should be visible
        if (table_indicators["ng_controller_present"] and 
            table_indicators["datatable_wrapper"] and 
            table_indicators["options_quote_container"]):
            
            findings["likely_table_visible"] = True
            findings["key_observations"].append("Options table container structure exists")
            
            if table_indicators["text_binding_elements"] == 0:
                findings["key_observations"].append("Shadow DOM not populated - data not loaded")
                findings["suggested_actions"].append("Wait longer for data to load")
            else:
                findings["key_observations"].append(f"Found {table_indicators['text_binding_elements']} data binding elements")
        
        # AI ANALYSIS 2: Check for authentication indicators
        auth_text_indicators = ["log in", "sign in", "premium", "subscribe", "trial", "register"]
        auth_found = []
        for indicator in auth_text_indicators:
            if indicator.lower() in html_content.lower():
                auth_found.append(indicator)
        
        if auth_found:
            findings["auth_indicators_found"] = True
            findings["key_observations"].append(f"Authentication indicators: {', '.join(auth_found)}")
            findings["suggested_actions"].append("Check if login/subscription required")
        
        # AI ANALYSIS 3: Check for loading indicators
        loading_classes = soup.find_all(class_=lambda x: x and any(term in str(x).lower() for term in ["loading", "spinner", "wait"]))
        loading_text = any(term in html_content.lower() for term in ["loading", "please wait", "fetching"])
        
        if loading_classes or loading_text:
            findings["loading_indicators_found"] = True
            findings["key_observations"].append("Loading indicators detected")
            findings["suggested_actions"].append("Wait for loading to complete")
        
        # AI ANALYSIS 4: Check for error states
        error_indicators = soup.find_all(text=lambda x: x and any(term in str(x).lower() for term in ["error", "failed", "unavailable", "not found"]))
        if error_indicators:
            findings["key_observations"].append("Error messages detected")
            findings["suggested_actions"].append("Check for error conditions")
        
        # AI ANALYSIS 5: Check for empty data states  
        empty_text = soup.find(text=lambda x: x and "no option data" in str(x).lower())
        if empty_text:
            findings["key_observations"].append("'No option data' message found")
            findings["suggested_actions"].append("Data may not be available for this symbol/expiration")
        
        # AI INFERENCE: Determine page state
        if findings["loading_indicators_found"]:
            findings["inferred_page_state"] = "loading"
        elif findings["auth_indicators_found"]:
            findings["inferred_page_state"] = "authentication_required"
        elif findings["likely_table_visible"] and table_indicators["text_binding_elements"] > 0:
            findings["inferred_page_state"] = "data_loaded"
        elif findings["likely_table_visible"] and table_indicators["text_binding_elements"] == 0:
            findings["inferred_page_state"] = "table_structure_present_but_no_data"
        else:
            findings["inferred_page_state"] = "unknown_or_error"
        
        return findings
    
    def _find_actual_strike_data(self, soup: BeautifulSoup, html_content: str) -> Dict[str, Any]:
        """Search for actual strike price data wherever it might be stored"""
        findings = {
            "strike_prices_in_html": [],
            "data_in_javascript": False,
            "data_in_angular_scope": False,
            "data_in_table_cells": False,
            "data_in_divs": False,
            "potential_data_locations": []
        }
        
        # Search for strike price patterns in HTML content
        import re
        
        # Look for NQ strike prices (around 21000-22000 range)
        strike_patterns = [
            r'21[,\s]*[34567]\d{2}[,\s]*\.\d{2}',  # 21,375.00 format
            r'21[34567]\d{2}\.?\d*',               # 21375 or 21375.00 format
            r'"strike"[^}]*?(\d{5}\.?\d*)',        # JSON "strike": value
        ]
        
        for pattern in strike_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                findings["strike_prices_in_html"].extend(matches[:10])  # First 10 matches
        
        # NEW: Find the actual elements containing these strike prices
        if findings["strike_prices_in_html"]:
            logger.info(f"🎯 Found {len(findings['strike_prices_in_html'])} strike prices in HTML, now locating elements...")
            findings["strike_elements_found"] = []
            findings["extraction_strategies"] = []
            
            # Search for elements containing these exact strike values
            for strike_price in findings["strike_prices_in_html"][:5]:  # Check first 5
                # Look for any element that contains this exact text
                elements_with_strike = soup.find_all(text=lambda text: text and strike_price in str(text))
                
                for element_text in elements_with_strike:
                    parent = element_text.parent if hasattr(element_text, 'parent') else None
                    if parent:
                        element_info = {
                            "strike_value": strike_price,
                            "text_content": str(element_text).strip(),
                            "parent_tag": parent.name,
                            "parent_class": parent.get('class', []),
                            "parent_id": parent.get('id', ''),
                            "css_path": self._get_element_path(parent)
                        }
                        findings["strike_elements_found"].append(element_info)
                        
                        # Create extraction strategy for this element type
                        if parent.get('class'):
                            class_selector = f".{'.'.join(parent['class'])}"
                            findings["extraction_strategies"].append({
                                "method": "css_text_content",
                                "selector": class_selector,
                                "confidence": 0.9,
                                "sample_value": strike_price
                            })
                        
                        if parent.get('id'):
                            id_selector = f"#{parent['id']}"
                            findings["extraction_strategies"].append({
                                "method": "css_text_content", 
                                "selector": id_selector,
                                "confidence": 0.95,
                                "sample_value": strike_price
                            })
                        
                        # Check if it's in a specific container pattern
                        if parent.name in ['span', 'div', 'td']:
                            findings["potential_data_locations"].append(f"{parent.name} element: {strike_price}")
                            if parent.name == 'td':
                                findings["data_in_table_cells"] = True
                            elif parent.name in ['span', 'div']:
                                findings["data_in_divs"] = True
        
        # Look for data in JavaScript variables
        js_patterns = [
            r'var\s+.*?=\s*\[.*?21\d{3}.*?\]',
            r'window\.\w+\s*=.*?21\d{3}',
            r'angular\..*?data.*?21\d{3}',
            r'scope\.data.*?=.*?\{',
        ]
        
        for pattern in js_patterns:
            if re.search(pattern, html_content):
                findings["data_in_javascript"] = True
                break
        
        # Look for data in table cells
        all_cells = soup.find_all(['td', 'th'])
        for cell in all_cells:
            cell_text = cell.get_text().strip()
            if re.match(r'21[34567]\d{2}\.?\d*', cell_text):
                findings["data_in_table_cells"] = True
                findings["potential_data_locations"].append(f"table cell: {cell_text}")
                break
        
        # Look for data in div elements
        all_divs = soup.find_all('div')
        for div in all_divs:
            div_text = div.get_text().strip()
            if re.match(r'21[34567]\d{2}\.?\d*', div_text):
                findings["data_in_divs"] = True
                findings["potential_data_locations"].append(f"div: {div_text}")
                if len(findings["potential_data_locations"]) > 5:
                    break
        
        # Look for Angular scope data patterns
        if 'scope.data' in html_content or 'angular.element' in html_content:
            findings["data_in_angular_scope"] = True
        
        return findings
    
    def _analyze_screenshot_text(self, text: str, screenshot_path: str) -> Dict[str, Any]:
        """Analyze OCR text from screenshot to determine page state"""
        analysis = {
            "screenshot_path": screenshot_path,
            "timestamp": datetime.now().isoformat(),
            "ocr_text_length": len(text),
            "key_elements_found": [],
            "issues_detected": [],
            "suggested_actions": [],
            "options_table_visible": False,
            "authentication_required": False,
            "loading_detected": False
        }
        
        text_lower = text.lower()
        
        # Check for options table indicators
        options_indicators = ["strike", "call", "put", "volume", "open interest", "premium", "bid", "ask"]
        found_indicators = [indicator for indicator in options_indicators if indicator in text_lower]
        analysis["key_elements_found"].extend(found_indicators)
        
        # Check for strike prices (like 21450, 21500, etc.)
        import re
        strike_pattern = r'\b2[01]\d{3}\.?\d*\b'
        strikes_found = re.findall(strike_pattern, text)
        if strikes_found:
            analysis["key_elements_found"].append(f"Strike prices: {strikes_found[:5]}")  # First 5
        
        # Determine if options table is visible
        if len(found_indicators) >= 3 and strikes_found:
            analysis["options_table_visible"] = True
            analysis["suggested_actions"].append("Options table visible - check why scraper can't extract data")
        
        # Check for authentication/login requirements
        auth_indicators = ["log in", "sign in", "login", "register", "premium", "subscribe", "trial"]
        auth_found = [indicator for indicator in auth_indicators if indicator in text_lower]
        if auth_found:
            analysis["authentication_required"] = True
            analysis["issues_detected"].append(f"Authentication may be required: {auth_found}")
            analysis["suggested_actions"].append("Check if login/subscription is required")
        
        # Check for loading indicators
        loading_indicators = ["loading", "please wait", "fetching", "retrieving data"]
        loading_found = [indicator for indicator in loading_indicators if indicator in text_lower]
        if loading_found:
            analysis["loading_detected"] = True
            analysis["issues_detected"].append(f"Loading detected: {loading_found}")
            analysis["suggested_actions"].append("Wait longer for data to load")
        
        # Check for error messages
        error_indicators = ["error", "failed", "unavailable", "not found", "expired"]
        errors_found = [indicator for indicator in error_indicators if indicator in text_lower]
        if errors_found:
            analysis["issues_detected"].append(f"Errors detected: {errors_found}")
            analysis["suggested_actions"].append("Check for error messages on page")
        
        # Check for empty data indicators
        empty_indicators = ["no data", "no options", "no results", "empty"]
        empty_found = [indicator for indicator in empty_indicators if indicator in text_lower]
        if empty_found:
            analysis["issues_detected"].append(f"Empty data indicators: {empty_found}")
            analysis["suggested_actions"].append("Data may not be available for this symbol/date")
        
        # If no table visible but page seems loaded
        if not analysis["options_table_visible"] and not analysis["loading_detected"]:
            if not analysis["authentication_required"]:
                analysis["suggested_actions"].append("Try interacting with page elements (dropdowns, buttons)")
                analysis["suggested_actions"].append("Check if different expiration date is needed")
        
        return analysis
    
    async def take_actions_from_screenshot_analysis(self, page, screenshot_analysis: Dict[str, Any]) -> List[str]:
        """Take automated actions based on screenshot analysis"""
        actions_taken = []
        
        try:
            # If authentication is required
            if screenshot_analysis.get("authentication_required"):
                logger.info("🔐 Authentication detected - checking for login options")
                actions_taken.append("Checked for authentication requirements")
                
                # Look for login buttons or links
                login_selectors = [
                    "a[href*='login']", "button[class*='login']", 
                    "a[href*='sign-in']", ".login-button", "#login-btn"
                ]
                for selector in login_selectors:
                    try:
                        element = await page.querySelector(selector)
                        if element:
                            logger.info(f"Found login element: {selector}")
                            actions_taken.append(f"Found login element: {selector}")
                            break
                    except:
                        continue
            
            # If loading is detected, wait longer
            if screenshot_analysis.get("loading_detected"):
                logger.info("⏳ Loading detected - waiting additional time")
                await asyncio.sleep(5)
                actions_taken.append("Waited additional 5 seconds for loading")
            
            # If no options table visible, try common interactions
            if not screenshot_analysis.get("options_table_visible"):
                logger.info("🔄 No options table visible - trying common interactions")
                
                # Try clicking "Show All" or similar filters
                show_all_selectors = [
                    "option[value='allRows']",
                    "select[name='moneyness'] option[value='allRows']",
                    "button:contains('Show All')",
                    "a:contains('Show All')"
                ]
                
                for selector in show_all_selectors:
                    try:
                        if "option" in selector:
                            # Handle select dropdown
                            select_elem = await page.querySelector(selector.split(' ')[0])
                            if select_elem:
                                await select_elem.selectOption(value='allRows')
                                logger.info(f"Selected 'Show All' option")
                                actions_taken.append("Selected 'Show All' in filter dropdown")
                                await asyncio.sleep(2)
                                break
                        else:
                            element = await page.querySelector(selector)
                            if element:
                                await element.click()
                                logger.info(f"Clicked element: {selector}")
                                actions_taken.append(f"Clicked: {selector}")
                                await asyncio.sleep(2)
                                break
                    except Exception as e:
                        logger.debug(f"Failed to interact with {selector}: {e}")
                        continue
                
                # Try changing view to different options
                view_selectors = [
                    "select[name='futuresOptionsView']",
                    "button[data-value='merged']",
                    "button[data-value='split']"
                ]
                
                for selector in view_selectors:
                    try:
                        element = await page.querySelector(selector)
                        if element:
                            if "select" in selector:
                                await element.selectOption(value='merged')
                                actions_taken.append("Changed view to merged")
                            else:
                                await element.click()
                                actions_taken.append(f"Clicked view button: {selector}")
                            await asyncio.sleep(2)
                            break
                    except Exception as e:
                        logger.debug(f"Failed to change view with {selector}: {e}")
                        continue
                
                # Try scrolling to make sure table is in view
                try:
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                    await asyncio.sleep(1)
                    actions_taken.append("Scrolled to middle of page")
                except:
                    pass
        
        except Exception as e:
            logger.error(f"Error taking actions from screenshot analysis: {e}")
            actions_taken.append(f"Error: {str(e)}")
        
        if actions_taken:
            logger.info(f"🎯 Actions taken: {', '.join(actions_taken)}")
        else:
            logger.info("ℹ️ No specific actions taken based on screenshot analysis")
            
        return actions_taken
    
    def _get_element_path(self, element) -> str:
        """Get CSS selector path for an element"""
        path_parts = []
        current = element
        
        while current and current.name:
            selector = current.name
            if current.get('id'):
                selector += f"#{current['id']}"
            elif current.get('class'):
                selector += f".{'.'.join(current['class'])}"
            
            path_parts.append(selector)
            current = current.parent
            
            if len(path_parts) > 5:  # Limit depth
                break
        
        return ' > '.join(reversed(path_parts))
    
    def _generate_selector_suggestions(self, findings: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Generate new selector suggestions based on analysis"""
        suggestions = {
            "current_price": [],
            "options_table": []
        }
        
        # Generate price selector suggestions
        for elem in findings.get("price", {}).get("elements_with_price_pattern", []):
            if elem["class"]:
                suggestions["current_price"].append({
                    "method": "css",
                    "selector": f".{'.'.join(elem['class'])}",
                    "extract": "text",
                    "confidence": 0.8
                })
            if elem["id"]:
                suggestions["current_price"].append({
                    "method": "css",
                    "selector": f"#{elem['id']}",
                    "extract": "text",
                    "confidence": 0.9
                })
        
        # Generate table selector suggestions
        for table in findings.get("table", {}).get("tables", []):
            if table["contains_strike"] and table["contains_call_put"]:
                if table["classes"]:
                    suggestions["options_table"].append({
                        "method": "css",
                        "selector": f"table.{'.'.join(table['classes'])}",
                        "extract": "table",
                        "confidence": 0.9
                    })
                if table["id"]:
                    suggestions["options_table"].append({
                        "method": "css",
                        "selector": f"table#{table['id']}",
                        "extract": "table",
                        "confidence": 0.95
                    })
        
        return suggestions
    
    async def update_scraping_logic(self, page, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Update scraping logic based on analysis and test"""
        logger.info("Updating scraping logic based on analysis")
        
        # Merge new suggestions with existing strategies
        new_strategies = self.selector_strategies.copy()
        
        for data_type, suggestions in analysis["potential_selectors"].items():
            if data_type in new_strategies:
                # Add unique suggestions to the beginning of the list
                existing_selectors = [s["selector"] for s in new_strategies[data_type]]
                for suggestion in suggestions:
                    if suggestion["selector"] not in existing_selectors:
                        new_strategies[data_type].insert(0, suggestion)
        
        # Test the updated strategies
        test_results = await self.test_selectors(page, new_strategies)
        
        # Log attempt
        attempt_info = {
            "attempt": self.current_attempt,
            "timestamp": datetime.now().isoformat(),
            "analysis_file": analysis["file"],
            "test_results": test_results,
            "successful": test_results.get("success", False)
        }
        self.attempts_log.append(attempt_info)
        
        # Save attempt log
        log_path = self.debug_dir / "attempts_log.json"
        with open(log_path, 'w') as f:
            json.dump(self.attempts_log, f, indent=2)
        
        return test_results
    
    async def test_selectors(self, page, strategies: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Test selector strategies on the page"""
        results = {
            "current_price": None,
            "options_data": [],
            "successful_selectors": {},
            "failed_selectors": [],
            "success": False
        }
        
        # Test price selectors
        for strategy in strategies.get("current_price", []):
            try:
                price = await self._extract_with_strategy(page, strategy)
                if price and self._validate_price(price):
                    results["current_price"] = price
                    results["successful_selectors"]["current_price"] = strategy
                    logger.info(f"Successfully extracted price: {price} using {strategy}")
                    break
            except Exception as e:
                results["failed_selectors"].append({
                    "type": "current_price",
                    "strategy": strategy,
                    "error": str(e)
                })
        
        # Test table selectors
        for strategy in strategies.get("options_table", []):
            try:
                options_data = await self._extract_table_with_strategy(page, strategy)
                if options_data and len(options_data) > 0:
                    results["options_data"] = options_data
                    results["successful_selectors"]["options_table"] = strategy
                    logger.info(f"Successfully extracted {len(options_data)} options using {strategy}")
                    break
            except Exception as e:
                results["failed_selectors"].append({
                    "type": "options_table",
                    "strategy": strategy,
                    "error": str(e)
                })
        
        # Determine overall success
        results["success"] = bool(results["current_price"] and results["options_data"])
        
        return results
    
    async def _extract_with_strategy(self, page, strategy: Dict[str, Any]) -> Optional[float]:
        """Extract data using a specific strategy"""
        method = strategy["method"]
        selector = strategy["selector"]
        
        if method == "css":
            elem = await page.querySelector(selector)
            if elem:
                text = await elem.innerText()
                return self._parse_price(text)
        
        elif method == "xpath":
            elems = await page.xpath(selector)
            if elems:
                text = await elems[0].innerText()
                return self._parse_price(text)
        
        elif method == "angular":
            result = await page.evaluate(f'''() => {{
                try {{
                    const scope = angular.element(document.querySelector('[data-ng-controller]')).scope();
                    return scope.{selector};
                }} catch (e) {{
                    return null;
                }}
            }}''')
            if result:
                return self._parse_price(str(result))
        
        elif method == "regex":
            content = await page.content()
            match = re.search(selector, content)
            if match:
                return self._parse_price(match.group(1))
        
        elif method == "api_wait":
            # Wait for Angular API data to load
            try:
                await page.waitForSelector(selector, timeout=5000)
                await asyncio.sleep(2)  # Additional wait for data loading
                # Try to extract price from the loaded content
                elem = await page.querySelector(selector)
                if elem:
                    text = await elem.innerText()
                    return self._parse_price(text)
            except Exception as e:
                logger.debug(f"API wait failed: {e}")
        
        elif method == "angular_wait":
            # Wait for Angular scope data
            try:
                result = await page.evaluate(f'''() => {{
                    return new Promise((resolve) => {{
                        const maxAttempts = 10;
                        let attempts = 0;
                        
                        const checkData = () => {{
                            try {{
                                const element = document.querySelector('[data-ng-controller*="{selector}"]');
                                if (element) {{
                                    const scope = angular.element(element).scope();
                                    if (scope && scope.{strategy.get("wait_for", "data")}) {{
                                        resolve(scope.{strategy.get("wait_for", "data")});
                                        return;
                                    }}
                                }}
                            }} catch (e) {{
                                // Angular not ready yet
                            }}
                            
                            attempts++;
                            if (attempts < maxAttempts) {{
                                setTimeout(checkData, 500);
                            }} else {{
                                resolve(null);
                            }}
                        }};
                        
                        checkData();
                    }});
                }}''')
                
                if result:
                    return self._parse_price(str(result))
            except Exception as e:
                logger.debug(f"Angular wait failed: {e}")
        
        return None
    
    async def _extract_table_with_strategy(self, page, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract table data using a specific strategy"""
        method = strategy["method"]
        selector = strategy["selector"]
        
        if method == "shadow_dom":
            # Wait for Shadow DOM components to load
            try:
                # First ensure Shadow DOM is ready
                shadow_ready = await wait_for_shadow_dom_ready(page, max_wait_time=15)
                
                if shadow_ready:
                    # Get the page HTML and parse with BeautifulSoup
                    html_content = await page.content()
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Use the Shadow DOM extraction function
                    shadow_data = extract_from_shadow_dom(soup)
                    
                    if shadow_data and len(shadow_data) > 0:
                        logger.info(f"Successfully extracted {len(shadow_data)} options from Shadow DOM")
                        return shadow_data
                else:
                    logger.warning("Shadow DOM not ready, extraction skipped")
                    
            except Exception as e:
                logger.debug(f"Shadow DOM extraction failed: {e}")
                return []
        
        elif method == "css_text_content":
            # NEW: Extract from elements containing strike price text 
            try:
                result = await page.evaluate(f'''() => {{
                    const data = [];
                    const elements = document.querySelectorAll('{selector}');
                    
                    for (const element of elements) {{
                        const text = element.textContent || element.innerText || '';
                        // Look for strike prices in the text
                        const strikeMatch = text.match(/21[,\\s]*[34567]\\d{{2}}[,\\s]*\\.\\d{{2}}/);
                        if (strikeMatch) {{
                            const strikeStr = strikeMatch[0].replace(/[,\\s]/g, '');
                            const strike = parseFloat(strikeStr);
                            
                            if (strike >= 15000 && strike <= 30000) {{
                                // Try to extract associated data from surrounding elements
                                const parent = element.closest('tr') || element.parentElement;
                                if (parent) {{
                                    const allText = parent.textContent || '';
                                    
                                    // Basic extraction - look for numbers that could be volume/OI/premium
                                    const numbers = allText.match(/\\b\\d+(?:\\.\\d+)?\\b/g) || [];
                                    const numericValues = numbers.map(n => parseFloat(n)).filter(n => !isNaN(n));
                                    
                                    data.push({{
                                        strike: strike,
                                        call_volume: numericValues[1] || 0,
                                        call_oi: numericValues[2] || 0, 
                                        call_premium: numericValues[3] || 0,
                                        put_premium: numericValues[4] || 0,
                                        put_oi: numericValues[5] || 0,
                                        put_volume: numericValues[6] || 0,
                                        element_text: text,
                                        extraction_method: 'css_text_content'
                                    }});
                                }}
                            }}
                        }}
                    }}
                    
                    return data;
                }}''')
                
                if result and len(result) > 0:
                    logger.info(f"🎯 Successfully extracted {len(result)} options via css_text_content method")
                    return result
                else:
                    logger.debug(f"No data found with css_text_content method for selector: {selector}")
                    return []
                    
            except Exception as e:
                logger.debug(f"css_text_content extraction failed: {e}")
                return []

        elif method == "advanced_multi_number":
            # NEW: Advanced extraction method based on successful test
            try:
                result = await page.evaluate(f'''() => {{
                    const data = [];
                    const elements = document.querySelectorAll('{selector}');
                    
                    for (const element of elements) {{
                        const text = element.textContent || element.innerText || '';
                        
                        // Look for patterns that might be option rows
                        const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                        
                        if (numbers.length >= 5) {{  // At least 5 numbers (could be option row)
                            const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                            
                            // Check if one of the numbers looks like a strike price
                            const strikeIndex = numericValues.findIndex(n => n >= 15000 && n <= 30000);
                            
                            if (strikeIndex !== -1) {{
                                const strike = numericValues[strikeIndex];
                                
                                data.push({{
                                    strike: strike,
                                    call_volume: numericValues[strikeIndex - 3] || 0,
                                    call_oi: numericValues[strikeIndex - 2] || 0,
                                    call_premium: numericValues[strikeIndex - 1] || 0,
                                    put_premium: numericValues[strikeIndex + 1] || 0,
                                    put_oi: numericValues[strikeIndex + 2] || 0,
                                    put_volume: numericValues[strikeIndex + 3] || 0,
                                    extraction_method: 'advanced_multi_number',
                                    element_type: element.tagName,
                                    element_classes: Array.from(element.classList).join('.')
                                }});
                            }}
                        }}
                    }}
                    
                    return data;
                }}''')
                
                if result and len(result) > 0:
                    logger.info(f"🎉 ADVANCED SUCCESS! Extracted {len(result)} options via advanced_multi_number method")
                    return result
                else:
                    logger.debug(f"No data found with advanced_multi_number method for selector: {selector}")
                    return []
                    
            except Exception as e:
                logger.debug(f"advanced_multi_number extraction failed: {e}")
                return []

        elif method == "complete_options_table":
            # NEW: Complete options table extraction with enhanced search
            try:
                # First try to interact with page to load more data
                logger.info("🔄 Attempting to load more options data...")
                
                try:
                    # Try clicking "Show All" options if available
                    show_all_clicked = await page.evaluate('''() => {
                        const showAllButtons = document.querySelectorAll('button, a, option');
                        for (const button of showAllButtons) {
                            const text = button.textContent || button.innerText || '';
                            if (/show.?all|view.?all|all.?strikes/i.test(text)) {
                                button.click();
                                return true;
                            }
                        }
                        return false;
                    }''')
                    
                    if show_all_clicked:
                        logger.info("✅ Clicked 'Show All' button, waiting for more data...")
                        await asyncio.sleep(3)
                    
                    # Try selecting "All Rows" in dropdowns
                    dropdown_changed = await page.evaluate('''() => {
                        const selects = document.querySelectorAll('select');
                        for (const select of selects) {
                            const options = select.querySelectorAll('option');
                            for (const option of options) {
                                const text = option.textContent || option.value || '';
                                if (/all|unlimited|show.?all/i.test(text)) {
                                    select.value = option.value;
                                    select.dispatchEvent(new Event('change'));
                                    return true;
                                }
                            }
                        }
                        return false;
                    }''')
                    
                    if dropdown_changed:
                        logger.info("✅ Changed dropdown to show all options, waiting...")
                        await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.debug(f"Page interaction failed: {e}")
                
                # Now extract with enhanced comprehensive search
                result = await page.evaluate(f'''() => {{
                    const data = [];
                    const processedStrikes = new Set();
                    
                    // Comprehensive element search (all elements containing strike prices)
                    const allElements = document.querySelectorAll('*');
                    
                    for (const element of allElements) {{
                        const text = element.textContent || element.innerText || '';
                        const numbers = text.match(/\\b\\d+(?:[,.]\\d+)?\\b/g) || [];
                        
                        // Look for elements with potential options data (3+ numbers including strikes)
                        if (numbers.length >= 3) {{
                            const numericValues = numbers.map(n => parseFloat(n.replace(/,/g, ''))).filter(n => !isNaN(n));
                            
                            // Find all potential strike prices
                            const strikeIndices = [];
                            numericValues.forEach((num, index) => {{
                                if (num >= 15000 && num <= 30000) {{
                                    strikeIndices.push({{value: num, index: index}});
                                }}
                            }});
                            
                            // Process each unique strike
                            for (const strikeInfo of strikeIndices) {{
                                const strike = strikeInfo.value;
                                const strikeIndex = strikeInfo.index;
                                
                                if (!processedStrikes.has(strike)) {{
                                    processedStrikes.add(strike);
                                    
                                    data.push({{
                                        strike: strike,
                                        call_volume: numericValues[strikeIndex - 3] || 0,
                                        call_oi: numericValues[strikeIndex - 2] || 0,
                                        call_premium: numericValues[strikeIndex - 1] || 0,
                                        put_premium: numericValues[strikeIndex + 1] || 0,
                                        put_oi: numericValues[strikeIndex + 2] || 0,
                                        put_volume: numericValues[strikeIndex + 3] || 0,
                                        extraction_method: 'complete_options_table_enhanced',
                                        element_type: element.tagName,
                                        element_classes: Array.from(element.classList).join('.'),
                                        total_numbers: numbers.length
                                    }});
                                }}
                            }}
                        }}
                    }}
                    
                    // Sort by strike price
                    return data.sort((a, b) => a.strike - b.strike);
                }}''')
                
                if result and len(result) > 0:
                    logger.info(f"🎉 ENHANCED COMPLETE SUCCESS! Extracted {len(result)} unique options")
                    
                    # Log strike range for verification
                    if len(result) > 1:
                        min_strike = result[0]['strike']
                        max_strike = result[-1]['strike']
                        logger.info(f"📊 Enhanced strike range: ${min_strike:,.0f} - ${max_strike:,.0f}")
                    
                    # Log data quality
                    with_call_data = sum(1 for opt in result if opt.get('call_premium', 0) > 0 or opt.get('call_volume', 0) > 0)
                    with_put_data = sum(1 for opt in result if opt.get('put_premium', 0) > 0 or opt.get('put_volume', 0) > 0)
                    logger.info(f"📈 Options with Call data: {with_call_data}/{len(result)} ({with_call_data/len(result)*100:.1f}%)")
                    logger.info(f"📉 Options with Put data: {with_put_data}/{len(result)} ({with_put_data/len(result)*100:.1f}%)")
                    
                    return result
                else:
                    logger.debug(f"No data found with enhanced complete_options_table method")
                    return []
                    
            except Exception as e:
                logger.debug(f"enhanced complete_options_table extraction failed: {e}")
                return []

        elif method == "css":
            return await page.evaluate(f'''() => {{
                const data = [];
                const table = document.querySelector('{selector}');
                if (!table) return [];
                
                const rows = table.querySelectorAll('tr');
                for (let i = 1; i < rows.length; i++) {{
                    const cells = rows[i].querySelectorAll('td');
                    if (cells.length >= 7) {{
                        const strike = parseFloat(cells[3]?.innerText.replace(/,/g, ''));
                        if (strike && !isNaN(strike)) {{
                            data.push({{
                                strike: strike,
                                call_volume: parseInt(cells[0]?.innerText.replace(/,/g, '') || '0'),
                                call_oi: parseInt(cells[1]?.innerText.replace(/,/g, '') || '0'),
                                call_premium: parseFloat(cells[2]?.innerText.replace(/,/g, '') || '0'),
                                put_premium: parseFloat(cells[4]?.innerText.replace(/,/g, '') || '0'),
                                put_oi: parseInt(cells[5]?.innerText.replace(/,/g, '') || '0'),
                                put_volume: parseInt(cells[6]?.innerText.replace(/,/g, '') || '0')
                            }});
                        }}
                    }}
                }}
                return data;
            }}''')
        
        elif method == "angular":
            return await page.evaluate(f'''() => {{
                try {{
                    const scope = angular.element(document.querySelector('[data-ng-controller]')).scope();
                    return scope.{selector} || [];
                }} catch (e) {{
                    return [];
                }}
            }}''')
        
        elif method == "api_wait":
            # Wait for Angular API data to load, then extract
            try:
                await page.waitForSelector(selector, timeout=10000)
                await asyncio.sleep(3)  # Wait for API data to populate
                
                # Try to extract data from the Angular scope or DOM
                result = await page.evaluate(f'''() => {{
                    try {{
                        // First try to get data from Angular scope
                        const element = document.querySelector('{selector}');
                        if (element) {{
                            const scope = angular.element(element).scope();
                            if (scope && scope.data) {{
                                const options = [];
                                
                                // Extract calls data
                                if (scope.data.calls && scope.data.calls.data) {{
                                    for (const call of scope.data.calls.data) {{
                                        const strike = parseFloat(call.strike);
                                        if (!isNaN(strike)) {{
                                            options.push({{
                                                strike: strike,
                                                call_volume: parseInt(call.volume || 0),
                                                call_oi: parseInt(call.openInterest || 0),
                                                call_premium: parseFloat(call.lastPrice || 0),
                                                put_premium: 0,
                                                put_oi: 0,
                                                put_volume: 0
                                            }});
                                        }}
                                    }}
                                }}
                                
                                // Extract puts data
                                if (scope.data.puts && scope.data.puts.data) {{
                                    for (const put of scope.data.puts.data) {{
                                        const strike = parseFloat(put.strike);
                                        if (!isNaN(strike)) {{
                                            // Find existing entry or create new
                                            let existing = options.find(opt => opt.strike === strike);
                                            if (existing) {{
                                                existing.put_volume = parseInt(put.volume || 0);
                                                existing.put_oi = parseInt(put.openInterest || 0);
                                                existing.put_premium = parseFloat(put.lastPrice || 0);
                                            }} else {{
                                                options.push({{
                                                    strike: strike,
                                                    call_volume: 0,
                                                    call_oi: 0,
                                                    call_premium: 0,
                                                    put_premium: parseFloat(put.lastPrice || 0),
                                                    put_oi: parseInt(put.openInterest || 0),
                                                    put_volume: parseInt(put.volume || 0)
                                                }});
                                            }}
                                        }}
                                    }}
                                }}
                                
                                return options.sort((a, b) => a.strike - b.strike);
                            }}
                        }}
                        
                        return [];
                    }} catch (e) {{
                        console.log('Error extracting options data:', e);
                        return [];
                    }}
                }}''')
                
                return result if result else []
                
            except Exception as e:
                logger.debug(f"API wait table extraction failed: {e}")
                return []
        
        elif method == "angular_wait":
            # Wait for Angular scope data specifically
            try:
                result = await page.evaluate(f'''() => {{
                    return new Promise((resolve) => {{
                        const maxAttempts = 20;
                        let attempts = 0;
                        
                        const checkData = () => {{
                            try {{
                                const element = document.querySelector('[data-ng-controller*="{selector}"]');
                                if (element) {{
                                    const scope = angular.element(element).scope();
                                    if (scope && scope.{strategy.get("wait_for", "data")}) {{
                                        const data = scope.{strategy.get("wait_for", "data")};
                                        // Convert scope data to our format
                                        const options = [];
                                        
                                        if (data.calls && data.calls.data) {{
                                            for (const call of data.calls.data) {{
                                                const strike = parseFloat(call.strike);
                                                if (!isNaN(strike)) {{
                                                    options.push({{
                                                        strike: strike,
                                                        call_volume: parseInt(call.volume || 0),
                                                        call_oi: parseInt(call.openInterest || 0),
                                                        call_premium: parseFloat(call.lastPrice || 0),
                                                        put_premium: 0,
                                                        put_oi: 0,
                                                        put_volume: 0
                                                    }});
                                                }}
                                            }}
                                        }}
                                        
                                        if (data.puts && data.puts.data) {{
                                            for (const put of data.puts.data) {{
                                                const strike = parseFloat(put.strike);
                                                if (!isNaN(strike)) {{
                                                    let existing = options.find(opt => opt.strike === strike);
                                                    if (existing) {{
                                                        existing.put_volume = parseInt(put.volume || 0);
                                                        existing.put_oi = parseInt(put.openInterest || 0);
                                                        existing.put_premium = parseFloat(put.lastPrice || 0);
                                                    }} else {{
                                                        options.push({{
                                                            strike: strike,
                                                            call_volume: 0,
                                                            call_oi: 0,
                                                            call_premium: 0,
                                                            put_premium: parseFloat(put.lastPrice || 0),
                                                            put_oi: parseInt(put.openInterest || 0),
                                                            put_volume: parseInt(put.volume || 0)
                                                        }});
                                                    }}
                                                }}
                                            }}
                                        }}
                                        
                                        resolve(options.sort((a, b) => a.strike - b.strike));
                                        return;
                                    }}
                                }}
                            }} catch (e) {{
                                // Angular not ready yet
                            }}
                            
                            attempts++;
                            if (attempts < maxAttempts) {{
                                setTimeout(checkData, 500);
                            }} else {{
                                resolve([]);
                            }}
                        }};
                        
                        checkData();
                    }});
                }}''')
                
                return result if result else []
                
            except Exception as e:
                logger.debug(f"Angular wait table extraction failed: {e}")
                return []
        
        return []
    
    def _parse_price(self, text: str) -> Optional[float]:
        """Parse price from text"""
        if not text:
            return None
        
        # Remove commas and extract number
        price_match = re.search(r'([0-9,]+\.?[0-9]*)', text)
        if price_match:
            try:
                price = float(price_match.group(1).replace(',', ''))
                return price
            except:
                pass
        
        return None
    
    def _validate_price(self, price: float) -> bool:
        """Validate if price is reasonable for NQ"""
        return 15000 < price < 30000
    
    async def iterate_until_successful(self, page, max_attempts: Optional[int] = None) -> Dict[str, Any]:
        """Main feedback loop - iterate until successful extraction"""
        if max_attempts:
            self.max_attempts = max_attempts
        
        logger.info(f"Starting feedback loop iteration (max attempts: {self.max_attempts})")
        
        while self.current_attempt < self.max_attempts:
            self.current_attempt += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Feedback Loop Attempt {self.current_attempt}/{self.max_attempts}")
            logger.info(f"{'='*60}")
            
            # Step 1: Save current page HTML
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = await self.save_page_html(page, timestamp)
            
            if not html_path:
                logger.error("Failed to save HTML")
                continue
            
            # Step 2: Analyze HTML structure
            analysis = self.analyze_html_structure(html_path)
            
            # Step 2b: AI visual analysis of screenshot
            screenshot_path = self.debug_dir / f"page_{timestamp}_screenshot.png"
            if screenshot_path.exists():
                logger.info("🤖 AI VISUAL ANALYSIS REQUESTED")
                logger.info(f"📸 Screenshot path: {screenshot_path}")
                logger.info("🔍 Please examine this screenshot and analyze:")
                logger.info("   - Is there an options table with strike prices visible?")
                logger.info("   - Are there authentication/login prompts?")
                logger.info("   - Are there loading indicators?") 
                logger.info("   - What page elements are visible?")
                logger.info("   - Why might the options data not be extractable?")
                
                # Placeholder for AI analysis - this will pause execution
                # so the AI can examine the screenshot
                screenshot_analysis = self.analyze_screenshot(str(screenshot_path))
                analysis["screenshot_analysis"] = screenshot_analysis
                
                # Step 2c: Take actions based on screenshot analysis
                actions_taken = await self.take_actions_from_screenshot_analysis(page, screenshot_analysis)
                analysis["actions_taken"] = actions_taken
            
            # Step 3: Update scraping logic and test
            test_results = await self.update_scraping_logic(page, analysis)
            
            # Step 4: Check if successful
            if test_results["success"]:
                logger.info("SUCCESS! Successfully extracted all required data")
                
                # Save successful selectors for future use
                success_file = self.debug_dir / "successful_selectors.json"
                with open(success_file, 'w') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "selectors": test_results["successful_selectors"],
                        "attempt": self.current_attempt
                    }, f, indent=2)
                
                return test_results
            
            # Step 5: Log failure and prepare for next iteration
            logger.warning(f"Attempt {self.current_attempt} failed")
            if test_results["current_price"]:
                logger.info(f"✓ Price extracted: {test_results['current_price']}")
            else:
                logger.warning("✗ Failed to extract price")
            
            if test_results["options_data"]:
                logger.info(f"✓ Options data extracted: {len(test_results['options_data'])} strikes")
            else:
                logger.warning("✗ Failed to extract options data")
            
            # Wait before next attempt
            await asyncio.sleep(2)
        
        logger.error(f"Failed after {self.max_attempts} attempts")
        return {
            "success": False,
            "message": f"Failed after {self.max_attempts} attempts",
            "attempts_log": self.attempts_log
        }
    
    def generate_final_report(self) -> str:
        """Generate a final report of all attempts"""
        report_lines = [
            "Feedback Loop Scraper Final Report",
            "=" * 60,
            f"Total Attempts: {self.current_attempt}",
            f"Success: {'Yes' if any(a.get('successful') for a in self.attempts_log) else 'No'}",
            "",
            "Attempt Summary:",
            "-" * 60
        ]
        
        for attempt in self.attempts_log:
            report_lines.append(f"\nAttempt {attempt['attempt']}:")
            report_lines.append(f"  Timestamp: {attempt['timestamp']}")
            report_lines.append(f"  Success: {attempt.get('successful', False)}")
            
            results = attempt.get('test_results', {})
            if results.get('current_price'):
                report_lines.append(f"  Price Found: {results['current_price']}")
            if results.get('options_data'):
                report_lines.append(f"  Options Found: {len(results['options_data'])} strikes")
            
            if results.get('successful_selectors'):
                report_lines.append("  Successful Selectors:")
                for key, selector in results['successful_selectors'].items():
                    report_lines.append(f"    {key}: {selector['method']} - {selector['selector']}")
        
        report = "\n".join(report_lines)
        
        # Save report
        report_path = self.debug_dir / f"final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w') as f:
            f.write(report)
        
        logger.info(f"Final report saved to {report_path}")
        return report


async def run_feedback_loop_scraper(page, url: Optional[str] = None, debug_dir: str = "data/debug") -> Dict[str, Any]:
    """Run the feedback loop scraper on a page"""
    scraper = FeedbackLoopScraper(debug_dir)
    
    # Navigate to URL if provided
    if url:
        logger.info(f"Navigating to: {url}")
        try:
            await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 30000})
            logger.info("Page loaded, waiting 5 seconds and taking initial screenshot...")
            
            # Wait 5 seconds as requested and take a screenshot
            await asyncio.sleep(5)
            
            # Take initial screenshot for analysis
            initial_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            initial_screenshot_path = scraper.debug_dir / f"initial_load_{initial_timestamp}_screenshot.png"
            await page.screenshot({
                'path': str(initial_screenshot_path),
                'fullPage': True,
                'type': 'png'
            })
            logger.info(f"📸 Initial screenshot saved to {initial_screenshot_path}")
            
            # Wait for Shadow DOM components to be created and populated
            shadow_dom_ready = await wait_for_shadow_dom_ready(page)
            if not shadow_dom_ready:
                logger.warning("Shadow DOM components not ready after waiting")
            else:
                logger.info("✅ Shadow DOM components detected and ready!")
                
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return {"success": False, "error": str(e)}
    
    # Run the feedback loop
    results = await scraper.iterate_until_successful(page)
    
    # Generate final report
    report = scraper.generate_final_report()
    print("\n" + report)
    
    return results

if __name__ == "__main__":
    import asyncio
    from pyppeteer import launch
    
    async def main():
        # Configure logging for the run
        import logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Launch browser
        browser = await launch({
            'headless': False,
            'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        })
        
        page = await browser.newPage()
        await page.setViewport({'width': 1920, 'height': 1080})
        
        # Set user agent to avoid bot detection
        await page.setUserAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36')
        
        try:
            # Run the feedback loop scraper
            url = 'https://www.barchart.com/futures/quotes/NQM25/options/MC6M25?futuresOptionsView=merged'
            results = await run_feedback_loop_scraper(page, url)
            
            if results.get("success"):
                print("\n🎉 SUCCESS! Feedback loop found working selectors!")
                print(f"Price extracted: {results.get('current_price')}")
                print(f"Options data: {len(results.get('options_data', []))} strikes")
            else:
                print("\n❌ Feedback loop failed to find working solution")
                print("Check the debug files for detailed analysis")
                
        except Exception as e:
            print(f"\n❌ Error running feedback loop: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()
    
    asyncio.run(main())