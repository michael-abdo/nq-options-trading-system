"""
Analysis Engine - Live Streaming Components

This package provides real-time streaming integration for IFD v3.0 analysis.
"""

# Core integration
from .integration import (
    AnalysisEngine,
    run_analysis_engine,
    run_ab_testing_analysis,
    run_specific_algorithm,
    compare_algorithm_performance
)

# Live streaming components
try:
    from .live_streaming import (
        StreamingBridge,
        create_streaming_bridge,
        create_dashboard_streaming_bridge,
        EventProcessor,
        create_standard_processor,
        RealTimePressureEngine,
        create_standard_engine,
        StreamingDataValidator,
        create_mbo_validation_rules,
        ValidationResult,
        RealTimeBaselineManager,
        create_baseline_manager,
        BaselineContext,
        create_live_streaming_pipeline
    )

    LIVE_STREAMING_AVAILABLE = True

except ImportError:
    LIVE_STREAMING_AVAILABLE = False

# Version
__version__ = "3.0.0"

# Main exports
__all__ = [
    # Core
    "AnalysisEngine",
    "run_analysis_engine",
    "run_ab_testing_analysis",
    "run_specific_algorithm",
    "compare_algorithm_performance",

    # Live streaming
    "StreamingBridge",
    "create_streaming_bridge",
    "create_dashboard_streaming_bridge",
    "EventProcessor",
    "create_standard_processor",
    "RealTimePressureEngine",
    "create_standard_engine",
    "StreamingDataValidator",
    "create_mbo_validation_rules",
    "ValidationResult",
    "RealTimeBaselineManager",
    "create_baseline_manager",
    "BaselineContext",
    "create_live_streaming_pipeline",

    # Status
    "LIVE_STREAMING_AVAILABLE"
]
