#!/usr/bin/env python3
"""Test OCR parsing logic to document current failures and verify fixes."""

import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from tasks.options_trading_system.data_ingestion.barchart_web_scraper.ocr_extractor import OCRExtractor


class TestOCRParsing(unittest.TestCase):
    """Test cases documenting current OCR parsing failures."""
    
    def setUp(self):
        """Set up test extractor."""
        self.extractor = OCRExtractor()
    
    def test_volume_oi_parsing_bug(self):
        """Test that documents the volume/OI parsing bug.
        
        Current behavior: Volume=6, OI=27 (from date 06/27/25)
        Expected behavior: Volume=None, OI=None (since text shows N/A)
        """
        # Actual line from OCR output
        sample_line = "3,500.00C   N/A         19,244.75   19,244.75   19,244.75   +84.50      19,292.75   19,336.00   N/A         N/A         384,895.00  06/27/25"
        
        # Parse the line
        contract = self.extractor._parse_contract_line(sample_line)
        
        # Now correctly parses N/A values
        self.assertIsNone(contract['volume'], "Should parse N/A as None")
        self.assertIsNone(contract['open_interest'], "Should parse N/A as None")
        
    def test_price_parsing_accuracy(self):
        """Test that price parsing works correctly (this should pass)."""
        sample_line = "3,500.00C   N/A         19,244.75   19,244.75   19,244.75   +84.50      19,292.75   19,336.00   N/A         N/A         384,895.00  06/27/25"
        
        contract = self.extractor._parse_contract_line(sample_line)
        
        # These should work correctly
        self.assertEqual(contract['strike'], 3500.0)
        self.assertEqual(contract['type'], 'Call')
        self.assertEqual(contract['last'], 19244.75)
        self.assertEqual(contract['bid'], 19292.75)
        self.assertEqual(contract['ask'], 19336.0)
        
    def test_put_contract_parsing(self):
        """Test put contract parsing with current bug."""
        # Sample put contract line
        put_line = "20,000.00P  N/A         51.00       51.00       51.00s      -1.00       48.00       52.75       N/A         360         1.00        06/27/25"
        
        contract = self.extractor._parse_contract_line(put_line)
        
        # Now correctly parses actual OI value
        self.assertEqual(contract['type'], 'Put')
        self.assertEqual(contract['strike'], 20000.0)
        self.assertEqual(contract['open_interest'], 360, "Now correctly parses actual OI value")
        
    def test_edge_cases(self):
        """Test various edge cases in OCR output."""
        edge_cases = [
            # Missing spaces
            "3,500.00CN/A19,244.7519,244.7519,244.75+84.5019,292.7519,336.00N/AN/A384,895.0006/27/25",
            # Extra spaces
            "3,500.00C    N/A    19,244.75    19,244.75    19,244.75    +84.50    19,292.75    19,336.00    N/A    N/A    384,895.00    06/27/25",
            # Settlement indicator 's'
            "3,500.00C   N/A         19,244.75s  19,244.75s  19,244.75s  +84.50      19,292.75   19,336.00   N/A         N/A         384,895.00  06/27/25",
        ]
        
        for line in edge_cases:
            contract = self.extractor._parse_contract_line(line)
            # Should at least extract strike correctly
            self.assertIsNotNone(contract)
            self.assertEqual(contract['strike'], 3500.0)
            
    def test_regex_patterns(self):
        """Test individual regex patterns to understand the issue."""
        sample_line = "3,500.00C   N/A         19,244.75   19,244.75   19,244.75   +84.50      19,292.75   19,336.00   N/A         N/A         384,895.00  06/27/25"
        
        # Test volume pattern
        import re
        volume_pattern = r'(N/A|\d+)'
        volumes = re.findall(volume_pattern, sample_line)
        
        # This is the problem - it finds too many matches!
        self.assertGreater(len(volumes), 20, "Volume pattern is too greedy")
        self.assertEqual(volumes[-3], '06', "Incorrectly captures date part as volume")
        self.assertEqual(volumes[-2], '27', "Incorrectly captures date part as OI")
        
    def test_mock_data_parsing(self):
        """Test parsing with mock data format."""
        # The mock data has a cleaner format
        mock_line = "3,500.00C   N/A         19,244.75   19,244.75   19,244.75   +84.50      19,300.00   19,358.75   N/A         N/A         384,895.00  06/27/25"
        
        # Mock data parsing uses different logic
        contracts = self.extractor._parse_mock_contracts(f"Strike Open High Low Last Change Bid Ask Volume Open Int Premium Time\n{mock_line}")
        
        self.assertEqual(len(contracts), 1)
        contract = contracts[0]
        
        # Mock parsing actually handles N/A correctly!
        self.assertIsNone(contract['volume'], "Mock parsing correctly returns None for N/A")
        self.assertIsNone(contract['open_interest'], "Mock parsing correctly returns None for N/A")


class TestExpectedBehavior(unittest.TestCase):
    """Tests for the expected correct behavior after fix."""
    
    def setUp(self):
        """Set up test extractor."""
        self.extractor = OCRExtractor()
        
    def test_correct_na_parsing(self):
        """Test that N/A values are parsed correctly."""
        sample_line = "3,500.00C   N/A         19,244.75   19,244.75   19,244.75   +84.50      19,292.75   19,336.00   N/A         N/A         384,895.00  06/27/25"
        
        contract = self.extractor._parse_contract_line(sample_line)
        
        # After fix, these should be None
        self.assertIsNone(contract['volume'])
        self.assertIsNone(contract['open_interest'])
        
    def test_correct_actual_values(self):
        """Test parsing when there are actual volume/OI values."""
        # Line with real values
        sample_line = "22,800.00C  N/A         630.00      630.00      630.00s     +5.00       628.00      633.00      15          726         1,260.00    06/27/25"
        
        contract = self.extractor._parse_contract_line(sample_line)
        
        # Should parse actual values correctly
        self.assertEqual(contract['volume'], 15)
        self.assertEqual(contract['open_interest'], 726)
        

if __name__ == "__main__":
    # Run tests and show detailed output
    unittest.main(verbosity=2)