#!/usr/bin/env python3
"""
OCR Text Extractor for Barchart Screenshots
Supports both real OCR (when available) and mock extraction for development
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import OCR libraries
OCR_AVAILABLE = False
OCR_ENGINE = None

try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
    OCR_ENGINE = "pytesseract"
    logger.info("✅ PyTesseract OCR available")
except ImportError:
    try:
        import easyocr
        OCR_AVAILABLE = True
        OCR_ENGINE = "easyocr"
        logger.info("✅ EasyOCR available")
    except ImportError:
        logger.warning("⚠️  No OCR library available. Install pytesseract or easyocr for real OCR")
        logger.warning("   pip install pytesseract pillow")
        logger.warning("   Also install Tesseract-OCR: https://github.com/tesseract-ocr/tesseract")


class OCRExtractor:
    """Extract text from Barchart options screenshots"""
    
    def __init__(self):
        self.ocr_available = OCR_AVAILABLE
        self.ocr_engine = OCR_ENGINE
        self.reader = None
        
        if OCR_ENGINE == "easyocr":
            self.reader = easyocr.Reader(['en'])
    
    def extract_text_from_screenshot(self, image_path: str) -> Dict[str, Any]:
        """
        Extract text from screenshot using OCR or mock data
        
        Returns:
            Dict containing:
            - success: bool
            - text: extracted text
            - method: 'ocr' or 'mock'
            - contracts: list of parsed contract data
        """
        try:
            if self.ocr_available:
                return self._extract_with_ocr(image_path)
            else:
                return self._extract_mock_data(image_path)
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": "failed"
            }
    
    def _extract_with_ocr(self, image_path: str) -> Dict[str, Any]:
        """Extract text using real OCR"""
        try:
            if self.ocr_engine == "pytesseract":
                # Use pytesseract
                image = Image.open(image_path)
                text = pytesseract.image_to_string(image)
                
                # Also try to get data as a dataframe for better table parsing
                try:
                    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
                    return {
                        "success": True,
                        "text": text,
                        "structured_data": data,
                        "method": "pytesseract",
                        "contracts": self._parse_ocr_text(text, data)
                    }
                except:
                    return {
                        "success": True,
                        "text": text,
                        "method": "pytesseract",
                        "contracts": self._parse_ocr_text(text)
                    }
                    
            elif self.ocr_engine == "easyocr":
                # Use easyocr
                result = self.reader.readtext(image_path)
                text = '\n'.join([item[1] for item in result])
                
                return {
                    "success": True,
                    "text": text,
                    "raw_results": result,
                    "method": "easyocr",
                    "contracts": self._parse_ocr_text(text)
                }
                
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "method": self.ocr_engine
            }
    
    def _extract_mock_data(self, image_path: str) -> Dict[str, Any]:
        """
        Generate mock data based on the screenshot we saw
        This simulates OCR output for development
        """
        # Mock data based on the actual screenshot content
        mock_text = """Nasdaq 100 E-Mini Sep '25 (NQU25)
22,836.25 +84.75 (+0.37%)
OPTIONS PRICES for Mon, Jun 30th, 2025

