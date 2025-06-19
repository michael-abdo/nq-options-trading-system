#!/usr/bin/env python3
"""
NQ OPTIONS QUOTE PRESSURE MONITOR WITH IFD v3 INTEGRATION
========================================================

Enhanced version of the quote pressure monitor that integrates with IFD v3
through the QuotePressureAdapter for real-time institutional flow detection.

This version:
1. Monitors live quote pressure as before
2. Converts quote data to PressureMetrics using the adapter
3. Feeds PressureMetrics to IFD v3 for enhanced analysis
4. Provides both quote-based and IFD-based alerts
"""

import databento as db
import time
from datetime import datetime, timezone
from collections import defaultdict, deque
import json
import sys
import os

# Add parent directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

# Import adapter and integration
from quote_pressure_adapter import QuotePressureAdapter, QuotePressureSnapshot
from ifd_integration import QuotePressureToIFDPipeline

print("🎯 NQ OPTIONS QUOTE PRESSURE MONITOR + IFD v3")
print("="*60)
print("Enhanced institutional detection with IFD v3 integration")
print("="*60)

# Configuration
API_KEY = os.getenv('DATABENTO_API_KEY')
INSTITUTIONAL_SIZE_THRESHOLD = 50  # Contracts
PRESSURE_RATIO_THRESHOLD = 2.0

# Initialize IFD integration pipeline
ifd_pipeline = QuotePressureToIFDPipeline(
    window_minutes=5,
    volume_multiplier=10.0
)

# Track quote pressure for key strikes
quote_pressure = defaultdict(lambda: {
    'symbol': '',
    'bid_size': 0,
    'ask_size': 0,
    'bid_price': 0,
    'ask_price': 0,
    'pressure_ratio': 0,
    'last_update': None,
    'pressure_history': deque(maxlen=20),
    'strike': 0,
    'option_type': ''
})

institutional_alerts = []
ifd_signals = []
total_quotes_processed = 0

def calculate_pressure_metrics(bid_size, ask_size, symbol):
    """Calculate institutional pressure indicators"""
    if ask_size == 0:
        return float('inf'), "EXTREME_BUY"
    if bid_size == 0:
        return 0, "EXTREME_SELL"

    pressure_ratio = bid_size / ask_size

    if pressure_ratio > PRESSURE_RATIO_THRESHOLD:
        direction = "BUY_PRESSURE"
    elif pressure_ratio < (1/PRESSURE_RATIO_THRESHOLD):
        direction = "SELL_PRESSURE"
    else:
        direction = "NEUTRAL"

    return pressure_ratio, direction

