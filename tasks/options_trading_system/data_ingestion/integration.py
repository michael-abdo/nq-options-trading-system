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

# Import validated child solutions
from barchart_saved_data.solution import load_barchart_saved_data
from tradovate_api_data.solution import load_tradovate_api_data
from data_normalizer.solution import normalize_options_data


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
        """Load data from all configured sources"""
        results = {}
        
        # Load Barchart if configured
        if "barchart" in self.config:
            try:
                barchart_data = load_barchart_saved_data(
                    self.config["barchart"]["file_path"]
                )
                results["barchart"] = {
                    "status": "success",
                    "contracts": barchart_data["options_summary"]["total_contracts"],
                    "quality": barchart_data["quality_metrics"],
                    "data": barchart_data
                }
            except Exception as e:
                results["barchart"] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # Load Tradovate if configured
        if "tradovate" in self.config:
            try:
                tradovate_data = load_tradovate_api_data(
                    self.config["tradovate"]
                )
                results["tradovate"] = {
                    "status": "success",
                    "contracts": tradovate_data["options_summary"]["total_contracts"],
                    "quality": tradovate_data["quality_metrics"],
                    "data": tradovate_data
                }
            except Exception as e:
                results["tradovate"] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        self.sources = results
        return results
    
    def normalize_pipeline_data(self) -> Dict[str, Any]:
        """Normalize all loaded data into standard format"""
        if not self.sources:
            raise ValueError("No data sources loaded. Call load_all_sources() first.")
        
        # Use the data_normalizer to normalize all sources
        normalized_result = normalize_options_data(self.config)
        
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