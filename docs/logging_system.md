# NQ Options EV Trading System - Logging Documentation

## Overview

The NQ Options EV Trading System includes a comprehensive logging framework that captures all system activities, calculations, and decisions for full transparency and debugging capabilities.

## Log Directory Structure

Logs are organized by session in timestamped directories:

```
logs/
├── YYYY-MM-DD_HH-MM-SS/
│   ├── main.log         # All log messages
│   ├── calculations.log # Calculation-specific logs
│   ├── data.log        # Data fetching and parsing logs
│   └── errors.log      # Warnings and errors only
```

## Log Files

### main.log
- Contains all log messages from all components
- Includes DEBUG, INFO, WARNING, and ERROR levels
- Rotates at 10MB with 5 backup files

### calculations.log
- Focused on probability and EV calculations
- Includes detailed factor calculations
- Shows step-by-step computation process

### data.log
- Tracks URL generation and data fetching
- Records scraping activities
- Documents data parsing results

### errors.log
- Contains only WARNING and ERROR messages
- Quick reference for troubleshooting
- Includes full stack traces for exceptions

## Log Levels

- **DEBUG**: Detailed information for debugging (file only)
- **INFO**: General informational messages (console + file)
- **WARNING**: Warning messages that don't stop execution
- **ERROR**: Error messages with stack traces

## Key Features

### 1. Comprehensive Coverage
Every major decision point and calculation is logged:
- URL generation for contracts
- Data loading/scraping
- Strike price analysis
- Factor calculations (OI, Volume, PCR, Distance)
- Probability calculations
- EV calculations
- Filtering decisions
- Report generation

### 2. Structured Logging
- Section headers for better readability
- Function entry/exit tracking with `@log_function_call` decorator
- Separate loggers for different components

### 3. Color-Coded Console Output
- Green: INFO messages
- Yellow: WARNING messages
- Red: ERROR messages
- Cyan: DEBUG messages (when enabled)

### 4. Performance Tracking
- Timestamps with millisecond precision
- Function execution tracking
- Clear indication of system flow

## Usage

### Basic Usage
The logging system is automatically initialized when running the scripts:

```python
from utils.logging_config import setup_logging, get_logger

# Set up logging
log_dir, session_id = setup_logging(log_level=logging.DEBUG, console_level=logging.INFO)
logger = get_logger(__name__)

# Use the logger
logger.info("Starting system...")
```

### Component-Specific Logging
```python
# For calculations
calc_logger = get_logger(f"{__name__}.calculations")
calc_logger.info("Calculating probability...")

# For data operations
data_logger = get_logger(f"{__name__}.data")
data_logger.info("Fetching data...")
```

### Log Sections
```python
from utils.logging_config import log_section

log_section("STARTING ANALYSIS")
# ... your code ...
log_section("ANALYSIS COMPLETE")
```

## Example Log Output

### Console Output
```
[09:25:06] INFO: ============================================================
[09:25:06] INFO:                STARTING NQ OPTIONS EV SYSTEM                
[09:25:06] INFO: ============================================================
[09:25:06] INFO: Testing all TP/SL combinations for current price: 21376.75
[09:25:06] INFO: Valid LONG setup: TP=21450, SL=21350, EV=55.64
[09:25:06] INFO: Found 3 quality setups
```

### File Output (main.log)
```
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability | === Calculating Probability ===
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability | Current: 21376.75, TP: 21450, SL: 21350, Direction: long
[2025-06-02 09:25:06] DEBUG    | __main__             | calculate_probability | Max OI: 17700, Max Volume: 2800
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability | Normalized factors:
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability |   OI Factor: 1.0000 (weight: 0.35)
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability |   Volume Factor: 1.0000 (weight: 0.25)
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability |   PCR Factor: 0.2976 (weight: 0.25)
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability |   Distance Factor: 0.9966 (weight: 0.15)
[2025-06-02 09:25:06] INFO     | __main__             | calculate_probability | Final probability: 82.39%
```

## Debugging Tips

1. **Check errors.log first** - Quick overview of any issues
2. **Use calculations.log** - Verify probability and EV calculations
3. **Review main.log** - Full execution flow and decision trail
4. **Monitor data.log** - Troubleshoot data fetching issues

## Configuration

The logging system can be configured in `utils/logging_config.py`:

- Change log levels
- Modify log formats
- Adjust file rotation settings
- Customize console colors

## Best Practices

1. Always check logs after system runs
2. Review calculation logs to understand trading decisions
3. Monitor error logs for potential issues
4. Use session IDs to correlate logs with specific runs
5. Archive important log sessions for compliance/review