#!/usr/bin/env python3
"""
Live Monitor - Continuous chart monitoring with alerts
Monitors price action and generates alerts based on configured conditions
"""

import sys
import os
import time
import signal
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Add parent directories to path
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent))
sys.path.append(str(script_dir.parent.parent))

from databento_5m_provider import Databento5MinuteProvider
from chart_config_manager import ChartConfigManager
from utils.timezone_utils import get_eastern_time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('outputs/live_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class LiveMarketMonitor:
    """Live market monitoring with alert system"""

    def __init__(self, symbol="NQM5", config_name="default"):
        self.symbol = symbol
        self.running = True
        self.data_provider = Databento5MinuteProvider()

        # Load configuration
        config_manager = ChartConfigManager()
        self.config = config_manager.load_config(config_name)

        # Monitoring settings
        self.check_interval = self.config.get("chart", {}).get("update_interval", 30)
        self.alert_cooldown = 300  # 5 minutes between same alerts
        self.last_alerts = {}

        # Alert thresholds
        self.price_change_threshold = 0.005  # 0.5% price change
        self.volume_spike_threshold = 2.0    # 2x average volume

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info(f"Initialized live monitor for {symbol}")
        logger.info(f"Check interval: {self.check_interval} seconds")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Shutdown signal received")
        self.running = False

    def check_market_conditions(self):
        """Check current market conditions and generate alerts"""
        try:
            # Get latest data (50 bars for indicators)
            df = self.data_provider.get_latest_bars(self.symbol, 50)
            if df.empty:
                logger.warning("No data available")
                return None

            current_bar = df.iloc[-1]
            current_time = get_eastern_time()

            # Calculate indicators
            sma_20 = df['close'].rolling(20).mean().iloc[-1] if len(df) >= 20 else None
            volume_ma = df['volume'].rolling(20).mean().iloc[-1] if len(df) >= 20 else None

            # Price change from 5 bars ago (25 minutes)
            price_change_pct = 0
            if len(df) >= 6:
                old_price = df['close'].iloc[-6]
                price_change_pct = (current_bar['close'] - old_price) / old_price

            # Volume spike detection
            volume_spike = False
            if volume_ma and volume_ma > 0:
                volume_ratio = current_bar['volume'] / volume_ma
                volume_spike = volume_ratio > self.volume_spike_threshold

            # Market conditions summary
            conditions = {
                'timestamp': current_time,
                'price': current_bar['close'],
                'volume': current_bar['volume'],
                'price_change_pct': price_change_pct,
                'volume_ratio': current_bar['volume'] / volume_ma if volume_ma else 0,
                'sma_20': sma_20,
                'above_sma': current_bar['close'] > sma_20 if sma_20 else None,
                'volume_spike': volume_spike
            }

            # Check for alerts
            self._check_alerts(conditions)

            return conditions

        except Exception as e:
            logger.error(f"Error checking market conditions: {e}")
            return None

    def _check_alerts(self, conditions):
        """Check conditions and generate alerts"""
        alerts = []
        current_time = conditions['timestamp']

        # Price movement alert
        if abs(conditions['price_change_pct']) > self.price_change_threshold:
            direction = "UP" if conditions['price_change_pct'] > 0 else "DOWN"
            alert_key = f"price_move_{direction}"

            if self._should_alert(alert_key, current_time):
                alert_msg = f"🚨 PRICE ALERT: {self.symbol} moved {direction} {conditions['price_change_pct']:.2%} to ${conditions['price']:,.2f}"
                alerts.append(alert_msg)
                self.last_alerts[alert_key] = current_time

        # Volume spike alert
        if conditions['volume_spike']:
            alert_key = "volume_spike"

            if self._should_alert(alert_key, current_time):
                alert_msg = f"📊 VOLUME ALERT: {self.symbol} volume spike {conditions['volume_ratio']:.1f}x average (Volume: {conditions['volume']:,})"
                alerts.append(alert_msg)
                self.last_alerts[alert_key] = current_time

        # SMA crossover alert
        if conditions['above_sma'] is not None:
            if conditions['above_sma']:
                alert_key = "above_sma"
                alert_msg = f"📈 TECHNICAL: {self.symbol} above SMA20 at ${conditions['price']:,.2f}"
            else:
                alert_key = "below_sma"
                alert_msg = f"📉 TECHNICAL: {self.symbol} below SMA20 at ${conditions['price']:,.2f}"

            if self._should_alert(alert_key, current_time):
                alerts.append(alert_msg)
                self.last_alerts[alert_key] = current_time

        # Log alerts
        for alert in alerts:
            logger.warning(alert)
            print(f"[{current_time.strftime('%H:%M:%S')}] {alert}")

    def _should_alert(self, alert_key, current_time):
        """Check if enough time has passed since last alert of this type"""
        if alert_key not in self.last_alerts:
            return True

        time_since_last = (current_time - self.last_alerts[alert_key]).total_seconds()
        return time_since_last > self.alert_cooldown

    def print_status(self, conditions):
        """Print current market status"""
        if not conditions:
            return

        timestamp = conditions['timestamp'].strftime('%H:%M:%S')
        price = conditions['price']
        volume = conditions['volume']
        price_change = conditions['price_change_pct']

        # Status indicators
        price_arrow = "🔺" if price_change > 0.001 else "🔻" if price_change < -0.001 else "➡️"
        volume_indicator = "🔥" if conditions['volume_spike'] else "📊"
        sma_indicator = "📈" if conditions.get('above_sma') else "📉" if conditions.get('above_sma') is False else "➖"

        status = f"[{timestamp}] {self.symbol}: ${price:,.2f} {price_arrow} ({price_change:+.2%}) | Vol: {volume:,} {volume_indicator} | SMA: {sma_indicator}"
        print(status)

    def run(self, verbose=False):
        """Run the live monitoring loop"""
        logger.info("Starting live market monitor...")
        print(f"🔍 Monitoring {self.symbol} every {self.check_interval} seconds")
        print("📊 Alerts enabled for price moves >0.5% and volume spikes >2x")
        print("🔔 Press Ctrl+C to stop monitoring")
        print("=" * 80)

        consecutive_errors = 0
        max_errors = 5

        while self.running:
            try:
                conditions = self.check_market_conditions()

                if conditions:
                    if verbose:
                        self.print_status(conditions)
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        logger.error(f"Too many consecutive errors ({max_errors}), stopping monitor")
                        break

                # Wait for next check
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                consecutive_errors += 1
                if consecutive_errors >= max_errors:
                    logger.error(f"Too many consecutive errors ({max_errors}), stopping monitor")
                    break
                time.sleep(10)  # Wait before retrying

        logger.info("Live monitor stopped")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Live market monitor with alerts")
    parser.add_argument("--symbol", default="NQM5", help="Contract symbol to monitor")
    parser.add_argument("--config", default="default", help="Configuration preset")
    parser.add_argument("--verbose", action="store_true", help="Show detailed status updates")
    parser.add_argument("--interval", type=int, help="Check interval in seconds (overrides config)")

    args = parser.parse_args()

    try:
        monitor = LiveMarketMonitor(args.symbol, args.config)

        # Override interval if specified
        if args.interval:
            monitor.check_interval = args.interval

        monitor.run(verbose=args.verbose)
        return 0

    except Exception as e:
        logger.error(f"Monitor failed to start: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
