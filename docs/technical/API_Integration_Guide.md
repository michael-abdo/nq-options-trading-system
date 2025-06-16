# API Integration Guide & Data Formats

## Overview
The IFD v3.0 Trading System provides comprehensive API endpoints for real-time data streaming, signal integration, and system monitoring. This guide covers all available endpoints, data formats, and integration patterns for external systems.

## Table of Contents
- [WebSocket API Endpoints](#websocket-api-endpoints)
- [REST API Endpoints](#rest-api-endpoints)
- [Data Format Specifications](#data-format-specifications)
- [Authentication](#authentication)
- [Integration Examples](#integration-examples)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)

## WebSocket API Endpoints

### 1. Real-Time Signal Stream
**Endpoint**: `ws://localhost:8765/signals`

**Description**: Real-time IFD v3.0 signals with confidence scoring and market context.

**Connection Example**:
```javascript
const ws = new WebSocket('ws://localhost:8765/signals');

ws.onopen = function(event) {
    console.log('Connected to signal stream');

    // Subscribe to specific symbols
    ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: ['NQM5', 'ESM5'],
        signal_types: ['institutional_flow', 'pressure_spike']
    }));
};

ws.onmessage = function(event) {
    const signal = JSON.parse(event.data);
    processSignal(signal);
};
```

**Signal Data Format**:
```json
{
    "type": "signal",
    "timestamp": "2025-06-16T20:30:45.123Z",
    "signal_id": "ifd_20250616_203045_001",
    "symbol": "NQM5",
    "signal_type": "institutional_flow",
    "confidence": 0.85,
    "strength": "strong",
    "direction": "bullish",
    "expected_value": 125.50,
    "pressure_metrics": {
        "imbalance_ratio": 2.34,
        "volume_concentration": 0.78,
        "order_flow_delta": 1250,
        "pressure_baseline": 0.45
    },
    "market_context": {
        "price": 21742.50,
        "volume": 69546,
        "volatility": 0.023,
        "session": "regular"
    },
    "risk_metrics": {
        "risk_score": 0.25,
        "max_drawdown": 50.0,
        "win_probability": 0.72
    },
    "metadata": {
        "algorithm_version": "ifd_v3.0",
        "processing_time_ms": 24.6,
        "data_sources": ["databento_mbo", "barchart_fallback"]
    }
}
```

### 2. Market Data Stream
**Endpoint**: `ws://localhost:8765/market_data`

**Description**: Real-time market data feed with OHLCV data and order book information.

**Market Data Format**:
```json
{
    "type": "market_data",
    "timestamp": "2025-06-16T20:30:45.123Z",
    "symbol": "NQM5",
    "data_type": "ohlcv",
    "interval": "1m",
    "data": {
        "open": 21740.25,
        "high": 21745.00,
        "low": 21738.50,
        "close": 21742.50,
        "volume": 1250,
        "vwap": 21741.85,
        "trades": 47
    },
    "order_book": {
        "bid": 21742.25,
        "ask": 21742.75,
        "bid_size": 25,
        "ask_size": 18,
        "spread": 0.50
    },
    "metadata": {
        "source": "databento_mbo",
        "latency_ms": 12.3,
        "quality_score": 0.98
    }
}
```

### 3. System Status Stream
**Endpoint**: `ws://localhost:8765/status`

**Description**: Real-time system health and performance metrics.

**Status Data Format**:
```json
{
    "type": "system_status",
    "timestamp": "2025-06-16T20:30:45.123Z",
    "system_health": {
        "status": "healthy",
        "uptime_seconds": 3600,
        "cpu_usage": 0.45,
        "memory_usage": 0.62,
        "disk_usage": 0.34
    },
    "data_sources": {
        "databento": {
            "status": "connected",
            "latency_ms": 15.2,
            "messages_per_second": 150,
            "error_rate": 0.001
        },
        "barchart": {
            "status": "standby",
            "cache_hit_rate": 0.95,
            "last_update": "2025-06-16T20:25:00.000Z"
        }
    },
    "performance_metrics": {
        "signal_generation_rate": 0.25,
        "average_processing_time_ms": 24.6,
        "total_signals_generated": 1247,
        "accuracy_rate": 0.73
    },
    "alerts": [
        {
            "level": "warning",
            "message": "CPU usage above 70%",
            "timestamp": "2025-06-16T20:29:30.000Z"
        }
    ]
}
```

### 4. Alert Stream
**Endpoint**: `ws://localhost:8765/alerts`

**Description**: Real-time system alerts and notifications.

**Alert Data Format**:
```json
{
    "type": "alert",
    "timestamp": "2025-06-16T20:30:45.123Z",
    "alert_id": "alert_20250616_203045_001",
    "level": "critical",
    "category": "system",
    "title": "High Memory Usage Detected",
    "message": "System memory usage has exceeded 85% threshold",
    "details": {
        "current_usage": 0.87,
        "threshold": 0.85,
        "trend": "increasing",
        "affected_components": ["data_processor", "signal_generator"]
    },
    "suggested_actions": [
        "Restart data processing services",
        "Clear temporary cache files",
        "Monitor memory usage trends"
    ],
    "metadata": {
        "source": "monitoring_system",
        "severity_score": 8.5,
        "auto_resolve": false
    }
}
```

## REST API Endpoints

### 1. Historical Signals
**Endpoint**: `GET /api/v1/signals/history`

**Parameters**:
- `symbol` (required): Trading symbol (e.g., "NQM5")
- `start_date` (required): Start date (ISO format)
- `end_date` (required): End date (ISO format)
- `signal_type` (optional): Filter by signal type
- `min_confidence` (optional): Minimum confidence threshold
- `limit` (optional): Maximum results (default: 100)

**Example Request**:
```bash
curl -X GET "http://localhost:8080/api/v1/signals/history" \
  -H "Authorization: Bearer your-api-token" \
  -G \
  -d "symbol=NQM5" \
  -d "start_date=2025-06-15T00:00:00Z" \
  -d "end_date=2025-06-16T23:59:59Z" \
  -d "min_confidence=0.70"
```

**Response Format**:
```json
{
    "status": "success",
    "count": 25,
    "signals": [
        {
            "signal_id": "ifd_20250616_143022_001",
            "timestamp": "2025-06-16T14:30:22.456Z",
            "symbol": "NQM5",
            "signal_type": "institutional_flow",
            "confidence": 0.82,
            "direction": "bullish",
            "expected_value": 95.25,
            "outcome": {
                "realized_pnl": 87.50,
                "accuracy": true,
                "duration_minutes": 45
            }
        }
    ],
    "metadata": {
        "query_time_ms": 45.2,
        "cache_hit": true,
        "next_page": "/api/v1/signals/history?page=2&..."
    }
}
```

### 2. System Configuration
**Endpoint**: `GET /api/v1/config`

**Description**: Retrieve current system configuration.

**Response Format**:
```json
{
    "status": "success",
    "config": {
        "environment": "production",
        "data_sources": {
            "databento": {
                "enabled": true,
                "mode": "live",
                "symbols": ["NQM5", "ESM5"],
                "rate_limit": 1000
            }
        },
        "ifd_v3": {
            "confidence_threshold": 0.75,
            "pressure_baseline_days": 20,
            "performance_optimized": true
        },
        "alerts": {
            "enabled": true,
            "channels": ["email", "slack", "websocket"],
            "thresholds": {
                "cpu_usage": 80,
                "memory_usage": 85,
                "error_rate": 0.01
            }
        }
    }
}
```

### 3. Performance Metrics
**Endpoint**: `GET /api/v1/metrics`

**Parameters**:
- `timeframe` (optional): "1h", "6h", "24h", "7d" (default: "1h")
- `metrics` (optional): Comma-separated list of specific metrics

**Response Format**:
```json
{
    "status": "success",
    "timeframe": "1h",
    "metrics": {
        "performance": {
            "signal_count": 15,
            "accuracy_rate": 0.73,
            "average_latency_ms": 24.6,
            "p99_latency_ms": 89.2
        },
        "system": {
            "cpu_usage": {
                "current": 0.45,
                "average": 0.52,
                "peak": 0.78
            },
            "memory_usage": {
                "current": 0.62,
                "average": 0.58,
                "peak": 0.71
            }
        },
        "data_quality": {
            "completeness": 0.98,
            "error_rate": 0.002,
            "source_reliability": {
                "databento": 0.99,
                "barchart": 0.95
            }
        }
    }
}
```

### 4. Health Check
**Endpoint**: `GET /api/v1/health`

**Description**: System health check endpoint for monitoring systems.

**Response Format**:
```json
{
    "status": "healthy",
    "timestamp": "2025-06-16T20:30:45.123Z",
    "version": "3.0.1",
    "uptime_seconds": 3600,
    "components": {
        "data_ingestion": {
            "status": "healthy",
            "last_update": "2025-06-16T20:30:40.000Z"
        },
        "signal_processor": {
            "status": "healthy",
            "processing_rate": 150.5
        },
        "websocket_server": {
            "status": "healthy",
            "active_connections": 5
        },
        "database": {
            "status": "healthy",
            "connection_pool": 8
        }
    }
}
```

## Data Format Specifications

### 1. Signal Format Specification

**Core Signal Object**:
```typescript
interface Signal {
    signal_id: string;           // Unique identifier
    timestamp: string;           // ISO 8601 format
    symbol: string;              // Trading symbol
    signal_type: SignalType;     // Signal classification
    confidence: number;          // 0.0 to 1.0 range
    strength: SignalStrength;    // "weak" | "moderate" | "strong"
    direction: Direction;        // "bullish" | "bearish" | "neutral"
    expected_value: number;      // Expected profit/loss in points
    pressure_metrics: PressureMetrics;
    market_context: MarketContext;
    risk_metrics: RiskMetrics;
    metadata: SignalMetadata;
}

type SignalType =
    | "institutional_flow"
    | "pressure_spike"
    | "volume_anomaly"
    | "order_imbalance";

type SignalStrength = "weak" | "moderate" | "strong";
type Direction = "bullish" | "bearish" | "neutral";
```

**Pressure Metrics**:
```typescript
interface PressureMetrics {
    imbalance_ratio: number;        // Order flow imbalance
    volume_concentration: number;   // Volume concentration index
    order_flow_delta: number;      // Net order flow
    pressure_baseline: number;     // 20-day baseline
    institutional_score: number;   // Institutional activity score
}
```

**Market Context**:
```typescript
interface MarketContext {
    price: number;                 // Current price
    volume: number;                // Session volume
    volatility: number;            // Realized volatility
    session: SessionType;          // Trading session
    market_hours: boolean;         // Market open/closed
    economic_events: EconomicEvent[]; // Scheduled events
}

type SessionType = "pre_market" | "regular" | "post_market" | "extended";
```

### 2. Market Data Format

**OHLCV Data**:
```typescript
interface OHLCVData {
    timestamp: string;
    symbol: string;
    interval: string;              // "1m", "5m", "1h", etc.
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    vwap: number;                  // Volume weighted average price
    trades: number;                // Number of trades
}
```

**Order Book Data**:
```typescript
interface OrderBookData {
    timestamp: string;
    symbol: string;
    bid: number;
    ask: number;
    bid_size: number;
    ask_size: number;
    spread: number;
    depth: {
        bids: [number, number][];  // [price, size] pairs
        asks: [number, number][];  // [price, size] pairs
    };
}
```

### 3. Error Response Format

**Standard Error Response**:
```json
{
    "status": "error",
    "error": {
        "code": "INVALID_SYMBOL",
        "message": "Symbol 'INVALID' is not supported",
        "details": {
            "supported_symbols": ["NQM5", "ESM5", "YMM5"],
            "provided_symbol": "INVALID"
        },
        "timestamp": "2025-06-16T20:30:45.123Z",
        "request_id": "req_20250616_203045_001"
    }
}
```

**Error Codes**:
- `INVALID_SYMBOL`: Unsupported trading symbol
- `AUTHENTICATION_FAILED`: API key invalid or expired
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_PARAMETER`: Request parameter validation failed
- `INTERNAL_ERROR`: Server-side processing error
- `SERVICE_UNAVAILABLE`: Service temporarily unavailable

## Authentication

### 1. API Key Authentication

**Header Format**:
```http
Authorization: Bearer your-api-key-here
```

**API Key Generation**:
```bash
# Generate new API key
python3 scripts/generate_api_key.py --user "integration_system" --permissions "read,stream"

# Test API key
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8080/api/v1/health"
```

### 2. WebSocket Authentication

**Connection with Authentication**:
```javascript
const ws = new WebSocket('ws://localhost:8765/signals', [], {
    headers: {
        'Authorization': 'Bearer your-api-key'
    }
});

// Alternative: Send auth message after connection
ws.onopen = function() {
    ws.send(JSON.stringify({
        type: 'auth',
        token: 'your-api-key'
    }));
};
```

### 3. Rate Limiting

**Default Limits**:
- WebSocket connections: 10 per API key
- REST API requests: 1000 per hour
- Signal stream: No limit (subject to system capacity)

**Rate Limit Headers**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1623456789
```

## Integration Examples

### 1. Python Integration

**Basic Signal Consumer**:
```python
import asyncio
import websockets
import json
from typing import Dict, Any

class IFDSignalConsumer:
    def __init__(self, api_key: str, endpoint: str = "ws://localhost:8765/signals"):
        self.api_key = api_key
        self.endpoint = endpoint
        self.ws = None

    async def connect(self):
        """Connect to signal stream"""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        self.ws = await websockets.connect(self.endpoint, extra_headers=headers)

        # Subscribe to signals
        await self.ws.send(json.dumps({
            "action": "subscribe",
            "symbols": ["NQM5"],
            "signal_types": ["institutional_flow"]
        }))

    async def listen(self):
        """Listen for signals"""
        try:
            async for message in self.ws:
                signal = json.loads(message)
                await self.process_signal(signal)
        except websockets.exceptions.ConnectionClosed:
            print("Connection closed, attempting reconnect...")
            await self.reconnect()

    async def process_signal(self, signal: Dict[str, Any]):
        """Process incoming signal"""
        if signal.get("type") == "signal":
            confidence = signal.get("confidence", 0)
            if confidence >= 0.75:  # High confidence signals only
                print(f"High confidence signal: {signal['signal_id']}")
                print(f"Direction: {signal['direction']}")
                print(f"Expected Value: {signal['expected_value']}")
                # Implement your trading logic here

    async def reconnect(self):
        """Reconnect with exponential backoff"""
        for attempt in range(5):
            try:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                await self.connect()
                break
            except Exception as e:
                print(f"Reconnect attempt {attempt + 1} failed: {e}")

# Usage
async def main():
    consumer = IFDSignalConsumer("your-api-key")
    await consumer.connect()
    await consumer.listen()

if __name__ == "__main__":
    asyncio.run(main())
```

**REST API Client**:
```python
import requests
from typing import List, Dict, Any
from datetime import datetime, timedelta

class IFDAPIClient:
    def __init__(self, api_key: str, base_url: str = "http://localhost:8080"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {api_key}"}

    def get_historical_signals(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        min_confidence: float = 0.70
    ) -> List[Dict[str, Any]]:
        """Get historical signals"""
        params = {
            "symbol": symbol,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "min_confidence": min_confidence
        }

        response = requests.get(
            f"{self.base_url}/api/v1/signals/history",
            headers=self.headers,
            params=params
        )

        if response.status_code == 200:
            return response.json()["signals"]
        else:
            raise Exception(f"API Error: {response.status_code} - {response.text}")

    def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        response = requests.get(
            f"{self.base_url}/api/v1/health",
            headers=self.headers
        )

        return response.json()

# Usage
client = IFDAPIClient("your-api-key")
signals = client.get_historical_signals(
    symbol="NQM5",
    start_date=datetime.now() - timedelta(days=1),
    end_date=datetime.now()
)
print(f"Found {len(signals)} signals")
```

### 2. JavaScript Integration

**Browser WebSocket Client**:
```javascript
class IFDDashboard {
    constructor(apiKey, wsEndpoint = 'ws://localhost:8765/signals') {
        this.apiKey = apiKey;
        this.wsEndpoint = wsEndpoint;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    connect() {
        this.ws = new WebSocket(this.wsEndpoint);

        this.ws.onopen = (event) => {
            console.log('Connected to IFD signal stream');
            this.reconnectAttempts = 0;

            // Authenticate
            this.ws.send(JSON.stringify({
                type: 'auth',
                token: this.apiKey
            }));

            // Subscribe to signals
            this.ws.send(JSON.stringify({
                action: 'subscribe',
                symbols: ['NQM5'],
                signal_types: ['institutional_flow', 'pressure_spike']
            }));
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onclose = (event) => {
            console.log('WebSocket connection closed');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'signal':
                this.displaySignal(data);
                break;
            case 'market_data':
                this.updateMarketData(data);
                break;
            case 'system_status':
                this.updateSystemStatus(data);
                break;
            default:
                console.log('Unknown message type:', data.type);
        }
    }

    displaySignal(signal) {
        const signalElement = document.createElement('div');
        signalElement.className = `signal ${signal.direction}`;
        signalElement.innerHTML = `
            <div class="signal-header">
                <span class="symbol">${signal.symbol}</span>
                <span class="confidence">${(signal.confidence * 100).toFixed(1)}%</span>
            </div>
            <div class="signal-body">
                <div class="direction ${signal.direction}">${signal.direction.toUpperCase()}</div>
                <div class="expected-value">EV: ${signal.expected_value}</div>
                <div class="timestamp">${new Date(signal.timestamp).toLocaleTimeString()}</div>
            </div>
        `;

        document.getElementById('signals-container').prepend(signalElement);

        // Remove old signals (keep last 10)
        const signals = document.querySelectorAll('.signal');
        if (signals.length > 10) {
            signals[signals.length - 1].remove();
        }
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.pow(2, this.reconnectAttempts) * 1000; // Exponential backoff

            console.log(`Reconnecting in ${delay/1000} seconds (attempt ${this.reconnectAttempts})`);

            setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.error('Max reconnection attempts reached');
        }
    }
}

// Usage
const dashboard = new IFDDashboard('your-api-key');
dashboard.connect();
```

### 3. Trading Platform Integration

**MT5/cTrader Integration Example**:
```python
# Example integration with MetaTrader 5
import MetaTrader5 as mt5
from ifd_signal_consumer import IFDSignalConsumer

class MT5IFDIntegration:
    def __init__(self, mt5_login: int, mt5_password: str, mt5_server: str, ifd_api_key: str):
        self.mt5_login = mt5_login
        self.mt5_password = mt5_password
        self.mt5_server = mt5_server
        self.ifd_consumer = IFDSignalConsumer(ifd_api_key)

    async def initialize(self):
        """Initialize MT5 and IFD connections"""
        # Initialize MT5
        if not mt5.initialize():
            raise Exception("MT5 initialization failed")

        # Login to MT5
        if not mt5.login(self.mt5_login, password=self.mt5_password, server=self.mt5_server):
            raise Exception("MT5 login failed")

        # Connect to IFD stream
        await self.ifd_consumer.connect()

    async def process_signal(self, signal):
        """Process IFD signal and place trades"""
        if signal.get("confidence", 0) < 0.80:
            return  # Only trade high confidence signals

        symbol = self.convert_symbol(signal["symbol"])  # Convert NQM5 to NQ-JUN25
        direction = signal["direction"]
        lot_size = self.calculate_position_size(signal)

        if direction == "bullish":
            order_type = mt5.ORDER_TYPE_BUY
        elif direction == "bearish":
            order_type = mt5.ORDER_TYPE_SELL
        else:
            return  # Skip neutral signals

        # Place order
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "magic": 12345,
            "comment": f"IFD Signal {signal['signal_id']}"
        }

        result = mt5.order_send(request)
        if result.retcode == mt5.TRADE_RETCODE_DONE:
            print(f"Order placed successfully: {result.order}")
        else:
            print(f"Order failed: {result.comment}")
```

## Error Handling

### 1. WebSocket Error Handling

**Connection Errors**:
```javascript
ws.onerror = function(error) {
    console.error('WebSocket Error:', error);

    // Implement exponential backoff reconnection
    setTimeout(() => {
        connect();
    }, Math.min(1000 * Math.pow(2, reconnectAttempts), 30000));
};

ws.onclose = function(event) {
    if (event.code !== 1000) {
        console.log('Unexpected close, code:', event.code);
        // Handle abnormal closure
    }
};
```

**Message Validation**:
```javascript
ws.onmessage = function(event) {
    try {
        const data = JSON.parse(event.data);

        // Validate message structure
        if (!data.type || !data.timestamp) {
            console.warn('Invalid message format:', data);
            return;
        }

        handleMessage(data);
    } catch (error) {
        console.error('Message parsing error:', error);
    }
};
```

### 2. REST API Error Handling

**Response Validation**:
```python
def make_api_request(endpoint, params=None):
    try:
        response = requests.get(endpoint, params=params, timeout=30)

        # Check HTTP status
        if response.status_code == 429:
            # Rate limited - implement backoff
            wait_time = int(response.headers.get('Retry-After', 60))
            time.sleep(wait_time)
            return make_api_request(endpoint, params)  # Retry

        elif response.status_code >= 400:
            error_data = response.json()
            raise APIError(error_data['error']['code'], error_data['error']['message'])

        return response.json()

    except requests.exceptions.RequestException as e:
        raise ConnectionError(f"API request failed: {e}")
```

## Performance Considerations

### 1. WebSocket Optimization

**Connection Pooling**:
```python
class WebSocketPool:
    def __init__(self, max_connections=5):
        self.connections = []
        self.max_connections = max_connections

    async def get_connection(self):
        if len(self.connections) < self.max_connections:
            ws = await websockets.connect("ws://localhost:8765/signals")
            self.connections.append(ws)
            return ws
        else:
            # Round-robin existing connections
            return self.connections[len(self.connections) % self.max_connections]
```

**Message Batching**:
```javascript
class MessageBatcher {
    constructor(batchSize = 10, flushInterval = 1000) {
        this.batch = [];
        this.batchSize = batchSize;
        this.flushInterval = flushInterval;

        setInterval(() => this.flush(), flushInterval);
    }

    addMessage(message) {
        this.batch.push(message);

        if (this.batch.length >= this.batchSize) {
            this.flush();
        }
    }

    flush() {
        if (this.batch.length > 0) {
            this.processBatch(this.batch);
            this.batch = [];
        }
    }
}
```

### 2. Data Compression

**Enable Compression**:
```python
# WebSocket with compression
ws = await websockets.connect(
    "ws://localhost:8765/signals",
    compression="deflate"
)

# REST API with compression
headers = {
    "Authorization": "Bearer your-api-key",
    "Accept-Encoding": "gzip, deflate"
}
```

## Security Best Practices

### 1. API Key Management

```python
# Secure API key storage
import keyring

# Store API key securely
keyring.set_password("ifd_system", "api_key", "your-api-key")

# Retrieve API key
api_key = keyring.get_password("ifd_system", "api_key")
```

### 2. Input Validation

```python
def validate_signal_data(signal):
    required_fields = ["signal_id", "timestamp", "symbol", "confidence"]

    for field in required_fields:
        if field not in signal:
            raise ValueError(f"Missing required field: {field}")

    if not (0 <= signal["confidence"] <= 1):
        raise ValueError("Confidence must be between 0 and 1")

    if signal["symbol"] not in SUPPORTED_SYMBOLS:
        raise ValueError(f"Unsupported symbol: {signal['symbol']}")
```

### 3. Rate Limiting Implementation

```python
from functools import wraps
import time

def rate_limit(calls_per_second=10):
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed

            if left_to_wait > 0:
                time.sleep(left_to_wait)

            last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper
    return decorator

@rate_limit(calls_per_second=5)
def api_call():
    # Your API call here
    pass
```

## Monitoring and Logging

### 1. Connection Monitoring

```python
import logging
from datetime import datetime

class ConnectionMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.metrics = {
            "connections": 0,
            "messages_sent": 0,
            "messages_received": 0,
            "errors": 0
        }

    def log_connection(self, endpoint):
        self.metrics["connections"] += 1
        self.logger.info(f"Connected to {endpoint} at {datetime.now()}")

    def log_message(self, direction, message_type):
        if direction == "sent":
            self.metrics["messages_sent"] += 1
        else:
            self.metrics["messages_received"] += 1

        self.logger.debug(f"Message {direction}: {message_type}")

    def log_error(self, error):
        self.metrics["errors"] += 1
        self.logger.error(f"Connection error: {error}")

    def get_stats(self):
        return self.metrics.copy()
```

### 2. Performance Monitoring

```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            success = True
        except Exception as e:
            result = None
            success = False
            raise
        finally:
            duration = (time.time() - start_time) * 1000  # Convert to ms

            # Log performance metrics
            logger.info(f"{func.__name__} completed in {duration:.2f}ms, success: {success}")

            # Send to monitoring system
            send_metric(f"{func.__name__}.duration", duration)
            send_metric(f"{func.__name__}.success", 1 if success else 0)

        return result
    return wrapper

@monitor_performance
async def process_signal(signal):
    # Your signal processing logic
    pass
```

This comprehensive API integration guide provides all the necessary information for integrating with the IFD v3.0 Trading System. For additional support or custom integration requirements, consult the system documentation or contact the development team.
