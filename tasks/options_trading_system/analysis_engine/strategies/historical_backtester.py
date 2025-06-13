#!/usr/bin/env python3
"""
Historical Backtesting Framework for IFD Algorithm Validation

This module provides comprehensive historical backtesting capabilities
to validate algorithm performance across different market conditions
and time periods.

Features:
- Multi-timeframe backtesting
- Market regime analysis
- Walk-forward optimization
- Monte Carlo simulation
- Performance attribution
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from utils.timezone_utils import get_eastern_time, get_utc_time
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict, field
from enum import Enum
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')


class MarketRegime(Enum):
    """Market regime classification"""
    BULL_QUIET = "BULL_QUIET"
    BULL_VOLATILE = "BULL_VOLATILE"
    BEAR_QUIET = "BEAR_QUIET"
    BEAR_VOLATILE = "BEAR_VOLATILE"
    SIDEWAYS = "SIDEWAYS"
    CRASH = "CRASH"
    RECOVERY = "RECOVERY"


@dataclass
class BacktestConfig:
    """Backtest configuration parameters"""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0

    # Position sizing
    position_sizing: str = "fixed"  # fixed, kelly, volatility_adjusted
    max_positions: int = 10
    max_position_size: float = 0.1  # 10% of capital

    # Risk management
    stop_loss: float = 0.02  # 2%
    take_profit: float = 0.05  # 5%
    max_drawdown_limit: float = 0.15  # 15%

    # Transaction costs
    commission_per_contract: float = 1.0
    slippage_ticks: int = 1
    tick_value: float = 0.25

    # Data parameters
    lookback_days: int = 20
    resample_frequency: str = "5T"  # 5 minutes

    # Optimization
    walk_forward_windows: int = 12
    optimization_metric: str = "sharpe_ratio"


@dataclass
class BacktestTrade:
    """Individual trade record"""
    trade_id: str
    algorithm_version: str
    entry_time: datetime
    exit_time: Optional[datetime]

    # Trade details
    symbol: str
    strike: float
    option_type: str
    side: str  # LONG or SHORT
    quantity: int

    # Prices
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss_price: float = 0.0
    take_profit_price: float = 0.0

    # P&L
    gross_pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0
    net_pnl: float = 0.0

    # Trade metadata
    signal_confidence: float = 0.0
    market_regime: Optional[MarketRegime] = None
    exit_reason: str = ""  # stop_loss, take_profit, signal_exit, eod


@dataclass
class BacktestResults:
    """Comprehensive backtest results"""
    backtest_id: str
    algorithm_version: str
    config: BacktestConfig

    # Performance metrics
    total_return: float = 0.0
    annualized_return: float = 0.0
    volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0

    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    var_95: float = 0.0  # Value at Risk
    cvar_95: float = 0.0  # Conditional VaR

    # Trading statistics
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0

    # Time-based metrics
    trades_per_day: float = 0.0
    avg_holding_period: float = 0.0
    longest_winning_streak: int = 0
    longest_losing_streak: int = 0

    # Market regime performance
    regime_performance: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Detailed records
    trades: List[BacktestTrade] = field(default_factory=list)
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)


class HistoricalDataLoader:
    """Load and prepare historical market data"""

    def __init__(self, data_dir: str = "data/historical"):
        self.data_dir = data_dir
        self.cache = {}

    def load_options_data(self, symbol: str, start_date: datetime,
                         end_date: datetime) -> pd.DataFrame:
        """
        Load historical options data

        Returns DataFrame with columns:
        - timestamp, symbol, strike, option_type, bid, ask, last, volume, open_interest
        """
        # In production, this would load from database or files
        # For now, generate synthetic data for testing

        dates = pd.date_range(start_date, end_date, freq='5T')
        dates = dates[dates.dayofweek < 5]  # Weekdays only
        dates = dates[(dates.hour >= 9) & (dates.hour < 16)]  # Market hours

        # Generate strikes around 21350 (NQ example)
        strikes = np.arange(21000, 21700, 25)

        data_rows = []
        for date in dates:
            base_price = 21350 + np.sin(date.hour) * 50  # Synthetic intraday movement

            for strike in strikes:
                for opt_type in ['CALL', 'PUT']:
                    # Synthetic option pricing
                    intrinsic = max(0, base_price - strike) if opt_type == 'CALL' else max(0, strike - base_price)
                    time_value = abs(base_price - strike) * 0.01 + np.random.uniform(1, 5)

                    bid = intrinsic + time_value - 0.5
                    ask = intrinsic + time_value + 0.5
                    last = (bid + ask) / 2

                    volume = np.random.poisson(100) if abs(base_price - strike) < 100 else np.random.poisson(20)
                    open_interest = np.random.randint(100, 5000)

                    data_rows.append({
                        'timestamp': date,
                        'symbol': symbol,
                        'strike': strike,
                        'option_type': opt_type,
                        'bid': bid,
                        'ask': ask,
                        'last': last,
                        'volume': volume,
                        'open_interest': open_interest,
                        'underlying_price': base_price
                    })

        return pd.DataFrame(data_rows)

    def load_market_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Load market indicators (VIX, volume, etc.)"""
        dates = pd.date_range(start_date, end_date, freq='D')

        # Synthetic market data
        data = []
        for date in dates:
            vix = 15 + np.random.normal(0, 3)  # VIX around 15
            volume = np.random.normal(1000000, 200000)

            data.append({
                'date': date,
                'vix': max(10, vix),
                'market_volume': max(500000, volume),
                'spy_return': np.random.normal(0.0005, 0.01)  # Daily return
            })

        return pd.DataFrame(data)


