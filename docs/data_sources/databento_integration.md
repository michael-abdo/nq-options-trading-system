# Databento API Integration

## Overview
This document describes the integration with Databento API for retrieving NQ Future Options data.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements_databento.txt
```

### 2. Environment Configuration
The API key is stored in the `.env` file:
```
DATABENTO_API_KEY=your-api-key-here
```

### 3. Test Connection
Run the minimal test to verify API connectivity:
```bash
python tests/test_databento_api.py
```

## API Usage

### Key Datasets for NQ Options
- **GLBX.MDP3**: CME Globex MDP 3.0 (primary dataset for futures/options)
- **OPRA.PILLAR**: Options data from OPRA

### Schemas Available
- `ohlcv-1h`: Hourly OHLCV bars
- `ohlcv-1m`: Minute OHLCV bars  
- `trades`: Individual trades
- `mbp-10`: Market by price (10 levels)
- `tbbo`: Top of book best bid/offer

### Symbol Formats
- Futures root: `NQ`
- Options format: `NQ{expiry}{C/P}{strike}`
- Example: `NQM24C20000` (June 2024 20000 Call)

## Cost Considerations
- Always use `get_cost()` before retrieving data
- Costs vary by dataset, schema, and time range
- Historical data is charged per symbol per day

## Example Usage

```python
import databento as db
from datetime import datetime, timedelta

# Initialize client
client = db.Historical(api_key)

# Get NQ options chain
end_date = datetime.now()
start_date = end_date - timedelta(days=1)

data = client.timeseries.get_range(
    dataset='GLBX.MDP3',
    symbols=['NQ'],
    schema='ohlcv-1h',
    start=start_date,
    end=end_date,
    stype_in='root_symbol'
)

# Convert to DataFrame
df = data.to_df()
```

## Integration Points

### 1. Data Ingestion Pipeline
- Replace/supplement Barchart API with Databento
- Real-time streaming available via Live client
- Historical data for backtesting

### 2. Options Chain Retrieval
- Use definition schema to get full options chain
- Filter by expiry, strike range, option type
- Calculate implied volatility from prices

### 3. Volume Analysis
- Access to tick-by-tick trade data
- Aggregate volume by strike/expiry
- Identify institutional flow patterns

## Next Steps
1. Implement options chain parser
2. Create data normalizer for Databento format
3. Add caching layer for cost optimization
4. Integrate with existing analysis pipeline