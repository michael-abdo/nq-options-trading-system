#!/usr/bin/env python3
"""
IFD v3 Integration for Quote Pressure Monitor
============================================

This script demonstrates how to integrate the quote pressure monitor with IFD v3's
analysis pipeline using the QuotePressureAdapter.

Flow:
1. Quote pressure monitor captures live quote data
2. QuotePressureAdapter converts to PressureMetrics format
3. PressureMetrics fed to IFD v3 for institutional flow analysis

Key Features:
- Real-time conversion of quote snapshots to volume metrics
- Maintains compatibility with IFD v3's expected data format
- Preserves time window aggregation semantics
- Handles the fundamental difference between quotes and trades
"""

import os
import sys
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)

# Import adapter and IFD v3 components
from quote_pressure_adapter import QuotePressureAdapter, QuotePressureSnapshot

# Try importing IFD v3 components
try:
    from tasks.options_trading_system.analysis_engine.institutional_flow_v3.solution import (
        InstitutionalFlowDetectorV3, InstitutionalSignalV3
    )
    IFD_AVAILABLE = True
except ImportError:
    IFD_AVAILABLE = False
    print("⚠️  IFD v3 not available - running in standalone mode")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QuotePressureToIFDPipeline:
    """
    Integration pipeline that connects quote pressure monitoring to IFD v3
    """

    def __init__(self, window_minutes: int = 5, volume_multiplier: float = 10.0):
        """
        Initialize the integration pipeline

        Args:
            window_minutes: Time window for pressure aggregation
            volume_multiplier: Multiplier for converting quote changes to volume
        """
        # Initialize adapter
        self.adapter = QuotePressureAdapter(
            window_minutes=window_minutes,
            volume_multiplier=volume_multiplier
        )

        # Initialize IFD v3 if available
        if IFD_AVAILABLE:
            self.ifd = InstitutionalFlowDetectorV3()
            logger.info("✅ IFD v3 initialized successfully")
        else:
            self.ifd = None
            logger.warning("⚠️  Running without IFD v3 integration")

        # Track processed signals
        self.processed_signals = []

    def process_quote_data(self, quote_data: dict) -> Optional[Dict[str, Any]]:
        """
        Process raw quote data from monitor and return institutional signal if detected

        Args:
            quote_data: Dictionary with quote pressure data from monitor

        Returns:
            InstitutionalSignalV3 if significant activity detected, None otherwise
        """
        try:
            # Convert to QuotePressureSnapshot
            snapshot = self._create_snapshot_from_quote_data(quote_data)

            # Process through adapter
            pressure_metrics = self.adapter.add_quote_snapshot(snapshot)

            # If we have completed metrics, analyze with IFD v3
            if pressure_metrics and self.ifd:
                signal = self.ifd.analyze_pressure(pressure_metrics)

                if signal and signal.final_confidence >= 0.7:
                    logger.info(f"🎯 Institutional signal detected: {signal.strike} "
                              f"{signal.option_type} - Confidence: {signal.final_confidence:.2f}")
                    self.processed_signals.append(signal)
                    return signal

            elif pressure_metrics:
                # Log metrics even without IFD
                logger.info(f"📊 Pressure metrics generated: {pressure_metrics.strike} "
                          f"{pressure_metrics.option_type} - Ratio: {pressure_metrics.pressure_ratio:.2f}")

        except Exception as e:
            logger.error(f"Error processing quote data: {e}")

        return None

    def _create_snapshot_from_quote_data(self, quote_data: dict) -> QuotePressureSnapshot:
        """Convert raw quote data to QuotePressureSnapshot"""

        # Extract symbol components
        symbol = quote_data['symbol']

        # Determine option type
        if ' C' in symbol:
            option_type = 'C'
        elif ' P' in symbol:
            option_type = 'P'
        else:
            raise ValueError(f"Cannot determine option type from symbol: {symbol}")

        return QuotePressureSnapshot(
            timestamp=quote_data.get('last_update', datetime.now(timezone.utc)),
            symbol=symbol,
            strike=quote_data['strike'],
            option_type=option_type,
            bid_size=quote_data['bid_size'],
            ask_size=quote_data['ask_size'],
            bid_price=quote_data['bid_price'],
            ask_price=quote_data['ask_price'],
            pressure_ratio=quote_data['pressure_ratio']
        )

    def process_institutional_alert(self, alert: dict) -> Optional[Dict[str, Any]]:
        """
        Process an institutional alert from the quote monitor

        This is called when the quote monitor detects significant activity
        """
        # Create enhanced quote data from alert
        quote_data = {
            'symbol': alert['symbol'],
            'strike': alert['strike'],
            'bid_size': int(alert['bid'].split(' x ')[1]),
            'ask_size': int(alert['ask'].split(' x ')[1]),
            'bid_price': float(alert['bid'].split(' x ')[0].replace('$', '')),
            'ask_price': float(alert['ask'].split(' x ')[0].replace('$', '')),
            'pressure_ratio': alert['pressure_ratio'],
            'last_update': datetime.now(timezone.utc)
        }

        return self.process_quote_data(quote_data)

    def get_summary_report(self) -> dict:
        """Generate summary report of processed signals"""

        if not self.processed_signals:
            return {
                'total_signals': 0,
                'message': 'No institutional signals detected yet'
            }

        # Group signals by strike and type
        signal_groups = {}
        for signal in self.processed_signals:
            key = f"{signal.strike}_{signal.option_type}"
            if key not in signal_groups:
                signal_groups[key] = []
            signal_groups[key].append(signal)

        # Calculate statistics
        high_confidence_count = sum(1 for s in self.processed_signals if s.final_confidence >= 0.8)

        return {
            'total_signals': len(self.processed_signals),
            'high_confidence_signals': high_confidence_count,
            'unique_strikes': len(signal_groups),
            'signal_breakdown': {
                key: {
                    'count': len(signals),
                    'avg_confidence': sum(s.final_confidence for s in signals) / len(signals),
                    'dominant_side': max(set(s.dominant_side for s in signals),
                                       key=lambda x: sum(1 for s in signals if s.dominant_side == x))
                }
                for key, signals in signal_groups.items()
            }
        }


# Example integration with live monitor
def integrate_with_live_monitor():
    """
    Example of how to integrate with the live quote pressure monitor
    """
    print("🔗 IFD v3 Integration for Quote Pressure Monitor")
    print("=" * 60)

    # Initialize pipeline
    pipeline = QuotePressureToIFDPipeline(window_minutes=5, volume_multiplier=10.0)

    # Simulate processing institutional alerts
    # In production, this would be called from nq_options_quote_pressure.py

    sample_alert = {
        'time': '14:35:22',
        'symbol': 'NQM5 C22000',
        'strike': 22000,
        'bid': '$152.50 x 85',
        'ask': '$153.00 x 25',
        'pressure_ratio': 3.4,
        'direction': 'BUY_PRESSURE',
        'reasons': ['Large bid: 85 contracts', 'Extreme buy pressure: 3.40'],
        'spread': 0.50
    }

    print(f"\nProcessing institutional alert: {sample_alert['symbol']}")
    signal = pipeline.process_institutional_alert(sample_alert)

    if signal:
        print(f"\n✅ IFD v3 Signal Generated:")
        print(f"   Strike: {signal.strike} {signal.option_type}")
        print(f"   Confidence: {signal.final_confidence:.2f}")
        print(f"   Direction: {signal.dominant_side}")
        print(f"   Signal Type: {signal.signal_type}")

    # Generate summary
    summary = pipeline.get_summary_report()
    print(f"\n📊 Summary Report:")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    integrate_with_live_monitor()
