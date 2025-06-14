# Setup Instructions for EOD Trading System

## API Key Configuration ✅

Your new Databento API key has been configured in `.env`:
```
DATABENTO_API_KEY=db-GwY53Q48Yy7tNMSBnFBwQCkM86uTP
```

## Installing Dependencies

Due to macOS system protection, you need to use a virtual environment:

### Option 1: Create Virtual Environment (Recommended)
```bash
# Create virtual environment
python3 -m venv trading_env

# Activate it
source trading_env/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

### Option 2: Install Specific Packages for Charts
```bash
# Activate your existing virtual environment first, then:
pip install plotly jsonschema

# Or if you must install system-wide (not recommended):
pip3 install --user plotly jsonschema
```

### Option 3: Using Homebrew
```bash
# For system-wide installation via Homebrew:
brew install plotly
```

## Running the System

### 1. Full Pipeline
```bash
python3 scripts/run_pipeline.py
```

### 2. 5-Minute Chart
```bash
# After installing plotly:
python3 scripts/nq_5m_chart.py

# With custom settings:
python3 scripts/nq_5m_chart.py --days 5 --profile aggressive
```

## Verifying Installation

Run the installation test:
```bash
python3 scripts/test_installation.py
```

## Missing Dependencies

The system requires these packages for full functionality:
- **plotly** - For 5-minute chart visualization
- **jsonschema** - For configuration validation
- **python-dotenv** - For environment variable loading (already installed)

## Current Status

✅ **API Key**: Updated and ready
✅ **Pipeline**: Working correctly
❌ **5-Min Chart**: Requires plotly installation

## Quick Start

1. Create/activate virtual environment
2. Run: `pip install plotly jsonschema`
3. Test: `python3 scripts/nq_5m_chart.py --help`
4. Run full system: `python3 scripts/run_pipeline.py`