def detect_institutional_positioning(record):
    """Enhanced detection with IFD v3 integration"""
    global total_quotes_processed, institutional_alerts, ifd_signals

    record_type = type(record).__name__

    # Process market-by-price quotes
    if record_type == 'MbpMsg':
        total_quotes_processed += 1

        # Extract quote data
        instrument_id = getattr(record, 'instrument_id', 0)
        bid_price = getattr(record, 'bid_px_00', 0) / 1_000_000_000 if getattr(record, 'bid_px_00', 0) > 0 else 0
        ask_price = getattr(record, 'ask_px_00', 0) / 1_000_000_000 if getattr(record, 'ask_px_00', 0) > 0 else 0
        bid_size = getattr(record, 'bid_sz_00', 0)
        ask_size = getattr(record, 'ask_sz_00', 0)

        # Get symbol from mapping
        symbol = symbol_mappings.get(instrument_id, f"ID:{instrument_id}")

        # Only process NQ options near the money
        if 'NQ' in symbol and ('C' in symbol or 'P' in symbol):
            try:
                # Extract strike and option type
                if ' C' in symbol:
                    strike = float(symbol.split(' C')[1])
                    option_type = 'C'
                elif ' P' in symbol:
                    strike = float(symbol.split(' P')[1])
                    option_type = 'P'
                else:
                    return

                # Only monitor near-the-money strikes
                if not (19000 <= strike <= 25000):
                    return

            except (ValueError, IndexError):
                return

            # Calculate pressure metrics
            pressure_ratio, direction = calculate_pressure_metrics(bid_size, ask_size, symbol)

            # Update tracking
            current_data = quote_pressure[instrument_id]
            current_data.update({
                'symbol': symbol,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'pressure_ratio': pressure_ratio,
                'last_update': datetime.now(timezone.utc),
                'strike': strike,
                'option_type': option_type
            })

            # Track pressure changes
            current_data['pressure_history'].append({
                'time': datetime.now(timezone.utc),
                'pressure_ratio': pressure_ratio,
                'bid_size': bid_size,
                'ask_size': ask_size
            })

            # Send to IFD pipeline for analysis
            try:
                ifd_signal = ifd_pipeline.process_quote_data(current_data)
                if ifd_signal:
                    ifd_signals.append(ifd_signal)
                    print(f"\n🎯 IFD v3 INSTITUTIONAL SIGNAL!")
                    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
                    print(f"   Strike: {ifd_signal.strike} {ifd_signal.option_type}")
                    print(f"   Confidence: {ifd_signal.final_confidence:.2f}")
                    print(f"   Signal Type: {ifd_signal.signal_type}")
                    print(f"   Direction: {ifd_signal.dominant_side}")

                    # Save IFD signal
                    with open('/Users/Mike/trading/algos/EOD/quote_pressure_monitor/ifd_signals.jsonl', 'a') as f:
                        signal_dict = {
                            'timestamp': ifd_signal.timestamp.isoformat(),
                            'strike': ifd_signal.strike,
                            'option_type': ifd_signal.option_type,
                            'confidence': ifd_signal.final_confidence,
                            'signal_type': ifd_signal.signal_type,
                            'dominant_side': ifd_signal.dominant_side,
                            'pressure_ratio': ifd_signal.pressure_ratio
                        }
                        f.write(json.dumps(signal_dict) + '\n')

            except Exception as e:
                # Continue with regular detection if IFD fails
                pass

            # ORIGINAL QUOTE-BASED DETECTION (kept for comparison)
            institutional_signal = False
            signal_reason = []

            # 1. Large quote sizes
            if bid_size >= INSTITUTIONAL_SIZE_THRESHOLD:
                institutional_signal = True
                signal_reason.append(f"Large bid: {bid_size} contracts")

            if ask_size >= INSTITUTIONAL_SIZE_THRESHOLD:
                institutional_signal = True
                signal_reason.append(f"Large ask: {ask_size} contracts")

            # 2. Extreme pressure ratios
            if pressure_ratio > 3.0:
                institutional_signal = True
                signal_reason.append(f"Extreme buy pressure: {pressure_ratio:.2f}")
            elif pressure_ratio < 0.33:
                institutional_signal = True
                signal_reason.append(f"Extreme sell pressure: {pressure_ratio:.2f}")

            # 3. Sudden size changes
            if len(current_data['pressure_history']) >= 2:
                prev = current_data['pressure_history'][-2]
                bid_change = bid_size - prev['bid_size']
                ask_change = ask_size - prev['ask_size']

                if abs(bid_change) >= 25:
                    institutional_signal = True
                    signal_reason.append(f"Bid size change: {bid_change:+d}")

                if abs(ask_change) >= 25:
                    institutional_signal = True
                    signal_reason.append(f"Ask size change: {ask_change:+d}")

            # Quote-based alert
            if institutional_signal:
                alert = {
                    'time': datetime.now().strftime('%H:%M:%S'),
                    'symbol': symbol,
                    'strike': strike,
                    'bid': f"${bid_price:.2f} x {bid_size}",
                    'ask': f"${ask_price:.2f} x {ask_size}",
                    'pressure_ratio': pressure_ratio,
                    'direction': direction,
                    'reasons': signal_reason,
                    'spread': ask_price - bid_price if ask_price > 0 and bid_price > 0 else 0
                }

                institutional_alerts.append(alert)

                print(f"\n📊 Quote Pressure Alert:")
                print(f"   Time: {alert['time']}")
                print(f"   Symbol: {alert['symbol']}")
                print(f"   Bid: {alert['bid']}")
                print(f"   Ask: {alert['ask']}")
                print(f"   Signals: {', '.join(alert['reasons'])}")

                # Save to file
                with open('/Users/Mike/trading/algos/EOD/quote_pressure_monitor/institutional_alerts.jsonl', 'a') as f:
                    f.write(json.dumps(alert) + '\n')

