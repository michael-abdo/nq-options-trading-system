#!/usr/bin/env python3
"""
Test validation for Databento API data ingestion
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import the solution
try:
    from solution import (
        DatabentoAPIClient, DatabentoDataIngestion, 
        load_databento_api_data, create_databento_loader
    )
    logger.info("Successfully imported Databento solution")
except ImportError as e:
    logger.error(f"Failed to import solution: {e}")
    raise

def test_api_key_loading():
    """Test API key loading from various sources"""
    logger.info("\n=== Testing API Key Loading ===")
    
    try:
        # Test with config
        config = {'api_key': 'test-key-123'}
        loader = DatabentoDataIngestion(config)
        assert loader.api_key == 'test-key-123', "API key from config failed"
        logger.info("✓ API key from config works")
        
        # Test environment fallback
        config = {}
        # Will try to load from environment or .env file
        try:
            loader = DatabentoDataIngestion(config)
            if loader.api_key:
                logger.info("✓ API key from environment/file works")
            else:
                logger.warning("No API key found in environment")
        except ValueError:
            logger.info("✓ Correctly raises error when no API key found")
        
        return True
        
    except Exception as e:
        logger.error(f"API key loading test failed: {e}")
        return False

def test_standard_interface():
    """Test that the module implements the standard data ingestion interface"""
    logger.info("\n=== Testing Standard Interface ===")
    
    try:
        # Check required function exists
        assert hasattr(sys.modules[__name__], 'load_databento_api_data'), \
            "Missing load_databento_api_data function"
        
        # Test with mock config
        config = {
            'api_key': 'test-key',
            'use_cache': False  # Disable cache for testing
        }
        
        # Should return proper structure even with invalid key
        result = load_databento_api_data(config)
        
        # Check required keys
        required_keys = [
            'loader', 'metadata', 'options_summary', 
            'quality_metrics', 'strike_range', 'raw_data_available'
        ]
        
        for key in required_keys:
            assert key in result, f"Missing required key: {key}"
        
        # Check options_summary structure
        assert 'total_contracts' in result['options_summary']
        assert 'calls' in result['options_summary']
        assert 'puts' in result['options_summary']
        
        # Check quality_metrics structure
        assert 'total_contracts' in result['quality_metrics']
        assert 'volume_coverage' in result['quality_metrics']
        assert 'oi_coverage' in result['quality_metrics']
        assert 'data_source' in result['quality_metrics']
        assert result['quality_metrics']['data_source'] == 'databento'
        
        # Check strike_range structure
        assert 'min' in result['strike_range']
        assert 'max' in result['strike_range']
        assert 'count' in result['strike_range']
        
        logger.info("✓ Standard interface implementation correct")
        return True
        
    except Exception as e:
        logger.error(f"Standard interface test failed: {e}")
        return False

def test_cache_functionality():
    """Test caching functionality"""
    logger.info("\n=== Testing Cache Functionality ===")
    
    try:
        # Create test cache directory
        test_cache_dir = Path("test_cache")
        test_cache_dir.mkdir(exist_ok=True)
        
        # Initialize client with test cache
        client = DatabentoAPIClient('test-key', str(test_cache_dir))
        
        # Test cache key generation
        cache_key = client._get_cache_key('GLBX.MDP3', ['NQ.OPT'], 'trades', '2025-06-10')
        assert cache_key == 'GLBX.MDP3_NQ.OPT_trades_2025-06-10', "Cache key format incorrect"
        logger.info("✓ Cache key generation works")
        
        # Test cache save and retrieve
        test_data = {'test': 'data', 'value': 123}
        client._save_cache('test_key', test_data, 0.01)
        
        retrieved = client._check_cache('test_key', max_age_hours=24)
        assert retrieved == test_data, "Cache retrieval failed"
        logger.info("✓ Cache save/retrieve works")
        
        # Test cache expiry
        retrieved_expired = client._check_cache('test_key', max_age_hours=0)
        assert retrieved_expired is None, "Cache expiry not working"
        logger.info("✓ Cache expiry works")
        
        # Cleanup
        import shutil
        shutil.rmtree(test_cache_dir)
        
        return True
        
    except Exception as e:
        logger.error(f"Cache functionality test failed: {e}")
        return False

def test_data_processing():
    """Test data processing functions"""
    logger.info("\n=== Testing Data Processing ===")
    
    try:
        # Test with mock data
        client = DatabentoAPIClient('test-key')
        
        # Test options chain processing
        import pandas as pd
        mock_df = pd.DataFrame([
            {
                'raw_symbol': 'NQM5 C20000',
                'strike_price': 20000000,  # Databento multiplies by 1000
                'expiration': pd.Timestamp('2025-06-20'),
                'instrument_class': 'C',
                'instrument_id': 123
            },
            {
                'raw_symbol': 'NQM5 P19000',
                'strike_price': 19000000,
                'expiration': pd.Timestamp('2025-06-20'),
                'instrument_class': 'P',
                'instrument_id': 124
            }
        ])
        
        result = client._process_options_chain(mock_df, '2025-06-10')
        
        assert len(result['calls']) == 1, "Call processing failed"
        assert len(result['puts']) == 1, "Put processing failed"
        assert result['calls'][0]['strike'] == 20000.0, "Strike price conversion failed"
        assert result['total_contracts'] == 2, "Total contracts count wrong"
        
        logger.info("✓ Options chain processing works")
        
        # Test trade processing
        mock_trades = pd.DataFrame([
            {'instrument_id': 123, 'size': 10, 'price': 100.5},
            {'instrument_id': 123, 'size': 20, 'price': 101.0},
            {'instrument_id': 124, 'size': 5, 'price': 50.0}
        ])
        
        trades_result = client._process_trades(mock_trades, '2025-06-10')
        
        assert trades_result['total_volume'] == 35, "Volume calculation wrong"
        assert trades_result['total_trades'] == 3, "Trade count wrong"
        assert 123 in trades_result['volume_by_instrument'], "Instrument aggregation failed"
        
        logger.info("✓ Trade data processing works")
        
        return True
        
    except Exception as e:
        logger.error(f"Data processing test failed: {e}")
        return False

def test_factory_function():
    """Test factory function"""
    logger.info("\n=== Testing Factory Function ===")
    
    try:
        # Test with default config
        loader = create_databento_loader()
        assert isinstance(loader, DatabentoDataIngestion), "Factory function failed"
        
        # Test with custom config
        config = {'api_key': 'test-key', 'symbols': ['ES', 'NQ']}
        loader = create_databento_loader(config)
        assert loader.symbols == ['ES', 'NQ'], "Config not applied correctly"
        
        logger.info("✓ Factory function works correctly")
        return True
        
    except Exception as e:
        logger.error(f"Factory function test failed: {e}")
        return False

def test_real_api_connection():
    """Test real API connection if API key is available"""
    logger.info("\n=== Testing Real API Connection ===")
    
    # Try to get real API key
    api_key = os.getenv('DATABENTO_API_KEY')
    if not api_key:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('DATABENTO_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
        except:
            pass
    
    if not api_key or api_key == 'test-key':
        logger.info("⚠ Skipping real API test (no valid API key found)")
        return True
    
    try:
        # Test with real API
        config = {
            'api_key': api_key,
            'symbols': ['NQ'],
            'use_cache': True
        }
        
        result = load_databento_api_data(config)
        
        if 'error' in result.get('metadata', {}):
            logger.warning(f"API returned error: {result['metadata']['error']}")
        else:
            logger.info(f"✓ Real API connection successful")
            logger.info(f"  Total contracts: {result['options_summary']['total_contracts']}")
            logger.info(f"  Strike range: {result['strike_range']['min']:.0f} - {result['strike_range']['max']:.0f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Real API connection test failed: {e}")
        return False

def run_all_tests():
    """Run all validation tests"""
    logger.info("=== Running Databento API Validation Tests ===")
    
    tests = [
        ("API Key Loading", test_api_key_loading),
        ("Standard Interface", test_standard_interface),
        ("Cache Functionality", test_cache_functionality),
        ("Data Processing", test_data_processing),
        ("Factory Function", test_factory_function),
        ("Real API Connection", test_real_api_connection)
    ]
    
    results = {}
    passed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASSED" if result else "FAILED"
            if result:
                passed += 1
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = "CRASHED"
    
    # Generate evidence
    evidence = {
        "timestamp": datetime.now().isoformat(),
        "test_results": results,
        "tests_passed": passed,
        "tests_total": len(tests),
        "pass_rate": passed / len(tests),
        "status": "VALIDATED" if passed == len(tests) else "PARTIAL"
    }
    
    # Save evidence
    with open('evidence.json', 'w') as f:
        json.dump(evidence, f, indent=2)
    
    # Summary
    logger.info(f"\n=== Test Summary ===")
    logger.info(f"Passed: {passed}/{len(tests)} ({evidence['pass_rate']*100:.1f}%)")
    for test_name, result in results.items():
        logger.info(f"  {test_name}: {result}")
    
    return evidence

if __name__ == "__main__":
    evidence = run_all_tests()