#!/usr/bin/env python3
"""
Test IFD v3.0 Configuration Integration
Tests configuration loading, validation, and chart integration with IFD settings
"""

import os
import sys
import json
import logging
from pathlib import Path

# Add parent directory for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

try:
    from scripts.chart_config_manager import ChartConfigManager
    from scripts.nq_5m_chart import NQFiveMinuteChart
    CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    print(f"❌ Config manager not available: {e}")
    CONFIG_MANAGER_AVAILABLE = False

logger = logging.getLogger(__name__)

def test_ifd_schema_validation():
    """Test that IFD configuration schema is properly defined"""
    print("=== Testing IFD Schema Validation ===")

    if not CONFIG_MANAGER_AVAILABLE:
        print("❌ Config manager not available - skipping test")
        return False

    try:
        # Initialize config manager
        config_manager = ChartConfigManager()
        print("✅ Config manager initialized")

        # Check if schema contains IFD v3.0 definitions
        schema = config_manager.schema

        if not schema:
            print("❌ Schema not loaded")
            return False

        print("✅ Schema loaded successfully")

        # Verify IFD is in enabled indicators enum
        indicators_enum = schema.get("properties", {}).get("indicators", {}).get("properties", {}).get("enabled", {}).get("items", {}).get("enum", [])

        if "ifd_v3" not in indicators_enum:
            print("❌ 'ifd_v3' not found in indicators enum")
            return False

        print("✅ 'ifd_v3' found in indicators enum")

        # Verify IFD section exists in schema
        ifd_schema = schema.get("properties", {}).get("indicators", {}).get("properties", {}).get("ifd_v3")

        if not ifd_schema:
            print("❌ IFD v3.0 configuration section not found in schema")
            return False

        print("✅ IFD v3.0 schema section found")

        # Verify required IFD configuration properties
        required_properties = [
            "show_signals", "show_confidence", "min_confidence_display",
            "signal_colors", "marker_sizes", "hover_info", "aggregation"
        ]

        ifd_properties = ifd_schema.get("properties", {})
        missing_properties = [prop for prop in required_properties if prop not in ifd_properties]

        if missing_properties:
            print(f"❌ Missing IFD properties in schema: {missing_properties}")
            return False

        print("✅ All required IFD properties found in schema")

        return True

    except Exception as e:
        print(f"❌ Schema validation test failed: {e}")
        return False

def test_ifd_preset_loading():
    """Test loading IFD configuration presets"""
    print("\\n=== Testing IFD Preset Loading ===")

    if not CONFIG_MANAGER_AVAILABLE:
        print("❌ Config manager not available - skipping test")
        return False

    try:
        config_manager = ChartConfigManager()

        # Test loading IFD-enabled presets
        ifd_presets = ["ifd_enabled", "ifd_advanced", "ifd_minimal"]

        results = {}

        for preset_name in ifd_presets:
            print(f"\\nTesting preset: {preset_name}")

            try:
                config = config_manager.load_config(preset_name)

                if not config:
                    print(f"❌ Failed to load {preset_name} config")
                    results[preset_name] = False
                    continue

                print(f"✅ {preset_name} config loaded")

                # Verify IFD is enabled
                enabled_indicators = config.get("indicators", {}).get("enabled", [])
                if "ifd_v3" not in enabled_indicators:
                    print(f"❌ IFD not enabled in {preset_name}")
                    results[preset_name] = False
                    continue

                print(f"✅ IFD enabled in {preset_name}")

                # Verify IFD configuration exists
                ifd_config = config.get("indicators", {}).get("ifd_v3", {})
                if not ifd_config:
                    print(f"❌ IFD configuration missing in {preset_name}")
                    results[preset_name] = False
                    continue

                print(f"✅ IFD configuration found in {preset_name}")

                # Verify essential IFD settings
                essential_settings = ["show_signals", "signal_colors", "marker_sizes"]
                missing_settings = [setting for setting in essential_settings if setting not in ifd_config]

                if missing_settings:
                    print(f"❌ Missing essential IFD settings in {preset_name}: {missing_settings}")
                    results[preset_name] = False
                    continue

                print(f"✅ All essential IFD settings present in {preset_name}")

                # Test configuration validation
                try:
                    config_manager.validate_config(config)
                    print(f"✅ {preset_name} passed schema validation")
                    results[preset_name] = True
                except Exception as validation_error:
                    print(f"❌ {preset_name} failed schema validation: {validation_error}")
                    results[preset_name] = False

            except Exception as e:
                print(f"❌ Error testing {preset_name}: {e}")
                results[preset_name] = False

        # Summary
        passed = sum(1 for result in results.values() if result)
        total = len(results)

        print(f"\\n📊 Preset Loading Results: {passed}/{total} passed")

        return passed == total

    except Exception as e:
        print(f"❌ Preset loading test failed: {e}")
        return False

