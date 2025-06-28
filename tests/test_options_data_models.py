#!/usr/bin/env python3
"""
Comprehensive unit tests for options_data_models.py
Tests all data model classes and their methods
"""

from datetime import datetime
import unittest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.utilities.options_data_models import (
    OptionType, ContractType, OptionGreeks, OptionsContract, 
    OptionsChainData, NormalizedOptionsData
)


class TestEnums(unittest.TestCase):
    """Test enumeration classes"""
    
    def test_option_type_enum(self):
        """Test OptionType enum values"""
        self.assertEqual(OptionType.CALL.value, "call")
        self.assertEqual(OptionType.PUT.value, "put")
    
    def test_contract_type_enum(self):
        """Test ContractType enum values"""
        self.assertEqual(ContractType.WEEKLY.value, "weekly")
        self.assertEqual(ContractType.MONTHLY.value, "monthly")
        self.assertEqual(ContractType.FRIDAY.value, "friday")
        self.assertEqual(ContractType.DAILY.value, "daily")
        self.assertEqual(ContractType.ZERODTR.value, "0dte")


class TestOptionGreeks(unittest.TestCase):
    """Test OptionGreeks dataclass"""
    
    def test_greeks_creation(self):
        """Test creating OptionGreeks instance"""
        greeks = OptionGreeks(
            delta=0.5,
            gamma=0.02,
            theta=-0.05,
            vega=0.1,
            rho=0.03
        )
        
        self.assertEqual(greeks.delta, 0.5)
        self.assertEqual(greeks.gamma, 0.02)
        self.assertEqual(greeks.theta, -0.05)
        self.assertEqual(greeks.vega, 0.1)
        self.assertEqual(greeks.rho, 0.03)
    
    def test_greeks_with_none_values(self):
        """Test OptionGreeks with None values"""
        greeks = OptionGreeks(delta=0.5)
        
        self.assertEqual(greeks.delta, 0.5)
        self.assertIsNone(greeks.gamma)
        self.assertIsNone(greeks.theta)
        self.assertIsNone(greeks.vega)
        self.assertIsNone(greeks.rho)


