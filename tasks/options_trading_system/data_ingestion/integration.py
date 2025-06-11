#!/usr/bin/env python3
"""
TASK: data_ingestion
TYPE: Parent Task Integration
PURPOSE: Integrate all data source children into unified data pipeline
"""

import sys
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add child tasks to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import data normalizer (still needed for pipeline)
from data_normalizer.solution import normalize_loaded_data


class DataIngestionPipeline:
    """Integrated data ingestion pipeline combining all data sources"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize pipeline with configuration
        
        Args:
            config: Dict with source configurations
        """
        self.config = config
        self.sources = {}
        self.normalized_data = None
        self.pipeline_metadata = {
            "pipeline_version": "1.0",
            "created_at": datetime.now().isoformat(),
            "sources_configured": list(config.keys())
        }
    
    def load_all_sources(self) -> Dict[str, Any]:
        """Load data from all configured sources using registry-driven approach"""
        results = {}
        
        # Import registry for dynamic source loading
        from sources_registry import get_sources_registry
        registry = get_sources_registry()
        
        # Handle both old-style config and new-style config
        if "data_sources" in self.config:
            # New configuration format with enabled/disabled sources
            from ..config_manager import get_config_manager
            config_manager = get_config_manager()
            
            enabled_sources = config_manager.get_enabled_sources(self.config)
            print(f"🔧 Enabled sources: {enabled_sources}")
            
            for source_name in enabled_sources:
                try:
                    # Validate source is available
                    if not registry.is_source_available(source_name):
                        results[source_name] = {
                            "status": "failed",
                            "error": f"Source not available: {source_name}"
                        }
                        continue
                    
                    # Get source configuration
                    source_config = config_manager.get_source_config(self.config, source_name)
                    
                    # Load data using registry
                    source_data = registry.load_source(source_name, source_config)
                    
                    # Process the result into standard pipeline format
                    results[source_name] = self._process_source_result(source_name, source_data)
                    
                except Exception as e:
                    print(f"❌ Failed to load {source_name}: {e}")
                    results[source_name] = {
                        "status": "failed",
                        "error": str(e)
                    }
        else:
            # Legacy configuration format - maintain backward compatibility
            self._load_sources_legacy_format(results, registry)
        
        self.sources = results
        return results
    
    def _process_source_result(self, source_name: str, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process raw source data into standard pipeline format"""
        
        # Handle different source data formats
        if "options_summary" in source_data:
            # Standard format
            total_contracts = source_data["options_summary"]["total_contracts"]
            quality_metrics = source_data.get("quality_metrics", {})
        elif "raw_data" in source_data:
            # Live API format  
            total_contracts = source_data.get("total_contracts", 0)
            quality_metrics = {
                "data_source": "live",
                "total_contracts": total_contracts,
                "volume_coverage": 1.0 if total_contracts > 0 else 0.0,
                "oi_coverage": 1.0 if total_contracts > 0 else 0.0
            }
            # Convert to standard format
            source_data = {
                "source": source_data.get("source", source_name),
                "raw_data": source_data["raw_data"],
                "options_summary": {"total_contracts": total_contracts},
                "quality_metrics": quality_metrics
            }
        else:
            # Minimal format
            total_contracts = 0
            quality_metrics = {
                "data_source": source_name,
                "total_contracts": 0,
                "volume_coverage": 0.0,
                "oi_coverage": 0.0
            }
        
        return {
            "status": "success",
            "contracts": total_contracts,
            "quality": quality_metrics,
            "data": source_data
        }
    
    def _load_sources_legacy_format(self, results: Dict[str, Any], registry):
        """Load sources using legacy configuration format for backward compatibility"""
        
        # Legacy format: check for each source individually using registry
        legacy_source_map = {
            "barchart": "barchart",
            "tradovate": "tradovate", 
            "polygon": "polygon",
            "databento": "databento"
        }
        
        for config_key, source_name in legacy_source_map.items():
            if config_key in self.config:
                try:
                    if registry.is_source_available(source_name):
                        source_data = registry.load_source(source_name, self.config[config_key])
                        results[source_name] = self._process_source_result(source_name, source_data)
                    else:
                        results[source_name] = {
                            "status": "failed",
                            "error": f"Source not available: {source_name}"
                        }
                except Exception as e:
                    results[source_name] = {
                        "status": "failed",
                        "error": str(e)
                    }
    
    def normalize_pipeline_data(self) -> Dict[str, Any]:
        """Normalize all loaded data into standard format"""
        if not self.sources:
            raise ValueError("No data sources loaded. Call load_all_sources() first.")
        
        # Use the data_normalizer to normalize already loaded sources
        normalized_result = normalize_loaded_data(self.sources)
        
        self.normalized_data = normalized_result
        return normalized_result
    
    def get_pipeline_summary(self) -> Dict[str, Any]:
        """Get summary of the entire data pipeline"""
        if not self.normalized_data:
            raise ValueError("No normalized data available. Run pipeline first.")
        
        summary = {
            "pipeline_metadata": self.pipeline_metadata,
            "sources_loaded": len([s for s in self.sources.values() if s["status"] == "success"]),
            "sources_failed": len([s for s in self.sources.values() if s["status"] == "failed"]),
            "total_contracts": self.normalized_data["normalized_data"]["summary"]["total_contracts"],
            "data_quality": self.normalized_data["quality_metrics"],
            "timestamp": datetime.now().isoformat()
        }
        
        # Add per-source summaries
        summary["source_details"] = {}
        for source_name, source_data in self.sources.items():
            if source_data["status"] == "success":
                summary["source_details"][source_name] = {
                    "contracts": source_data["contracts"],
                    "volume_coverage": source_data["quality"]["volume_coverage"],
                    "oi_coverage": source_data["quality"]["oi_coverage"]
                }
        
        return summary
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """Execute the complete data ingestion pipeline"""
        # Step 1: Load all sources
        load_results = self.load_all_sources()
        
        # Step 2: Normalize data
        normalized = self.normalize_pipeline_data()
        
        # Step 3: Get summary
        summary = self.get_pipeline_summary()
        
        return {
            "pipeline_status": "success",
            "load_results": load_results,
            "normalized_data": normalized["normalized_data"],
            "quality_metrics": normalized["quality_metrics"],
            "summary": summary
        }


# Module-level integration function
def create_data_ingestion_pipeline(config: Dict[str, Any]) -> DataIngestionPipeline:
    """
    Create and return configured data ingestion pipeline
    
    Args:
        config: Configuration for data sources
        
    Returns:
        Configured DataIngestionPipeline instance
    """
    return DataIngestionPipeline(config)


def run_data_ingestion(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run the complete data ingestion pipeline
    
    Args:
        config: Configuration for data sources
        
    Returns:
        Dict with pipeline results
    """
    pipeline = create_data_ingestion_pipeline(config)
    return pipeline.run_full_pipeline()