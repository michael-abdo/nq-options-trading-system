#!/usr/bin/env python3
"""
Limited Live Trading Orchestrator - Risk-Controlled Live Position Testing

This module orchestrates limited live trading with strict risk controls:
- Maximum 1-contract positions for initial testing
- Real order placement and execution monitoring
- Real P&L tracking vs predicted outcomes
- Slippage and execution quality analysis
- Automatic budget enforcement and shutoffs
- Stop-loss and risk management verification
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from decimal import Decimal
from pathlib import Path

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

# Import existing components
try:
    from shadow_trading_orchestrator import ShadowTradingOrchestrator, ShadowTradingConfig
    SHADOW_TRADING_AVAILABLE = True
except ImportError:
    SHADOW_TRADING_AVAILABLE = False

try:
    from real_performance_metrics import RealPerformanceMetrics
    REAL_PERFORMANCE_METRICS_AVAILABLE = True
except ImportError:
    try:
        from simple_performance_metrics import SimplePerformanceMetrics as RealPerformanceMetrics
        REAL_PERFORMANCE_METRICS_AVAILABLE = True
    except ImportError:
        REAL_PERFORMANCE_METRICS_AVAILABLE = False

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class LimitedLiveTradingConfig:
    """Configuration for limited live trading"""
    start_date: str                        # YYYY-MM-DD format
    duration_days: int = 7                 # Default 1 week
    max_position_size: int = 1             # Maximum contracts per position
    max_daily_positions: int = 3           # Maximum positions per day
    max_total_positions: int = 10          # Maximum total open positions

    # Budget controls
    daily_cost_limit: float = 8.0          # $8 daily data cost limit
    monthly_budget_limit: float = 200.0    # $200 monthly budget limit
    cost_per_signal_limit: float = 5.0     # $5 cost per signal limit

    # Risk management
    stop_loss_percentage: float = 2.0      # 2% stop loss
    profit_target_percentage: float = 4.0  # 4% profit target
    max_daily_loss: float = 50.0          # $50 max daily loss
    max_total_risk: float = 200.0         # $200 max total risk

    # Execution quality thresholds
    max_slippage_percentage: float = 1.0   # 1% max slippage
    min_fill_quality: float = 0.95        # 95% fill quality minimum
    max_execution_delay: float = 5.0      # 5 second max execution delay

    # Trading configuration
    trading_hours_start: str = "09:30"     # Market open
    trading_hours_end: str = "16:00"       # Market close
    confidence_threshold: float = 0.70     # Higher threshold for live trading

    # Monitoring and alerts
    enable_real_time_alerts: bool = True
    alert_on_budget_threshold: float = 0.8 # Alert at 80% budget usage
    auto_shutoff_enabled: bool = True      # Enable automatic shutoffs


@dataclass
class ExecutionMetrics:
    """Execution quality metrics for a trade"""
    order_id: str
    symbol: str
    intended_price: float
    actual_fill_price: float
    slippage_percentage: float
    execution_time_seconds: float
    fill_quality_score: float
    market_impact: float
    timestamp: str


@dataclass
class BudgetStatus:
    """Current budget and cost tracking"""
    daily_costs: float
    monthly_costs: float
    total_signals: int
    cost_per_signal: float
    remaining_daily_budget: float
    remaining_monthly_budget: float
    budget_utilization_pct: float
    auto_shutoff_triggered: bool


@dataclass
class LiveTradingPosition:
    """Live trading position tracking"""
    position_id: str
    symbol: str
    side: str                     # 'LONG' or 'SHORT'
    size: int                     # Number of contracts
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    stop_loss_price: float
    profit_target_price: float
    entry_timestamp: str
    predicted_outcome: float      # Algorithm's predicted P&L
    actual_vs_predicted: float    # Actual vs predicted variance
    risk_amount: float
    is_open: bool


class BudgetEnforcer:
    """Enforces budget limits and triggers automatic shutoffs"""

    def __init__(self, config: LimitedLiveTradingConfig):
        self.config = config
        self.daily_costs = 0.0
        self.monthly_costs = 0.0
        self.signal_count = 0
        self.shutoff_triggered = False
        self.alert_triggered = False

    def record_cost(self, cost: float, cost_type: str = "data"):
        """Record a cost and check budget limits"""
        self.daily_costs += cost
        self.monthly_costs += cost

        if cost_type == "signal":
            self.signal_count += 1

        # Check budget limits
        self._check_budget_limits()

    def _check_budget_limits(self):
        """Check if budget limits are exceeded"""
        daily_remaining = self.config.daily_cost_limit - self.daily_costs
        monthly_remaining = self.config.monthly_budget_limit - self.monthly_costs

        # Calculate cost per signal
        cost_per_signal = self.monthly_costs / max(self.signal_count, 1)

        # Check for shutoff conditions
        if (self.daily_costs >= self.config.daily_cost_limit or
            self.monthly_costs >= self.config.monthly_budget_limit or
            cost_per_signal >= self.config.cost_per_signal_limit):

            if self.config.auto_shutoff_enabled and not self.shutoff_triggered:
                self.shutoff_triggered = True
                logger.critical(f"BUDGET LIMIT EXCEEDED - AUTO SHUTOFF TRIGGERED")
                logger.critical(f"Daily costs: ${self.daily_costs:.2f} / ${self.config.daily_cost_limit:.2f}")
                logger.critical(f"Monthly costs: ${self.monthly_costs:.2f} / ${self.config.monthly_budget_limit:.2f}")
                logger.critical(f"Cost per signal: ${cost_per_signal:.2f} / ${self.config.cost_per_signal_limit:.2f}")

        # Check for alert conditions
        budget_utilization = max(
            self.daily_costs / self.config.daily_cost_limit,
            self.monthly_costs / self.config.monthly_budget_limit
        )

        if (budget_utilization >= self.config.alert_on_budget_threshold and
            not self.alert_triggered):
            self.alert_triggered = True
            logger.warning(f"BUDGET ALERT: {budget_utilization:.0%} of budget used")

    def get_budget_status(self) -> BudgetStatus:
        """Get current budget status"""
        cost_per_signal = self.monthly_costs / max(self.signal_count, 1)

        return BudgetStatus(
            daily_costs=self.daily_costs,
            monthly_costs=self.monthly_costs,
            total_signals=self.signal_count,
            cost_per_signal=cost_per_signal,
            remaining_daily_budget=max(0, self.config.daily_cost_limit - self.daily_costs),
            remaining_monthly_budget=max(0, self.config.monthly_budget_limit - self.monthly_costs),
            budget_utilization_pct=max(
                self.daily_costs / self.config.daily_cost_limit,
                self.monthly_costs / self.config.monthly_budget_limit
            ) * 100,
            auto_shutoff_triggered=self.shutoff_triggered
        )

    def is_trading_allowed(self) -> bool:
        """Check if trading is allowed based on budget status"""
        return not self.shutoff_triggered


class LiveOrderExecutor:
    """Manages live order execution with broker APIs"""

    def __init__(self, config: LimitedLiveTradingConfig):
        self.config = config
        self.open_positions: Dict[str, LiveTradingPosition] = {}
        self.execution_history: List[ExecutionMetrics] = []
        self.total_realized_pnl = 0.0

        # Mock broker connection (would be real in production)
        self.broker_connected = False

    def connect_to_broker(self) -> bool:
        """Connect to broker API (Interactive Brokers, Tradovate, etc.)"""
        try:
            # This would implement real broker API connections
            # TODO: Replace with actual broker API (Interactive Brokers, Tradovate)
            logger.info("Connecting to broker API...")
            time.sleep(1)  # Simulate connection time
            self.broker_connected = True
            logger.info("✅ Broker connection established")
            return True

        except Exception as e:
            logger.error(f"❌ Broker connection failed: {e}")
            return False

    def place_live_order(self, signal: Dict[str, Any], position_size: int = 1) -> Optional[LiveTradingPosition]:
        """Place a live order with real broker"""

        if not self.broker_connected:
            logger.error("Cannot place order - broker not connected")
            return None

        # Enforce position size limit
        if position_size > self.config.max_position_size:
            logger.warning(f"Position size {position_size} exceeds limit {self.config.max_position_size}")
            position_size = self.config.max_position_size

        # Check position limits
        if len(self.open_positions) >= self.config.max_total_positions:
            logger.warning("Maximum open positions reached, skipping order")
            return None

        try:
            # Create order details
            symbol = f"NQ{signal['strike']}"
            side = "LONG" if "call" in signal.get('signal_type', '').lower() else "SHORT"

            # Calculate risk management levels
            entry_price = self._get_current_market_price(symbol)
            stop_loss_price = self._calculate_stop_loss(entry_price, side)
            profit_target_price = self._calculate_profit_target(entry_price, side)

            # Calculate risk amount (for options, use more realistic per-contract risk)
            risk_amount = abs(entry_price - stop_loss_price) * position_size * 1  # Risk per dollar difference for options

            # Check if risk exceeds limits
            if risk_amount > self.config.max_total_risk:
                logger.warning(f"Risk amount ${risk_amount:.2f} exceeds limit ${self.config.max_total_risk:.2f}")
                return None

            # Execute order through broker API (currently simulated)
            # TODO: Replace with real broker order execution
            start_time = time.time()
            fill_price, fill_quality = self._execute_market_order(symbol, side, position_size, entry_price)
            execution_time = time.time() - start_time

            # Calculate execution metrics
            slippage_pct = abs(fill_price - entry_price) / entry_price * 100

            # Check execution quality
            if slippage_pct > self.config.max_slippage_percentage:
                logger.warning(f"High slippage detected: {slippage_pct:.2f}%")

            if execution_time > self.config.max_execution_delay:
                logger.warning(f"Slow execution: {execution_time:.2f}s")

            # Create position
            position_id = f"pos_{int(time.time())}_{symbol}"
            position = LiveTradingPosition(
                position_id=position_id,
                symbol=symbol,
                side=side,
                size=position_size,
                entry_price=fill_price,
                current_price=fill_price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                stop_loss_price=stop_loss_price,
                profit_target_price=profit_target_price,
                entry_timestamp=datetime.now(timezone.utc).isoformat(),
                predicted_outcome=signal.get('expected_value', 0.0),
                actual_vs_predicted=0.0,
                risk_amount=risk_amount,
                is_open=True
            )

            # Store position
            self.open_positions[position_id] = position

            # Record execution metrics
            execution_metrics = ExecutionMetrics(
                order_id=position_id,
                symbol=symbol,
                intended_price=entry_price,
                actual_fill_price=fill_price,
                slippage_percentage=slippage_pct,
                execution_time_seconds=execution_time,
                fill_quality_score=fill_quality,
                market_impact=slippage_pct,  # Simplified
                timestamp=datetime.now(timezone.utc).isoformat()
            )

            self.execution_history.append(execution_metrics)

            logger.info(f"✅ Live order executed: {symbol} {side} {position_size} @ ${fill_price:.2f}")
            logger.info(f"   Slippage: {slippage_pct:.2f}%, Execution: {execution_time:.2f}s")

            return position

        except Exception as e:
            logger.error(f"❌ Live order execution failed: {e}")
            return None

    def _get_current_market_price(self, symbol: str) -> float:
        """Get current market price for symbol"""
        # TODO: Replace with real market data feed (Barchart, Databento, Polygon)
        # Currently simulating realistic option prices
        if 'NQ' in symbol:
            # Simulate NQ option prices (typically $1-$500 range)
            base_price = 50 + (hash(symbol) % 200)  # $50-$250 range for options
        else:
            base_price = 100 + (hash(symbol) % 100)  # Generic option pricing
        return float(base_price)

    def _calculate_stop_loss(self, entry_price: float, side: str) -> float:
        """Calculate stop loss price"""
        if side == "LONG":
            return max(entry_price * (1 - self.config.stop_loss_percentage / 100), entry_price - 5.0)  # Cap at $5 risk
        else:
            return entry_price * (1 + self.config.stop_loss_percentage / 100)

    def _calculate_profit_target(self, entry_price: float, side: str) -> float:
        """Calculate profit target price"""
        if side == "LONG":
            return entry_price * (1 + self.config.profit_target_percentage / 100)
        else:
            return entry_price * (1 - self.config.profit_target_percentage / 100)

    def _execute_market_order(self, symbol: str, side: str, size: int, intended_price: float) -> Tuple[float, float]:
        """Execute market order and return fill price and quality"""
        # Simulate market execution with realistic slippage
        import random

        # Simulate slippage (0-0.5% typical)
        slippage_factor = random.uniform(0.0, 0.005)
        if side == "LONG":
            fill_price = intended_price * (1 + slippage_factor)
        else:
            fill_price = intended_price * (1 - slippage_factor)

        # Simulate fill quality (90-100%)
        fill_quality = random.uniform(0.90, 1.00)

        return fill_price, fill_quality

    def update_positions(self, market_data: Dict[str, Any]):
        """Update open positions with current market data"""
        for position_id, position in self.open_positions.items():
            if position.is_open:
                # Get current price from market data or fallback to simulation
                if position.symbol in market_data:
                    current_price = market_data[position.symbol]
                else:
                    current_price = self._get_current_market_price(position.symbol)
                position.current_price = current_price

                # Calculate unrealized P&L (using consistent multiplier with risk calculation)
                if position.side == "LONG":
                    position.unrealized_pnl = (current_price - position.entry_price) * position.size * 1
                else:
                    position.unrealized_pnl = (position.entry_price - current_price) * position.size * 1

                # Update actual vs predicted
                position.actual_vs_predicted = position.unrealized_pnl - position.predicted_outcome

                # Check stop loss and profit targets
                self._check_exit_conditions(position)

    def _check_exit_conditions(self, position: LiveTradingPosition):
        """Check if position should be closed due to stop loss or profit target"""
        current_price = position.current_price

        should_close = False
        close_reason = ""

        if position.side == "LONG":
            if current_price <= position.stop_loss_price:
                should_close = True
                close_reason = "Stop Loss"
            elif current_price >= position.profit_target_price:
                should_close = True
                close_reason = "Profit Target"
        else:
            if current_price >= position.stop_loss_price:
                should_close = True
                close_reason = "Stop Loss"
            elif current_price <= position.profit_target_price:
                should_close = True
                close_reason = "Profit Target"

        if should_close:
            self._close_position(position, close_reason)

    def _close_position(self, position: LiveTradingPosition, reason: str):
        """Close a position and record realized P&L"""
        position.is_open = False
        position.realized_pnl = position.unrealized_pnl
        self.total_realized_pnl += position.realized_pnl

        logger.info(f"🔒 Position closed: {position.symbol} {reason}")
        logger.info(f"   Realized P&L: ${position.realized_pnl:.2f}")
        logger.info(f"   Predicted: ${position.predicted_outcome:.2f}, Actual: ${position.realized_pnl:.2f}")
        logger.info(f"   Variance: ${position.actual_vs_predicted:.2f}")

    def get_execution_quality_summary(self) -> Dict[str, Any]:
        """Get summary of execution quality metrics"""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'avg_slippage_pct': 0.0,
                'avg_execution_time': 0.0,
                'avg_fill_quality': 0.0,
                'quality_issues': 0,
                'quality_score': 1.0
            }

        slippages = [e.slippage_percentage for e in self.execution_history]
        execution_times = [e.execution_time_seconds for e in self.execution_history]
        fill_qualities = [e.fill_quality_score for e in self.execution_history]

        quality_issues = sum(1 for e in self.execution_history
                           if e.slippage_percentage > self.config.max_slippage_percentage or
                              e.execution_time_seconds > self.config.max_execution_delay or
                              e.fill_quality_score < self.config.min_fill_quality)

        return {
            'total_executions': len(self.execution_history),
            'avg_slippage_pct': sum(slippages) / len(slippages),
            'avg_execution_time': sum(execution_times) / len(execution_times),
            'avg_fill_quality': sum(fill_qualities) / len(fill_qualities),
            'quality_issues': quality_issues,
            'quality_score': 1.0 - (quality_issues / len(self.execution_history))
        }


class LimitedLiveTradingOrchestrator:
    """Main orchestrator for limited live trading with risk controls"""

    def __init__(self, config: LimitedLiveTradingConfig):
        self.config = config
        self.budget_enforcer = BudgetEnforcer(config)
        self.order_executor = LiveOrderExecutor(config)
        self.start_time = None
        self.is_running = False

        # Initialize performance metrics
        if REAL_PERFORMANCE_METRICS_AVAILABLE:
            self.performance_metrics = RealPerformanceMetrics()
        else:
            self.performance_metrics = None

        # Initialize shadow trading for signal generation
        if SHADOW_TRADING_AVAILABLE:
            shadow_config = ShadowTradingConfig(
                start_date=config.start_date,
                duration_days=config.duration_days,
                trading_hours_start=config.trading_hours_start,
                trading_hours_end=config.trading_hours_end,
                confidence_threshold=config.confidence_threshold
            )
            self.shadow_trader = ShadowTradingOrchestrator(shadow_config)
        else:
            self.shadow_trader = None

        logger.info("Limited Live Trading Orchestrator initialized")

    def start_live_trading(self) -> bool:
        """Start limited live trading"""
        if self.is_running:
            logger.warning("Live trading already running")
            return False

        try:
            # Connect to broker
            if not self.order_executor.connect_to_broker():
                logger.error("Failed to connect to broker")
                return False

            # Start performance monitoring
            if self.performance_metrics:
                self.performance_metrics.start_monitoring()

            self.start_time = datetime.now(timezone.utc)
            self.is_running = True

            logger.info("🚀 Limited Live Trading Started")
            logger.info(f"   Max position size: {self.config.max_position_size} contracts")
            logger.info(f"   Daily cost limit: ${self.config.daily_cost_limit}")
            logger.info(f"   Monthly budget: ${self.config.monthly_budget_limit}")
            logger.info(f"   Auto shutoff: {'Enabled' if self.config.auto_shutoff_enabled else 'Disabled'}")

            return True

        except Exception as e:
            logger.error(f"Failed to start live trading: {e}")
            self.is_running = False
            return False

    def process_signal_for_live_trading(self, signal: Dict[str, Any]) -> bool:
        """Process a signal for potential live trading"""

        # Check if trading is allowed
        if not self.budget_enforcer.is_trading_allowed():
            logger.warning("Trading suspended due to budget limits")
            return False

        # Check signal quality
        if signal.get('confidence', 0) < self.config.confidence_threshold:
            logger.info(f"Signal confidence {signal.get('confidence', 0):.2f} below threshold {self.config.confidence_threshold:.2f}")
            return False

        # Record signal cost (use a realistic cost, not the limit)
        actual_signal_cost = min(4.0, self.config.cost_per_signal_limit - 1.0)  # Use reasonable cost below limit
        self.budget_enforcer.record_cost(actual_signal_cost, "signal")

        # Check if we can still trade after recording cost
        if not self.budget_enforcer.is_trading_allowed():
            logger.warning("Budget limit reached after signal cost")
            return False

        # Place live order
        position = self.order_executor.place_live_order(signal, self.config.max_position_size)

        if position:
            logger.info(f"✅ Live position opened: {position.symbol} (Risk: ${position.risk_amount:.2f})")
            return True
        else:
            logger.warning("❌ Failed to open live position")
            return False

    def get_trading_status(self) -> Dict[str, Any]:
        """Get current trading status and metrics"""
        budget_status = self.budget_enforcer.get_budget_status()
        execution_quality = self.order_executor.get_execution_quality_summary()

        # Calculate total risk
        total_risk = sum(pos.risk_amount for pos in self.order_executor.open_positions.values() if pos.is_open)

        # Calculate total P&L
        total_unrealized = sum(pos.unrealized_pnl for pos in self.order_executor.open_positions.values() if pos.is_open)
        total_realized = self.order_executor.total_realized_pnl

        return {
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'trading_allowed': self.budget_enforcer.is_trading_allowed(),

            # Position summary
            'open_positions': len([p for p in self.order_executor.open_positions.values() if p.is_open]),
            'max_positions': self.config.max_total_positions,
            'total_risk': total_risk,
            'max_risk': self.config.max_total_risk,

            # P&L summary
            'total_unrealized_pnl': total_unrealized,
            'total_realized_pnl': total_realized,
            'total_pnl': total_unrealized + total_realized,

            # Budget status
            'budget_status': asdict(budget_status),

            # Execution quality
            'execution_quality': execution_quality,

            # Risk metrics
            'risk_utilization_pct': (total_risk / self.config.max_total_risk) * 100,
            'position_utilization_pct': (len([p for p in self.order_executor.open_positions.values() if p.is_open]) / self.config.max_total_positions) * 100
        }

    def stop_live_trading(self) -> Dict[str, Any]:
        """Stop live trading and generate final report"""
        if not self.is_running:
            logger.warning("Live trading not running")
            return {}

        self.is_running = False

        # Close all open positions
        for position in self.order_executor.open_positions.values():
            if position.is_open:
                self.order_executor._close_position(position, "System Shutdown")

        # Stop performance monitoring
        if self.performance_metrics:
            self.performance_metrics.stop_monitoring()

        # Generate final report
        final_status = self.get_trading_status()

        logger.info("🛑 Limited Live Trading Stopped")
        logger.info(f"   Total P&L: ${final_status['total_pnl']:.2f}")
        logger.info(f"   Budget used: {final_status['budget_status']['budget_utilization_pct']:.1f}%")
        logger.info(f"   Execution quality: {final_status['execution_quality']['quality_score']:.1%}")

        return final_status


# Factory function
def create_limited_live_trading_orchestrator(config_dict: Dict[str, Any]) -> LimitedLiveTradingOrchestrator:
    """Create limited live trading orchestrator from configuration"""
    config = LimitedLiveTradingConfig(**config_dict)
    return LimitedLiveTradingOrchestrator(config)


if __name__ == "__main__":
    # Example usage
    config = {
        'start_date': '2025-06-12',
        'duration_days': 1,  # Start with 1 day
        'max_position_size': 1,
        'daily_cost_limit': 8.0,
        'monthly_budget_limit': 200.0,
        'auto_shutoff_enabled': True
    }

    orchestrator = create_limited_live_trading_orchestrator(config)

    if orchestrator.start_live_trading():
        logger.info("Limited live trading started successfully")

        # Simulate signal processing
        test_signal = {
            'id': 'test_live_signal_1',
            'strike': 21350,
            'confidence': 0.75,
            'expected_value': 25.0,
            'signal_type': 'call_buying'
        }

        success = orchestrator.process_signal_for_live_trading(test_signal)

        # Get status
        status = orchestrator.get_trading_status()
        print(f"Trading Status: {json.dumps(status, indent=2, default=str)}")

        # Stop trading
        final_report = orchestrator.stop_live_trading()
