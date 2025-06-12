# Databento API Integration

## Overview
This document describes the integration with Databento API for retrieving NQ Future Options data.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements_databento.txt
```

### 2. Environment Configuration
The API key can be configured in multiple ways:
- Environment variable: `DATABENTO_API_KEY`
- Configuration file: `.env` file in project root
- Direct configuration in pipeline config

```bash
export DATABENTO_API_KEY=your-api-key-here
```

### 3. Test Connection
Run the setup script to verify everything works:
```bash
./setup_databento.sh
```

Or test manually:
```bash
python tests/test_databento_api.py
```

## Subscription Requirements

### CME Globex Live Data License
- **Cost**: $179/month for Standard plan
- **Includes**: All CME futures and options (NQ, ES, etc.)
- **Coverage**: Real-time and historical data access
- **Sign up**: https://databento.com/pricing#cme

### Free Credits
- New users receive $125 in free credits
- Credits apply to API usage costs (historical data queries)
- Live data requires the subscription regardless of credits

## Configuration

Add to your pipeline configuration:
```python
config = {
    "databento": {
        "api_key": "your-api-key",  # Or use DATABENTO_API_KEY env var
        "symbols": ["NQ"],
        "use_cache": True,
        "cache_dir": "outputs/databento_cache"
    }
}
```

## API Usage

### Available Datasets
- **GLBX.MDP3**: CME Globex MDP 3.0 (futures and options)
- **OPRA.PILLAR**: US equity options (alternative for testing)

### Schemas Supported
- `definition`: Contract definitions and metadata
- `trades`: Individual trade data with volume
- `ohlcv-1h`: Hourly OHLCV bars
- `ohlcv-1d`: Daily OHLCV bars
- `mbp-1`: Market by price (best bid/offer)
- `mbp-10`: Market by price (10 levels)

### Symbol Formats
- **Futures**: `NQ.FUT` (all NQ futures)
- **Options**: `NQ.OPT` (all NQ options)
- **Specific contracts**: `NQM5 C20000` (June 2025 20000 Call)

## Data Processing

### Options Chain Retrieval
```python
from tasks.options_trading_system.data_ingestion.databento_api.solution import DatabentoAPIClient

client = DatabentoAPIClient(api_key)
chain = client.get_nq_options_chain()

print(f"Found {chain['total_contracts']} contracts")
print(f"Calls: {len(chain['calls'])}")
print(f"Puts: {len(chain['puts'])}")
```

### Trade Data Analysis
```python
trades = client.get_options_trades()
print(f"Total volume: {trades['total_volume']}")
print(f"Active instruments: {len(trades['volume_by_instrument'])}")
```

## Cost Optimization

### Intelligent Caching
- SQLite-based cache with configurable expiry (default: 24 hours)
- Automatic cost checking before API calls
- Cache hit logging for monitoring

### Cost Limits
- Definition data: $1.00 maximum per query
- Trade data: $5.00 maximum per query
- Configurable in the client initialization

### Best Practices
1. Use caching for repeated queries
2. Query historical data in batches
3. Monitor your usage in Databento dashboard
4. Use appropriate schemas (daily vs hourly vs trades)

## Integration with Pipeline

The Databento source integrates seamlessly with the existing data pipeline:

```python
from tasks.options_trading_system.data_ingestion.integration import create_data_ingestion_pipeline

config = {
    "databento": {
        "api_key": os.getenv("DATABENTO_API_KEY"),
        "symbols": ["NQ"],
        "use_cache": True
    }
}

pipeline = create_data_ingestion_pipeline(config)
results = pipeline.run_full_pipeline()
```

## Data Quality

### Expected Metrics
- **Total contracts**: ~1,200-1,500 NQ options
- **Volume coverage**: 10-20% of contracts have volume data
- **Strike range**: Typically 50+ strikes above/below current price

### Quality Indicators
- Contracts with volume data
- Timestamp freshness
- Strike coverage breadth
- Trade count per instrument

## Troubleshooting

### Common Issues

1. **403 License Error**
   - Need CME Globex subscription ($179/month)
   - Check subscription status in Databento dashboard

2. **Date Range Errors**
   - Databento requires end date > start date
   - Future dates may have restricted access

3. **High Costs**
   - Check query parameters (date range, symbol count)
   - Use caching to avoid repeated queries
   - Monitor usage in dashboard

4. **Import Errors**
   - Ensure `databento` package is installed
   - Check Python path and virtual environment

### Performance Tips
- Use historical data (5+ days old) for backtesting
- Limit live queries to necessary data only
- Leverage caching for repeated analysis
- Monitor API costs regularly

## See Also
- [Implementation Summary](../databento_implementation_summary.md)
- [Setup Script](../../setup_databento.sh)
- [Test Suite](../../tests/test_databento_api.py)
