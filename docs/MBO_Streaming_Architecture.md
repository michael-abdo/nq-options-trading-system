# MBO Streaming Architecture for IFD v3.0

## Overview
This document outlines the Market-By-Order (MBO) streaming architecture for Institutional Flow Detection v3.0, replacing the historical API approach with real-time streaming for enhanced bid/ask pressure analysis.

## Architecture Components

### 1. MBO Streaming Pipeline
```
Databento Live Stream → Event Buffer → Pressure Aggregator → SQLite Storage → IFD v3.0 Analysis
         ↓                    ↓              ↓                    ↓
    Usage Monitor → Reconnection Logic → Cost Tracker → Historical Baseline
```

### 2. Core Classes

#### MBOStreamingClient
- **Purpose**: Real-time WebSocket connection to Databento
- **Responsibilities**:
  - Establish live connection using `db.Live()`
  - Subscribe to MBO schema for NQ.OPT
  - Handle connection lifecycle and authentication
  - Buffer incoming events for processing

#### MBOEventProcessor  
- **Purpose**: Process individual MBO events in real-time
- **Responsibilities**:
  - Parse MBO event data structure
  - Derive trade initiation direction (BUY/SELL)
  - Extract bid/ask prices and volumes
  - Filter and validate event quality

#### PressureAggregator
- **Purpose**: Calculate bid/ask pressure metrics from tick data
- **Responsibilities**:
  - Aggregate trades by strike and time window
  - Calculate pressure ratios (ask_volume / bid_volume)
  - Maintain rolling statistics for baselines
  - Generate institutional flow signals

#### MBODatabase
- **Purpose**: Efficient storage of processed MBO metrics
- **Responsibilities**:
  - Time-series storage of pressure metrics
  - Historical baseline calculations
  - Data compression and retention policies
  - Fast retrieval for analysis engine

#### StreamManager
- **Purpose**: Orchestrate the entire MBO streaming pipeline
- **Responsibilities**:
  - Coordinate all components
  - Handle errors and reconnections
  - Monitor performance and costs
  - Provide control interface

### 3. Data Flow

#### Real-Time Processing
```
MBO Event → Parse → Derive Direction → Aggregate by Strike → Store Metrics → Signal Detection
```

#### Historical Baseline
```
Daily Job → Fetch 20-day History → Calculate Baselines → Update Local Cache → Ready for Comparison
```

### 4. Cost Management Strategy

#### Smart Streaming
- **Market Hours Only**: 9:30 AM - 4:00 PM ET
- **Parent Symbol**: Subscribe to 'NQ.OPT' to get all strikes
- **Selective Processing**: Focus on active strikes near the money

#### Usage Monitoring
- **Daily Budget**: $10 maximum per trading day
- **Real-time Tracking**: Monitor data consumption
- **Automatic Cutoff**: Stop streaming at 80% of budget
- **Reconnection Throttling**: Exponential backoff for failures

### 5. Data Structures

#### MBO Event
```python
{
    "timestamp": "2025-06-10T13:05:23.145Z",
    "instrument_id": 123456,
    "strike": 21900.0,
    "option_type": "C",  # C=Call, P=Put
    "bid_price": 16.00,
    "ask_price": 17.00,
    "trade_price": 16.50,
    "trade_size": 10,
    "side": "BUY"  # Derived: BUY if hit ask, SELL if hit bid
}
```

#### Pressure Metrics
```python
{
    "strike": 21900.0,
    "option_type": "C",
    "time_window": "2025-06-10T13:05:00Z",  # 5-minute windows
    "bid_volume": 150,
    "ask_volume": 320,
    "pressure_ratio": 2.13,  # ask_volume / bid_volume
    "total_trades": 25,
    "avg_trade_size": 18.8,
    "dominant_side": "BUY"
}
```

### 6. Performance Targets

#### Latency
- **Event Processing**: <10ms per event
- **Pressure Calculation**: <50ms per 5-minute window
- **Signal Generation**: <100ms end-to-end

#### Throughput
- **Expected Volume**: 100-1000 events/minute per active strike
- **Storage Rate**: ~1MB/hour of processed metrics
- **Memory Usage**: <500MB for 6.5-hour trading day

#### Reliability
- **Uptime**: >99.9% during market hours
- **Data Completeness**: >95% of all MBO events captured
- **Reconnection Time**: <30 seconds average

### 7. Error Handling

#### Stream Disconnection
```python
def handle_disconnection():
    log_disconnection_time()
    wait_exponential_backoff()
    attempt_reconnection()
    if reconnected:
        request_missed_data()
    else:
        fallback_to_historical_mode()
```

#### Data Quality Issues
- **Invalid Events**: Log and skip malformed data
- **Missing Timestamps**: Use system time with warning
- **Price Anomalies**: Flag for manual review
- **Volume Spikes**: Validate against exchange limits

### 8. Testing Strategy

#### Unit Tests
- **Event Processing**: Mock MBO events, verify parsing
- **Pressure Calculation**: Known inputs, expected outputs
- **Storage**: Database operations and retrieval
- **Cost Monitoring**: Usage tracking accuracy

#### Integration Tests
- **End-to-End**: Live stream → processing → storage → analysis
- **Reconnection**: Simulated disconnections and recovery
- **Performance**: Load testing with high-frequency data
- **Cost Control**: Budget limit enforcement

#### Validation Tests
- **Signal Quality**: Compare v3.0 vs v1.0 on historical data
- **Latency**: Measure processing delays under load
- **Accuracy**: Validate pressure ratios against known patterns

## Implementation Phases

### Phase 1: Core Streaming (Week 1)
- [ ] MBOStreamingClient with live connection
- [ ] Basic event processing and parsing
- [ ] SQLite storage for processed metrics
- [ ] Simple reconnection logic

### Phase 2: Pressure Calculations (Week 2)
- [ ] PressureAggregator implementation
- [ ] Real-time bid/ask pressure derivation
- [ ] Time-window aggregation (5-minute windows)
- [ ] Basic signal generation

### Phase 3: Advanced Features (Week 3)
- [ ] Historical baseline integration
- [ ] Cost monitoring and budget controls
- [ ] Advanced reconnection strategies
- [ ] Performance optimization

### Phase 4: Testing & Validation (Week 4)
- [ ] Comprehensive test suite
- [ ] Live data quality validation
- [ ] Performance benchmarking
- [ ] Production readiness assessment

## Success Metrics

### Technical Performance
- **Processing Latency**: <100ms end-to-end
- **Data Completeness**: >95% event capture rate
- **System Uptime**: >99.9% during market hours
- **Memory Efficiency**: <500MB peak usage

### Signal Quality
- **Pressure Accuracy**: >90% correct direction detection
- **False Positive Rate**: <30% (significant improvement over v1.0)
- **Signal Confidence**: Statistical significance >0.8
- **Baseline Stability**: <5% daily variation in historical metrics

### Cost Efficiency
- **Daily Budget**: <$10 per trading day
- **Monthly Total**: <$200 including historical data
- **Cost per Signal**: <$2 per actionable signal
- **ROI**: >25% improvement over v1.0 system

This architecture provides the foundation for real-time institutional flow detection with the granular bid/ask pressure analysis required for IFD v3.0.