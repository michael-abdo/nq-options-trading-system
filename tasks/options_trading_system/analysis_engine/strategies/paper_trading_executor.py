#!/usr/bin/env python3
"""
Paper Trading Execution Engine for IFD v1.0 vs v3.0 Comparison

This module provides paper trading capabilities to validate algorithm
performance in a simulated environment before production deployment.

Features:
- Simulated order execution with realistic fills
- Position tracking and P&L calculation
- Risk management and position limits
- Performance metrics collection
- Integration with A/B testing framework
"""

import json
import os
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import threading
from collections import defaultdict


class OrderType(Enum):
    """Order types supported by paper trading"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderStatus(Enum):
    """Order status tracking"""
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class PositionSide(Enum):
    """Position direction"""
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class Order:
    """Paper trading order representation"""
    order_id: str
    symbol: str
    strike: float
    option_type: str  # CALL or PUT
    side: str  # BUY or SELL
    quantity: int
    order_type: OrderType
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    # Order state
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_fill_price: float = 0.0

    # Timestamps
    created_time: datetime = field(default_factory=datetime.now)
    filled_time: Optional[datetime] = None

    # Source tracking
    algorithm_version: str = ""
    signal_id: str = ""


@dataclass
class Position:
    """Paper trading position tracking"""
    symbol: str
    strike: float
    option_type: str

    # Position details
    quantity: int = 0
    average_cost: float = 0.0
    current_price: float = 0.0

    # P&L tracking
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0

    # Timestamps
    opened_time: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def update_price(self, new_price: float):
        """Update position with new market price"""
        self.current_price = new_price
        if self.quantity != 0:
            self.unrealized_pnl = (new_price - self.average_cost) * self.quantity
        self.last_updated = get_eastern_time()


@dataclass
class TradingSession:
    """Paper trading session tracking"""
    session_id: str
    start_time: datetime
    algorithm_version: str

    # Account details
    starting_capital: float = 100000.0
    current_capital: float = 100000.0
    buying_power: float = 100000.0

    # Position limits
    max_positions: int = 10
    max_position_size: int = 5
    max_loss_per_trade: float = 1000.0

    # Performance tracking
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_capital: float = 100000.0

    # Risk metrics
    current_exposure: float = 0.0
    max_exposure: float = 0.0


class PaperTradingExecutor:
    """
    Paper trading execution engine for algorithm validation

    Features:
    - Realistic order fills based on market data
    - Position and P&L tracking
    - Risk management enforcement
    - Performance metrics collection
    """

    def __init__(self, output_dir: str = "outputs/paper_trading"):
        """
        Initialize paper trading executor

        Args:
            output_dir: Directory for saving trading logs
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # Trading sessions by algorithm version
        self.sessions: Dict[str, TradingSession] = {}

        # Order and position tracking
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Dict[str, Position]] = {}  # {algo_version: {symbol: Position}}

        # Market data cache
        self.market_prices: Dict[str, float] = {}

        # Thread safety
        self._lock = threading.Lock()

        # Execution log
        self.execution_log: List[Dict[str, Any]] = []

    def start_session(self, algorithm_version: str, starting_capital: float = 100000.0) -> str:
        """
        Start a new paper trading session

        Args:
            algorithm_version: Algorithm version (v1.0 or v3.0)
            starting_capital: Initial capital amount

        Returns:
            Session ID
        """
        session_id = f"paper_{algorithm_version}_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}"

        with self._lock:
            session = TradingSession(
                session_id=session_id,
                start_time=get_eastern_time(),
                algorithm_version=algorithm_version,
                starting_capital=starting_capital,
                current_capital=starting_capital,
                buying_power=starting_capital
            )

            self.sessions[algorithm_version] = session
            self.positions[algorithm_version] = {}

        print(f"📊 Paper trading session started: {session_id}")
        print(f"   Algorithm: {algorithm_version}")
        print(f"   Capital: ${starting_capital:,.2f}")

        return session_id

    def submit_order(self, algorithm_version: str, signal_data: Dict[str, Any]) -> Optional[str]:
        """
        Submit a paper trading order based on signal

        Args:
            algorithm_version: Source algorithm version
            signal_data: Trading signal data

        Returns:
            Order ID if successful, None if rejected
        """
        if algorithm_version not in self.sessions:
            print(f"Error: No active session for {algorithm_version}")
            return None

        # Extract order details from signal
        symbol = signal_data.get("symbol", "")
        strike = signal_data.get("strike", 0)
        option_type = signal_data.get("option_type", "")
        direction = signal_data.get("direction", "")
        confidence = signal_data.get("confidence", 0)
        entry_price = signal_data.get("entry_price", 0)

        # Determine order parameters
        side = "BUY" if direction == "LONG" else "SELL"
        quantity = self._calculate_position_size(algorithm_version, entry_price, confidence)

        if quantity == 0:
            print(f"Position size calculation returned 0 for {symbol}")
            return None

        # Create order
        order_id = f"ORD_{get_eastern_time().strftime('%Y%m%d_%H%M%S_%f')}"

        order = Order(
            order_id=order_id,
            symbol=symbol,
            strike=strike,
            option_type=option_type,
            side=side,
            quantity=quantity,
            order_type=OrderType.LIMIT,
            limit_price=entry_price,
            algorithm_version=algorithm_version,
            signal_id=signal_data.get("signal_id", "")
        )

        # Risk checks
        if not self._validate_order(algorithm_version, order):
            print(f"Order rejected due to risk limits: {order_id}")
            return None

        with self._lock:
            self.orders[order_id] = order

            # Log order submission
            self._log_execution({
                "event": "ORDER_SUBMITTED",
                "order_id": order_id,
                "algorithm_version": algorithm_version,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "limit_price": entry_price,
                "signal_confidence": confidence
            })

        # Simulate order fill (in real implementation, this would check market data)
        self._simulate_order_fill(order_id)

        return order_id

    def _calculate_position_size(self, algorithm_version: str, price: float,
                                confidence: float) -> int:
        """Calculate position size based on Kelly Criterion and risk limits"""
        session = self.sessions[algorithm_version]

        # Base position size from available capital
        max_position_value = session.buying_power * 0.1  # Max 10% per position

        # Adjust by confidence (Kelly-inspired sizing)
        confidence_multiplier = min(confidence, 1.0)  # Cap at 100%

        # Calculate contracts
        contract_value = price * 100  # Options multiplier
        base_contracts = int(max_position_value / contract_value)

        # Apply confidence adjustment
        sized_contracts = int(base_contracts * confidence_multiplier)

        # Apply position limits
        final_contracts = min(sized_contracts, session.max_position_size)

        # Ensure at least 1 contract for testing
        return max(1, final_contracts)

    def _validate_order(self, algorithm_version: str, order: Order) -> bool:
        """Validate order against risk limits"""
        session = self.sessions[algorithm_version]

        # Check position limits
        current_positions = len(self.positions[algorithm_version])
        if current_positions >= session.max_positions:
            return False

        # Check buying power
        order_value = order.quantity * (order.limit_price or 0) * 100
        if order_value > session.buying_power:
            return False

        # Check max loss per trade
        potential_loss = order_value  # Worst case for options
        if potential_loss > session.max_loss_per_trade:
            return False

        return True

    def _simulate_order_fill(self, order_id: str):
        """Simulate order execution with realistic fills"""
        order = self.orders.get(order_id)
        if not order:
            return

        # Simulate market conditions (in production, use real market data)
        fill_price = order.limit_price or 0

        # Add slight slippage for market orders
        if order.order_type == OrderType.MARKET:
            slippage = 0.01 if order.side == "BUY" else -0.01
            fill_price *= (1 + slippage)

        # Update order status
        with self._lock:
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_fill_price = fill_price
            order.filled_time = get_eastern_time()

            # Update position
            self._update_position(order)

            # Update session capital
            session = self.sessions[order.algorithm_version]
            order_value = order.filled_quantity * fill_price * 100

            if order.side == "BUY":
                session.current_capital -= order_value
                session.buying_power -= order_value
            else:
                session.current_capital += order_value
                session.buying_power += order_value

            # Log execution
            self._log_execution({
                "event": "ORDER_FILLED",
                "order_id": order_id,
                "fill_price": fill_price,
                "fill_quantity": order.filled_quantity,
                "order_value": order_value
            })

    def _update_position(self, order: Order):
        """Update position based on filled order"""
        positions = self.positions[order.algorithm_version]
        position_key = f"{order.symbol}_{order.strike}_{order.option_type}"

        if position_key not in positions:
            positions[position_key] = Position(
                symbol=order.symbol,
                strike=order.strike,
                option_type=order.option_type
            )

        position = positions[position_key]

        if order.side == "BUY":
            # Adding to position
            total_cost = (position.quantity * position.average_cost +
                         order.filled_quantity * order.average_fill_price)
            position.quantity += order.filled_quantity
            position.average_cost = total_cost / position.quantity if position.quantity > 0 else 0
        else:
            # Reducing position
            if position.quantity >= order.filled_quantity:
                # Calculate realized P&L
                realized = (order.average_fill_price - position.average_cost) * order.filled_quantity
                position.realized_pnl += realized
                position.quantity -= order.filled_quantity

                # Update session P&L
                session = self.sessions[order.algorithm_version]
                session.total_pnl += realized

                if realized > 0:
                    session.winning_trades += 1
                else:
                    session.losing_trades += 1

        # Remove position if flat
        if position.quantity == 0:
            del positions[position_key]

    def update_market_prices(self, price_data: Dict[str, float]):
        """Update market prices for position marking"""
        with self._lock:
            self.market_prices.update(price_data)

            # Update all positions
            for algo_version, positions in self.positions.items():
                session = self.sessions[algo_version]
                total_unrealized = 0

                for position in positions.values():
                    price_key = f"{position.symbol}_{position.strike}_{position.option_type}"
                    if price_key in price_data:
                        position.update_price(price_data[price_key])
                        total_unrealized += position.unrealized_pnl

                # Update session metrics
                session.current_capital = session.starting_capital + session.total_pnl + total_unrealized

                # Track drawdown
                if session.current_capital > session.peak_capital:
                    session.peak_capital = session.current_capital

                drawdown = session.peak_capital - session.current_capital
                session.max_drawdown = max(session.max_drawdown, drawdown)

    def get_session_performance(self, algorithm_version: str) -> Dict[str, Any]:
        """Get current performance metrics for a session"""
        if algorithm_version not in self.sessions:
            return {"error": "No active session"}

        session = self.sessions[algorithm_version]
        positions = self.positions[algorithm_version]

        # Calculate current metrics
        total_unrealized = sum(p.unrealized_pnl for p in positions.values())
        total_realized = session.total_pnl

        return {
            "session_id": session.session_id,
            "algorithm_version": algorithm_version,
            "duration_hours": (get_eastern_time() - session.start_time).total_seconds() / 3600,
            "starting_capital": session.starting_capital,
            "current_capital": session.current_capital,
            "total_pnl": total_realized + total_unrealized,
            "realized_pnl": total_realized,
            "unrealized_pnl": total_unrealized,
            "total_trades": session.total_trades,
            "winning_trades": session.winning_trades,
            "losing_trades": session.losing_trades,
            "win_rate": session.winning_trades / max(session.total_trades, 1),
            "max_drawdown": session.max_drawdown,
            "current_positions": len(positions),
            "position_details": [asdict(p) for p in positions.values()]
        }

    def compare_sessions(self) -> Dict[str, Any]:
        """Compare performance across all active sessions"""
        comparison = {
            "timestamp": get_eastern_time().isoformat(),
            "sessions": {},
            "winner": None,
            "summary": {}
        }

        best_pnl = float('-inf')
        best_algo = None

        for algo_version, session in self.sessions.items():
            performance = self.get_session_performance(algo_version)
            comparison["sessions"][algo_version] = performance

            if performance["total_pnl"] > best_pnl:
                best_pnl = performance["total_pnl"]
                best_algo = algo_version

        comparison["winner"] = best_algo
        comparison["summary"] = {
            "best_pnl": best_pnl,
            "algorithms_tested": list(self.sessions.keys()),
            "total_sessions": len(self.sessions)
        }

        return comparison

    def _log_execution(self, event_data: Dict[str, Any]):
        """Log execution events"""
        event_data["timestamp"] = get_eastern_time().isoformat()
        self.execution_log.append(event_data)

        # Save to file periodically
        if len(self.execution_log) % 10 == 0:
            self._save_execution_log()

    def _save_execution_log(self):
        """Save execution log to file"""
        log_file = os.path.join(
            self.output_dir,
            f"execution_log_{get_eastern_time().strftime('%Y%m%d')}.json"
        )

        with open(log_file, 'w') as f:
            json.dump(self.execution_log, f, indent=2, default=str)

    def stop_all_sessions(self) -> Dict[str, Any]:
        """Stop all trading sessions and save final results"""
        final_results = {
            "stop_time": get_eastern_time().isoformat(),
            "sessions": {}
        }

        for algo_version in list(self.sessions.keys()):
            performance = self.get_session_performance(algo_version)
            final_results["sessions"][algo_version] = performance

        # Save final results
        results_file = os.path.join(
            self.output_dir,
            f"paper_trading_results_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(results_file, 'w') as f:
            json.dump(final_results, f, indent=2, default=str)

        # Save execution log
        self._save_execution_log()

        print(f"💾 Paper trading results saved to: {results_file}")

        return final_results


# Module-level convenience functions
def create_paper_trader() -> PaperTradingExecutor:
    """Create paper trading executor instance"""
    return PaperTradingExecutor()


def run_paper_trading_comparison(duration_hours: float = 24.0) -> Dict[str, Any]:
    """
    Run paper trading comparison between v1.0 and v3.0

    Args:
        duration_hours: Duration of paper trading test

    Returns:
        Comparison results
    """
    from ab_testing_coordinator import create_ab_coordinator
    from config_manager import get_config_manager
    import time

    # Create paper trader
    trader = create_paper_trader()

    # Start sessions for both algorithms
    v1_session = trader.start_session("v1.0")
    v3_session = trader.start_session("v3.0")

    # Create A/B testing coordinator
    config_manager = get_config_manager()
    ab_coordinator = create_ab_coordinator(config_manager)

    # Start A/B test with paper trading
    ab_session = ab_coordinator.start_ab_test(
        "ifd_v1_production",
        "ifd_v3_production",
        duration_hours=duration_hours
    )

    print(f"📈 Paper trading comparison started for {duration_hours} hours")

    # In production, this would run for the full duration
    # For testing, we'll simulate with a shorter duration
    test_duration = min(duration_hours * 3600, 300)  # Max 5 minutes for testing

    start_time = get_eastern_time()
    while (get_eastern_time() - start_time).total_seconds() < test_duration:
        # Get signals from A/B test
        status = ab_coordinator.get_test_status()

        # In production, process real signals here
        # For now, we'll simulate with the comparison data

        time.sleep(10)  # Check every 10 seconds

    # Stop A/B test
    ab_results = ab_coordinator.stop_ab_test()

    # Stop paper trading and get results
    paper_results = trader.stop_all_sessions()

    # Combine results
    combined_results = {
        "paper_trading": paper_results,
        "ab_testing": ab_results,
        "duration_hours": duration_hours,
        "summary": {
            "paper_trading_winner": paper_results.get("winner"),
            "ab_testing_recommendation": ab_results.recommended_algorithm,
            "agreement": paper_results.get("winner") == ab_results.recommended_algorithm
        }
    }

    return combined_results


if __name__ == "__main__":
    # Example usage
    trader = create_paper_trader()

    # Start sessions
    trader.start_session("v1.0")
    trader.start_session("v3.0")

    # Simulate some orders
    v1_signal = {
        "symbol": "NQM25",
        "strike": 21350,
        "option_type": "CALL",
        "direction": "LONG",
        "confidence": 0.75,
        "entry_price": 125.50,
        "signal_id": "sig_001"
    }

    v3_signal = {
        "symbol": "NQM25",
        "strike": 21375,
        "option_type": "CALL",
        "direction": "LONG",
        "confidence": 0.82,
        "entry_price": 118.25,
        "signal_id": "sig_002"
    }

    # Submit orders
    order1 = trader.submit_order("v1.0", v1_signal)
    order2 = trader.submit_order("v3.0", v3_signal)

    print(f"Order 1: {order1}")
    print(f"Order 2: {order2}")

    # Update prices
    trader.update_market_prices({
        "NQM25_21350_CALL": 128.00,
        "NQM25_21375_CALL": 122.50
    })

    # Get performance
    v1_perf = trader.get_session_performance("v1.0")
    v3_perf = trader.get_session_performance("v3.0")

    print(f"\nv1.0 Performance: {v1_perf}")
    print(f"v3.0 Performance: {v3_perf}")

    # Compare
    comparison = trader.compare_sessions()
    print(f"\nComparison: {comparison}")
