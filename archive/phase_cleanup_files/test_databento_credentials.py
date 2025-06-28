#!/usr/bin/env python3
"""Test Databento API credentials and connection"""

import os
import sys
import json
from datetime import datetime

# Add the project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import databento as db
    print("✅ Databento package imported successfully")
except ImportError as e:
    print(f"❌ Failed to import databento: {e}")
    sys.exit(1)

def test_databento_credentials():
    """Test Databento API credentials"""
    
    # Get API key from environment
    api_key = os.environ.get('DATABENTO_API_KEY')
    if not api_key:
        print("❌ DATABENTO_API_KEY not found in environment")
        return False
    
    print(f"✅ DATABENTO_API_KEY found ({len(api_key)} chars)")
    
    try:
        # Initialize client
        client = db.Historical(api_key)
        print("✅ Databento client initialized")
        
        # Test API connection by getting account info
        # This is a lightweight call that validates credentials
        print("\nTesting API connection...")
        
        # Try a simple metadata query to validate connection
        # This doesn't consume any data usage
        datasets = client.metadata.list_datasets()
        print(f"✅ API connection successful! Found {len(datasets)} datasets")
        
        # Check if GLBX.MDP3 is available
        glbx_available = 'GLBX.MDP3' in datasets
        if glbx_available:
            print("✅ GLBX.MDP3 dataset is available")
        else:
            print("❌ GLBX.MDP3 dataset not found")
            print(f"   Available datasets: {', '.join(datasets[:5])}...")
        
        # Get account usage info (doesn't consume credits)
        try:
            usage_info = client.get_usage()
            print(f"\n📊 Account Usage Information:")
            if hasattr(usage_info, 'total'):
                print(f"   Total usage: ${usage_info.total:.2f}")
            else:
                print(f"   Usage info: {usage_info}")
        except Exception as e:
            print(f"⚠️  Could not retrieve usage info: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Databento API error: {e}")
        return False

def test_dataset_access():
    """Test specific dataset access for NQ options"""
    api_key = os.environ.get('DATABENTO_API_KEY')
    if not api_key:
        return False
    
    try:
        client = db.Historical(api_key)
        
        # Test GLBX.MDP3 dataset access for NQ
        print("\n📋 Testing GLBX.MDP3 dataset access...")
        
        # Get metadata for NQ futures (doesn't consume usage)
        try:
            # List available symbols for GLBX.MDP3
            symbols = client.metadata.list_symbols(
                dataset='GLBX.MDP3',
                symbols=['NQ'],  # NQ futures root
                start='2025-01-01'
            )
            
            nq_symbols = [s for s in symbols if 'NQ' in s.raw_symbol]
            print(f"✅ Found {len(nq_symbols)} NQ-related symbols")
            
            # Show a few examples
            if nq_symbols:
                print("\nExample NQ symbols:")
                for sym in nq_symbols[:5]:
                    print(f"   - {sym.raw_symbol}: {sym.description}")
            
            return True
            
        except Exception as e:
            print(f"❌ Could not access GLBX.MDP3 dataset: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Dataset test error: {e}")
        return False

def main():
    """Run all credential tests"""
    print("=" * 50)
    print("Databento Credential Validation")
    print("=" * 50)
    
    # Load environment variables
    if os.path.exists('.env'):
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Loaded .env file")
    
    # Run tests
    creds_valid = test_databento_credentials()
    
    if creds_valid:
        dataset_valid = test_dataset_access()
        
        if dataset_valid:
            print("\n🎉 All Databento tests passed!")
            
            # Save test results
            results = {
                'timestamp': datetime.now().isoformat(),
                'credentials_valid': True,
                'glbx_mdp3_access': True,
                'api_key_length': len(os.environ.get('DATABENTO_API_KEY', '')),
                'test_status': 'PASSED'
            }
        else:
            results = {
                'timestamp': datetime.now().isoformat(),
                'credentials_valid': True,
                'glbx_mdp3_access': False,
                'test_status': 'PARTIAL'
            }
    else:
        results = {
            'timestamp': datetime.now().isoformat(),
            'credentials_valid': False,
            'test_status': 'FAILED'
        }
    
    # Save results
    output_file = 'outputs/databento_credential_test.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n📝 Test results saved to {output_file}")

if __name__ == "__main__":
    main()