#!/usr/bin/env python3
"""
5-Minute Chart Configuration Manager
Handles loading, validation, and management of chart configurations
"""

import json
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
import jsonschema
from jsonschema import validate, ValidationError

logger = logging.getLogger(__name__)

class ChartConfigManager:
    """Manages 5-minute chart configuration files and settings"""

    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager

        Args:
            config_dir: Directory containing config files (default: ../config)
        """
        if config_dir is None:
            script_dir = Path(__file__).parent
            self.config_dir = script_dir.parent / "config"
        else:
            self.config_dir = Path(config_dir)

        self.schema_file = self.config_dir / "5m_chart_config.json"
        self.examples_dir = self.config_dir / "5m_chart_examples"
        self.user_config_file = self.config_dir / "5m_chart_user.json"

        # Load schema for validation
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for validation"""
        try:
            with open(self.schema_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"Schema file not found: {self.schema_file}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {e}")
            return {}

    def load_config(self, config_name: str = "default") -> Dict[str, Any]:
        """
        Load a configuration by name

        Args:
            config_name: Name of config to load (default, scalping, etc.)

        Returns:
            Dictionary containing configuration
        """
        # Try user config first
        if config_name == "user" and self.user_config_file.exists():
            config_file = self.user_config_file
        else:
            # Try examples directory
            config_file = self.examples_dir / f"{config_name}.json"

        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            return self._get_default_config()

        try:
            with open(config_file, 'r') as f:
                config = json.load(f)

            # Validate against schema
            if self.schema:
                self.validate_config(config)

            logger.info(f"Loaded configuration: {config_name}")
            return config

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_file}: {e}")
            return self._get_default_config()
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            return self._get_default_config()

    def save_user_config(self, config: Dict[str, Any]) -> bool:
        """
        Save user configuration to persistent file

        Args:
            config: Configuration dictionary to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Validate before saving
            if self.schema:
                self.validate_config(config)

            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.user_config_file, 'w') as f:
                json.dump(config, f, indent=2)

            logger.info(f"Saved user configuration to: {self.user_config_file}")
            return True

        except ValidationError as e:
            logger.error(f"Cannot save invalid configuration: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against schema

        Args:
            config: Configuration to validate

        Returns:
            True if valid, raises ValidationError if invalid
        """
        if not self.schema:
            logger.warning("No schema available for validation")
            return True

        try:
            validate(instance=config, schema=self.schema)
            return True
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            raise

    def list_available_configs(self) -> List[str]:
        """
        List all available configuration files

        Returns:
            List of configuration names
        """
        configs = []

        # Add user config if it exists
        if self.user_config_file.exists():
            configs.append("user")

        # Add example configs
        if self.examples_dir.exists():
            for config_file in self.examples_dir.glob("*.json"):
                configs.append(config_file.stem)

        return sorted(configs)

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get a basic default configuration

        Returns:
            Default configuration dictionary
        """
        return {
            "chart": {
                "theme": "dark",
                "height": 800,
                "width": 1200,
                "update_interval": 30,
                "time_range_hours": 4,
                "show_volume": True,
                "volume_height_ratio": 0.3
            },
            "indicators": {
                "enabled": ["sma"],
                "sma": {
                    "periods": [20, 50],
                    "colors": ["blue", "orange"]
                },
                "ema": {
                    "periods": [12, 26],
                    "colors": ["cyan", "magenta"]
                },
                "vwap": {
                    "enabled": False,
                    "color": "yellow",
                    "line_width": 2.0
                }
            },
            "data": {
                "symbol": "NQM5",
                "timezone": "US/Eastern",
                "cache_enabled": True,
                "cache_duration_minutes": 15
            },
            "display": {
                "price_format": "decimal_2",
                "volume_format": "thousands",
                "show_current_price": True,
                "show_statistics": True,
                "show_update_time": True,
                "grid_enabled": True
            },
            "export": {
                "default_format": "html",
                "include_timestamp": True,
                "output_directory": "outputs"
            }
        }

    def get_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get a summary of configuration settings

        Args:
            config: Configuration dictionary

        Returns:
            Summary dictionary
        """
        return {
            "theme": config.get("chart", {}).get("theme", "unknown"),
            "update_interval": config.get("chart", {}).get("update_interval", 0),
            "time_range": config.get("chart", {}).get("time_range_hours", 0),
            "indicators_enabled": config.get("indicators", {}).get("enabled", []),
            "show_volume": config.get("chart", {}).get("show_volume", False),
            "symbol": config.get("data", {}).get("symbol", "unknown")
        }

    def merge_configs(self, base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two configurations with override taking precedence

        Args:
            base_config: Base configuration
            override_config: Override configuration (CLI args, etc.)

        Returns:
            Merged configuration
        """
        def deep_merge(base: Dict, override: Dict) -> Dict:
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        return deep_merge(base_config, override_config)

def main():
    """Demo of configuration manager"""
    import argparse

    parser = argparse.ArgumentParser(description="Chart Configuration Manager Demo")
    parser.add_argument("--config", default="default", help="Configuration to load")
    parser.add_argument("--list", action="store_true", help="List available configurations")
    parser.add_argument("--validate", help="Validate a specific configuration file")

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(level=logging.INFO)

    config_manager = ChartConfigManager()

    if args.list:
        print("Available configurations:")
        for config in config_manager.list_available_configs():
            print(f"  - {config}")
    elif args.validate:
        try:
            config = config_manager.load_config(args.validate)
            print(f"✅ Configuration '{args.validate}' is valid")
            summary = config_manager.get_config_summary(config)
            print(f"Summary: {summary}")
        except Exception as e:
            print(f"❌ Configuration '{args.validate}' is invalid: {e}")
    else:
        config = config_manager.load_config(args.config)
        print(f"Loaded configuration '{args.config}':")
        print(json.dumps(config_manager.get_config_summary(config), indent=2))

if __name__ == "__main__":
    main()