class TestOptionsContract(unittest.TestCase):
    """Test OptionsContract dataclass"""
    
    def test_contract_creation_minimal(self):
        """Test creating OptionsContract with minimal data"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18"
        )
        
        self.assertEqual(contract.strike, 100.0)
        self.assertEqual(contract.expiration_date, "2025-07-18")
        self.assertEqual(contract.source, "unknown")
        self.assertIsInstance(contract.timestamp, datetime)
    
    def test_contract_creation_full(self):
        """Test creating OptionsContract with full data"""
        greeks = OptionGreeks(delta=0.5, gamma=0.02)
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            contract_type="weekly",
            call_symbol="CALL100",
            call_last=5.50,
            call_change=0.25,
            call_bid=5.45,
            call_ask=5.55,
            call_volume=1000,
            call_open_interest=5000,
            call_implied_volatility=0.25,
            call_greeks=greeks,
            put_symbol="PUT100",
            put_last=4.50,
            put_change=-0.15,
            put_bid=4.45,
            put_ask=4.55,
            put_volume=800,
            put_open_interest=4000,
            put_implied_volatility=0.23,
            put_greeks=greeks,
            underlying_symbol="NQ",
            underlying_price=105.0,
            source="barchart_api"
        )
        
        self.assertEqual(contract.strike, 100.0)
        self.assertEqual(contract.call_last, 5.50)
        self.assertEqual(contract.put_last, 4.50)
        self.assertEqual(contract.underlying_price, 105.0)
        self.assertEqual(contract.call_greeks.delta, 0.5)
    
    def test_to_dict_conversion(self):
        """Test converting OptionsContract to dictionary"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            call_last=5.50,
            underlying_price=105.0
        )
        
        data = contract.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["strike"], 100.0)
        self.assertEqual(data["call_last"], 5.50)
        self.assertIsInstance(data["timestamp"], str)  # Should be ISO format
    
    def test_get_moneyness(self):
        """Test moneyness calculation"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            underlying_price=105.0
        )
        
        # Test with embedded underlying price
        moneyness = contract.get_moneyness()
        self.assertAlmostEqual(moneyness, 100.0 / 105.0, places=5)
        
        # Test with provided underlying price
        moneyness_custom = contract.get_moneyness(110.0)
        self.assertAlmostEqual(moneyness_custom, 100.0 / 110.0, places=5)
        
        # Test with no price available
        contract_no_price = OptionsContract(strike=100.0, expiration_date="2025-07-18")
        self.assertIsNone(contract_no_price.get_moneyness())
    
    def test_is_itm_call(self):
        """Test in-the-money check for calls"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            underlying_price=105.0
        )
        
        # Call is ITM when strike < underlying
        self.assertTrue(contract.is_itm(OptionType.CALL))
        self.assertTrue(contract.is_itm(OptionType.CALL, 110.0))
        self.assertFalse(contract.is_itm(OptionType.CALL, 95.0))
        
        # Test with no price
        contract_no_price = OptionsContract(strike=100.0, expiration_date="2025-07-18")
        self.assertIsNone(contract_no_price.is_itm(OptionType.CALL))
    
    def test_is_itm_put(self):
        """Test in-the-money check for puts"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            underlying_price=95.0
        )
        
        # Put is ITM when strike > underlying
        self.assertTrue(contract.is_itm(OptionType.PUT))
        self.assertTrue(contract.is_itm(OptionType.PUT, 90.0))
        self.assertFalse(contract.is_itm(OptionType.PUT, 105.0))
    
    def test_get_bid_ask_spread(self):
        """Test bid-ask spread calculation"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            call_bid=5.45,
            call_ask=5.55,
            put_bid=4.45,
            put_ask=4.55
        )
        
        # Test call spread
        call_spread = contract.get_bid_ask_spread(OptionType.CALL)
        self.assertAlmostEqual(call_spread, 0.10, places=5)
        
        # Test put spread
        put_spread = contract.get_bid_ask_spread(OptionType.PUT)
        self.assertAlmostEqual(put_spread, 0.10, places=5)
        
        # Test with missing data
        contract_partial = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            call_bid=5.45
        )
        self.assertIsNone(contract_partial.get_bid_ask_spread(OptionType.CALL))
    
    def test_get_mid_price(self):
        """Test mid price calculation"""
        contract = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            call_bid=5.45,
            call_ask=5.55,
            put_bid=4.45,
            put_ask=4.55
        )
        
        # Test call mid price
        call_mid = contract.get_mid_price(OptionType.CALL)
        self.assertAlmostEqual(call_mid, 5.50, places=5)
        
        # Test put mid price
        put_mid = contract.get_mid_price(OptionType.PUT)
        self.assertAlmostEqual(put_mid, 4.50, places=5)
        
        # Test with missing data
        contract_partial = OptionsContract(
            strike=100.0,
            expiration_date="2025-07-18",
            call_ask=5.55
        )
        self.assertIsNone(contract_partial.get_mid_price(OptionType.CALL))


