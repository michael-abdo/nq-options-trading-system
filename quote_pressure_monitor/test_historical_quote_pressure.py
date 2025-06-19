#!/usr/bin/env python3
"""
Test quote pressure adapter with historical data to verify it activates
"""

import os
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
import databento as db
from quote_pressure_adapter import QuotePressureAdapter
from ifd_integration import QuotePressureToIFDPipeline

# Load environment variables
load_dotenv()

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_historical_quote_pressure():
    """Test quote pressure detection with historical data"""

    # Create adapter and pipeline
    adapter = QuotePressureAdapter(
        window_minutes=5,
        volume_multiplier=10.0
    )

    pipeline = QuotePressureToIFDPipeline(
        window_minutes=5,
        volume_multiplier=10.0
    )

    # Initialize Databento client
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))

    # Use a date range where we know there's activity
    # Let's try a recent trading day (today is 6/18/2025)
    start_date = "2025-06-17T14:30:00"  # Yesterday 2:30 PM ET - active trading
    end_date = "2025-06-17T16:00:00"    # Yesterday 4:00 PM ET

    print(f"🔍 Testing quote pressure with historical data from {start_date} to {end_date}")
    print("=" * 80)

    # Track statistics
    total_quotes = 0
    quote_pressure_signals = 0
    ifd_signals = 0
    last_quotes = {}

    try:
        # Request quote data (mbp-1 for top-of-book quotes)
        data = client.timeseries.get_range(
            dataset="GLBX.MDP3",
            symbols=["NQ.OPT"],  # All NQ options
            schema="mbp-1",      # Market by price (quotes)
            start=start_date,
            end=end_date,
            stype_in="parent"
        )

        print("📊 Processing historical quote data...")
        print("-" * 80)

        for record in data:
            if hasattr(record, 'levels') and len(record.levels) > 0:
                total_quotes += 1

                # Extract quote data
                level = record.levels[0]
                # Get symbol using the correct attribute
                symbol = str(record.instrument_id) if hasattr(record, 'instrument_id') else str(record)[:10]
                bid_size = level.bid_sz
                ask_size = level.ask_sz
                bid_price = level.bid_px / 1e9  # Convert to dollars
                ask_price = level.ask_px / 1e9

                # Skip if sizes are 0
                if bid_size == 0 or ask_size == 0:
                    continue

                # Calculate quote pressure
                pressure_ratio = bid_size / ask_size if ask_size > 0 else 0

                # Direct quote pressure detection
                if bid_size >= 50 and pressure_ratio > 2.0:
                    quote_pressure_signals += 1
                    print(f"\n🐋 QUOTE PRESSURE SIGNAL #{quote_pressure_signals}")
                    print(f"   Symbol: {symbol}")
                    print(f"   Bid Size: {bid_size} | Ask Size: {ask_size}")
                    print(f"   Pressure Ratio: {pressure_ratio:.2f}")
                    print(f"   Bid: ${bid_price:.2f} | Ask: ${ask_price:.2f}")

                # Feed to adapter/pipeline
                quote_data = {
                    'symbol': symbol,
                    'bid_size': bid_size,
                    'ask_size': ask_size,
                    'bid_price': bid_price,
                    'ask_price': ask_price,
                    'timestamp': record.ts_event / 1e9  # Convert to seconds
                }

                # Get last quote for this symbol to calculate changes
                last_quote = last_quotes.get(symbol, {})
                if last_quote:
                    quote_data['bid_size_change'] = bid_size - last_quote.get('bid_size', bid_size)
                    quote_data['ask_size_change'] = ask_size - last_quote.get('ask_size', ask_size)
                else:
                    quote_data['bid_size_change'] = 0
                    quote_data['ask_size_change'] = 0

                last_quotes[symbol] = {
                    'bid_size': bid_size,
                    'ask_size': ask_size
                }

                # Process through pipeline
                result = pipeline.process_quote_data(quote_data)
                if result and result.get('signal_generated'):
                    ifd_signals += 1
                    signal = result['signal']
                    print(f"\n🎯 IFD v3 SIGNAL #{ifd_signals}")
                    print(f"   Strike: {signal.strike}")
                    print(f"   Direction: {signal.direction}")
                    print(f"   Confidence: {signal.confidence:.2f}")
                    print(f"   Pressure Ratio: {signal.pressure_ratio:.2f}")

                # Show progress every 1000 quotes
                if total_quotes % 1000 == 0:
                    print(f"   Processed {total_quotes} quotes...")

        print("\n" + "=" * 80)
        print("📈 HISTORICAL TEST RESULTS:")
        print(f"   Total Quotes Processed: {total_quotes:,}")
        print(f"   Quote Pressure Signals: {quote_pressure_signals}")
        print(f"   IFD v3 Signals: {ifd_signals}")
        print(f"   Signal Rate: {(quote_pressure_signals/total_quotes*100):.2f}%" if total_quotes > 0 else "N/A")

        if quote_pressure_signals == 0 and ifd_signals == 0:
            print("\n⚠️  No signals detected. Try adjusting:")
            print("   - Time window (currently 5 minutes)")
            print("   - Min quote size threshold (currently 10)")
            print("   - Pressure ratio threshold (currently 1.5)")
            print("   - Date/time range (try more active periods)")
        else:
            print("\n✅ SUCCESS! The quote pressure system is working!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTrying a different approach with specific NQ option symbols...")

        # Try with specific options we found before
        try:
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQZ4 C19800", "NQZ4 C20000", "NQZ4 C20200"],  # Specific strikes
                schema="mbp-1",
                start=start_date,
                end=end_date
            )

            for record in data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    total_quotes += 1
                    level = record.levels[0]
                    print(f"Quote: {record.symbol} - Bid: {level.bid_sz} @ ${level.bid_px/1e9:.2f}, Ask: {level.ask_sz} @ ${level.ask_px/1e9:.2f}")

        except Exception as e2:
            print(f"Second attempt error: {e2}")

if __name__ == "__main__":
    test_historical_quote_pressure()