Calls
Strike      Open        High        Low         Last        Change      Bid         Ask         Volume      Open Int    Premium     Time
3,500.00C   N/A         19,244.75   19,244.75   19,244.75   +84.50      19,300.00   19,358.75   N/A         N/A         384,895.00  06/27/25
4,000.00C   N/A         18,744.75   18,744.75   18,744.75s  +84.25      18,800.00   18,858.75   N/A         N/A         374,895.00  06/27/25
4,500.00C   N/A         18,245.00   18,245.00   18,245.00s  +84.25      18,300.00   18,358.75   N/A         N/A         364,900.00  06/27/25
5,000.00C   N/A         17,745.25   17,745.25   17,745.25s  +84.25      17,800.00   17,858.75   N/A         N/A         354,905.00  06/27/25
5,500.00C   N/A         17,245.50   17,245.50   17,245.50s  +84.25      17,300.00   17,358.75   N/A         N/A         344,910.00  06/27/25
6,000.00C   N/A         16,745.50   16,745.50   16,745.50s  +84.00      16,800.00   16,858.75   N/A         N/A         334,910.00  06/27/25
6,500.00C   N/A         16,245.75   16,245.75   16,245.75s  +84.25      16,300.00   16,358.75   N/A         N/A         324,915.00  06/27/25"""
        
        # Parse the mock text into contracts
        contracts = self._parse_mock_contracts(mock_text)
        
        return {
            "success": True,
            "text": mock_text,
            "method": "mock",
            "contracts": contracts,
            "warning": "Using mock data - install pytesseract for real OCR"
        }
    
    def _parse_mock_contracts(self, text: str) -> List[Dict[str, Any]]:
        """Parse mock text into contract format"""
        contracts = []
        lines = text.split('\n')
        
        # Find the data rows (after "Strike" header)
        data_started = False
        for line in lines:
            if 'Strike' in line and 'Open' in line:
                data_started = True
                continue
                
            if data_started and line.strip():
                # Parse contract line
                parts = line.split()
                if len(parts) >= 12:
                    try:
                        contract = {
                            "strike": self._parse_strike(parts[0]),
                            "type": "Call" if 'C' in parts[0] else "Put",
                            "open": self._parse_price(parts[1]),
                            "high": self._parse_price(parts[2]),
                            "low": self._parse_price(parts[3]),
                            "last": self._parse_price(parts[4]),
                            "change": self._parse_price(parts[5]),
                            "bid": self._parse_price(parts[6]),
                            "ask": self._parse_price(parts[7]),
                            "volume": self._parse_volume(parts[8]),
                            "open_interest": self._parse_volume(parts[9]),
                            "premium": self._parse_price(parts[10]),
                            "time": parts[11] if len(parts) > 11 else None
                        }
                        contracts.append(contract)
                    except Exception as e:
                        logger.warning(f"Failed to parse line: {line}, error: {e}")
        
        return contracts
    
    def _parse_ocr_text(self, text: str, structured_data: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Parse OCR text into structured contract data"""
        contracts = []
        
        # Try to use structured data if available (pytesseract)
        if structured_data:
            return self._parse_structured_ocr_data(structured_data)
        
        # Otherwise parse raw text
        lines = text.split('\n')
        
        # Look for contract data patterns
        # Pattern: strike price with C/P, followed by prices and volumes
        contract_pattern = r'(\d{1,2},?\d{3}\.\d{2}[CP])\s+'
        
        for line in lines:
            if re.search(contract_pattern, line):
                try:
                    contract = self._parse_contract_line(line)
                    if contract:
                        contracts.append(contract)
                except Exception as e:
                    logger.debug(f"Failed to parse line: {line}, error: {e}")
        
        return contracts
    
    def _parse_structured_ocr_data(self, data: Dict) -> List[Dict[str, Any]]:
        """Parse structured OCR data from pytesseract"""
        contracts = []
        
        # Group text by line numbers
        lines = {}
        for i, text in enumerate(data['text']):
            if text.strip():
                line_num = data['line_num'][i]
                if line_num not in lines:
                    lines[line_num] = []
                lines[line_num].append({
                    'text': text,
                    'left': data['left'][i],
                    'top': data['top'][i]
                })
        
        # Process each line
        for line_num, words in sorted(lines.items()):
            line_text = ' '.join([w['text'] for w in sorted(words, key=lambda x: x['left'])])
            
            # Check if this looks like a contract line
            if re.search(r'\d{1,2},?\d{3}\.\d{2}[CP]', line_text):
                try:
                    contract = self._parse_contract_line(line_text)
                    if contract:
                        contracts.append(contract)
                except:
                    pass
        
        return contracts
    
    def _parse_contract_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single contract line with improved logic"""
        # Remove extra spaces and normalize
        line = re.sub(r'\s+', ' ', line.strip())
        
        # Extract strike and type
        strike_match = re.search(r'(\d{1,2},?\d{3}\.\d{2})([CP])', line)
        if not strike_match:
            return None
        
        strike = self._parse_strike(strike_match.group(1))
        option_type = "Call" if strike_match.group(2) == 'C' else "Put"
        
        # First, extract and remove the date to avoid confusion
        date_pattern = r'\d{2}/\d{2}/\d{2}'
        date_match = re.search(date_pattern, line)
        if date_match:
            # Remove date from line for cleaner parsing
            line_without_date = line[:date_match.start()].rstrip()
        else:
            line_without_date = line
        
        # Extract prices - look for patterns like "18,744.75" or "N/A"
        price_pattern = r'(N/A|(?:\d{1,2},)?\d{3,4}\.\d{2})'
        prices = re.findall(price_pattern, line_without_date)
        
        # Build contract dict with available data
        contract = {
            "strike": strike,
            "type": option_type,
            "open": self._parse_price(prices[0]) if len(prices) > 0 else None,
            "high": self._parse_price(prices[1]) if len(prices) > 1 else None,
            "low": self._parse_price(prices[2]) if len(prices) > 2 else None,
            "last": self._parse_price(prices[3]) if len(prices) > 3 else None,
            "bid": self._parse_price(prices[5]) if len(prices) > 5 else None,
            "ask": self._parse_price(prices[6]) if len(prices) > 6 else None,
            "premium": self._parse_price(prices[9]) if len(prices) > 9 else None
        }
        
        # Extract volume and OI using a more structured approach
        # The table structure is consistent:
        # Strike | Open | High | Low | Last | Change | Bid | Ask | Volume | OI | Premium | Time
        
        volume = None
        open_interest = None
        
        # Split the line and identify segments
        segments = line_without_date.split()
        
        try:
            # Simple approach: Volume and OI are always after bid/ask prices
            # but before the premium (last large decimal number)
            
            # Find all segments that are either N/A or pure numbers (potential volume/OI)
            vol_oi_candidates = []
            
            for i, seg in enumerate(segments):
                if i == 0:  # Skip strike
                    continue
                    
                # Look for N/A or pure numbers (not prices with decimals)
                if seg == 'N/A' or (seg.replace(',', '').isdigit() and '.' not in seg):
                    vol_oi_candidates.append((i, seg))
            
            # Volume and OI should be consecutive and appear after several price fields
            # Typically around indices 8-9 when open is N/A, or 9-10 when open has value
            if len(vol_oi_candidates) >= 2:
                # Look for two consecutive candidates
                for j in range(len(vol_oi_candidates) - 1):
                    idx1, val1 = vol_oi_candidates[j]
                    idx2, val2 = vol_oi_candidates[j + 1]
                    
                    # Check if they're consecutive
                    if idx2 - idx1 == 1 and idx1 >= 7:  # After price fields
                        # This is likely volume and OI
                        if val1 == 'N/A':
                            volume = None
                        else:
                            volume = int(val1.replace(',', ''))
                            
                        if val2 == 'N/A':
                            open_interest = None
                        else:
                            open_interest = int(val2.replace(',', ''))
                        break
            elif len(vol_oi_candidates) == 1:
                # Only one candidate - might be just volume or OI
                idx, val = vol_oi_candidates[0]
                if idx >= 7:
                    if val == 'N/A':
                        volume = None
                    else:
                        volume = int(val.replace(',', ''))
                        
        except Exception as e:
            # If parsing fails, default to None
            logger.debug(f"Volume/OI parsing failed: {e}")
            pass
        
        contract["volume"] = volume
        contract["open_interest"] = open_interest
        
        return contract
    
    def _parse_strike(self, value: str) -> float:
        """Parse strike price, removing commas"""
        from .parsing_utils import ParsingUtils
        return ParsingUtils.parse_strike(value)
    
    def _parse_price(self, value: str) -> Optional[float]:
        """Parse price value, handling N/A and commas"""
        from .parsing_utils import ParsingUtils
        return ParsingUtils.parse_price(value)
    
    def _parse_volume(self, value: str) -> Optional[int]:
        """Parse volume/OI value"""
        from .parsing_utils import ParsingUtils
        return ParsingUtils.parse_volume_or_oi(value)


# Module-level convenience function
def extract_text_from_screenshot(image_path: str) -> Dict[str, Any]:
    """Extract text from a Barchart screenshot"""
    extractor = OCRExtractor()
    return extractor.extract_text_from_screenshot(image_path)


if __name__ == "__main__":
    # Test with an existing screenshot
    import sys
    
    if len(sys.argv) > 1:
        screenshot_path = sys.argv[1]
    else:
        # Try to find a recent screenshot
        screenshots_dir = Path("outputs/screenshots/validation")
        if screenshots_dir.exists():
            screenshots = list(screenshots_dir.rglob("*.png"))
            if screenshots:
                screenshot_path = str(screenshots[-1])
                print(f"Using screenshot: {screenshot_path}")
            else:
                print("No screenshots found")
                sys.exit(1)
        else:
            print("Screenshots directory not found")
            sys.exit(1)
    
    result = extract_text_from_screenshot(screenshot_path)
    
    if result["success"]:
        print(f"\n✅ Text extraction successful using {result['method']}")
        print(f"\nExtracted {len(result.get('contracts', []))} contracts")
        
        if result.get('warning'):
            print(f"\n⚠️  {result['warning']}")
        
        # Show first few contracts
        for i, contract in enumerate(result.get('contracts', [])[:3]):
            print(f"\nContract {i+1}:")
            print(f"  Strike: {contract.get('strike')}")
            print(f"  Type: {contract.get('type')}")
            print(f"  Last: {contract.get('last')}")
            print(f"  Bid: {contract.get('bid')}")
            print(f"  Ask: {contract.get('ask')}")
    else:
        print(f"\n❌ Text extraction failed: {result.get('error')}")