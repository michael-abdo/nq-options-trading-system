# NQ Options Quote Pressure Monitor

## 🎯 Key Insight

**Options don't trade much, but QUOTES tell the institutional story.**

This tool monitors live quote pressure (bid/ask size changes) in NQ options to detect institutional positioning.

## ✅ What We Discovered

1. **Live Streaming Works**: Getting 1000+ NQ option symbols
2. **Correct Format**: `NQM5 C21980` (not `NQH25 C22000`)
3. **All Strikes Available**: From $2,000 to $33,500 strikes
4. **Parent Symbol Works**: `NQ.OPT` includes everything

## 🔄 The Strategy

Instead of waiting for rare trades, monitor **quote pressure**:

```python
# Large bid appears = Institutional buyer
if bid_size >= 50:
    print("🐋 Institutional buyer positioning")

# Asks pulled = Supply removed
if ask_size_decrease > 25:
    print("🚀 Bullish - sellers retreating")

# Pressure ratio shift = Directional bias
pressure_ratio = bid_size / ask_size
if pressure_ratio > 2.0:
    print("📈 Strong buy pressure")
```

## 🕐 Optimal Timing

**Best signals during:**
- **2:30-4:00 PM ET**: End-of-day institutional positioning
- **9:30-10:30 AM ET**: Market open positioning
- **ATM ± 3 strikes**: Where institutions focus

## 🚀 Usage

```bash
cd /Users/Mike/trading/algos/EOD/quote_pressure_monitor
python3 nq_options_quote_pressure.py
```

## 📊 What It Monitors

- **Strike Range**: $19,000 - $25,000 (near current NQ price)
- **Quote Sizes**: Bid/Ask contract sizes
- **Pressure Changes**: Sudden size increases/decreases
- **Institutional Threshold**: 50+ contracts

## 🚨 Alert Conditions

1. **Large Quote Sizes**: ≥50 contracts on bid or ask
2. **Extreme Pressure**: Ratio >3.0 or <0.33
3. **Sudden Changes**: ±25 contract size shifts
4. **Strike Focus**: Near-the-money options only

## 📁 Output

Alerts saved to: `institutional_alerts.jsonl`

Each alert contains:
- Timestamp and symbol
- Bid/ask prices and sizes
- Pressure ratio and direction
- Specific trigger reasons
- Options spread data

## 💡 Trading Application

Use alerts to:
1. **Position NQ futures** based on options flow
2. **Time entries** around institutional activity
3. **Confirm directional bias** before trades
4. **Scale position size** based on signal strength

## ⚙️ Configuration

Adjust thresholds in script:
- `INSTITUTIONAL_SIZE_THRESHOLD = 50`  # Contracts
- `PRESSURE_RATIO_THRESHOLD = 2.0`    # Pressure ratio
- Strike range: 19000-25000           # Price range

---

**This is the breakthrough - quote pressure detection for institutional NQ options flow!**