class MarketRegimeDetector:
    """Detect and classify market regimes"""

    @staticmethod
    def detect_regime(market_data: pd.DataFrame, lookback: int = 20) -> MarketRegime:
        """Detect current market regime based on indicators"""
        if len(market_data) < lookback:
            return MarketRegime.SIDEWAYS

        recent_data = market_data.tail(lookback)

        # Calculate metrics
        returns = recent_data['spy_return'].values
        volatility = np.std(returns) * np.sqrt(252)  # Annualized
        trend = np.mean(returns)
        vix_avg = recent_data['vix'].mean()

        # Classify regime
        if volatility > 0.25 or vix_avg > 25:
            # High volatility
            if trend < -0.001:
                if trend < -0.005:
                    return MarketRegime.CRASH
                return MarketRegime.BEAR_VOLATILE
            elif trend > 0.001:
                return MarketRegime.BULL_VOLATILE
            else:
                return MarketRegime.SIDEWAYS
        else:
            # Low volatility
            if trend < -0.0005:
                return MarketRegime.BEAR_QUIET
            elif trend > 0.0005:
                return MarketRegime.BULL_QUIET
            else:
                return MarketRegime.SIDEWAYS


class HistoricalBacktester:
    """
    Comprehensive historical backtesting engine

    Features:
    - Multi-algorithm comparison
    - Market regime analysis
    - Walk-forward optimization
    - Monte Carlo simulation
    """

    def __init__(self, output_dir: str = "outputs/backtests"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        self.data_loader = HistoricalDataLoader()
        self.regime_detector = MarketRegimeDetector()

        # Results storage
        self.backtest_results: Dict[str, BacktestResults] = {}

    def run_backtest(self, algorithm_version: str, config: BacktestConfig,
                    progress_callback: Optional[callable] = None) -> BacktestResults:
        """
        Run historical backtest for an algorithm

        Args:
            algorithm_version: Algorithm to test (v1.0, v3.0)
            config: Backtest configuration
            progress_callback: Optional callback for progress updates

        Returns:
            BacktestResults object
        """
        backtest_id = f"backtest_{algorithm_version}_{get_eastern_time().strftime('%Y%m%d_%H%M%S')}"

        print(f"🚀 Starting backtest: {backtest_id}")
        print(f"   Algorithm: {algorithm_version}")
        print(f"   Period: {config.start_date.date()} to {config.end_date.date()}")
        print(f"   Capital: ${config.initial_capital:,.0f}")

        # Initialize results
        results = BacktestResults(
            backtest_id=backtest_id,
            algorithm_version=algorithm_version,
            config=config
        )

        # Load historical data
        options_data = self.data_loader.load_options_data(
            "NQM25", config.start_date, config.end_date
        )
        market_data = self.data_loader.load_market_data(
            config.start_date, config.end_date
        )

        # Initialize portfolio
        portfolio = {
            'capital': config.initial_capital,
            'positions': {},
            'equity_curve': [],
            'peak_equity': config.initial_capital
        }

        # Group data by day for processing
        daily_groups = options_data.groupby(options_data['timestamp'].dt.date)
        total_days = len(daily_groups)

        for day_num, (date, day_data) in enumerate(daily_groups):
            if progress_callback:
                progress_callback(day_num / total_days)

            # Detect market regime
            current_regime = self.regime_detector.detect_regime(
                market_data[market_data['date'] <= pd.Timestamp(date)]
            )

            # Process intraday data
            for timestamp, snapshot in day_data.groupby('timestamp'):
                # Generate signals using algorithm
                signals = self._generate_signals(
                    algorithm_version, snapshot, portfolio, current_regime
                )

                # Execute trades
                for signal in signals:
                    trade = self._execute_trade(
                        signal, portfolio, config, timestamp, current_regime
                    )
                    if trade:
                        results.trades.append(trade)

                # Update positions
                self._update_positions(portfolio, snapshot, timestamp, config)

                # Record equity
                current_equity = self._calculate_equity(portfolio, snapshot)
                portfolio['equity_curve'].append({
                    'timestamp': timestamp,
                    'equity': current_equity,
                    'cash': portfolio['capital'],
                    'positions_value': current_equity - portfolio['capital']
                })

                # Update peak for drawdown calculation
                if current_equity > portfolio['peak_equity']:
                    portfolio['peak_equity'] = current_equity

            # End of day processing
            self._process_end_of_day(portfolio, date, config)

        # Calculate final metrics
        self._calculate_metrics(results, portfolio)

        # Save results
        self._save_results(results)

        print(f"✅ Backtest completed: {backtest_id}")
        self._print_summary(results)

        return results

    def _generate_signals(self, algorithm_version: str, market_snapshot: pd.DataFrame,
                         portfolio: Dict[str, Any], regime: MarketRegime) -> List[Dict[str, Any]]:
        """Generate trading signals based on algorithm logic"""
        signals = []

        # Get high volume/OI options
        active_options = market_snapshot[
            (market_snapshot['volume'] > 100) &
            (market_snapshot['open_interest'] > 500)
        ].copy()

        if algorithm_version == "v1.0":
            # Dead Simple v1.0 logic
            active_options['vol_oi_ratio'] = active_options['volume'] / active_options['open_interest']

            # Find extreme vol/OI ratios
            extreme_signals = active_options[active_options['vol_oi_ratio'] > 10]

            for _, opt in extreme_signals.iterrows():
                confidence = min(opt['vol_oi_ratio'] / 50, 1.0)  # Scale confidence

                signals.append({
                    'symbol': opt['symbol'],
                    'strike': opt['strike'],
                    'option_type': opt['option_type'],
                    'direction': 'LONG',  # v1.0 always goes long on high vol/OI
                    'confidence': confidence,
                    'entry_price': opt['ask'],  # Use ask for market order
                    'signal_strength': opt['vol_oi_ratio']
                })

        elif algorithm_version == "v3.0":
            # Enhanced IFD v3.0 logic with market regime awareness
            active_options['vol_oi_ratio'] = active_options['volume'] / active_options['open_interest']

            # Adjust thresholds based on market regime
            if regime in [MarketRegime.BEAR_VOLATILE, MarketRegime.CRASH]:
                vol_threshold = 5  # Lower threshold in volatile markets
            else:
                vol_threshold = 10

            # Find institutional flow signals
            institutional_signals = active_options[active_options['vol_oi_ratio'] > vol_threshold]

            for _, opt in institutional_signals.iterrows():
                # v3.0 considers direction based on option type and market regime
                if regime in [MarketRegime.BEAR_QUIET, MarketRegime.BEAR_VOLATILE]:
                    # In bear markets, puts are more likely to be directional
                    direction = 'SHORT' if opt['option_type'] == 'PUT' else 'LONG'
                else:
                    direction = 'LONG' if opt['option_type'] == 'CALL' else 'SHORT'

                # Enhanced confidence calculation
                base_confidence = min(opt['vol_oi_ratio'] / 50, 0.8)
                regime_adjustment = 0.1 if regime != MarketRegime.SIDEWAYS else 0
                confidence = min(base_confidence + regime_adjustment, 0.95)

                signals.append({
                    'symbol': opt['symbol'],
                    'strike': opt['strike'],
                    'option_type': opt['option_type'],
                    'direction': direction,
                    'confidence': confidence,
                    'entry_price': opt['ask'] if direction == 'LONG' else opt['bid'],
                    'signal_strength': opt['vol_oi_ratio'] * (1.2 if regime != MarketRegime.SIDEWAYS else 1.0)
                })

        # Filter for position limits
        max_new_positions = portfolio.get('max_positions', 10) - len(portfolio['positions'])
        return signals[:max_new_positions]

    def _execute_trade(self, signal: Dict[str, Any], portfolio: Dict[str, Any],
                      config: BacktestConfig, timestamp: datetime,
                      regime: MarketRegime) -> Optional[BacktestTrade]:
        """Execute a trade based on signal"""
        # Calculate position size
        position_size = self._calculate_position_size(
            signal, portfolio, config
        )

        if position_size == 0:
            return None

        # Calculate trade costs
        entry_price = signal['entry_price']
        commission = config.commission_per_contract * position_size
        slippage = config.slippage_ticks * config.tick_value * position_size

        total_cost = (entry_price * position_size * 100) + commission + slippage

        # Check if we have enough capital
        if total_cost > portfolio['capital']:
            return None

        # Create trade record
        trade = BacktestTrade(
            trade_id=f"trade_{timestamp.strftime('%Y%m%d_%H%M%S')}_{signal['strike']}",
            algorithm_version=signal.get('algorithm_version', 'unknown'),
            entry_time=timestamp,
            exit_time=None,
            symbol=signal['symbol'],
            strike=signal['strike'],
            option_type=signal['option_type'],
            side=signal['direction'],
            quantity=position_size,
            entry_price=entry_price,
            stop_loss_price=entry_price * (1 - config.stop_loss),
            take_profit_price=entry_price * (1 + config.take_profit),
            commission=commission,
            slippage=slippage,
            signal_confidence=signal['confidence'],
            market_regime=regime
        )

        # Update portfolio
        portfolio['capital'] -= total_cost
        position_key = f"{signal['symbol']}_{signal['strike']}_{signal['option_type']}"
        portfolio['positions'][position_key] = trade

        return trade

    def _calculate_position_size(self, signal: Dict[str, Any],
                                portfolio: Dict[str, Any],
                                config: BacktestConfig) -> int:
        """Calculate position size based on strategy"""
        available_capital = portfolio['capital']

        if config.position_sizing == "fixed":
            # Fixed percentage of capital
            max_position_value = available_capital * config.max_position_size
            contracts = int(max_position_value / (signal['entry_price'] * 100))

        elif config.position_sizing == "kelly":
            # Kelly Criterion sizing
            win_prob = signal['confidence']
            win_loss_ratio = config.take_profit / config.stop_loss

            kelly_fraction = (win_prob * win_loss_ratio - (1 - win_prob)) / win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25%

            position_value = available_capital * kelly_fraction
            contracts = int(position_value / (signal['entry_price'] * 100))

        elif config.position_sizing == "volatility_adjusted":
            # Size inversely proportional to volatility
            # In production, would use actual volatility
            base_size = available_capital * config.max_position_size
            vol_adjustment = 1.0  # Placeholder

            position_value = base_size * vol_adjustment
            contracts = int(position_value / (signal['entry_price'] * 100))

        else:
            contracts = 1  # Default

        return max(0, min(contracts, 10))  # Cap at 10 contracts

    def _update_positions(self, portfolio: Dict[str, Any], market_snapshot: pd.DataFrame,
                         timestamp: datetime, config: BacktestConfig):
        """Update existing positions with current prices"""
        positions_to_close = []

        for position_key, trade in portfolio['positions'].items():
            # Find current price
            current_data = market_snapshot[
                (market_snapshot['symbol'] == trade.symbol) &
                (market_snapshot['strike'] == trade.strike) &
                (market_snapshot['option_type'] == trade.option_type)
            ]

            if current_data.empty:
                continue

            current_price = current_data.iloc[0]['last']

            # Check exit conditions
            exit_reason = None

            if trade.side == "LONG":
                if current_price <= trade.stop_loss_price:
                    exit_reason = "stop_loss"
                elif current_price >= trade.take_profit_price:
                    exit_reason = "take_profit"
            else:  # SHORT
                if current_price >= trade.stop_loss_price:
                    exit_reason = "stop_loss"
                elif current_price <= trade.take_profit_price:
                    exit_reason = "take_profit"

            if exit_reason:
                # Close position
                trade.exit_time = timestamp
                trade.exit_price = current_price
                trade.exit_reason = exit_reason

                # Calculate P&L
                if trade.side == "LONG":
                    gross_pnl = (current_price - trade.entry_price) * trade.quantity * 100
                else:
                    gross_pnl = (trade.entry_price - current_price) * trade.quantity * 100

                trade.gross_pnl = gross_pnl
                trade.net_pnl = gross_pnl - trade.commission - trade.slippage

                # Update portfolio
                portfolio['capital'] += trade.net_pnl + (trade.entry_price * trade.quantity * 100)
                positions_to_close.append(position_key)

        # Remove closed positions
        for position_key in positions_to_close:
            del portfolio['positions'][position_key]

    def _calculate_equity(self, portfolio: Dict[str, Any], market_snapshot: pd.DataFrame) -> float:
        """Calculate total portfolio equity"""
        equity = portfolio['capital']

        for trade in portfolio['positions'].values():
            # Find current price
            current_data = market_snapshot[
                (market_snapshot['symbol'] == trade.symbol) &
                (market_snapshot['strike'] == trade.strike) &
                (market_snapshot['option_type'] == trade.option_type)
            ]

            if not current_data.empty:
                current_price = current_data.iloc[0]['last']

                if trade.side == "LONG":
                    position_value = current_price * trade.quantity * 100
                else:
                    # For short positions, calculate P&L
                    position_value = (2 * trade.entry_price - current_price) * trade.quantity * 100

                equity += position_value

        return equity

    def _process_end_of_day(self, portfolio: Dict[str, Any], date: Any, config: BacktestConfig):
        """End of day processing - close all positions if configured"""
        # For intraday strategies, could close all positions
        # For this backtest, we'll keep positions overnight
        pass

    def _calculate_metrics(self, results: BacktestResults, portfolio: Dict[str, Any]):
        """Calculate comprehensive performance metrics"""
        equity_curve = pd.DataFrame(portfolio['equity_curve'])

        if equity_curve.empty:
            return

        # Calculate returns
        equity_curve['returns'] = equity_curve['equity'].pct_change()

        # Basic metrics
        total_days = (results.config.end_date - results.config.start_date).days
        trading_days = len(equity_curve['timestamp'].dt.date.unique())

        results.total_return = (equity_curve['equity'].iloc[-1] / results.config.initial_capital) - 1
        results.annualized_return = (1 + results.total_return) ** (252 / trading_days) - 1

        # Risk metrics
        daily_returns = equity_curve.groupby(equity_curve['timestamp'].dt.date)['returns'].last()
        results.volatility = daily_returns.std() * np.sqrt(252)

        # Sharpe ratio (assuming 0% risk-free rate)
        if results.volatility > 0:
            results.sharpe_ratio = results.annualized_return / results.volatility

        # Sortino ratio (downside deviation)
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 0:
            downside_vol = downside_returns.std() * np.sqrt(252)
            if downside_vol > 0:
                results.sortino_ratio = results.annualized_return / downside_vol

        # Maximum drawdown
        equity_curve['peak'] = equity_curve['equity'].cummax()
        equity_curve['drawdown'] = (equity_curve['equity'] - equity_curve['peak']) / equity_curve['peak']
        results.max_drawdown = equity_curve['drawdown'].min()

        # Calmar ratio
        if results.max_drawdown < 0:
            results.calmar_ratio = results.annualized_return / abs(results.max_drawdown)

        # Trade statistics
        completed_trades = [t for t in results.trades if t.exit_time is not None]
        results.total_trades = len(completed_trades)

        if results.total_trades > 0:
            winning_trades = [t for t in completed_trades if t.net_pnl > 0]
            losing_trades = [t for t in completed_trades if t.net_pnl < 0]

            results.winning_trades = len(winning_trades)
            results.losing_trades = len(losing_trades)
            results.win_rate = results.winning_trades / results.total_trades

            if winning_trades:
                results.avg_win = np.mean([t.net_pnl for t in winning_trades])

            if losing_trades:
                results.avg_loss = np.mean([t.net_pnl for t in losing_trades])

                total_wins = sum(t.net_pnl for t in winning_trades)
                total_losses = abs(sum(t.net_pnl for t in losing_trades))

                if total_losses > 0:
                    results.profit_factor = total_wins / total_losses

            # Average holding period
            holding_periods = [(t.exit_time - t.entry_time).total_seconds() / 3600
                             for t in completed_trades if t.exit_time]
            if holding_periods:
                results.avg_holding_period = np.mean(holding_periods)

            # Trades per day
            results.trades_per_day = results.total_trades / trading_days

        # Value at Risk (95%)
        if len(daily_returns) > 20:
            results.var_95 = np.percentile(daily_returns, 5)
            results.cvar_95 = daily_returns[daily_returns <= results.var_95].mean()

        # Monthly returns
        monthly_returns = equity_curve.groupby(
            pd.Grouper(key='timestamp', freq='M')
        )['returns'].apply(lambda x: (1 + x).prod() - 1)

        results.monthly_returns = {
            str(date): ret for date, ret in monthly_returns.items()
        }

        # Market regime performance
        for trade in completed_trades:
            if trade.market_regime:
                regime_name = trade.market_regime.value

                if regime_name not in results.regime_performance:
                    results.regime_performance[regime_name] = {
                        'trades': 0,
                        'win_rate': 0,
                        'avg_pnl': 0,
                        'total_pnl': 0
                    }

                regime_stats = results.regime_performance[regime_name]
                regime_stats['trades'] += 1
                regime_stats['total_pnl'] += trade.net_pnl

        # Calculate regime win rates
        for regime_name, stats in results.regime_performance.items():
            regime_trades = [t for t in completed_trades
                           if t.market_regime and t.market_regime.value == regime_name]

            if regime_trades:
                regime_wins = [t for t in regime_trades if t.net_pnl > 0]
                stats['win_rate'] = len(regime_wins) / len(regime_trades)
                stats['avg_pnl'] = stats['total_pnl'] / len(regime_trades)

        # Store equity curve
        results.equity_curve = equity_curve.to_dict('records')

    def run_walk_forward_optimization(self, algorithm_version: str,
                                     config: BacktestConfig,
                                     parameter_grid: Dict[str, List[Any]]) -> Dict[str, Any]:
        """
        Run walk-forward optimization

        Args:
            algorithm_version: Algorithm to optimize
            config: Base configuration
            parameter_grid: Parameters to optimize

        Returns:
            Optimization results
        """
        print(f"🔧 Starting walk-forward optimization for {algorithm_version}")

        results = {
            'algorithm': algorithm_version,
            'windows': [],
            'best_parameters': None,
            'out_of_sample_performance': []
        }

        # Calculate window size
        total_days = (config.end_date - config.start_date).days
        window_size = total_days // config.walk_forward_windows

        for window in range(config.walk_forward_windows - 1):
            # Define in-sample and out-of-sample periods
            in_sample_start = config.start_date + timedelta(days=window * window_size)
            in_sample_end = in_sample_start + timedelta(days=window_size * 2 // 3)
            out_sample_start = in_sample_end
            out_sample_end = out_sample_start + timedelta(days=window_size // 3)

            print(f"\nWindow {window + 1}:")
            print(f"  In-sample: {in_sample_start.date()} to {in_sample_end.date()}")
            print(f"  Out-sample: {out_sample_start.date()} to {out_sample_end.date()}")

            # Optimize on in-sample data
            best_params = self._optimize_parameters(
                algorithm_version,
                in_sample_start,
                in_sample_end,
                parameter_grid,
                config
            )

            # Test on out-of-sample data
            test_config = BacktestConfig(
                start_date=out_sample_start,
                end_date=out_sample_end,
                initial_capital=config.initial_capital,
                **best_params
            )

            test_results = self.run_backtest(algorithm_version, test_config)

            results['windows'].append({
                'window': window + 1,
                'best_parameters': best_params,
                'in_sample_period': f"{in_sample_start.date()} to {in_sample_end.date()}",
                'out_sample_period': f"{out_sample_start.date()} to {out_sample_end.date()}",
                'out_sample_sharpe': test_results.sharpe_ratio,
                'out_sample_return': test_results.total_return
            })

            results['out_of_sample_performance'].append(test_results.sharpe_ratio)

        # Average out-of-sample performance
        avg_oos_sharpe = np.mean(results['out_of_sample_performance'])

        print(f"\n✅ Walk-forward optimization complete")
        print(f"Average out-of-sample Sharpe: {avg_oos_sharpe:.2f}")

        return results

    def _optimize_parameters(self, algorithm_version: str, start_date: datetime,
                           end_date: datetime, parameter_grid: Dict[str, List[Any]],
                           base_config: BacktestConfig) -> Dict[str, Any]:
        """Optimize parameters on in-sample data"""
        best_sharpe = -float('inf')
        best_params = {}

        # Generate parameter combinations
        from itertools import product

        param_names = list(parameter_grid.keys())
        param_values = [parameter_grid[name] for name in param_names]

        for values in product(*param_values):
            params = dict(zip(param_names, values))

            # Create test configuration
            test_config = BacktestConfig(
                start_date=start_date,
                end_date=end_date,
                initial_capital=base_config.initial_capital,
                **params
            )

            # Run backtest
            results = self.run_backtest(algorithm_version, test_config)

            # Check if better
            if results.sharpe_ratio > best_sharpe:
                best_sharpe = results.sharpe_ratio
                best_params = params

        return best_params

    def run_monte_carlo_simulation(self, algorithm_version: str,
                                  config: BacktestConfig,
                                  num_simulations: int = 1000) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for risk analysis

        Args:
            algorithm_version: Algorithm to test
            config: Backtest configuration
            num_simulations: Number of simulations

        Returns:
            Simulation results
        """
        print(f"🎲 Running Monte Carlo simulation ({num_simulations} iterations)")

        # First, run base backtest to get trade distribution
        base_results = self.run_backtest(algorithm_version, config)

        if not base_results.trades:
            return {"error": "No trades in base backtest"}

        # Extract trade returns
        trade_returns = [t.net_pnl / config.initial_capital
                        for t in base_results.trades if t.net_pnl != 0]

        if not trade_returns:
            return {"error": "No completed trades"}

        # Run simulations
        simulation_results = []

        for sim in range(num_simulations):
            if sim % 100 == 0:
                print(f"  Simulation {sim}/{num_simulations}")

            # Bootstrap sample trades
            num_trades = len(trade_returns)
            sampled_returns = np.random.choice(trade_returns, size=num_trades, replace=True)

            # Calculate metrics
            total_return = np.sum(sampled_returns)
            max_drawdown = self._calculate_max_drawdown_from_returns(sampled_returns)

            simulation_results.append({
                'total_return': total_return,
                'max_drawdown': max_drawdown,
                'num_trades': num_trades
            })

        # Calculate statistics
        returns = [r['total_return'] for r in simulation_results]
        drawdowns = [r['max_drawdown'] for r in simulation_results]

        mc_results = {
            'num_simulations': num_simulations,
            'return_mean': np.mean(returns),
            'return_std': np.std(returns),
            'return_5th_percentile': np.percentile(returns, 5),
            'return_95th_percentile': np.percentile(returns, 95),
            'drawdown_mean': np.mean(drawdowns),
            'drawdown_95th_percentile': np.percentile(drawdowns, 95),
            'probability_of_loss': len([r for r in returns if r < 0]) / num_simulations,
            'probability_of_50pct_drawdown': len([d for d in drawdowns if d < -0.5]) / num_simulations
        }

        print(f"\n📊 Monte Carlo Results:")
        print(f"  Expected Return: {mc_results['return_mean']:.1%}")
        print(f"  Return Std Dev: {mc_results['return_std']:.1%}")
        print(f"  5% VaR: {mc_results['return_5th_percentile']:.1%}")
        print(f"  Probability of Loss: {mc_results['probability_of_loss']:.1%}")

        return mc_results

    def _calculate_max_drawdown_from_returns(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from a series of returns"""
        equity = [1.0]

        for ret in returns:
            equity.append(equity[-1] * (1 + ret))

        peak = equity[0]
        max_dd = 0

        for value in equity:
            if value > peak:
                peak = value

            dd = (value - peak) / peak
            if dd < max_dd:
                max_dd = dd

        return max_dd

    def compare_algorithms(self, algorithms: List[str], config: BacktestConfig) -> Dict[str, Any]:
        """
        Compare multiple algorithms on same historical data

        Args:
            algorithms: List of algorithm versions
            config: Backtest configuration

        Returns:
            Comparison results
        """
        print(f"🔍 Comparing algorithms: {algorithms}")

        comparison = {
            'period': f"{config.start_date.date()} to {config.end_date.date()}",
            'algorithms': {},
            'rankings': {},
            'summary': {}
        }

        # Run backtest for each algorithm
        for algo in algorithms:
            print(f"\nTesting {algo}...")
            results = self.run_backtest(algo, config)

            comparison['algorithms'][algo] = {
                'total_return': results.total_return,
                'sharpe_ratio': results.sharpe_ratio,
                'sortino_ratio': results.sortino_ratio,
                'max_drawdown': results.max_drawdown,
                'win_rate': results.win_rate,
                'profit_factor': results.profit_factor,
                'total_trades': results.total_trades,
                'calmar_ratio': results.calmar_ratio
            }

        # Rank algorithms by different metrics
        metrics = ['sharpe_ratio', 'total_return', 'win_rate', 'profit_factor']

        for metric in metrics:
            ranked = sorted(algorithms,
                          key=lambda x: comparison['algorithms'][x][metric],
                          reverse=True)
            comparison['rankings'][metric] = ranked

        # Overall ranking (equal weight to each metric)
        scores = {}
        for algo in algorithms:
            score = 0
            for metric in metrics:
                rank = comparison['rankings'][metric].index(algo)
                score += len(algorithms) - rank  # Higher score for better rank
            scores[algo] = score

        overall_ranking = sorted(algorithms, key=lambda x: scores[x], reverse=True)
        comparison['rankings']['overall'] = overall_ranking

        # Summary
        winner = overall_ranking[0]
        comparison['summary'] = {
            'recommended_algorithm': winner,
            'reasoning': f"{winner} ranked highest across multiple metrics"
        }

        return comparison

    def _save_results(self, results: BacktestResults):
        """Save backtest results to file"""
        filename = f"{results.backtest_id}_results.json"
        filepath = os.path.join(self.output_dir, filename)

        # Convert to dict for JSON serialization
        results_dict = asdict(results)

        # Convert datetime objects to strings
        def convert_dates(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        results_dict = json.loads(json.dumps(results_dict, default=convert_dates))

        with open(filepath, 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"💾 Results saved to: {filepath}")

    def _print_summary(self, results: BacktestResults):
        """Print backtest summary"""
        print("\n" + "=" * 60)
        print("BACKTEST SUMMARY")
        print("=" * 60)
        print(f"Algorithm: {results.algorithm_version}")
        print(f"Period: {results.config.start_date.date()} to {results.config.end_date.date()}")
        print(f"\nPERFORMANCE:")
        print(f"  Total Return: {results.total_return:.1%}")
        print(f"  Annualized Return: {results.annualized_return:.1%}")
        print(f"  Sharpe Ratio: {results.sharpe_ratio:.2f}")
        print(f"  Max Drawdown: {results.max_drawdown:.1%}")
        print(f"\nTRADING:")
        print(f"  Total Trades: {results.total_trades}")
        print(f"  Win Rate: {results.win_rate:.1%}")
        print(f"  Profit Factor: {results.profit_factor:.2f}")
        print(f"  Avg Win: ${results.avg_win:.2f}")
        print(f"  Avg Loss: ${results.avg_loss:.2f}")
        print("=" * 60)


# Module-level convenience functions
def create_backtester() -> HistoricalBacktester:
    """Create historical backtester instance"""
    return HistoricalBacktester()


def run_standard_backtest(algorithm_version: str = "v3.0",
                         days_back: int = 90) -> BacktestResults:
    """
    Run standard backtest

    Args:
        algorithm_version: Algorithm to test
        days_back: Number of days to backtest

    Returns:
        Backtest results
    """
    backtester = create_backtester()

    config = BacktestConfig(
        start_date=get_eastern_time() - timedelta(days=days_back),
        end_date=get_eastern_time(),
        initial_capital=100000.0,
        position_sizing="kelly",
        max_positions=10,
        stop_loss=0.02,
        take_profit=0.05
    )

    return backtester.run_backtest(algorithm_version, config)


if __name__ == "__main__":
    # Example usage
    backtester = create_backtester()

    # Define test configuration
    config = BacktestConfig(
        start_date=datetime(2024, 10, 1),
        end_date=datetime(2024, 12, 31),
        initial_capital=100000.0,
        position_sizing="kelly",
        max_positions=10,
        stop_loss=0.02,  # 2% stop loss
        take_profit=0.05  # 5% take profit
    )

    # Compare v1.0 and v3.0
    comparison = backtester.compare_algorithms(["v1.0", "v3.0"], config)

    print("\n🏆 ALGORITHM COMPARISON")
    print("=" * 60)
    for algo, metrics in comparison['algorithms'].items():
        print(f"\n{algo}:")
        for metric, value in metrics.items():
            if isinstance(value, float):
                if 'return' in metric or 'rate' in metric or 'drawdown' in metric:
                    print(f"  {metric}: {value:.1%}")
                else:
                    print(f"  {metric}: {value:.2f}")
            else:
                print(f"  {metric}: {value}")

    print(f"\n🥇 Winner: {comparison['summary']['recommended_algorithm']}")
    print(f"Reason: {comparison['summary']['reasoning']}")
