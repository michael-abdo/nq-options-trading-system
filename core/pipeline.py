#!/usr/bin/env python3
"""
Pipeline orchestration engine for modular trading analysis
"""

import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Type
import importlib
import yaml

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logging_config import setup_logging, get_logger

from .interfaces import DataSourceInterface, StrategyInterface, OutputInterface
from .interfaces import DataSourceError, StrategyError, OutputError, ConfigurationError
from .data_models import OptionsChain, AnalysisResult


class AnalysisPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(self, config_path: str = None):
        """Initialize pipeline with configuration"""
        # Set up logging
        self.log_dir, self.session_id = setup_logging()
        self.logger = get_logger(__name__)
        
        # Load configuration
        self.config_path = config_path or "config"
        self.data_sources = {}
        self.strategies = {}
        self.outputs = {}
        
        self._load_configurations()
        self._register_plugins()
    
    def _load_configurations(self):
        """Load all configuration files"""
        self.logger.info("📁 Loading pipeline configurations...")
        
        config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), self.config_path)
        
        # Load data source configs
        try:
            with open(os.path.join(config_dir, "data_sources.yaml"), 'r') as f:
                self.data_source_configs = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning("⚠️ data_sources.yaml not found, using defaults")
            self.data_source_configs = {"sources": {}}
        
        # Load strategy configs
        try:
            with open(os.path.join(config_dir, "strategies.yaml"), 'r') as f:
                self.strategy_configs = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning("⚠️ strategies.yaml not found, using defaults")
            self.strategy_configs = {"strategies": {}}
        
        # Load pipeline configs
        try:
            with open(os.path.join(config_dir, "pipeline.yaml"), 'r') as f:
                self.pipeline_configs = yaml.safe_load(f)
        except FileNotFoundError:
            self.logger.warning("⚠️ pipeline.yaml not found, using defaults")
            self.pipeline_configs = {"pipelines": {}}
    
    def _register_plugins(self):
        """Register all available plugins"""
        self.logger.info("🔌 Registering plugins...")
        
        # Register data sources
        for name, config in self.data_source_configs.get("sources", {}).items():
            try:
                self.register_data_source(name, config)
            except Exception as e:
                self.logger.error(f"❌ Failed to register data source {name}: {e}")
        
        # Register strategies
        for name, config in self.strategy_configs.get("strategies", {}).items():
            try:
                self.register_strategy(name, config)
            except Exception as e:
                self.logger.error(f"❌ Failed to register strategy {name}: {e}")
        
        self.logger.info(f"✅ Registered {len(self.data_sources)} data sources, {len(self.strategies)} strategies")
    
    def register_data_source(self, name: str, config: Dict[str, Any]):
        """Register a data source plugin"""
        class_path = config["class"]
        module_path, class_name = class_path.rsplit(".", 1)
        
        try:
            module = importlib.import_module(module_path)
            source_class = getattr(module, class_name)
            
            if not issubclass(source_class, DataSourceInterface):
                raise ConfigurationError(f"Class {class_path} must inherit from DataSourceInterface")
            
            source_instance = source_class(config.get("config", {}))
            self.data_sources[name] = source_instance
            self.logger.info(f"📊 Registered data source: {name}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to register data source {name}: {e}")
    
    def register_strategy(self, name: str, config: Dict[str, Any]):
        """Register an analysis strategy plugin"""
        class_path = config["class"]
        module_path, class_name = class_path.rsplit(".", 1)
        
        try:
            module = importlib.import_module(module_path)
            strategy_class = getattr(module, class_name)
            
            if not issubclass(strategy_class, StrategyInterface):
                raise ConfigurationError(f"Class {class_path} must inherit from StrategyInterface")
            
            strategy_instance = strategy_class(config.get("config", {}))
            self.strategies[name] = strategy_instance
            self.logger.info(f"🧮 Registered strategy: {name}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to register strategy {name}: {e}")
    
    def get_data(self, source_name: str) -> OptionsChain:
        """Fetch data from a specific source"""
        if source_name not in self.data_sources:
            raise DataSourceError(f"Data source '{source_name}' not found")
        
        source = self.data_sources[source_name]
        self.logger.info(f"📡 Fetching data from {source_name}...")
        
        try:
            # Validate connection first
            if not source.validate_connection():
                raise DataSourceError(f"Cannot connect to {source_name}")
            
            # Fetch data
            data = source.fetch_data()
            
            # Log data quality
            quality = data.data_quality_metrics
            self.logger.info(f"📊 Data quality: {quality['total_contracts']} contracts, "
                           f"{quality['volume_coverage']:.1%} volume coverage, "
                           f"{quality['oi_coverage']:.1%} OI coverage")
            
            return data
            
        except Exception as e:
            raise DataSourceError(f"Failed to fetch data from {source_name}: {e}")
    
    def run_strategy(self, strategy_name: str, data: OptionsChain) -> AnalysisResult:
        """Run a specific strategy on data"""
        if strategy_name not in self.strategies:
            raise StrategyError(f"Strategy '{strategy_name}' not found")
        
        strategy = self.strategies[strategy_name]
        self.logger.info(f"🧮 Running strategy: {strategy_name}")
        
        try:
            # Validate data requirements
            is_valid, errors = strategy.validate_data(data)
            if not is_valid:
                raise StrategyError(f"Data validation failed for {strategy_name}: {errors}")
            
            # Run analysis
            result = strategy.analyze(data)
            
            # Log results
            self.logger.info(f"✅ Strategy {strategy_name} completed: "
                           f"{len(result.signals)} signals, {len(result.metrics)} metrics")
            
            return result
            
        except Exception as e:
            raise StrategyError(f"Strategy {strategy_name} failed: {e}")
    
    def run_pipeline(self, pipeline_name: str) -> List[AnalysisResult]:
        """Run a complete analysis pipeline"""
        if pipeline_name not in self.pipeline_configs.get("pipelines", {}):
            raise ConfigurationError(f"Pipeline '{pipeline_name}' not found")
        
        pipeline_config = self.pipeline_configs["pipelines"][pipeline_name]
        self.logger.info(f"🚀 Running pipeline: {pipeline_name}")
        
        results = []
        
        try:
            # 1. Fetch data
            source_name = pipeline_config["data_source"]
            data = self.get_data(source_name)
            
            # 2. Run strategies
            strategy_names = pipeline_config["strategies"]
            for strategy_name in strategy_names:
                try:
                    result = self.run_strategy(strategy_name, data)
                    results.append(result)
                except StrategyError as e:
                    self.logger.error(f"❌ Strategy {strategy_name} failed: {e}")
                    # Continue with other strategies
            
            # 3. Generate outputs (if configured)
            if "outputs" in pipeline_config:
                for output_name in pipeline_config["outputs"]:
                    try:
                        self._generate_output(output_name, results, data)
                    except Exception as e:
                        self.logger.error(f"❌ Output {output_name} failed: {e}")
            
            self.logger.info(f"✅ Pipeline {pipeline_name} completed: {len(results)} successful analyses")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Pipeline {pipeline_name} failed: {e}")
            raise
    
    def _generate_output(self, output_name: str, results: List[AnalysisResult], data: OptionsChain):
        """Generate output using specified formatter"""
        # This would be implemented with output plugins
        # For now, just log the results
        self.logger.info(f"📄 Generating output: {output_name}")
        
        # Simple text output for now
        if output_name == "summary":
            for result in results:
                self.logger.info(f"Strategy {result.strategy_name}: {len(result.signals)} signals")
    
    def list_available_components(self):
        """List all available components"""
        print("\n" + "="*60)
        print("AVAILABLE PIPELINE COMPONENTS")
        print("="*60)
        
        print(f"\n📊 Data Sources ({len(self.data_sources)}):")
        for name, source in self.data_sources.items():
            info = source.get_info()
            print(f"  • {name}: {info['name']}")
        
        print(f"\n🧮 Strategies ({len(self.strategies)}):")
        for name, strategy in self.strategies.items():
            info = strategy.get_info()
            reqs = info['requirements']
            print(f"  • {name}: {info['name']}")
            print(f"    Requirements: vol={reqs.requires_volume}, oi={reqs.requires_open_interest}")
        
        print(f"\n🚀 Pipelines ({len(self.pipeline_configs.get('pipelines', {}))}):")
        for name, config in self.pipeline_configs.get("pipelines", {}).items():
            source = config.get("data_source", "unknown")
            strategies = config.get("strategies", [])
            print(f"  • {name}: {source} → {', '.join(strategies)}")
        
        print("="*60)
    
    def run_single_analysis(self, source_name: str, strategy_names: List[str]) -> List[AnalysisResult]:
        """Run specific strategies on a data source"""
        self.logger.info(f"🎯 Running single analysis: {source_name} → {strategy_names}")
        
        # Get data
        data = self.get_data(source_name)
        
        # Run strategies
        results = []
        for strategy_name in strategy_names:
            try:
                result = self.run_strategy(strategy_name, data)
                results.append(result)
            except StrategyError as e:
                self.logger.error(f"❌ Strategy {strategy_name} failed: {e}")
        
        return results