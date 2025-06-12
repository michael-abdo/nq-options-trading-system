#!/usr/bin/env python3
"""
Enhanced Configuration Manager for IFD v1.0 vs v3.0 A/B Testing

This module provides a comprehensive configuration management system that supports:
- Separate config profiles for v1.0 and v3.0 algorithms
- A/B testing configuration framework
- Real-time vs historical data mode selection
- Backward compatibility with existing pipeline
- Performance comparison and validation settings
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from enum import Enum


class DataMode(Enum):
    """Data processing modes"""
    REAL_TIME = "real_time"
    HISTORICAL = "historical"
    SIMULATION = "simulation"


class AlgorithmVersion(Enum):
    """Algorithm versions for institutional flow detection"""
    V1_0 = "v1.0"  # Dead Simple Volume Spike
    V3_0 = "v3.0"  # Enhanced MBO Streaming with Baselines
    BOTH = "both"  # A/B testing mode


class TestingMode(Enum):
    """Testing and validation modes"""
    PRODUCTION = "production"
    A_B_TESTING = "ab_testing"
    PAPER_TRADING = "paper_trading"
    VALIDATION = "validation"


@dataclass
class ConfigProfile:
    """Configuration profile for different scenarios"""
    name: str
    description: str
    algorithm_version: AlgorithmVersion
    data_mode: DataMode
    testing_mode: TestingMode
    config: Dict[str, Any]
    created_at: datetime
    last_modified: datetime


class ConfigManager:
    """
    Enhanced configuration manager for IFD v1.0 vs v3.0 A/B testing

    Features:
    - Profile-based configuration management
    - A/B testing support with parallel execution
    - Data mode switching (real-time vs historical)
    - Performance comparison settings
    - Backward compatibility
    """

    def __init__(self, config_dir: str = "config/profiles"):
        """
        Initialize configuration manager

        Args:
            config_dir: Directory to store configuration profiles
        """
        self.config_dir = config_dir
        self.profiles: Dict[str, ConfigProfile] = {}

        # Ensure config directory exists
        os.makedirs(config_dir, exist_ok=True)

        # Load existing profiles
        self._load_profiles()

        # Create default profiles if none exist
        if not self.profiles:
            self._create_default_profiles()

    def _load_profiles(self):
        """Load configuration profiles from disk"""
        if not os.path.exists(self.config_dir):
            return

        for filename in os.listdir(self.config_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(self.config_dir, filename)
                try:
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        profile = ConfigProfile(
                            name=data['name'],
                            description=data['description'],
                            algorithm_version=AlgorithmVersion(data['algorithm_version']),
                            data_mode=DataMode(data['data_mode']),
                            testing_mode=TestingMode(data['testing_mode']),
                            config=data['config'],
                            created_at=datetime.fromisoformat(data['created_at']),
                            last_modified=datetime.fromisoformat(data['last_modified'])
                        )
                        self.profiles[profile.name] = profile
                except Exception as e:
                    print(f"Warning: Failed to load profile {filename}: {e}")

    def _save_profile(self, profile: ConfigProfile):
        """Save configuration profile to disk"""
        filepath = os.path.join(self.config_dir, f"{profile.name}.json")

        data = {
            'name': profile.name,
            'description': profile.description,
            'algorithm_version': profile.algorithm_version.value,
            'data_mode': profile.data_mode.value,
            'testing_mode': profile.testing_mode.value,
            'config': profile.config,
            'created_at': profile.created_at.isoformat(),
            'last_modified': profile.last_modified.isoformat()
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def _create_default_profiles(self):
        """Create default configuration profiles"""

        # v1.0 Production Profile
        v1_production = ConfigProfile(
            name="ifd_v1_production",
            description="IFD v1.0 Dead Simple Algorithm - Production Settings",
            algorithm_version=AlgorithmVersion.V1_0,
            data_mode=DataMode.REAL_TIME,
            testing_mode=TestingMode.PRODUCTION,
            config={
                "dead_simple": {
                    "min_vol_oi_ratio": 10,
                    "min_volume": 500,
                    "min_dollar_size": 100000,
                    "max_distance_percent": 2.0,
                    "confidence_thresholds": {
                        "extreme": 50,
                        "very_high": 30,
                        "high": 20,
                        "moderate": 10
                    }
                },
                "data_sources": {
                    "primary": ["barchart", "polygon"],
                    "fallback": ["tradovate"],
                    "mode": "real_time"
                },
                "risk_management": {
                    "max_position_size": 10,
                    "max_daily_trades": 20,
                    "stop_loss_percent": 15
                }
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )

        # v3.0 Production Profile
        v3_production = ConfigProfile(
            name="ifd_v3_production",
            description="IFD v3.0 Enhanced MBO Streaming - Production Settings",
            algorithm_version=AlgorithmVersion.V3_0,
            data_mode=DataMode.REAL_TIME,
            testing_mode=TestingMode.PRODUCTION,
            config={
                "institutional_flow_v3": {
                    "db_path": "outputs/ifd_v3_production.db",
                    "pressure_thresholds": {
                        "min_pressure_ratio": 2.0,
                        "min_volume_concentration": 0.4,
                        "min_time_persistence": 0.5,
                        "min_trend_strength": 0.6
                    },
                    "confidence_thresholds": {
                        "min_baseline_anomaly": 2.0,
                        "min_overall_confidence": 0.7
                    },
                    "market_making_penalty": 0.4,
                    "historical_baselines": {
                        "lookback_days": 20,
                        "min_data_quality": 0.9
                    }
                },
                "data_sources": {
                    "primary": ["databento"],
                    "fallback": ["barchart", "polygon"],
                    "mode": "real_time",
                    "mbo_streaming": True
                },
                "risk_management": {
                    "max_position_size": 15,
                    "max_daily_trades": 30,
                    "stop_loss_percent": 12,
                    "confidence_scaling": True
                }
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )

        # A/B Testing Profile
        ab_testing = ConfigProfile(
            name="ab_testing_production",
            description="A/B Testing v1.0 vs v3.0 - Live Comparison",
            algorithm_version=AlgorithmVersion.BOTH,
            data_mode=DataMode.REAL_TIME,
            testing_mode=TestingMode.A_B_TESTING,
            config={
                "ab_testing": {
                    "enabled": True,
                    "split_ratio": 0.5,  # 50/50 split
                    "comparison_period_hours": 24,
                    "min_signals_for_comparison": 10,
                    "performance_metrics": [
                        "signal_accuracy",
                        "win_rate",
                        "false_positive_rate",
                        "average_confidence",
                        "processing_latency"
                    ]
                },
                "v1_config": v1_production.config["dead_simple"],
                "v3_config": v3_production.config["institutional_flow_v3"],
                "data_sources": {
                    "shared": True,
                    "primary": ["databento", "barchart"],
                    "mode": "real_time"
                },
                "performance_tracking": {
                    "track_processing_time": True,
                    "track_memory_usage": True,
                    "track_api_costs": True,
                    "save_comparison_data": True,
                    "comparison_output_dir": "outputs/ab_testing"
                }
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )

        # Paper Trading Profile
        paper_trading = ConfigProfile(
            name="paper_trading_validation",
            description="Paper Trading Validation - Historical Data Testing",
            algorithm_version=AlgorithmVersion.BOTH,
            data_mode=DataMode.HISTORICAL,
            testing_mode=TestingMode.PAPER_TRADING,
            config={
                "paper_trading": {
                    "enabled": True,
                    "simulation_period_days": 14,
                    "starting_capital": 100000,
                    "position_sizing": "confidence_weighted",
                    "transaction_costs": 0.02,  # $2 per contract
                    "slippage": 0.25  # quarter point
                },
                "v1_config": {
                    **v1_production.config["dead_simple"],
                    # Adjusted for paper trading
                    "min_vol_oi_ratio": 8,  # Slightly looser for more signals
                    "min_dollar_size": 75000  # Lower threshold for testing
                },
                "v3_config": {
                    **v3_production.config["institutional_flow_v3"],
                    # Adjusted for paper trading
                    "pressure_thresholds": {
                        "min_pressure_ratio": 1.8,  # Slightly looser
                        "min_volume_concentration": 0.35,
                        "min_time_persistence": 0.45,
                        "min_trend_strength": 0.55
                    },
                    "confidence_thresholds": {
                        "min_baseline_anomaly": 1.8,
                        "min_overall_confidence": 0.65
                    }
                },
                "data_sources": {
                    "mode": "historical",
                    "date_range": {
                        "start": "2025-05-27",  # 2 weeks before current
                        "end": "2025-06-09"
                    },
                    "primary": ["barchart"],  # Use cached historical data
                    "simulation_speed": 1.0  # Real-time speed
                },
                "validation_metrics": {
                    "track_pnl": True,
                    "track_drawdown": True,
                    "track_sharpe_ratio": True,
                    "track_win_rate": True,
                    "track_signal_quality": True,
                    "generate_trade_log": True
                }
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )

        # Conservative Testing Profile
        conservative_testing = ConfigProfile(
            name="conservative_testing",
            description="Conservative Testing - High Confidence Signals Only",
            algorithm_version=AlgorithmVersion.V3_0,
            data_mode=DataMode.REAL_TIME,
            testing_mode=TestingMode.VALIDATION,
            config={
                "institutional_flow_v3": {
                    "db_path": "outputs/ifd_v3_conservative.db",
                    "pressure_thresholds": {
                        "min_pressure_ratio": 3.0,  # Very high threshold
                        "min_volume_concentration": 0.6,
                        "min_time_persistence": 0.7,
                        "min_trend_strength": 0.8
                    },
                    "confidence_thresholds": {
                        "min_baseline_anomaly": 3.0,  # 3 standard deviations
                        "min_overall_confidence": 0.85  # Very high confidence
                    },
                    "market_making_penalty": 0.5,  # Strong MM filtering
                    "historical_baselines": {
                        "lookback_days": 30,  # Longer baseline
                        "min_data_quality": 0.95
                    }
                },
                "risk_management": {
                    "max_position_size": 5,  # Smaller positions
                    "max_daily_trades": 10,  # Fewer trades
                    "stop_loss_percent": 8,  # Tighter stops
                    "confidence_scaling": True,
                    "min_signal_confidence": 0.85
                }
            },
            created_at=datetime.now(),
            last_modified=datetime.now()
        )

        # Save all default profiles
        for profile in [v1_production, v3_production, ab_testing, paper_trading, conservative_testing]:
            self.profiles[profile.name] = profile
            self._save_profile(profile)

    def get_profile(self, name: str) -> Optional[ConfigProfile]:
        """Get configuration profile by name"""
        return self.profiles.get(name)

    def list_profiles(self) -> List[str]:
        """List all available configuration profiles"""
        return list(self.profiles.keys())

    def create_profile(self, name: str, description: str, algorithm_version: AlgorithmVersion,
                      data_mode: DataMode, testing_mode: TestingMode, config: Dict[str, Any]) -> ConfigProfile:
        """Create a new configuration profile"""

        profile = ConfigProfile(
            name=name,
            description=description,
            algorithm_version=algorithm_version,
            data_mode=data_mode,
            testing_mode=testing_mode,
            config=config,
            created_at=datetime.now(),
            last_modified=datetime.now()
        )

        self.profiles[name] = profile
        self._save_profile(profile)

        return profile

    def update_profile(self, name: str, **kwargs) -> Optional[ConfigProfile]:
        """Update an existing configuration profile"""

        if name not in self.profiles:
            return None

        profile = self.profiles[name]

        # Update fields
        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.last_modified = datetime.now()

        self._save_profile(profile)
        return profile

    def get_analysis_config(self, profile_name: str) -> Dict[str, Any]:
        """
        Get analysis configuration for the analysis engine

        Args:
            profile_name: Name of the configuration profile

        Returns:
            Dict compatible with run_analysis_engine()
        """
        profile = self.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Profile '{profile_name}' not found")

        # Base configuration with existing analyses
        analysis_config = {
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
            "risk": {
                "multiplier": 20,
                "immediate_threat_distance": 10,
                "near_term_distance": 25,
                "medium_term_distance": 50
            },
            "volume_shock": {
                "volume_ratio_threshold": 4.0,
                "min_volume_threshold": 100,
                "pressure_threshold": 50.0,
                "high_delta_threshold": 2000,
                "emergency_delta_threshold": 5000,
                "validation_mode": True
            }
        }

        # Add algorithm-specific configuration
        if profile.algorithm_version == AlgorithmVersion.V1_0:
            analysis_config["dead_simple"] = profile.config.get("dead_simple", {})

        elif profile.algorithm_version == AlgorithmVersion.V3_0:
            analysis_config["institutional_flow_v3"] = profile.config.get("institutional_flow_v3", {})

        elif profile.algorithm_version == AlgorithmVersion.BOTH:
            # A/B testing mode - include both
            analysis_config["dead_simple"] = profile.config.get("v1_config", {})
            analysis_config["institutional_flow_v3"] = profile.config.get("v3_config", {})
            analysis_config["ab_testing"] = profile.config.get("ab_testing", {})

        return analysis_config

    def get_data_config(self, profile_name: str) -> Dict[str, Any]:
        """
        Get data configuration for the data ingestion pipeline

        Args:
            profile_name: Name of the configuration profile

        Returns:
            Dict compatible with data ingestion pipeline
        """
        profile = self.get_profile(profile_name)
        if not profile:
            raise ValueError(f"Profile '{profile_name}' not found")

        data_sources = profile.config.get("data_sources", {})

        # Base data configuration
        data_config = {
            "mode": data_sources.get("mode", "real_time"),
            "primary_sources": data_sources.get("primary", ["barchart"]),
            "fallback_sources": data_sources.get("fallback", [])
        }

        # Add mode-specific configuration
        if profile.data_mode == DataMode.HISTORICAL:
            date_range = data_sources.get("date_range", {})
            data_config.update({
                "historical_mode": True,
                "start_date": date_range.get("start"),
                "end_date": date_range.get("end"),
                "simulation_speed": data_sources.get("simulation_speed", 1.0)
            })

        elif profile.data_mode == DataMode.REAL_TIME:
            data_config.update({
                "real_time_mode": True,
                "mbo_streaming": data_sources.get("mbo_streaming", False)
            })

        return data_config

    def create_ab_testing_config(self, v1_profile: str, v3_profile: str,
                                testing_duration_hours: int = 24) -> ConfigProfile:
        """
        Create A/B testing configuration from existing v1.0 and v3.0 profiles

        Args:
            v1_profile: Name of v1.0 profile
            v3_profile: Name of v3.0 profile
            testing_duration_hours: Duration for A/B testing

        Returns:
            New A/B testing profile
        """
        v1_config = self.get_profile(v1_profile)
        v3_config = self.get_profile(v3_profile)

        if not v1_config or not v3_config:
            raise ValueError("Both v1.0 and v3.0 profiles must exist")

        ab_config = {
            "ab_testing": {
                "enabled": True,
                "v1_profile": v1_profile,
                "v3_profile": v3_profile,
                "duration_hours": testing_duration_hours,
                "split_ratio": 0.5,
                "performance_metrics": [
                    "signal_accuracy", "win_rate", "processing_latency",
                    "false_positive_rate", "average_confidence"
                ]
            },
            "v1_config": v1_config.config,
            "v3_config": v3_config.config,
            "data_sources": {
                "shared": True,
                "mode": "real_time"
            }
        }

        profile_name = f"ab_test_{v1_profile}_vs_{v3_profile}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        return self.create_profile(
            name=profile_name,
            description=f"A/B Testing: {v1_profile} vs {v3_profile}",
            algorithm_version=AlgorithmVersion.BOTH,
            data_mode=DataMode.REAL_TIME,
            testing_mode=TestingMode.A_B_TESTING,
            config=ab_config
        )


# Module-level convenience functions
def get_config_manager() -> ConfigManager:
    """Get singleton configuration manager instance"""
    if not hasattr(get_config_manager, '_instance'):
        get_config_manager._instance = ConfigManager()
    return get_config_manager._instance


def load_profile_config(profile_name: str) -> Dict[str, Any]:
    """Load configuration for a specific profile"""
    manager = get_config_manager()
    return manager.get_analysis_config(profile_name)


def create_ab_test(v1_profile: str = "ifd_v1_production",
                  v3_profile: str = "ifd_v3_production") -> str:
    """Create A/B testing configuration and return profile name"""
    manager = get_config_manager()
    profile = manager.create_ab_testing_config(v1_profile, v3_profile)
    return profile.name


if __name__ == "__main__":
    # Example usage and testing
    manager = ConfigManager()

    print("Available profiles:")
    for profile_name in manager.list_profiles():
        profile = manager.get_profile(profile_name)
        print(f"  - {profile_name}: {profile.description}")
        print(f"    Algorithm: {profile.algorithm_version.value}, Mode: {profile.data_mode.value}")

    # Test A/B configuration creation
    ab_profile = manager.create_ab_testing_config("ifd_v1_production", "ifd_v3_production")
    print(f"\nCreated A/B testing profile: {ab_profile.name}")

    # Test configuration retrieval
    config = manager.get_analysis_config("ifd_v3_production")
    print(f"\nv3.0 analysis config keys: {list(config.keys())}")
