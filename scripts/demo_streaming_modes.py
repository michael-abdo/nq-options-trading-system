#!/usr/bin/env python3
"""
Demonstration of Live Streaming Modes:
- Development Mode: Simulated data, no authentication required
- Staging Mode: Real data with shadow trading (no execution)
- Production Mode: Full live trading capability
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(current_dir))

from tasks.options_trading_system.analysis_engine import (
    create_streaming_bridge,
    LIVE_STREAMING_AVAILABLE
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_development_mode():
    """Demonstrate development mode with simulated data"""
    print("\n" + "="*60)
    print("🧪 DEVELOPMENT MODE DEMO")
    print("="*60)

    if not LIVE_STREAMING_AVAILABLE:
        print("❌ Live streaming components not available")
        return

    # Create bridge in development mode
    config = {
        'mode': 'development',
        'data_simulation': True,
        'simulation_interval': 2,  # Generate data every 2 seconds
        'market_hours_enforcement': False,  # Allow anytime
        'daily_budget': 0,  # No cost in dev mode
    }

    bridge = create_streaming_bridge(config)

    # Track signals
    signals_received = []

    def on_signal(signal):
        signals_received.append(signal)
        print(f"\n📡 DEV Signal: {signal.strike}{signal.option_type}")
        print(f"   Confidence: {signal.final_confidence:.2%}")
        print(f"   Direction: {signal.expected_direction}")

    bridge.register_signal_callback(on_signal)

    # Start streaming
    print("\n🚀 Starting development mode streaming...")
    if bridge.start_streaming():
        print("✅ Streaming started successfully")

        # Run for 10 seconds
        print("\n⏱️  Running for 10 seconds...")
        time.sleep(10)

        # Stop streaming
        bridge.stop()

        # Show results
        status = bridge.get_bridge_status()
        print(f"\n📊 Development Mode Results:")
        print(f"   Events processed: {status['events_processed']}")
        print(f"   Signals generated: {status['signals_generated']}")
        print(f"   Errors: {status['error_count']}")
        print(f"   Used simulated data: {status['simulated_data']}")

    else:
        print("❌ Failed to start streaming")


def demo_staging_mode():
    """Demonstrate staging mode with shadow trading"""
    print("\n" + "="*60)
    print("👻 STAGING MODE DEMO")
    print("="*60)

    if not LIVE_STREAMING_AVAILABLE:
        print("❌ Live streaming components not available")
        return

    # Create bridge in staging mode
    config = {
        'mode': 'staging',
        'market_hours_enforcement': True,
        'daily_budget': 25.0,
        'shadow_trading': True,  # Track but don't execute
    }

    bridge = create_streaming_bridge(config)

    # Check market hours
    if not bridge._check_market_hours():
        print("⏰ Markets are closed. In staging mode, this would prevent streaming.")
        print("   For demo purposes, switching to development mode simulation...")

        # Switch to dev mode for demo
        config['mode'] = 'development'
        config['data_simulation'] = True
        config['market_hours_enforcement'] = False
        bridge = create_streaming_bridge(config)
        bridge.shadow_mode = True  # Still track as shadow

    # Start streaming
    print("\n🚀 Starting staging mode streaming...")
    if bridge.start_streaming():
        print("✅ Streaming started (shadow mode)")

        # Run for 10 seconds
        print("\n⏱️  Running for 10 seconds...")
        time.sleep(10)

        # Stop streaming
        bridge.stop()

        # Show shadow signals
        shadow_signals = bridge.get_shadow_signals()
        print(f"\n👻 Shadow Trading Results:")
        print(f"   Shadow signals tracked: {len(shadow_signals)}")

        if shadow_signals:
            print("\n   Recent shadow signals:")
            for i, signal in enumerate(shadow_signals[-3:], 1):
                print(f"   {i}. {signal.strike}{signal.option_type} - "
                      f"{signal.expected_direction} "
                      f"(confidence: {signal.final_confidence:.2%})")

        status = bridge.get_bridge_status()
        print(f"\n   Total events: {status['events_processed']}")
        print(f"   Shadow mode active: {status['shadow_mode']}")

    else:
        print("❌ Failed to start streaming")


def demo_production_mode():
    """Demonstrate production mode configuration"""
    print("\n" + "="*60)
    print("🚀 PRODUCTION MODE CONFIGURATION")
    print("="*60)

    if not LIVE_STREAMING_AVAILABLE:
        print("❌ Live streaming components not available")
        return

    # Production configuration
    config = {
        'mode': 'production',
        'symbols': ['NQ.OPT'],
        'daily_budget': 25.0,
        'market_hours_enforcement': True,
        'cost_monitoring': True,
        'max_errors': 10,
        'reconnect_delay': 30,
        'ifd_config': {
            'baseline_db_path': 'outputs/ifd_v3_baselines.db',
            'min_final_confidence': 0.7,  # Higher threshold for production
            'pressure_analysis': {
                'min_pressure_ratio': 2.5,  # More conservative
                'min_total_volume': 150,
                'min_confidence': 0.85
            }
        }
    }

    print("\n📋 Production Configuration:")
    print(f"   Mode: {config['mode']}")
    print(f"   Symbols: {config['symbols']}")
    print(f"   Daily Budget: ${config['daily_budget']}")
    print(f"   Market Hours Enforcement: {config['market_hours_enforcement']}")
    print(f"   Min Confidence: {config['ifd_config']['min_final_confidence']}")

    # Create bridge
    bridge = create_streaming_bridge(config)

    # Check pre-flight conditions
    print("\n🔍 Pre-flight Checks:")

    # Market hours
    market_open = bridge._check_market_hours()
    print(f"   Market Hours: {'✅ OPEN' if market_open else '❌ CLOSED'}")

    # Authentication (would check in real production)
    print("   Authentication: [Would check Databento API key]")
    print("   Budget Remaining: [Would check usage monitor]")

    # Status
    status = bridge.get_bridge_status()
    print(f"\n📊 Bridge Status:")
    print(f"   Mode: {status['mode']}")
    print(f"   Ready: {status['components_initialized']}")
    print(f"   Market Hours OK: {status['market_hours']}")

    print("\n⚠️  Note: Production mode requires:")
    print("   - Valid Databento API key")
    print("   - Markets to be open")
    print("   - Sufficient daily budget")
    print("   - All safety checks to pass")


def main():
    """Run all mode demonstrations"""
    print("\n" + "="*70)
    print("LIVE STREAMING MODES DEMONSTRATION")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check components
    if not LIVE_STREAMING_AVAILABLE:
        print("\n❌ ERROR: Live streaming components not available!")
        print("   Please ensure all dependencies are installed.")
        return

    print("\n✅ Live streaming components available")

    # Run demos
    try:
        # Development mode
        demo_development_mode()

        # Staging mode
        demo_staging_mode()

        # Production mode info
        demo_production_mode()

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo error: {e}")
        import traceback
        traceback.print_exc()

    print("\n\n✅ Demo completed!")
    print("="*70)


if __name__ == "__main__":
    main()
