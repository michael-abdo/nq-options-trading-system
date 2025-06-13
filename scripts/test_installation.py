#!/usr/bin/env python3
"""
Test Installation - Verify 5-minute chart system installation
Tests all components to ensure proper installation and configuration
"""

import sys
import os
import importlib
from pathlib import Path
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstallationTester:
    """Test the 5-minute chart system installation"""

    def __init__(self):
        self.script_dir = Path(__file__).parent
        self.project_root = self.script_dir.parent
        self.errors = []
        self.warnings = []

    def test_python_version(self):
        """Test Python version compatibility"""
        print("🐍 Testing Python version...")

        version = sys.version_info
        if version.major != 3 or version.minor < 8:
            self.errors.append(f"Python 3.8+ required, found {version.major}.{version.minor}")
            return False

        print(f"  ✅ Python {version.major}.{version.minor}.{version.micro}")
        return True

    def test_required_packages(self):
        """Test required Python packages"""
        print("📦 Testing required packages...")

        required_packages = [
            'plotly', 'pandas', 'numpy', 'pytz', 'jsonschema'
        ]

        missing_packages = []

        for package in required_packages:
            try:
                importlib.import_module(package)
                print(f"  ✅ {package}")
            except ImportError:
                missing_packages.append(package)
                print(f"  ❌ {package} - Missing")

        if missing_packages:
            self.errors.append(f"Missing required packages: {', '.join(missing_packages)}")
            print(f"  💡 Install with: pip install {' '.join(missing_packages)}")
            return False

        return True

    def test_project_structure(self):
        """Test project directory structure"""
        print("📁 Testing project structure...")

        required_files = [
            'scripts/nq_5m_chart.py',
            'scripts/databento_5m_provider.py',
            'scripts/chart_config_manager.py',
            'utils/timezone_utils.py',
            'config/5m_chart_config.json',
            'config/5m_chart_examples/default.json'
        ]

        missing_files = []

        for file_path in required_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                print(f"  ✅ {file_path}")
            else:
                missing_files.append(file_path)
                print(f"  ❌ {file_path} - Missing")

        if missing_files:
            self.errors.append(f"Missing required files: {', '.join(missing_files)}")
            return False

        return True

    def test_configuration_system(self):
        """Test configuration loading and validation"""
        print("⚙️ Testing configuration system...")

        try:
            # Add to path
            sys.path.append(str(self.script_dir))
            sys.path.append(str(self.project_root))

            from chart_config_manager import ChartConfigManager

            config_manager = ChartConfigManager(str(self.project_root / "config"))

            # Test loading configurations
            configs_to_test = ['default', 'minimal', 'scalping']

            for config_name in configs_to_test:
                try:
                    config = config_manager.load_config(config_name)
                    if config_manager.validate_config(config):
                        print(f"  ✅ {config_name} configuration")
                    else:
                        self.warnings.append(f"Configuration {config_name} validation failed")
                        print(f"  ⚠️ {config_name} configuration - Validation failed")
                except Exception as e:
                    self.errors.append(f"Failed to load {config_name} configuration: {e}")
                    print(f"  ❌ {config_name} configuration - {e}")

            return True

        except ImportError as e:
            self.errors.append(f"Cannot import configuration manager: {e}")
            print(f"  ❌ Configuration manager import failed: {e}")
            return False

    def test_chart_creation(self):
        """Test basic chart creation without data"""
        print("📊 Testing chart creation...")

        try:
            # Test minimal chart creation
            sys.path.append(str(self.script_dir))
            sys.path.append(str(self.project_root))

            from nq_5m_chart import NQFiveMinuteChart
            from chart_config_manager import ChartConfigManager

            config_manager = ChartConfigManager(str(self.project_root / "config"))
            config = config_manager.load_config("minimal")

            # Create chart instance (without actually fetching data)
            chart = NQFiveMinuteChart(config=config)

            # Test configuration properties
            assert chart.symbol == config["data"]["symbol"]
            assert chart.theme == config["chart"]["theme"]
            assert chart.height == config["chart"]["height"]

            print(f"  ✅ Chart instance created")
            print(f"  ✅ Configuration properties loaded")

            return True

        except Exception as e:
            self.errors.append(f"Chart creation failed: {e}")
            print(f"  ❌ Chart creation failed: {e}")
            return False

    def test_databento_connection(self):
        """Test Databento connection (if API key available)"""
        print("🌐 Testing Databento connection...")

        api_key = os.getenv('DATABENTO_API_KEY')
        if not api_key:
            self.warnings.append("DATABENTO_API_KEY not set - skipping connection test")
            print("  ⚠️ DATABENTO_API_KEY not set - skipping connection test")
            return True

        try:
            sys.path.append(str(self.script_dir))

            from databento_5m_provider import Databento5MinuteProvider

            provider = Databento5MinuteProvider()

            # Test with minimal data request
            df = provider.get_latest_bars("NQM5", 1)

            if df is not None and not df.empty:
                print(f"  ✅ Databento connection successful")
                print(f"  ✅ Data retrieval working")
                return True
            else:
                self.warnings.append("Databento connection successful but no data returned")
                print("  ⚠️ Connection successful but no data returned")
                return True

        except Exception as e:
            self.warnings.append(f"Databento connection test failed: {e}")
            print(f"  ⚠️ Databento connection test failed: {e}")
            return True  # Don't fail installation for connection issues

    def test_command_line_interface(self):
        """Test command line interface"""
        print("💻 Testing command line interface...")

        try:
            # Test help command
            result = subprocess.run([
                sys.executable,
                str(self.script_dir / "nq_5m_chart.py"),
                "--help"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                print("  ✅ Command line help working")
            else:
                self.warnings.append("Command line help returned non-zero exit code")
                print("  ⚠️ Command line help issues")

            # Test list configs
            result = subprocess.run([
                sys.executable,
                str(self.script_dir / "nq_5m_chart.py"),
                "--list-configs"
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0 and "default" in result.stdout:
                print("  ✅ Configuration listing working")
            else:
                self.warnings.append("Configuration listing not working properly")
                print("  ⚠️ Configuration listing issues")

            return True

        except subprocess.TimeoutExpired:
            self.warnings.append("Command line interface tests timed out")
            print("  ⚠️ Command line tests timed out")
            return True
        except Exception as e:
            self.warnings.append(f"Command line interface test failed: {e}")
            print(f"  ⚠️ Command line test failed: {e}")
            return True

    def run_all_tests(self):
        """Run all installation tests"""
        print("🚀 5-Minute Chart Installation Test")
        print("=" * 50)

        tests = [
            ("Python Version", self.test_python_version),
            ("Required Packages", self.test_required_packages),
            ("Project Structure", self.test_project_structure),
            ("Configuration System", self.test_configuration_system),
            ("Chart Creation", self.test_chart_creation),
            ("Databento Connection", self.test_databento_connection),
            ("Command Line Interface", self.test_command_line_interface),
        ]

        passed = 0
        failed = 0

        for test_name, test_func in tests:
            print(f"\n{test_name}:")
            try:
                if test_func():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                self.errors.append(f"Test {test_name} crashed: {e}")
                failed += 1
                print(f"  ❌ Test crashed: {e}")

        # Summary
        print("\n" + "=" * 50)
        print("📋 INSTALLATION TEST SUMMARY")
        print("=" * 50)

        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️ Warnings: {len(self.warnings)}")

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")

        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if not self.errors:
            print(f"\n🎉 Installation test completed successfully!")
            print(f"✅ All critical components are working")

            if self.warnings:
                print(f"⚠️ Some warnings detected - check configuration")

            print(f"\n🚀 Ready to use:")
            print(f"  python3 scripts/nq_5m_chart.py --list-configs")
            print(f"  python3 scripts/nq_5m_chart.py --config default --save")

            return True
        else:
            print(f"\n❌ Installation test failed!")
            print(f"🔧 Please fix the errors above before using the system")
            return False

def main():
    """Main entry point"""
    tester = InstallationTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