def test_chart_integration():
    """Test chart integration with IFD configuration"""
    print("\\n=== Testing Chart Integration ===")

    try:
        # Test chart initialization with IFD config
        config_manager = ChartConfigManager()
        ifd_config = config_manager.load_config("ifd_enabled")

        if not ifd_config:
            print("❌ Failed to load IFD config for chart test")
            return False

        print("✅ IFD config loaded for chart test")

        # Initialize chart with IFD configuration
        chart = NQFiveMinuteChart(config=ifd_config)
        print("✅ Chart initialized with IFD configuration")

        # Verify IFD is enabled in chart
        if "ifd_v3" not in chart.indicators_enabled:
            print("❌ IFD not enabled in chart indicators")
            return False

        print("✅ IFD enabled in chart indicators")

        # Verify data provider has IFD support
        provider_status = chart.data_provider.get_ifd_bridge_status()

        print(f"📊 IFD Bridge Status:")
        print(f"   Enabled: {provider_status.get('enabled', False)}")
        print(f"   Available: {provider_status.get('available', False)}")

        if provider_status.get('enabled', False):
            print("✅ IFD bridge enabled in data provider")
        else:
            print("⚠️ IFD bridge not enabled (may be expected if IFD components not available)")

        # Test configuration access in chart
        chart_ifd_config = chart.config.get("indicators", {}).get("ifd_v3", {})

        if not chart_ifd_config:
            print("❌ IFD configuration not accessible in chart")
            return False

        print("✅ IFD configuration accessible in chart")

        # Verify configuration properties
        required_chart_config = ["show_signals", "signal_colors", "marker_sizes"]
        missing_config = [prop for prop in required_chart_config if prop not in chart_ifd_config]

        if missing_config:
            print(f"❌ Missing IFD configuration in chart: {missing_config}")
            return False

        print("✅ All required IFD configuration available in chart")

        # Test default values
        show_signals = chart_ifd_config.get("show_signals", False)
        min_confidence = chart_ifd_config.get("min_confidence_display", 0.0)

        print(f"📊 IFD Chart Settings:")
        print(f"   Show Signals: {show_signals}")
        print(f"   Min Confidence: {min_confidence}")

        return True

    except Exception as e:
        print(f"❌ Chart integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_examples():
    """Test that configuration examples are valid and complete"""
    print("\\n=== Testing Configuration Examples ===")

    try:
        config_dir = Path(__file__).parent.parent / "config" / "5m_chart_examples"

        if not config_dir.exists():
            print(f"❌ Examples directory not found: {config_dir}")
            return False

        print(f"✅ Examples directory found: {config_dir}")

        # Find all IFD-related configuration files
        ifd_config_files = list(config_dir.glob("ifd_*.json"))

        if not ifd_config_files:
            print("❌ No IFD configuration examples found")
            return False

        print(f"✅ Found {len(ifd_config_files)} IFD configuration examples")

        config_manager = ChartConfigManager()

        results = {}

        for config_file in ifd_config_files:
            config_name = config_file.stem
            print(f"\\nTesting configuration: {config_name}")

            try:
                # Load and validate configuration
                with open(config_file, 'r') as f:
                    config = json.load(f)

                print(f"✅ {config_name} JSON parsed successfully")

                # Validate against schema
                config_manager.validate_config(config)
                print(f"✅ {config_name} passed schema validation")

                # Check IFD-specific requirements
                ifd_config = config.get("indicators", {}).get("ifd_v3", {})

                if not ifd_config:
                    print(f"❌ {config_name} missing IFD configuration")
                    results[config_name] = False
                    continue

                # Validate IFD configuration completeness
                required_sections = ["signal_colors", "marker_sizes", "hover_info", "aggregation"]
                missing_sections = [section for section in required_sections if section not in ifd_config]

                if missing_sections:
                    print(f"❌ {config_name} missing IFD sections: {missing_sections}")
                    results[config_name] = False
                    continue

                print(f"✅ {config_name} has complete IFD configuration")
                results[config_name] = True

            except json.JSONDecodeError as e:
                print(f"❌ {config_name} has invalid JSON: {e}")
                results[config_name] = False
            except Exception as e:
                print(f"❌ {config_name} validation failed: {e}")
                results[config_name] = False

        # Summary
        passed = sum(1 for result in results.values() if result)
        total = len(results)

        print(f"\\n📊 Configuration Examples Results: {passed}/{total} passed")

        return passed == total

    except Exception as e:
        print(f"❌ Configuration examples test failed: {e}")
        return False

def main():
    """Run all IFD configuration tests"""
    print("=== IFD Configuration Test Suite ===")

    if not CONFIG_MANAGER_AVAILABLE:
        print("❌ Cannot run tests - configuration manager not available")
        return

    tests = [
        ("Schema Validation", test_ifd_schema_validation),
        ("Preset Loading", test_ifd_preset_loading),
        ("Chart Integration", test_chart_integration),
        ("Configuration Examples", test_configuration_examples)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)

        try:
            result = test_func()
            results.append((test_name, result))

            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")

        except Exception as e:
            print(f"💥 {test_name}: CRASHED - {e}")
            results.append((test_name, False))

    # Final Summary
    print(f"\\n{'='*60}")
    print("CONFIGURATION TEST SUMMARY")
    print('='*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:8} {test_name}")

    print(f"\\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 ALL IFD CONFIGURATION TESTS PASSED!")
        print("✅ IFD v3.0 integration is fully configured and ready")
    else:
        print("⚠️ Some configuration issues detected")
        print("❌ Review failed tests before using IFD features")

if __name__ == "__main__":
    main()
