#!/usr/bin/env python3
"""
Real-time Streaming Bridge - IFD v3.0 Live Integration

This module creates the critical bridge between MBO streaming data and IFD v3.0 analysis,
enabling real-time institutional flow detection from live market data.

Architecture:
- Connects MBOStreamingClient to IFDv3Engine
- Handles real-time pressure metrics processing
- Manages callback registration and event routing
- Provides cost monitoring and market hours controls
- Ensures bulletproof authentication and error handling

Integration Flow:
MBO WebSocket → PressureMetrics → IFD Analysis → InstitutionalSignalV3 → Dashboard
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from collections import deque
import queue

# Add paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
# Use current working directory as project root
project_root = os.getcwd()
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import required modules
try:
    from utils.timezone_utils import get_eastern_time, is_futures_market_hours
    TIMEZONE_UTILS_AVAILABLE = True
except ImportError:
    logger.warning("Timezone utils not available")
    TIMEZONE_UTILS_AVAILABLE = False
    # Create dummy functions
    def get_eastern_time():
        return datetime.now(timezone.utc)
    def is_futures_market_hours():
        return True

try:
    from scripts.databento_auth import DatabentoBulletproofAuth, ensure_trading_safe_databento_client
    DATABENTO_AUTH_AVAILABLE = True
except ImportError:
    logger.warning("Databento auth not available")
    DATABENTO_AUTH_AVAILABLE = False
    # Create dummy classes/functions
    class DatabentoBulletproofAuth:
        def load_and_validate_api_key(self): pass
        def assert_trading_safe(self): pass
    def ensure_trading_safe_databento_client():
        return type('Client', (), {'api_key': 'dummy'})()


# Import components
try:
    from tasks.options_trading_system.data_ingestion.databento_api.solution import (
        MBOStreamingClient, PressureMetrics, UsageMonitor, MBODatabase
    )
    from tasks.options_trading_system.analysis_engine.institutional_flow_v3.solution import (
        IFDv3Engine, InstitutionalSignalV3, create_ifd_v3_analyzer
    )
    COMPONENTS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Component imports not available: {e}")
    COMPONENTS_AVAILABLE = False

# Import WebSocket server components
try:
    from .websocket_server import create_dashboard_websocket_server, WebSocketSignalBroadcaster
    WEBSOCKET_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WebSocket server not available: {e}")
    WEBSOCKET_AVAILABLE = False

# Logger already set up above

class StreamingBridgeError(Exception):
    """Critical streaming bridge error"""
    pass

class LiveSignalManager:
    """Manages live institutional signals from real-time analysis"""

    def __init__(self, max_signals: int = 100):
        """Initialize signal manager

        Args:
            max_signals: Maximum number of signals to keep in memory
        """
        self.signals = deque(maxlen=max_signals)
        self.signal_callbacks = []
        self.lock = threading.Lock()

    def add_signal(self, signal: InstitutionalSignalV3):
        """Add new institutional signal"""
        with self.lock:
            self.signals.append(signal)

        # Notify callbacks
        for callback in self.signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")

    def register_signal_callback(self, callback: Callable[[InstitutionalSignalV3], None]):
        """Register callback for new signals"""
        self.signal_callbacks.append(callback)

    def get_recent_signals(self, limit: int = 10) -> List[InstitutionalSignalV3]:
        """Get recent signals"""
        with self.lock:
            return list(self.signals)[-limit:]

    def get_signal_summary(self) -> Dict[str, Any]:
        """Get summary of recent signal activity"""
        with self.lock:
            if not self.signals:
                return {
                    'total_signals': 0,
                    'avg_confidence': 0.0,
                    'latest_signal': None,
                    'signal_rate': 0.0
                }

            signals = list(self.signals)
            avg_confidence = sum(s.final_confidence for s in signals) / len(signals)

            return {
                'total_signals': len(signals),
                'avg_confidence': avg_confidence,
                'latest_signal': signals[-1].to_dict() if signals else None,
                'signal_rate': len(signals)  # Signals in recent window
            }

class StreamingBridge:
    """
    Real-time bridge connecting MBO streaming to IFD v3.0 analysis

    Responsibilities:
    - Connect MBO streaming client to IFD analysis engine
    - Process pressure metrics in real-time
    - Manage signal callbacks and distribution
    - Enforce market hours and cost controls
    - Provide comprehensive error handling and recovery
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize streaming bridge

        Args:
            config: Configuration for bridge components
        """
        self.config = config or self._get_default_config()

        # Determine mode
        self.mode = self.config.get('mode', 'production')
        self.is_development = self.mode == 'development'
        self.is_staging = self.mode == 'staging'
        self.is_production = self.mode == 'production'

        # Initialize core components
        self.mbo_client = None
        self.ifd_analyzer = None
        self.signal_manager = LiveSignalManager()
        self.is_running = False

        # WebSocket server for dashboard integration
        self.websocket_server = None
        self.websocket_broadcaster = None
        self.enable_websocket = self.config.get('enable_websocket_server', True)

        # Threading and safety
        self.bridge_thread = None
        self.stop_event = threading.Event()
        self.error_count = 0
        self.max_errors = self.config.get('max_errors', 10)

        # Performance tracking
        self.events_processed = 0
        self.signals_generated = 0
        self.start_time = None

        # Shadow mode for staging
        self.shadow_mode = self.is_staging
        self.shadow_signals = []

        # Data simulation for development
        self.use_simulated_data = self.is_development and self.config.get('data_simulation', True)

        logger.info(f"Streaming bridge initialized in {self.mode.upper()} mode")

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for streaming bridge"""
        return {
            # MBO Streaming
            'symbols': ['NQ.OPT'],
            'daily_budget': 25.0,

            # IFD Analysis
            'ifd_config': {
                'baseline_db_path': 'outputs/ifd_v3_baselines.db',
                'min_final_confidence': 0.6,
                'pressure_analysis': {
                    'min_pressure_ratio': 2.0,
                    'min_total_volume': 100,
                    'min_confidence': 0.8
                }
            },

            # Bridge Controls
            'max_errors': 10,
            'reconnect_delay': 30,
            'market_hours_enforcement': True,
            'cost_monitoring': True,

            # Database
            'mbo_db_path': 'outputs/mbo_streaming.db',

            # WebSocket Server
            'enable_websocket_server': True,
            'websocket_host': 'localhost',
            'websocket_port': 8765
        }

    def initialize_components(self):
        """Initialize MBO client and IFD analyzer with authentication"""
        try:
            # 1. Ensure trading-safe authentication
            if DATABENTO_AUTH_AVAILABLE and COMPONENTS_AVAILABLE:
                logger.info("🔐 Initializing bulletproof authentication...")
                client = ensure_trading_safe_databento_client()

                # 2. Initialize MBO streaming client
                logger.info("📡 Initializing MBO streaming client...")
                self.mbo_client = MBOStreamingClient(
                    api_key=client.api_key,
                    symbols=self.config.get('symbols', ['NQ.OPT'])
                )
            else:
                logger.info("🧪 Using mock MBO client for testing")
                self.mbo_client = type('MockMBOClient', (), {
                    'api_key': 'mock_key',
                    'start_streaming': lambda: None,
                    'stop_streaming': lambda: None,
                    'on_pressure_metrics': None
                })()

            # 3. Initialize IFD v3.0 analyzer
            logger.info("🧠 Initializing IFD v3.0 analyzer...")
            self.ifd_analyzer = create_ifd_v3_analyzer(self.config.get('ifd_config'))

            # 4. Connect pressure metrics callback
            self.mbo_client.on_pressure_metrics = self._on_pressure_metrics

            # 5. Initialize WebSocket server for dashboard integration
            if self.enable_websocket and WEBSOCKET_AVAILABLE:
                logger.info("🌐 Initializing WebSocket server for dashboard...")
                self.websocket_server = create_dashboard_websocket_server(
                    host=self.config.get('websocket_host', 'localhost'),
                    port=self.config.get('websocket_port', 8765)
                )
                self.websocket_broadcaster = WebSocketSignalBroadcaster(self.websocket_server)

                # Start WebSocket server
                self.websocket_server.start_server()
                logger.info(f"✅ WebSocket server started on {self.config.get('websocket_host', 'localhost')}:{self.config.get('websocket_port', 8765)}")
            else:
                logger.info("🔍 WebSocket server disabled or not available")

            logger.info("✅ All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Component initialization failed: {e}")
            raise StreamingBridgeError(f"Failed to initialize components: {e}")

    def _on_pressure_metrics(self, pressure_metrics: PressureMetrics):
        """Handle new pressure metrics from MBO streaming"""
        try:
            self.events_processed += 1

            # Run IFD v3.0 analysis
            signal = self.ifd_analyzer.analyze_pressure_event(pressure_metrics)

            if signal:
                self.signals_generated += 1

                # In staging mode, track signals separately (shadow trading)
                if self.shadow_mode:
                    self.shadow_signals.append(signal)
                    logger.info(f"👻 SHADOW Signal: {signal.strike}{signal.option_type} "
                              f"confidence={signal.final_confidence:.3f} "
                              f"strength={signal.signal_strength}")
                else:
                    # Normal signal processing
                    self.signal_manager.add_signal(signal)

                    # Broadcast signal to dashboard via WebSocket
                    if self.websocket_broadcaster:
                        self.websocket_broadcaster.broadcast_signal(signal)

                    logger.info(f"🎯 IFD Signal: {signal.strike}{signal.option_type} "
                              f"confidence={signal.final_confidence:.3f} "
                              f"strength={signal.signal_strength}")

        except Exception as e:
            self.error_count += 1
            logger.error(f"❌ Pressure metrics processing error: {e}")

            # Stop if too many errors
            if self.error_count >= self.max_errors:
                logger.critical(f"🚨 Too many errors ({self.error_count}), stopping bridge")
                self.stop()

    def _process_ifd_signal(self, signal: InstitutionalSignalV3):
        """Process IFD signal based on mode"""
        if self.shadow_mode:
            # In staging mode, just track the signal
            self.shadow_signals.append(signal)
            logger.info(f"👻 Shadow signal tracked: {signal.strike}{signal.option_type}")
        else:
            # Normal signal processing
            self.signal_manager.add_signal(signal)

    def start_streaming(self) -> bool:
        """Start real-time streaming with full safety checks"""
        try:
            # 1. Pre-flight safety checks
            if not self._pre_flight_checks():
                return False

            # 2. Initialize components
            if not self.initialize_components():
                return False

            # 3. Start streaming thread
            self.is_running = True
            self.start_time = get_eastern_time()
            self.stop_event.clear()

            self.bridge_thread = threading.Thread(target=self._streaming_loop, daemon=True)
            self.bridge_thread.start()

            logger.info("🚀 Streaming bridge started successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start streaming: {e}")
            self.is_running = False
            return False

    def _pre_flight_checks(self) -> bool:
        """Comprehensive pre-flight safety checks"""
        logger.info("🔍 Running pre-flight safety checks...")

        # 1. Check component availability
        if not COMPONENTS_AVAILABLE:
            logger.error("❌ Required components not available")
            return False

        # 2. Check market hours (if enforcement enabled)
        # Skip market hours check in development mode
        if self.config.get('market_hours_enforcement', True) and not self.is_development:
            if not is_futures_market_hours():
                logger.warning("⏰ Markets closed - streaming not started")
                return False

        # 3. Check authentication
        # Skip auth check in development mode with simulated data or when auth not available
        if not (self.is_development and self.use_simulated_data) and DATABENTO_AUTH_AVAILABLE:
            try:
                auth = DatabentoBulletproofAuth()
                auth.load_and_validate_api_key()
                auth.assert_trading_safe()
            except Exception as e:
                logger.error(f"❌ Authentication check failed: {e}")
                return False
        else:
            if not DATABENTO_AUTH_AVAILABLE:
                logger.info("🧪 Databento auth not available: Skipping authentication check")
            else:
                logger.info("🧪 Development mode: Skipping authentication check")

        logger.info("✅ All pre-flight checks passed")
        return True

    def _streaming_loop(self):
        """Main streaming loop with error handling and recovery"""
        logger.info("🔄 Starting streaming loop...")

        while self.is_running and not self.stop_event.is_set():
            try:
                # Check if we should continue streaming
                if not self._should_continue_streaming():
                    logger.info("🛑 Stopping streaming due to conditions")
                    break

                # Development mode with simulated data
                if self.is_development and self.use_simulated_data:
                    self._simulate_streaming_data()
                    # Wait before next simulation
                    time.sleep(self.config.get('simulation_interval', 5))

                # Production/Staging mode with real data
                elif self.mbo_client:
                    self.mbo_client.start_streaming()

                    # Wait or handle reconnection
                    if not self.stop_event.wait(self.config.get('reconnect_delay', 30)):
                        continue

            except Exception as e:
                self.error_count += 1
                logger.error(f"❌ Streaming loop error: {e}")

                if self.error_count >= self.max_errors:
                    logger.critical("🚨 Maximum errors reached, stopping")
                    break

                # Wait before retry
                time.sleep(self.config.get('reconnect_delay', 30))

        self.is_running = False
        logger.info("🔄 Streaming loop ended")

    def _should_continue_streaming(self) -> bool:
        """Check if streaming should continue based on all conditions"""
        # 1. Market hours check (skip in development mode)
        if self.config.get('market_hours_enforcement', True) and not self.is_development:
            if not is_futures_market_hours():
                logger.info("⏰ Markets closed, stopping streaming")
                return False

        # 2. Cost monitoring check
        if self.config.get('cost_monitoring', True) and self.mbo_client:
            if hasattr(self.mbo_client, 'usage_monitor'):
                if not self.mbo_client.usage_monitor.should_continue_streaming():
                    logger.warning("💰 Budget limit reached, stopping streaming")
                    return False

        # 3. Error count check
        if self.error_count >= self.max_errors:
            logger.error(f"❌ Too many errors ({self.error_count}), stopping")
            return False

        return True

    def stop(self):
        """Stop streaming bridge gracefully"""
        logger.info("🛑 Stopping streaming bridge...")

        self.is_running = False
        self.stop_event.set()

        # Stop MBO client
        if self.mbo_client:
            try:
                self.mbo_client.stop_streaming()
            except Exception as e:
                logger.error(f"Error stopping MBO client: {e}")

        # Stop WebSocket server
        if self.websocket_server:
            try:
                self.websocket_server.stop_server()
                logger.info("🌐 WebSocket server stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket server: {e}")

        # Wait for thread to finish
        if self.bridge_thread and self.bridge_thread.is_alive():
            self.bridge_thread.join(timeout=10)

        logger.info("✅ Streaming bridge stopped")

    def register_signal_callback(self, callback: Callable[[InstitutionalSignalV3], None]):
        """Register callback for new institutional signals"""
        self.signal_manager.register_signal_callback(callback)

    def get_bridge_status(self) -> Dict[str, Any]:
        """Get comprehensive bridge status"""
        runtime = (get_eastern_time() - self.start_time).total_seconds() if self.start_time else 0

        status = {
            'is_running': self.is_running,
            'mode': self.mode,
            'runtime_seconds': runtime,
            'events_processed': self.events_processed,
            'signals_generated': self.signals_generated,
            'error_count': self.error_count,
            'signal_rate': self.signals_generated / max(runtime / 60, 1),  # Signals per minute
            'market_hours': self._check_market_hours(),
            'components_initialized': bool(self.mbo_client and self.ifd_analyzer),
            'shadow_mode': self.shadow_mode,
            'simulated_data': self.use_simulated_data
        }

        # Add usage stats if available
        if self.mbo_client and hasattr(self.mbo_client, 'usage_monitor'):
            status['usage_stats'] = self.mbo_client.usage_monitor.get_usage_stats()

        # Add signal summary
        status['signal_summary'] = self.signal_manager.get_signal_summary()

        # Add WebSocket server status
        if self.websocket_server:
            status['websocket_server'] = {
                'enabled': self.enable_websocket,
                'running': self.websocket_server.is_running,
                'host': self.websocket_server.host,
                'port': self.websocket_server.port,
                'active_connections': len(self.websocket_server.clients),
                'total_connections': self.websocket_server.stats['connections_total'],
                'messages_sent': self.websocket_server.stats['messages_sent']
            }
        else:
            status['websocket_server'] = {'enabled': False, 'running': False}

        # Add shadow signal stats for staging mode
        if self.shadow_mode:
            status['shadow_signals_count'] = len(self.shadow_signals)
            status['shadow_signals'] = [s.to_dict() for s in self.shadow_signals[-5:]]  # Last 5

        # Add processor and engine stats if available
        if hasattr(self, 'processor') and self.processor:
            status['processor_stats'] = self.processor.get_performance_stats()

        if hasattr(self, 'pressure_engine') and self.pressure_engine:
            status['pressure_stats'] = self.pressure_engine.get_engine_stats()

        return status

    def get_recent_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent institutional signals as dictionaries"""
        signals = self.signal_manager.get_recent_signals(limit)
        return [signal.to_dict() for signal in signals]

    def _simulate_streaming_data(self):
        """Simulate MBO streaming data for development mode"""
        import random
        from datetime import datetime, timezone

        # Generate simulated pressure metrics
        strikes = [21800, 21900, 22000, 22100, 22200]

        for _ in range(random.randint(1, 5)):  # Generate 1-5 events
            strike = random.choice(strikes)
            option_type = random.choice(['C', 'P'])

            # Create simulated pressure metrics
            pressure_metrics = type('PressureMetrics', (), {
                'strike': float(strike),
                'option_type': option_type,
                'time_window': datetime.now(timezone.utc),
                'bid_volume': random.randint(100, 1000),
                'ask_volume': random.randint(100, 1000),
                'pressure_ratio': random.uniform(0.5, 3.0),
                'total_trades': random.randint(10, 100),
                'avg_trade_size': random.uniform(10, 200),
                'dominant_side': random.choice(['BUY', 'SELL']),
                'confidence': random.uniform(0.5, 1.0),
                'total_volume': random.randint(200, 2000)
            })()

            # Process through normal handler
            self._on_pressure_metrics(pressure_metrics)

            # Small delay between events
            time.sleep(0.1)

        logger.info(f"🧪 Simulated {_} pressure metrics events")

    def get_shadow_signals(self) -> List[InstitutionalSignalV3]:
        """Get shadow signals from staging mode"""
        if self.shadow_mode:
            return self.shadow_signals.copy()
        return []

    def _check_market_hours(self) -> bool:
        """Check if markets are open, considering mode"""
        # Development mode always allows streaming
        if self.is_development:
            return True

        # Otherwise check actual market hours
        return is_futures_market_hours()

# Factory function for easy integration
def create_streaming_bridge(config: Optional[Dict[str, Any]] = None) -> StreamingBridge:
    """Create and configure streaming bridge for live analysis"""

    default_config = {
        'symbols': ['NQ.OPT'],
        'daily_budget': 25.0,
        'market_hours_enforcement': True,
        'cost_monitoring': True,
        'ifd_config': {
            'baseline_db_path': 'outputs/ifd_v3_baselines.db',
            'min_final_confidence': 0.6
        }
    }

    if config:
        default_config.update(config)

    return StreamingBridge(default_config)

# Integration helper for dashboard
def create_dashboard_streaming_bridge() -> StreamingBridge:
    """Create streaming bridge optimized for dashboard integration"""

    config = {
        'symbols': ['NQ.OPT'],
        'daily_budget': 25.0,
        'market_hours_enforcement': True,
        'cost_monitoring': True,
        'max_errors': 5,  # More strict for dashboard
        'reconnect_delay': 15,  # Faster reconnection
        'ifd_config': {
            'baseline_db_path': 'outputs/ifd_v3_baselines.db',
            'min_final_confidence': 0.6,  # Lower threshold for more signals
            'pressure_analysis': {
                'min_pressure_ratio': 1.8,  # Slightly lower for more sensitivity
                'min_total_volume': 80,
                'min_confidence': 0.75
            }
        }
    }

    return StreamingBridge(config)

# Example usage and testing
if __name__ == "__main__":
    # Test streaming bridge
    print("=== Streaming Bridge Test ===")

    # Create bridge
    bridge = create_streaming_bridge()

    # Register test callback
    def test_signal_callback(signal: InstitutionalSignalV3):
        print(f"📡 Signal: {signal.strike}{signal.option_type} "
              f"confidence={signal.final_confidence:.3f}")

    bridge.register_signal_callback(test_signal_callback)

    # Test status
    print("\n📊 Bridge Status:")
    status = bridge.get_bridge_status()
    for key, value in status.items():
        print(f"  {key}: {value}")

    print("\n✅ Streaming bridge test completed")