class TestOptionsChainData(unittest.TestCase):
    """Test OptionsChainData dataclass"""
    
    def test_chain_creation_minimal(self):
        """Test creating OptionsChainData with minimal data"""
        contracts = [
            OptionsContract(strike=100.0, expiration_date="2025-07-18"),
            OptionsContract(strike=105.0, expiration_date="2025-07-18")
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            contracts=contracts
        )
        
        self.assertEqual(chain.underlying_symbol, "NQ")
        self.assertEqual(chain.expiration_date, "2025-07-18")
        self.assertEqual(len(chain.contracts), 2)
        self.assertEqual(chain.total_contracts, 2)
        self.assertEqual(chain.source, "unknown")
        self.assertIsInstance(chain.timestamp, datetime)
        self.assertIsInstance(chain.metadata, dict)
    
    def test_chain_post_init(self):
        """Test that post_init correctly sets total_contracts"""
        contracts = [
            OptionsContract(strike=i * 5.0, expiration_date="2025-07-18")
            for i in range(20, 30)
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            contracts=contracts
        )
        
        self.assertEqual(chain.total_contracts, 10)
    
    def test_to_dict_conversion(self):
        """Test converting OptionsChainData to dictionary"""
        contracts = [
            OptionsContract(strike=100.0, expiration_date="2025-07-18", call_last=5.50),
            OptionsContract(strike=105.0, expiration_date="2025-07-18", call_last=3.25)
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            underlying_price=102.50,
            contracts=contracts,
            source="test",
            metadata={"test": "value"}
        )
        
        data = chain.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data["underlying_symbol"], "NQ")
        self.assertEqual(data["underlying_price"], 102.50)
        self.assertEqual(len(data["contracts"]), 2)
        self.assertIsInstance(data["timestamp"], str)
        self.assertEqual(data["metadata"]["test"], "value")
        self.assertIsInstance(data["contracts"][0], dict)
        self.assertEqual(data["contracts"][0]["strike"], 100.0)
    
    def test_get_strikes(self):
        """Test getting sorted list of strikes"""
        contracts = [
            OptionsContract(strike=105.0, expiration_date="2025-07-18"),
            OptionsContract(strike=100.0, expiration_date="2025-07-18"),
            OptionsContract(strike=110.0, expiration_date="2025-07-18"),
            OptionsContract(strike=100.0, expiration_date="2025-07-18")  # Duplicate
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            contracts=contracts
        )
        
        strikes = chain.get_strikes()
        self.assertEqual(strikes, [100.0, 105.0, 110.0])  # Sorted and unique
    
    def test_get_contract_by_strike(self):
        """Test finding contract by strike price"""
        contracts = [
            OptionsContract(strike=100.0, expiration_date="2025-07-18", call_last=5.50),
            OptionsContract(strike=105.0, expiration_date="2025-07-18", call_last=3.25),
            OptionsContract(strike=110.0, expiration_date="2025-07-18", call_last=1.75)
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            contracts=contracts
        )
        
        # Test finding existing strike
        contract = chain.get_contract_by_strike(105.0)
        self.assertIsNotNone(contract)
        self.assertEqual(contract.call_last, 3.25)
        
        # Test non-existent strike
        contract_none = chain.get_contract_by_strike(115.0)
        self.assertIsNone(contract_none)
    
    def test_filter_by_moneyness(self):
        """Test filtering contracts by moneyness range"""
        contracts = [
            OptionsContract(strike=90.0, expiration_date="2025-07-18", underlying_price=100.0),
            OptionsContract(strike=95.0, expiration_date="2025-07-18", underlying_price=100.0),
            OptionsContract(strike=100.0, expiration_date="2025-07-18", underlying_price=100.0),
            OptionsContract(strike=105.0, expiration_date="2025-07-18", underlying_price=100.0),
            OptionsContract(strike=110.0, expiration_date="2025-07-18", underlying_price=100.0)
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            underlying_price=100.0,
            contracts=contracts
        )
        
        # Filter for near-the-money (0.95 to 1.05)
        filtered = chain.filter_by_moneyness(0.95, 1.05)
        strikes = [c.strike for c in filtered]
        self.assertEqual(strikes, [95.0, 100.0, 105.0])
        
        # Filter for out-of-the-money calls (moneyness > 1.0)
        otm_calls = chain.filter_by_moneyness(1.01, 1.20)
        otm_strikes = [c.strike for c in otm_calls]
        self.assertEqual(otm_strikes, [105.0, 110.0])
    
    def test_get_total_volume(self):
        """Test calculating total volume"""
        contracts = [
            OptionsContract(
                strike=100.0, 
                expiration_date="2025-07-18",
                call_volume=1000,
                put_volume=800
            ),
            OptionsContract(
                strike=105.0, 
                expiration_date="2025-07-18",
                call_volume=500,
                put_volume=600
            ),
            OptionsContract(
                strike=110.0, 
                expiration_date="2025-07-18",
                call_volume=None,  # Test None handling
                put_volume=300
            )
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            contracts=contracts
        )
        
        volume = chain.get_total_volume()
        self.assertEqual(volume["calls"], 1500)  # 1000 + 500 + 0
        self.assertEqual(volume["puts"], 1700)   # 800 + 600 + 300
        self.assertEqual(volume["total"], 3200)
    
    def test_get_total_open_interest(self):
        """Test calculating total open interest"""
        contracts = [
            OptionsContract(
                strike=100.0, 
                expiration_date="2025-07-18",
                call_open_interest=5000,
                put_open_interest=4000
            ),
            OptionsContract(
                strike=105.0, 
                expiration_date="2025-07-18",
                call_open_interest=3000,
                put_open_interest=3500
            ),
            OptionsContract(
                strike=110.0, 
                expiration_date="2025-07-18",
                call_open_interest=2000,
                put_open_interest=None  # Test None handling
            )
        ]
        
        chain = OptionsChainData(
            underlying_symbol="NQ",
            expiration_date="2025-07-18",
            contracts=contracts
        )
        
        oi = chain.get_total_open_interest()
        self.assertEqual(oi["calls"], 10000)  # 5000 + 3000 + 2000
        self.assertEqual(oi["puts"], 7500)    # 4000 + 3500 + 0
        self.assertEqual(oi["total"], 17500)


