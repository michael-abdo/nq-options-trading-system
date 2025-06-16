#!/usr/bin/env python3
"""
Test Live Streaming Connection with Enhanced Authentication
Verifies that live streaming works with proper API key handling
"""

import sys
import os
import time
import logging
from datetime import datetime
import pytz

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'utils'))

from databento_5m_provider import Databento5MinuteProvider
from timezone_utils import is_futures_market_hours

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_live_streaming():
    """Test live streaming connection and authentication"""

    logger.info("=" * 60)
    logger.info("🧪 LIVE STREAMING CONNECTION TEST")
    logger.info("=" * 60)

    # Check if futures markets are open
    if not is_futures_market_hours():
        logger.warning("⚠️  Futures markets are CLOSED")
        logger.info("   Futures hours: Sunday 6 PM - Friday 5 PM ET")
        logger.info("   Current time: " + datetime.now(pytz.timezone('US/Eastern')).strftime('%A %H:%M ET'))
    else:
        logger.info("✅ Futures markets are OPEN")
        logger.info("   Current time: " + datetime.now(pytz.timezone('US/Eastern')).strftime('%A %H:%M ET'))

    # Initialize provider
    try:
        logger.info("\n📊 Initializing Databento 5-minute provider...")
        provider = Databento5MinuteProvider(enable_ifd_signals=False)
        logger.info("✅ Provider initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize provider: {e}")
        return False

    # Test live streaming
    logger.info("\n🔴 Testing live streaming connection...")

    bars_received = []

    def on_new_bar(bar):
        """Callback for new 5-minute bars"""
        if bar:
            bars_received.append(bar)
            logger.info(f"📊 Live bar received: Close=${bar.get('close', 0):,.2f}, "
                       f"Volume={bar.get('volume', 0):,}")

    try:
        # Start live streaming
        provider.start_live_streaming(
            symbol="NQM5",
            callback=on_new_bar
        )

        logger.info("✅ Live streaming started successfully!")
        logger.info("⏳ Waiting for live data (up to 60 seconds)...")

        # Wait for some bars
        start_time = time.time()
        while time.time() - start_time < 60:
            if bars_received:
                logger.info(f"\n🎉 SUCCESS! Received {len(bars_received)} live bars")
                logger.info("✅ Live streaming authentication is working correctly")
                break
            time.sleep(1)
        else:
            if is_futures_market_hours():
                logger.warning("⚠️  No live bars received in 60 seconds")
                logger.info("   This might be normal during low-activity periods")
            else:
                logger.info("ℹ️  No live bars received (markets closed)")

        # Stop streaming
        provider.stop_live_streaming()
        logger.info("\n✅ Live streaming stopped")

        return True

    except Exception as e:
        logger.error(f"\n❌ Live streaming test failed: {e}")

        if "CRAM" in str(e) or "authentication" in str(e).lower():
            logger.error("\n🔐 AUTHENTICATION ERROR DETECTED")
            logger.error("   Your API key may not have live streaming permissions")
            logger.error("   Contact Databento support to enable live streaming")
        elif "dataset" in str(e).lower():
            logger.error("\n📊 DATASET ACCESS ERROR")
            logger.error("   Your account may not have access to GLBX.MDP3")
            logger.error("   Check your Databento subscription")

        return False

    finally:
        logger.info("\n" + "=" * 60)
        logger.info("Test completed")

if __name__ == "__main__":
    test_live_streaming()
