#!/usr/bin/env python3
"""
Configuration Manager for Options Trading System
Handles source enabling/disabling, validation, and configuration profiles
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Manages configuration for the options trading system with support for
    multiple data sources, source profiles, and validation
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._default_config = self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration"""
        return {
            "data_sources": {
                "databento": {
                    "enabled": True,
                    "config": {
                        "api_key": "${DATABENTO_API_KEY}",
                        "symbols": ["NQ"],
                        "use_cache": True,
                        "cache_dir": "outputs/databento_cache"
                    }
                },
                "barchart": {
                    "enabled": False,
                    "config": {
                        "use_live_api": True,
                        "futures_symbol": "NQM25",
                        "headless": True,
                        "file_path": "tasks/options_trading_system/data_ingestion/barchart_web_scraper/outputs/20250608/api_data/barchart_api_data_20250608_220140.json"
                    }
                },
                "polygon": {
                    "enabled": False,
                    "config": {
                        "api_key": "${POLYGON_API_KEY}",
                        "symbols": ["NQ"],
                        "use_cache": True
                    }
                },
                "tradovate": {
                    "enabled": False,
                    "config": {
                        "mode": "demo",
                        "cid": "6540", 
                        "secret": "f7a2b8f5-8348-424f-8ffa-047ab7502b7c",
                        "use_mock": True
                    }
                }
            },
            "analysis": {
                "expected_value": {
                    "weights": {
                        "oi_factor": 0.35,
                        "vol_factor": 0.25,
                        "pcr_factor": 0.25,
                        "distance_factor": 0.15
                    },
                    "min_ev": 15,
                    "min_probability": 0.60,
                    "max_risk": 150,
                    "min_risk_reward": 1.0
                },
                "momentum": {
                    "volume_threshold": 100,
                    "price_change_threshold": 0.05,
                    "momentum_window": 5,
                    "min_momentum_score": 0.6
                },
                "volatility": {
                    "iv_percentile_threshold": 75,
                    "iv_skew_threshold": 0.05,
                    "term_structure_slope_threshold": 0.02,
                    "min_volume_for_iv": 10
                }
            },
            "output": {
                "report": {
                    "style": "professional",
                    "include_details": True,
                    "include_market_context": True
                },
                "json": {
                    "include_raw_data": False,
                    "include_metadata": True,
                    "format_pretty": True,
                    "include_analysis_details": True
                }
            },
            "save": {
                "save_report": True,
                "save_json": True,
                "output_dir": "outputs",
                "timestamp_suffix": True
            }
        }
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get the default configuration"""
        return self._default_config.copy()
    
    def create_source_profile(self, profile_name: str, enabled_sources: List[str], 
                            source_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Create a source profile with specific sources enabled
        
        Args:
            profile_name: Name of the profile
            enabled_sources: List of source names to enable
            source_configs: Optional custom configurations for sources
            
        Returns:
            Complete configuration dict
        """
        config = self.get_default_config()
        
        # Disable all sources first
        for source_name in config["data_sources"]:
            config["data_sources"][source_name]["enabled"] = False
        
        # Enable specified sources
        for source_name in enabled_sources:
            if source_name in config["data_sources"]:
                config["data_sources"][source_name]["enabled"] = True
                
                # Apply custom config if provided
                if source_configs and source_name in source_configs:
                    config["data_sources"][source_name]["config"].update(
                        source_configs[source_name]
                    )
            else:
                logger.warning(f"Unknown source in profile {profile_name}: {source_name}")
        
        return config
    
    def save_profile(self, profile_name: str, config: Dict[str, Any]):
        """Save a configuration profile to file"""
        profile_file = self.config_dir / f"{profile_name}.json"
        
        with open(profile_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Saved profile '{profile_name}' to {profile_file}")
    
    def load_profile(self, profile_name: str) -> Dict[str, Any]:
        """Load a configuration profile from file"""
        profile_file = self.config_dir / f"{profile_name}.json"
        
        if not profile_file.exists():
            raise FileNotFoundError(f"Profile not found: {profile_file}")
        
        with open(profile_file, 'r') as f:
            config = json.load(f)
        
        # Resolve environment variables
        config = self._resolve_env_vars(config)
        
        logger.info(f"Loaded profile '{profile_name}' from {profile_file}")
        return config
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve environment variables in configuration"""
        config_str = json.dumps(config)
        
        # Replace ${VAR_NAME} with environment variable values
        import re
        env_vars = re.findall(r'\$\{([^}]+)\}', config_str)
        
        for env_var in env_vars:
            env_value = os.getenv(env_var)
            if env_value:
                config_str = config_str.replace(f"${{{env_var}}}", env_value)
            else:
                logger.warning(f"Environment variable not found: {env_var}")
        
        return json.loads(config_str)
    
    def get_enabled_sources(self, config: Dict[str, Any]) -> List[str]:
        """Get list of enabled source names from configuration"""
        enabled = []
        
        data_sources = config.get("data_sources", {})
        for source_name, source_config in data_sources.items():
            if source_config.get("enabled", False):
                enabled.append(source_name)
        
        return enabled
    
    def get_source_config(self, config: Dict[str, Any], source_name: str) -> Dict[str, Any]:
        """Get configuration for a specific source"""
        data_sources = config.get("data_sources", {})
        
        if source_name not in data_sources:
            raise ValueError(f"Source not found in configuration: {source_name}")
        
        source_data = data_sources[source_name]
        
        if not source_data.get("enabled", False):
            raise ValueError(f"Source is disabled: {source_name}")
        
        return source_data.get("config", {})
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """
        Validate configuration and return list of issues
        
        Returns:
            List of validation error messages (empty if valid)
        """
        issues = []
        
        # Check that at least one data source is enabled
        enabled_sources = self.get_enabled_sources(config)
        if not enabled_sources:
            issues.append("No data sources are enabled")
        
        # Validate each enabled source
        from data_ingestion.sources_registry import get_sources_registry
        registry = get_sources_registry()
        
        for source_name in enabled_sources:
            # Check if source is available
            if not registry.is_source_available(source_name):
                issues.append(f"Enabled source is not available: {source_name}")
                continue
            
            # Check required configuration
            try:
                source_config = self.get_source_config(config, source_name)
                source_info = registry.get_source_info(source_name)
                
                required_fields = source_info.get("required_config", [])
                for field in required_fields:
                    if field not in source_config:
                        issues.append(f"Missing required config for {source_name}: {field}")
                    elif not source_config[field]:
                        issues.append(f"Empty required config for {source_name}: {field}")
                        
            except Exception as e:
                issues.append(f"Error validating {source_name}: {str(e)}")
        
        return issues
    
    def create_standard_profiles(self):
        """Create and save standard configuration profiles"""
        
        # Databento only profile
        databento_config = self.create_source_profile("databento_only", ["databento"])
        self.save_profile("databento_only", databento_config)
        
        # Barchart only profile  
        barchart_config = self.create_source_profile("barchart_only", ["barchart"])
        self.save_profile("barchart_only", barchart_config)
        
        # All sources profile
        all_sources_config = self.create_source_profile(
            "all_sources", 
            ["databento", "barchart", "polygon", "tradovate"]
        )
        self.save_profile("all_sources", all_sources_config)
        
        # Testing profile (with mock data)
        testing_config = self.create_source_profile(
            "testing",
            ["barchart"],
            source_configs={
                "barchart": {
                    "use_live_api": False,
                    "file_path": "tasks/options_trading_system/data_ingestion/barchart_web_scraper/outputs/20250608/api_data/barchart_api_data_20250608_220140.json"
                }
            }
        )
        self.save_profile("testing", testing_config)
        
        logger.info("Created standard configuration profiles")
    
    def list_profiles(self) -> List[str]:
        """List all available configuration profiles"""
        profile_files = list(self.config_dir.glob("*.json"))
        return [f.stem for f in profile_files]
    
    def get_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary of configuration"""
        enabled_sources = self.get_enabled_sources(config)
        
        return {
            "enabled_sources": enabled_sources,
            "total_sources": len(config.get("data_sources", {})),
            "analysis_modules": list(config.get("analysis", {}).keys()),
            "output_formats": list(config.get("output", {}).keys()),
            "validation_issues": self.validate_config(config)
        }


# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


# Convenience functions
def load_config_profile(profile_name: str) -> Dict[str, Any]:
    """Load a configuration profile"""
    return get_config_manager().load_profile(profile_name)

def get_default_config() -> Dict[str, Any]:
    """Get the default configuration"""
    return get_config_manager().get_default_config()

def create_standard_profiles():
    """Create standard configuration profiles"""
    return get_config_manager().create_standard_profiles()

def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate a configuration"""
    return get_config_manager().validate_config(config)