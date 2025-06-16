# MBO Streaming Data Flow Analysis

## Complete Data Flow Architecture

### **1. WebSocket Connection Layer**
```
Databento Live API → WebSocket Connection
├── Dataset: GLBX.MDP3 (CME Globex)
├── Schema: 'trades' (full MBO requires premium subscription)
├── Symbols: ['NQ.OPT'] with parent symbology
├── Authentication: API key from .env file
└── Market Hours: Automatic 9:30 AM - 4:00 PM ET control
```

### **2. Event Queue Buffer**
```
Raw Databento Events → Queue(maxsize=10000)
├── Event Structure: {ts_event, instrument_id, bid_px_00, ask_px_00, price, size, sequence}
├── Queue Management: Timeout-based with overflow protection
├── Usage Tracking: Real-time byte count and cost estimation
└── Budget Control: Automatic shutdown at 80% of daily limit
```

### **3. Event Processing Pipeline**
```
Raw Event → MBOEventProcessor → MBOEvent Object
├── Timestamp Conversion: Nanosecond to datetime with UTC timezone
├── Price Scaling: Databento format (divide by 1,000,000)
├── Trade Side Derivation:
│   ├── BUY: trade_price >= ask_price
│   ├── SELL: trade_price <= bid_price
│   └── UNKNOWN: trade between bid/ask
├── Instrument Metadata: Strike/option type lookup (currently stubbed)
└── Data Validation: Skip events with missing essential fields
```

### **4. Pressure Aggregation Engine**
```
MBOEvent → PressureAggregator → PressureMetrics (5-minute windows)
├── Window Management: 5-minute intervals aligned to market time
├── Volume Tracking:
│   ├── Bid Volume: Accumulation of SELL trades (hitting bid)
│   ├── Ask Volume: Accumulation of BUY trades (hitting ask)
│   └── Pressure Ratio: ask_volume / bid_volume
├── Confidence Scoring: Based on sample size and volume dominance
├── Window Completion: Automatic expiration and finalization
└── Metrics Output: PressureMetrics dataclass with full statistics
```

### **5. SQLite Storage Layer**
```
PressureMetrics → SQLite Database → Indexed Storage
├── Table: pressure_metrics
│   ├── Fields: strike, option_type, time_window, bid_volume, ask_volume
│   ├── Metrics: pressure_ratio, total_trades, avg_trade_size, dominant_side
│   ├── Quality: confidence, created_at
│   └── Constraints: UNIQUE(strike, option_type, time_window)
├── Indexes:
│   ├── idx_pressure_time: Efficient time-based queries
│   ├── idx_pressure_strike: Strike/type lookups
│   └── idx_usage_date: Cost monitoring queries
└── Usage Monitoring: Separate table for cost/performance tracking
```

### **6. Cost & Usage Monitoring**
```
Real-time Tracking → UsageMonitor → SQLite Logs
├── Event Counting: Per-event size and throughput tracking
├── Cost Estimation: $0.01/MB + $1/hour streaming base cost
├── Budget Enforcement: Automatic cutoff at 80% of $25 daily limit
├── Performance Metrics: Latency, throughput, error rates
└── Historical Logging: Daily aggregation for trend analysis
```

## Current Gaps & Integration Points

### **Missing Connections**
1. **MBO → IFD Bridge**: No direct connection from PressureMetrics to IFD v3.0 analysis
2. **Real-time Signal Flow**: Pressure metrics stored but not fed to live analysis
3. **Dashboard Integration**: No WebSocket from analysis engine to dashboard
4. **Alert System**: No real-time notification when significant pressure detected

### **Integration Points Available**
1. **Callback System**: `on_pressure_metrics` callback ready for IFD integration
2. **Database Interface**: Structured storage with efficient querying
3. **Configuration**: Environment variables and market hours control
4. **Error Handling**: Comprehensive exception handling and logging

### **Data Quality & Validation**
- **Latency**: Sub-second from WebSocket to storage
- **Reliability**: Automatic reconnection and gap detection
- **Accuracy**: Price scaling and trade side derivation validated
- **Coverage**: All NQ options via parent symbol subscription

## Next Steps for Live Integration
1. Connect `on_pressure_metrics` callback to IFD v3.0 analysis engine
2. Implement real-time baseline context updates in IFD analysis
3. Create WebSocket bridge from IFD signals to dashboard display
4. Add real-time alert system for high-confidence institutional flow

## Performance Characteristics
- **Throughput**: 10,000 event queue capacity
- **Processing**: Separate thread for non-blocking analysis
- **Storage**: SQLite with optimized indexes for fast queries
- **Memory**: Efficient window management with automatic cleanup
- **Cost Control**: Real-time monitoring with automatic budget enforcement