def process_symbol_mapping(record):
    """Track symbol mappings for instrument ID lookup"""
    if hasattr(record, 'stype_out_symbol') and hasattr(record, 'instrument_id'):
        symbol = str(record.stype_out_symbol)
        instrument_id = record.instrument_id
        symbol_mappings[instrument_id] = symbol

# Track instrument ID to symbol mappings
symbol_mappings = {}
quotes_processed = 0

def quote_pressure_callback(record):
    """Main callback for live streaming data"""
    global quotes_processed

    # Process different record types
    if hasattr(record, 'instrument_id'):
        detect_institutional_positioning(record)
        quotes_processed += 1

        # Status update every 1000 quotes
        if quotes_processed % 1000 == 0:
            summary = ifd_pipeline.get_summary_report()
            print(f"\n📈 Progress: {quotes_processed:,} quotes | "
                  f"Quote Alerts: {len(institutional_alerts)} | "
                  f"IFD Signals: {summary.get('total_signals', 0)}")

    # Handle symbol mappings
    if hasattr(record, 'stype_out_symbol'):
        process_symbol_mapping(record)

def main():
    """Main execution with IFD v3 integration"""
    print(f"\n🔄 Connecting to Databento...")

    client = db.Live(key=API_KEY)

    try:
        # Subscribe to NQ options quotes
        client.subscribe(
            dataset='GLBX.MDP3',
            schema='mbp-1',
            symbols=['NQ.OPT'],
            start='2025-01-01T00:00:00'
        )

        # Add callback
        client.add_callback(quote_pressure_callback)
        client.start()

        print(f"🚀 Enhanced monitoring active with IFD v3...")
        print(f"🎯 Dual detection: Quote pressure + IFD analysis")
        print(f"⏰ Best signals typically 2:30-4:00 PM ET")
        print(f"\nPress Ctrl+C to stop monitoring\n")

        # Run until stopped
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\n📊 ENHANCED MONITORING SESSION COMPLETE")
        print(f"="*50)
        print(f"Total quotes processed: {quotes_processed:,}")
        print(f"Quote-based alerts: {len(institutional_alerts)}")

        # Get IFD summary
        summary = ifd_pipeline.get_summary_report()
        print(f"\n🎯 IFD v3 Analysis Summary:")
        print(f"Total signals: {summary.get('total_signals', 0)}")
        print(f"High confidence: {summary.get('high_confidence_signals', 0)}")

        if summary.get('signal_breakdown'):
            print(f"\nSignal Breakdown by Strike:")
            for key, data in summary['signal_breakdown'].items():
                strike, otype = key.split('_')
                print(f"  {otype} {strike}: {data['count']} signals, "
                      f"avg confidence {data['avg_confidence']:.2f}, "
                      f"dominant: {data['dominant_side']}")

        if institutional_alerts:
            print(f"\n📊 Recent Quote Alerts:")
            for alert in institutional_alerts[-3:]:
                print(f"   {alert['time']}: {alert['symbol']} - {alert['direction']}")

        if ifd_signals:
            print(f"\n🎯 Recent IFD Signals:")
            for signal in ifd_signals[-3:]:
                print(f"   {signal.timestamp.strftime('%H:%M:%S')}: "
                      f"{signal.option_type} {signal.strike} - "
                      f"Confidence {signal.final_confidence:.2f}")

        print(f"\n📁 Alerts saved to:")
        print(f"   - institutional_alerts.jsonl (quote-based)")
        print(f"   - ifd_signals.jsonl (IFD v3 analysis)")

        client.stop()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
