# Quote Pressure to PressureMetrics Adapter

## Overview

The `quote_pressure_adapter.py` provides a seamless bridge between quote-based pressure monitoring and IFD v3's trade-based analysis pipeline. This adapter solves the fundamental challenge of converting snapshot-based quote data into the cumulative volume metrics that IFD v3 expects.

## Key Challenge: Quotes vs Trades

### Quote Data (What We Have)
- **Snapshot-based**: Current bid/ask sizes at specific moments
- **Standing orders**: Represents liquidity available, not executed trades
- **Example**: `bid_size: 50, ask_size: 30` at time T

### Trade Volume (What IFD v3 Expects)
- **Cumulative**: Total executed volume over time windows
- **Executed trades**: Actual transactions that occurred
- **Example**: `bid_volume: 1500, ask_volume: 2300` over 5 minutes

## Solution: Intelligent Conversion

The adapter uses several strategies to convert quote pressure into simulated trade volume:

### 1. Quote Change Tracking
- Monitors changes in bid/ask sizes between snapshots
- Interprets size increases as new trading interest
- Converts size decreases as potential executed trades

### 2. Volume Simulation Algorithm
```python
# Increasing bid size → Buying pressure → Simulated ask volume
if bid_change > 0:
    simulated_ask_volume = abs(bid_change) * volume_multiplier

# Decreasing ask size → Asks being lifted → Simulated ask volume
if ask_change < 0:
    simulated_ask_volume = abs(ask_change) * volume_multiplier * 0.5
```

### 3. Time Window Aggregation
- Maintains 5-minute windows (configurable)
- Accumulates simulated volumes within each window
- Generates PressureMetrics at window completion

### 4. Confidence Calculation
Based on three factors:
- **Activity Level**: Number of quote updates
- **Size Significance**: Average quote sizes
- **Pressure Consistency**: Stability of pressure direction

## Usage

### Basic Integration

```python
from quote_pressure_adapter import QuotePressureAdapter, QuotePressureSnapshot

# Create adapter
adapter = QuotePressureAdapter(
    window_minutes=5,      # 5-minute aggregation windows
    volume_multiplier=10.0 # Convert quote changes to volume
)

# Process quote snapshot
snapshot = QuotePressureSnapshot(
    timestamp=datetime.now(timezone.utc),
    symbol="NQM5 C22000",
    strike=22000,
    option_type="C",
    bid_size=75,
    ask_size=25,
    bid_price=150.75,
    ask_price=151.25,
    pressure_ratio=3.0
)

# Add to adapter (returns PressureMetrics when window completes)
metrics = adapter.add_quote_snapshot(snapshot)
if metrics:
    # Feed to IFD v3
    signal = ifd.analyze_pressure(metrics)
```

### Integration with Live Monitor

```python
from ifd_integration import QuotePressureToIFDPipeline

# Create integration pipeline
pipeline = QuotePressureToIFDPipeline(
    window_minutes=5,
    volume_multiplier=10.0
)

# Process quote data from monitor
quote_data = {
    'symbol': 'NQM5 C22000',
    'strike': 22000,
    'bid_size': 85,
    'ask_size': 25,
    'bid_price': 152.50,
    'ask_price': 153.00,
    'pressure_ratio': 3.4,
    'last_update': datetime.now(timezone.utc)
}

signal = pipeline.process_quote_data(quote_data)
```

## Configuration Parameters

### `window_minutes` (default: 5)
- Time window for aggregating quote pressure
- Should match IFD v3's expected window size
- Smaller windows = more responsive, larger = more stable

### `volume_multiplier` (default: 10.0)
- Converts quote size changes to simulated volume
- Higher values = more sensitive to quote changes
- Tune based on typical quote sizes vs trade volumes

## Output Format

The adapter produces standard `PressureMetrics` objects:

```python
PressureMetrics(
    strike=22000,
    option_type='C',
    time_window=datetime(2025, 1, 18, 14, 30),  # Window start
    bid_volume=1500,        # Simulated from quote changes
    ask_volume=2500,        # Simulated from quote changes
    pressure_ratio=1.67,    # ask_volume / bid_volume
    total_trades=24,        # Estimated from quote updates
    avg_trade_size=166.67,  # total_volume / total_trades
    dominant_side='BUY',    # Based on volume imbalance
    confidence=0.82         # Composite confidence score
)
```

## Integration Points

### 1. With Quote Monitor (`nq_options_quote_pressure.py`)
- Monitor captures live quote data
- Adapter converts to PressureMetrics
- Maintains real-time processing

### 2. With IFD v3
- PressureMetrics fed directly to `InstitutionalFlowDetectorV3`
- No modifications needed to IFD v3
- Preserves all analysis capabilities

### 3. Historical Analysis
- Can process saved quote pressure data
- Useful for backtesting and validation
- Maintains temporal consistency

## Limitations & Considerations

1. **Approximation**: Simulated volumes are estimates, not actual trades
2. **Calibration**: Volume multiplier may need tuning per market conditions
3. **Quote Quality**: Depends on frequency and quality of quote updates
4. **Market Hours**: Most effective during active trading hours

## Testing

Run the adapter test:
```bash
python quote_pressure_adapter.py
```

Run the integration test:
```bash
python ifd_integration.py
```

## Future Enhancements

1. **Dynamic Multiplier**: Adjust volume multiplier based on market conditions
2. **Quote Depth**: Incorporate multiple price levels (bid_sz_01, etc.)
3. **Spread Analysis**: Use bid-ask spread as additional signal
4. **Machine Learning**: Train multiplier based on historical quote-to-trade ratios
