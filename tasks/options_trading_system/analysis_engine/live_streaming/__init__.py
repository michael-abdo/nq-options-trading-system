"""
Live Streaming Components for IFD v3.0

This package contains all real-time streaming components for live institutional flow detection:
- StreamingBridge: Connects MBO streams to IFD analysis
- EventProcessor: Filters and batches streaming events
- PressureAggregator: Aggregates pressure metrics across timeframes
- DataValidator: Validates streaming data quality
- BaselineContextManager: Manages real-time baselines
"""

# Core streaming components
from .streaming_bridge import (
    StreamingBridge,
    create_streaming_bridge,
    create_dashboard_streaming_bridge,
    LiveSignalManager
)

from .event_processor import (
    EventProcessor,
    create_standard_processor
)

from .pressure_aggregator import (
    RealTimePressureEngine,
    create_standard_engine
)

from .data_validator import (
    StreamingDataValidator,
    create_mbo_validation_rules,
    ValidationResult
)

from .baseline_context_manager import (
    RealTimeBaselineManager,
    create_baseline_manager,
    BaselineContext
)

from .websocket_server import (
    DashboardWebSocketServer,
    WebSocketSignalBroadcaster,
    create_dashboard_websocket_server
)

# Version
__version__ = "1.0.0"

# Main exports
__all__ = [
    # Streaming Bridge
    "StreamingBridge",
    "create_streaming_bridge",
    "create_dashboard_streaming_bridge",
    "LiveSignalManager",

    # Event Processing
    "EventProcessor",
    "create_standard_processor",

    # Pressure Aggregation
    "RealTimePressureEngine",
    "create_standard_engine",

    # Data Validation
    "StreamingDataValidator",
    "create_mbo_validation_rules",
    "ValidationResult",

    # Baseline Management
    "RealTimeBaselineManager",
    "create_baseline_manager",
    "BaselineContext",

    # WebSocket Server
    "DashboardWebSocketServer",
    "WebSocketSignalBroadcaster",
    "create_dashboard_websocket_server"
]

# Factory function for complete live streaming setup
def create_live_streaming_pipeline(config=None):
    """
    Create a complete live streaming pipeline with all components

    Args:
        config: Configuration dictionary for all components

    Returns:
        Dictionary containing all initialized components
    """
    config = config or {}

    # Create all components
    bridge = create_streaming_bridge(config.get('bridge', {}))
    processor = create_standard_processor()
    engine = create_standard_engine()
    validator = StreamingDataValidator(create_mbo_validation_rules())
    baseline_manager = create_baseline_manager()

    return {
        'bridge': bridge,
        'processor': processor,
        'engine': engine,
        'validator': validator,
        'baseline_manager': baseline_manager
    }
