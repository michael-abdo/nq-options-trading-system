# DEAD Simple Strategy - Pseudocode

## Core Algorithm

```pseudocode
FUNCTION detect_institutional_flow(options_data, current_price):
    institutional_signals = []
    
    FOR each strike IN options_data:
        // Step 1: Calculate volume metrics
        vol_oi_ratio = strike.volume / strike.open_interest
        
        // Step 2: Apply filters
        IF vol_oi_ratio > 10 AND strike.volume > 500:
            
            // Step 3: Calculate dollar size
            dollar_size = strike.volume * strike.price * 20
            
            IF dollar_size > 100000:  // $100K minimum
                
                // Step 4: Determine direction
                direction = "LONG" IF strike.type == "CALL" ELSE "SHORT"
                target_price = strike.strike_price
                
                // Step 5: Create signal
                signal = {
                    "strike": strike.strike_price,
                    "type": strike.type,
                    "vol_oi_ratio": vol_oi_ratio,
                    "volume": strike.volume,
                    "dollar_size": dollar_size,
                    "direction": direction,
                    "entry_price": current_price,
                    "target_price": target_price,
                    "confidence": calculate_confidence(vol_oi_ratio)
                }
                
                institutional_signals.append(signal)
    
    // Sort by confidence/size
    RETURN sort_by_confidence(institutional_signals)


FUNCTION calculate_confidence(vol_oi_ratio):
    IF vol_oi_ratio > 50:
        RETURN "EXTREME"
    ELIF vol_oi_ratio > 30:
        RETURN "VERY_HIGH"
    ELIF vol_oi_ratio > 20:
        RETURN "HIGH"
    ELIF vol_oi_ratio > 10:
        RETURN "MODERATE"
    ELSE:
        RETURN "LOW"


FUNCTION execute_trade(signal, risk_parameters):
    // Step 1: Validate signal freshness
    IF signal.age > 5_MINUTES:
        RETURN "SIGNAL_TOO_OLD"
    
    // Step 2: Check position sizing
    position_size = calculate_position_size(
        signal.dollar_size,
        signal.confidence,
        risk_parameters.max_risk
    )
    
    // Step 3: Place order
    IF signal.direction == "LONG":
        order = create_buy_order(
            quantity: position_size,
            entry: signal.entry_price,
            target: signal.target_price,
            stop: calculate_stop_loss(signal)
        )
    ELSE:  // SHORT
        order = create_sell_order(
            quantity: position_size,
            entry: signal.entry_price,
            target: signal.target_price,
            stop: calculate_stop_loss(signal)
        )
    
    // Step 4: Monitor until target
    WHILE position_open AND NOT at_target:
        current_price = get_current_price()
        
        IF abs(current_price - signal.target_price) < TICK_SIZE:
            close_position()
            RETURN "TARGET_REACHED"
        
        IF stop_hit(current_price):
            close_position()
            RETURN "STOPPED_OUT"
        
        sleep(1_SECOND)


FUNCTION main_trading_loop():
    WHILE market_open:
        // Step 1: Get fresh options data
        options_data = fetch_options_data()
        current_price = get_current_price()
        
        // Step 2: Detect institutional flow
        signals = detect_institutional_flow(options_data, current_price)
        
        // Step 3: Filter for best opportunities
        best_signals = filter_top_signals(signals, max_concurrent=3)
        
        // Step 4: Execute trades
        FOR signal IN best_signals:
            IF not already_in_position(signal.strike):
                execute_trade(signal, risk_parameters)
        
        // Step 5: Wait before next scan
        sleep(30_SECONDS)
```

## Data Structure

```pseudocode
STRUCTURE OptionStrike:
    strike_price: DECIMAL
    type: STRING ("CALL" or "PUT")
    volume: INTEGER
    open_interest: INTEGER
    price: DECIMAL
    bid: DECIMAL
    ask: DECIMAL
    timestamp: DATETIME

STRUCTURE TradingSignal:
    strike: DECIMAL
    type: STRING
    vol_oi_ratio: DECIMAL
    volume: INTEGER
    dollar_size: DECIMAL
    direction: STRING ("LONG" or "SHORT")
    entry_price: DECIMAL
    target_price: DECIMAL
    confidence: STRING
    timestamp: DATETIME

STRUCTURE RiskParameters:
    max_risk: DECIMAL
    max_positions: INTEGER
    stop_loss_percent: DECIMAL
    position_size_percent: DECIMAL
```

## Key Functions

```pseudocode
FUNCTION filter_top_signals(signals, max_concurrent):
    // Prioritize by:
    // 1. Confidence level (EXTREME > VERY_HIGH > HIGH)
    // 2. Dollar size (bigger = more conviction)
    // 3. Distance to target (closer = faster profit)
    
    sorted_signals = signals.sort_by(
        confidence DESC,
        dollar_size DESC,
        distance_to_target ASC
    )
    
    RETURN sorted_signals[0:max_concurrent]


FUNCTION calculate_position_size(dollar_size, confidence, max_risk):
    // Scale position based on institutional conviction
    base_size = max_risk * 0.1  // 10% base allocation
    
    multiplier = CASE confidence:
        "EXTREME": 3.0
        "VERY_HIGH": 2.0
        "HIGH": 1.5
        "MODERATE": 1.0
        DEFAULT: 0.5
    
    position_size = base_size * multiplier
    
    // Cap at institutional size / 100 (follow don't lead)
    max_follow_size = dollar_size / 100
    
    RETURN MIN(position_size, max_follow_size)


FUNCTION calculate_stop_loss(signal):
    // Stop loss based on strike distance
    distance = abs(signal.entry_price - signal.target_price)
    
    IF signal.direction == "LONG":
        stop = signal.entry_price - (distance * 0.5)
    ELSE:  // SHORT
        stop = signal.entry_price + (distance * 0.5)
    
    RETURN stop
```

## Integration Points

```pseudocode
FUNCTION integrate_with_pipeline():
    // 1. Data Source Integration
    data_source = BarChartAPI()  // or TradovateAPI()
    
    // 2. Signal Generation
    signal_generator = DeadSimpleStrategy(
        min_vol_oi_ratio: 10,
        min_volume: 500,
        min_dollar_size: 100000
    )
    
    // 3. Risk Management
    risk_manager = RiskManager(
        max_risk_per_trade: 0.02,  // 2% per trade
        max_daily_loss: 0.06,      // 6% daily stop
        max_concurrent: 3          // 3 positions max
    )
    
    // 4. Execution Engine
    executor = TradovateExecutor(
        account: "DEMO3655059",
        mode: "LIVE"  // or "PAPER"
    )
    
    // 5. Monitoring
    monitor = PositionMonitor(
        check_interval: 1_SECOND,
        alert_on_target: TRUE,
        auto_close_at_target: TRUE
    )
    
    RETURN Pipeline(
        data_source,
        signal_generator,
        risk_manager,
        executor,
        monitor
    )
```