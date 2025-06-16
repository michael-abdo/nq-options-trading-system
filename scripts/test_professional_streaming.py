#!/usr/bin/env python3
"""
Test Professional Live Streaming - Industry Standard Implementation
Tests the updated live streaming using parent symbology
"""

import sys
import os
sys.path.append('.')
from databento_5m_provider import Databento5MinuteProvider
import time
import threading

def test_professional_streaming():
    print("🏢 TESTING PROFESSIONAL LIVE STREAMING")
    print("=" * 60)
    print("🎯 Using INDUSTRY STANDARD parent symbology")
    print("📋 Strategy: Let Databento route to most active contract")
    print()

    provider = Databento5MinuteProvider(enable_ifd_signals=False)

    print(f"🔍 Initial State:")
    print(f"   Buffer size: {len(provider._live_data_buffer)}")
    print(f"   Streaming status: {provider._is_streaming}")
    print(f"   Live client: {provider.live_client}")

    # Test callback to capture live data
    received_data = []

    def professional_callback(bar):
        if bar:
            received_data.append(bar)
            timestamp = bar['timestamp'].strftime('%H:%M:%S') if 'timestamp' in bar else 'Unknown'
            close_price = bar.get('close', 0)
            print(f"🎯 LIVE DATA: {timestamp} - ${close_price:,.2f}")

    print(f"\n🚀 Starting PROFESSIONAL live streaming...")
    print(f"   Symbol: NQ.FUT (parent symbology)")
    print(f"   Strategy: Databento routes to most active contract month")

    # Start streaming in a separate thread
    streaming_thread = threading.Thread(
        target=lambda: provider.start_live_streaming(
            symbol="NQ.FUT",  # Use the new default
            callback=professional_callback
        ),
        daemon=True
    )
    streaming_thread.start()

    print(f"✅ Streaming thread started. Monitoring for 30 seconds...")

    # Monitor for 30 seconds
    for i in range(30):
        time.sleep(1)

        if i % 5 == 0:  # Every 5 seconds
            print(f"\n📊 Status after {i} seconds:")
            print(f"   Thread alive: {streaming_thread.is_alive()}")
            print(f"   Streaming flag: {provider._is_streaming}")
            print(f"   Buffer size: {len(provider._live_data_buffer)}")
            print(f"   Callbacks received: {len(received_data)}")
            print(f"   Live client exists: {provider.live_client is not None}")

            if provider._live_data_buffer:
                latest = provider._live_data_buffer[-1]
                print(f"   Latest buffer: {latest['timestamp']} - ${latest['close']:,.2f}")

    print(f"\n🏆 PROFESSIONAL STREAMING RESULTS:")
    print(f"   Thread status: {'✅ Active' if streaming_thread.is_alive() else '❌ Terminated'}")
    print(f"   Final buffer size: {len(provider._live_data_buffer)}")
    print(f"   Total data received: {len(received_data)}")

    if len(received_data) > 0:
        print(f"\n🎯 SUCCESS: Professional streaming works!")
        print(f"   First data: {received_data[0]['timestamp']} - ${received_data[0]['close']:,.2f}")
        print(f"   Latest data: {received_data[-1]['timestamp']} - ${received_data[-1]['close']:,.2f}")
        print(f"   Data frequency: {len(received_data)} bars in 30 seconds")
    else:
        print(f"\n🔍 Still investigating:")
        print(f"   - Check if NQ.FUT is the correct parent symbol format")
        print(f"   - Verify Databento supports parent symbology for live streaming")
        print(f"   - May need to test alternative symbol formats")

    # Clean shutdown
    provider.stop_live_streaming()

    return len(received_data) > 0

if __name__ == "__main__":
    success = test_professional_streaming()
    if success:
        print("\n✅ READY FOR PRODUCTION: Professional live streaming operational")
    else:
        print("\n🔍 NEXT STEPS: Research alternative industry standard approaches")
