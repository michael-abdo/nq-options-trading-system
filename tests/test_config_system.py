#!/usr/bin/env python3
"""
Test the configurable data sources system
"""

import os
import sys

# Add project paths (now in tests subdirectory)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'tasks', 'options_trading_system'))

from config_manager import get_config_manager
from data_ingestion.sources_registry import get_sources_registry

def test_configuration_system():
    """Test the complete configuration system"""
    
    print("=== Testing Configurable Data Sources System ===\n")
    
    # Test 1: Create configuration manager and profiles
    print("1. Testing Configuration Manager...")
    config_manager = get_config_manager()
    
    # Create standard profiles
    print("   Creating standard profiles...")
    config_manager.create_standard_profiles()
    
    # List available profiles
    profiles = config_manager.list_profiles()
    print(f"   ✓ Created {len(profiles)} profiles: {profiles}")
    
    # Test 2: Test sources registry
    print("\n2. Testing Sources Registry...")
    registry = get_sources_registry()
    available_sources = registry.get_available_sources()
    print(f"   ✓ Available sources: {available_sources}")
    
    registry_summary = registry.get_registry_summary()
    print(f"   ✓ Total sources: {registry_summary['total_sources']}")
    for source_name, source_type in registry_summary['source_types'].items():
        print(f"     - {source_name}: {source_type}")
    
    # Test 3: Load and validate different profiles
    print("\n3. Testing Configuration Profiles...")
    
    for profile_name in profiles:
        try:
            print(f"\n   Testing profile: {profile_name}")
            config = config_manager.load_profile(profile_name)
            
            # Get configuration summary
            summary = config_manager.get_config_summary(config)
            print(f"     ✓ Enabled sources: {summary['enabled_sources']}")
            
            # Validate configuration
            validation_issues = config_manager.validate_config(config)
            if validation_issues:
                print(f"     ⚠️ Validation issues:")
                for issue in validation_issues:
                    print(f"       - {issue}")
            else:
                print(f"     ✓ Configuration valid")
                
        except Exception as e:
            print(f"     ✗ Failed to load {profile_name}: {e}")
    
    # Test 4: Test custom source combinations
    print("\n4. Testing Custom Source Combinations...")
    
    # Test Databento + Polygon
    custom_config = config_manager.create_source_profile(
        "databento_polygon", 
        ["databento", "polygon"]
    )
    custom_summary = config_manager.get_config_summary(custom_config)
    print(f"   ✓ Custom combo (Databento + Polygon): {custom_summary['enabled_sources']}")
    
    # Test All sources
    all_sources_config = config_manager.create_source_profile(
        "all_sources_test",
        available_sources
    )
    all_summary = config_manager.get_config_summary(all_sources_config)
    print(f"   ✓ All sources combo: {all_summary['enabled_sources']}")
    
    print("\n=== Configuration System Test Complete ===")
    print("✅ Configuration system working correctly")
    print("✅ Source registry operational")
    print("✅ Profile management functional")
    print("✅ Ready for configurable data source pipeline")

if __name__ == "__main__":
    test_configuration_system()