#!/usr/bin/env python3
"""
NQ OPTIONS QUOTE PRESSURE MONITOR
=================================

KEY INSIGHT: Options don't trade much, but QUOTES tell the institutional story.

This script monitors live quote pressure (bid/ask size changes) in NQ options
to detect institutional positioning during the critical 2:30-4:00 PM ET window.

Core Discovery:
- ✅ 1000+ NQ option symbols streaming successfully
- ✅ Symbol format: NQM5 C21980 (June 2025 expiry)
- ✅ Parent symbol NQ.OPT captures all strikes
- 🎯 Use mbp-1 schema for QUOTE data (not trades)
"""

import databento as db
import time
from datetime import datetime
from collections import defaultdict, deque
import json

print("🎯 NQ OPTIONS QUOTE PRESSURE MONITOR")
print("="*60)
print("Monitoring institutional positioning via quote pressure...")
print("Focus: Bid/Ask size changes (not trade volume)")
print("="*60)

# Configuration
API_KEY = os.getenv('DATABENTO_API_KEY')
INSTITUTIONAL_SIZE_THRESHOLD = 50  # Contracts
PRESSURE_RATIO_THRESHOLD = 2.0

# Track quote pressure for key strikes
quote_pressure = defaultdict(lambda: {
    'symbol': '',
    'bid_size': 0,
    'ask_size': 0,
    'bid_price': 0,
    'ask_price': 0,
    'pressure_ratio': 0,
    'last_update': None,
    'pressure_history': deque(maxlen=20)  # Last 20 updates
})

institutional_alerts = []
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
    """Core detection logic for institutional quote pressure"""
    global total_quotes_processed, institutional_alerts

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

        # Get symbol from mapping (populated by SymbolMappingMsg)
        symbol = symbol_mappings.get(instrument_id, f"ID:{instrument_id}")

        # Only process NQ options near the money
        if 'NQ' in symbol and ('C' in symbol or 'P' in symbol):
            # Focus on ATM ± $2000 (adjust based on current NQ price ~$21,000-22,000)
            try:
                if 'C' in symbol:
                    strike = float(symbol.split(' C')[1])
                elif 'P' in symbol:
                    strike = float(symbol.split(' P')[1])
                else:
                    return

                # Only monitor near-the-money strikes (most institutional activity)
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
                'last_update': datetime.now(),
                'strike': strike
            })

            # Track pressure changes
            current_data['pressure_history'].append({
                'time': datetime.now(),
                'pressure_ratio': pressure_ratio,
                'bid_size': bid_size,
                'ask_size': ask_size
            })

            # INSTITUTIONAL DETECTION LOGIC
            institutional_signal = False
            signal_reason = []

            # 1. Large quote sizes (institutional participation)
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

            # 3. Sudden size changes (institutional repositioning)
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

            # ALERT ON INSTITUTIONAL ACTIVITY
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

                print(f"\n🚨 INSTITUTIONAL QUOTE PRESSURE DETECTED!")
                print(f"   Time: {alert['time']}")
                print(f"   Symbol: {alert['symbol']} (Strike: ${alert['strike']})")
                print(f"   Bid: {alert['bid']}")
                print(f"   Ask: {alert['ask']}")
                print(f"   Pressure Ratio: {alert['pressure_ratio']:.2f} ({alert['direction']})")
                print(f"   Spread: ${alert['spread']:.3f}")
                print(f"   Signals: {', '.join(alert['reasons'])}")

                # Save to file for analysis
                with open('/Users/Mike/trading/algos/EOD/quote_pressure_monitor/institutional_alerts.jsonl', 'a') as f:
                    f.write(json.dumps(alert) + '\n')

def process_symbol_mapping(record):
    """Track symbol mappings for instrument ID lookup"""
    if hasattr(record, 'stype_out_symbol') and hasattr(record, 'instrument_id'):
        symbol = str(record.stype_out_symbol)
        instrument_id = record.instrument_id
        symbol_mappings[instrument_id] = symbol

        # Show mapping for NQ options
        if 'NQ' in symbol and ('C' in symbol or 'P' in symbol):
            print(f"📋 Mapped: {symbol} → ID {instrument_id}")

# Global symbol mapping
symbol_mappings = {}
quotes_processed = 0

def quote_pressure_callback(record):
    """Main callback for processing quote pressure data"""
    global quotes_processed
    quotes_processed += 1

    record_type = type(record).__name__

    # Track symbol mappings
    if record_type == 'SymbolMappingMsg':
        process_symbol_mapping(record)

    # Process quote pressure
    elif record_type == 'MbpMsg':
        detect_institutional_positioning(record)

    # Progress updates
    if quotes_processed % 1000 == 0:
        nq_symbols = sum(1 for s in symbol_mappings.values() if 'NQ' in s and ('C' in s or 'P' in s))
        print(f"📊 Progress: {quotes_processed} records | {nq_symbols} NQ options mapped | {len(institutional_alerts)} alerts")

def main():
    """Main monitoring function"""
    print(f"\n📡 Starting NQ Options Quote Pressure Monitor...")
    print(f"Schema: mbp-1 (Market By Price - Level 1)")
    print(f"Symbol: NQ.OPT (All NQ options)")
    print(f"Focus: Strike range $19,000 - $25,000")
    print(f"Threshold: {INSTITUTIONAL_SIZE_THRESHOLD}+ contracts = institutional")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}")

    try:
        client = db.Live(key=API_KEY)

        # Subscribe to NQ options quotes (NOT trades)
        client.subscribe(
            dataset="GLBX.MDP3",
            schema="mbp-1",  # Market By Price for quote data
            symbols=["NQ.OPT"],
            stype_in="parent",
            start=0,
        )

        client.add_callback(quote_pressure_callback)
        client.start()

        print(f"🚀 Quote pressure monitoring active...")
        print(f"🎯 Watching for institutional positioning signals...")
        print(f"⏰ Best signals typically 2:30-4:00 PM ET")
        print(f"\nPress Ctrl+C to stop monitoring\n")

        # Run until stopped
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print(f"\n\n📊 MONITORING SESSION COMPLETE")
        print(f"="*50)
        print(f"Total quotes processed: {quotes_processed}")
        print(f"NQ options symbols mapped: {sum(1 for s in symbol_mappings.values() if 'NQ' in s and ('C' in s or 'P' in s))}")
        print(f"Institutional alerts generated: {len(institutional_alerts)}")

        if institutional_alerts:
            print(f"\n🚨 INSTITUTIONAL ACTIVITY SUMMARY:")
            for alert in institutional_alerts[-5:]:  # Last 5 alerts
                print(f"   {alert['time']}: {alert['symbol']} - {alert['direction']} (Ratio: {alert['pressure_ratio']:.2f})")

        print(f"\n📁 Alerts saved to: institutional_alerts.jsonl")
        client.stop()

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
