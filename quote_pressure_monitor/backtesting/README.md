# 🔄 Simple Institutional Flow Backtester

## 💡 Strategy Concept

**Ultra-simple institutional flow following:**
1. **Detect institutional options flow** (≥50 bid size, ≥2.0 pressure ratio)
2. **Calculate average strike price** of calls vs puts
3. **Trade NQ futures in the direction of flow**:
   - Call flow → Go LONG NQ futures
   - Put flow → Go SHORT NQ futures
4. **Hold for 24 hours** then exit
5. **Calculate P&L** vs entry price

## 📊 What It Tests

- **Can we profit by following institutional options positioning?**
- **Do large option flows predict underlying futures movement?**
- **Is the average strike price relevant for entry timing?**

## 🎯 Key Metrics Tracked

- **Total P&L** in dollars
- **Win rate** percentage
- **Average P&L per trade**
- **Number of signals** generated
- **Volume-weighted flow** direction

## 🚀 Usage

```bash
cd backtesting
export DATABENTO_API_KEY=your_key
python3 simple_flow_backtester.py
```

## 📈 Sample Output

```
🎯 CALL_FLOW: LONG at $21,785
   Volume: 847 contracts (23 strikes)
   📈 Entry: $21,750.00 | Exit: $21,820.00
   💰 P&L: +70.00 pts = $+1,400.00

📊 BACKTEST RESULTS SUMMARY
Total Trades: 12
Total P&L: $+8,400.00
Avg P&L per Trade: $+700.00
Win Rate: 66.7%
```

## 📁 Output Files

- **backtest_results_[dates].json**: Complete trade log with entry/exit prices
- **Simple JSON format** for easy analysis in Excel/Python

## ⚙️ Configuration

Easy to modify parameters:
- `min_bid_size = 50`: Institutional threshold
- `min_pressure_ratio = 2.0`: Pressure threshold
- `hold_hours = 24`: Position hold time
- `time_window_hours = 1`: Analysis window size

## 🎯 Next Steps

If this simple approach shows promise:
1. **Multi-day backtests** across different market conditions
2. **Optimize hold periods** (1hr, 4hr, 24hr, 48hr)
3. **Strike price weighting** (closer to ATM = higher weight)
4. **Volume filtering** (minimum total volume thresholds)
5. **Market regime filters** (VIX, trend, volatility)

**Keep it simple first - prove the concept works!**