class TestNormalizedOptionsData(unittest.TestCase):
    """Test NormalizedOptionsData dataclass"""
    
    def test_normalized_data_creation(self):
        """Test creating NormalizedOptionsData"""
        contracts = [
            {
                "strike": 100.0,
                "call_last_price": 5.50,
                "call_bid": 5.45,
                "call_ask": 5.55,
                "call_volume": 1000,
                "call_open_interest": 5000,
                "put_last_price": 4.50,
                "put_bid": 4.45,
                "put_ask": 4.55,
                "put_volume": 800,
                "put_open_interest": 4000
            }
        ]
        
        summary = {
            "underlying_symbol": "NQ",
            "expiration_date": "2025-07-18",
            "underlying_price": 102.50,
            "total_contracts": 1
        }
        
        metadata = {
            "source": "barchart",
            "fetch_time": "2025-06-28T10:00:00"
        }
        
        normalized = NormalizedOptionsData(
            contracts=contracts,
            summary=summary,
            metadata=metadata
        )
        
        self.assertEqual(len(normalized.contracts), 1)
        self.assertEqual(normalized.summary["underlying_symbol"], "NQ")
        self.assertEqual(normalized.metadata["source"], "barchart")
    
    def test_to_options_chain_conversion(self):
        """Test converting NormalizedOptionsData to OptionsChainData"""
        contracts = [
            {
                "strike": 100.0,
                "expiration": "2025-07-18",
                "call_last_price": 5.50,
                "call_bid": 5.45,
                "call_ask": 5.55,
                "call_volume": 1000,
                "call_open_interest": 5000,
                "put_last_price": 4.50,
                "put_bid": 4.45,
                "put_ask": 4.55,
                "put_volume": 800,
                "put_open_interest": 4000
            },
            {
                "strike": 105.0,
                "call_last_price": 3.25,
                "call_volume": 500,
                "call_open_interest": 3000,
                "put_last_price": 6.75,
                "put_volume": 600,
                "put_open_interest": 3500
            }
        ]
        
        summary = {
            "underlying_symbol": "NQ",
            "expiration_date": "2025-07-18",
            "underlying_price": 102.50
        }
        
        metadata = {
            "source": "barchart_normalized"
        }
        
        normalized = NormalizedOptionsData(
            contracts=contracts,
            summary=summary,
            metadata=metadata
        )
        
        # Convert to OptionsChainData
        chain = normalized.to_options_chain()
        
        self.assertIsInstance(chain, OptionsChainData)
        self.assertEqual(chain.underlying_symbol, "NQ")
        self.assertEqual(chain.expiration_date, "2025-07-18")
        self.assertEqual(chain.underlying_price, 102.50)
        self.assertEqual(len(chain.contracts), 2)
        self.assertEqual(chain.source, "barchart_normalized")
        
        # Check first contract conversion
        first_contract = chain.contracts[0]
        self.assertEqual(first_contract.strike, 100.0)
        self.assertEqual(first_contract.call_last, 5.50)
        self.assertEqual(first_contract.call_bid, 5.45)
        self.assertEqual(first_contract.call_ask, 5.55)
        self.assertEqual(first_contract.call_volume, 1000)
        self.assertEqual(first_contract.call_open_interest, 5000)
        
        # Check second contract with missing expiration
        second_contract = chain.contracts[1]
        self.assertEqual(second_contract.strike, 105.0)
        self.assertEqual(second_contract.expiration_date, "2025-07-18")  # From summary


if __name__ == "__main__":
    unittest.main()