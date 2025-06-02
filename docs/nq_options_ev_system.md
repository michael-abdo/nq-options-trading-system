# NQ Options Expected Value Trading System

## 📋 **Project Overview**

A quantitative trading system that analyzes NQ (E-mini Nasdaq-100) futures options end-of-day data to identify optimal Target Price (TP) and Stop Loss (SL) combinations with the highest Expected Value (EV). The system uses options flow intelligence as a leading indicator for directional trades in underlying assets.

## 🎯 **Core Concept**

**Primary Optimization Metric: Expected Value (EV)**
```
EV = (Probability × Reward) - ((1 - Probability) × Risk)
```

The system calculates probability using weighted factors from options market data:
- **Open Interest Factor** (35% weight): Shows where smart money is positioned
- **Volume Factor** (25% weight): Indicates current conviction and momentum  
- **Put/Call Ratio Factor** (25% weight): Measures directional bias strength
- **Distance Factor** (15% weight): Accounts for probability decay with distance

## 📊 **Data Requirements**

### **Source: Barchart.com NQ EOD Options Data**

Required fields for each strike:
```
Strike_Price | Call_Volume | Call_OI | Call_Premium | Put_Volume | Put_OI | Put_Premium
```

### **Sample Data Structure:**
```
Strike | Call_Volume | Call_OI | Call_Premium | Put_Volume | Put_OI | Put_Premium
21200  |     250     |   1500  |    2.50      |    800     |  5200  |    8.75
21250  |     180     |   1200  |    4.25      |    650     |  4800  |   12.50
21300  |     320     |   2100  |    7.50      |    920     |  6500  |   18.25
21350  |     450     |   3200  |   12.75      |   1100     |  7200  |   26.50
21400  |     850     |   5500  |   22.50      |   1350     |  8900  |   38.75
21450  |    1200     |   8200  |   35.25      |   1580     |  9500  |   55.50
21500  |     980     |   6800  |   52.75      |   1820     |  8800  |   78.25
```

## 🧮 **Mathematical Framework**

### **Probability Calculation Formula:**
```
P(TP before SL) = 0.35×OI_factor + 0.25×Vol_factor + 0.25×PCR_factor + 0.15×Distance_factor
```

### **Factor Calculations:**

#### **1. OI Factor (Weight: 0.35)**
```python
OI_factor = Σ[Strike_OI × Distance_weight × Direction_modifier] / Max_OI_observed

Distance_weight:
- 0-1% from current: 1.0
- 1-2% from current: 0.8  
- 2-5% from current: 0.5
- 5%+ from current: 0.2

Direction_modifier:
- +1 if strike supports target direction
- -0.5 if strike opposes target direction
```

#### **2. Volume Factor (Weight: 0.25)**
```python
Vol_factor = Σ[Strike_Volume × Distance_weight × Direction_modifier] / Max_Vol_observed
# Same weighting structure as OI_factor
```

#### **3. PCR Factor (Weight: 0.25)**
```python
PCR_factor = (Call_Premium_Total - Put_Premium_Total) / (Call_Premium_Total + Put_Premium_Total)
# Result range: -1 (very bearish) to +1 (very bullish)
```

#### **4. Distance Factor (Weight: 0.15)**
```python
Distance_factor = 1 - (|Current_Price - Target_Price| / Current_Price)
# Result range: 0 (very far) to 1 (at current price)
```

### **Expected Value Calculation:**
```python
if target_price > current_price:  # Long trade
    reward = target_price - current_price
    risk = current_price - stop_loss
else:  # Short trade
    reward = current_price - target_price  
    risk = stop_loss - current_price

EV = (probability × reward) - ((1 - probability) × risk)
```

## 💻 **Implementation Architecture**

### **Core Functions:**

#### **Main Execution Function:**
```python
def main_trading_system():
    # 1. Data acquisition from Barchart
    # 2. Calculate EV for all TP/SL combinations  
    # 3. Filter and rank opportunities
    # 4. Check for perfect alignment setups
    # 5. Generate execution recommendations
    return best_opportunities
```

#### **Probability Calculator:**
```python
def calculate_probability(current_price, tp, sl, strike_factors, pcr_factor, pcr_oi_factor, direction):
    # Weight strikes between current and target
    # Apply direction modifiers
    # Normalize components to 0-1 range
    # Return probability (clamped 10-90%)
```

#### **EV Optimizer:**
```python
def calculate_ev_for_all_combinations(current_price, options_data):
    # Test all valid TP/SL combinations
    # Calculate probability for each
    # Compute EV and risk metrics
    # Return sorted by highest EV
```

### **Data Processing Pipeline:**

1. **Raw Data Ingestion** → Parse Barchart options data
2. **Factor Calculation** → Compute weighted factors for all strikes
3. **Combination Generation** → Create all valid TP/SL pairs
4. **Probability Modeling** → Apply weighted formula
5. **EV Optimization** → Calculate and rank by Expected Value
6. **Filtering** → Apply quality thresholds
7. **Alignment Detection** → Identify perfect setups
8. **Output Generation** → Format trading recommendations

## 🎯 **Trading Strategy**

### **Setup Identification:**

#### **Quality Filters:**
```python
quality_setups = [setup for setup in all_results if 
                 setup['EV'] > 15 and                    # Min +15 point EV
                 setup['Probability'] > 0.60 and        # Min 60% probability
                 setup['Risk'] <= 150 and               # Max 150 point risk
                 setup['Risk_Reward'] >= 1.0]           # Min 1:1 RR
```

#### **Perfect Alignment Bonus:**
When mathematical optimal TP matches highest liquidity strikes:
- **Maximum conviction setup**
- **Increased position sizing**
- **85%+ probability scores typical**

### **Position Sizing Framework:**
```python
if EV > 50:
    position_size = "LARGE (15-20% of portfolio)"
elif EV > 30:
    position_size = "MEDIUM (10-15% of portfolio)"  
else:
    position_size = "SMALL (5-10% of portfolio)"
```

### **Risk Management:**
- **Stop Loss**: Mathematically derived from equation
- **Target Price**: Highest EV strike level
- **Position Size**: Scaled by EV confidence
- **Maximum Risk**: 150 points per trade

## 📈 **Expected Outputs**

### **Daily Trading Report:**
```
Top 5 Trading Opportunities:
--------------------------------------------------------------------------------
Rank Direction TP     SL     Prob   RR     EV      
--------------------------------------------------------------------------------
1    Long      21450  21300  72.5%  1.9:1  +42.3
2    Long      21500  21250  68.2%  2.1:1  +38.7
3    Short     21250  21400  71.8%  2.0:1  +35.2
4    Long      21400  21300  74.1%  1.5:1  +32.8
5    Short     21300  21450  69.3%  1.5:1  +31.1
```

### **Execution Recommendation:**
```
Recommended Trade: Long NQ
Entry: Current price (21376)
Target: 21450 (+74 points)
Stop: 21300 (-76 points)
Position Size: LARGE (15-20% of portfolio)
Expected Value: +42.3 points per trade
```

## 🛠 **Technical Implementation**

### **Required Libraries:**
```python
import pandas as pd
import numpy as np
import requests  # For Barchart data API
import json
from datetime import datetime
import logging
```

### **Key Classes:**
```python
class OptionsStrike:
    def __init__(self, price, call_volume, call_oi, call_premium, 
                 put_volume, put_oi, put_premium):
        self.price = price
        self.call_volume = call_volume
        self.call_oi = call_oi
        self.call_premium = call_premium
        self.put_volume = put_volume
        self.put_oi = put_oi
        self.put_premium = put_premium

class TradeSetup:
    def __init__(self, tp, sl, direction, probability, reward, risk, ev):
        self.tp = tp
        self.sl = sl
        self.direction = direction
        self.probability = probability
        self.reward = reward
        self.risk = risk
        self.ev = ev
        self.risk_reward = reward / risk if risk > 0 else 0
```

### **Configuration Settings:**
```python
# Weighting factors (adjustable through backtesting)
WEIGHTS = {
    'oi_factor': 0.35,
    'vol_factor': 0.25, 
    'pcr_factor': 0.25,
    'distance_factor': 0.15
}

# Quality thresholds
MIN_EV = 15
MIN_PROBABILITY = 0.60
MAX_RISK = 150
MIN_RISK_REWARD = 1.0

# Distance weighting brackets
DISTANCE_WEIGHTS = {
    0.01: 1.0,  # 0-1%
    0.02: 0.8,  # 1-2%
    0.05: 0.5,  # 2-5%
    1.00: 0.2   # 5%+
}
```

## 📊 **Backtesting Framework**

### **Performance Metrics:**
- **Total Return**: Cumulative EV over time
- **Win Rate**: Percentage of trades hitting TP first
- **Average EV**: Mean expected value per trade
- **Maximum Drawdown**: Largest consecutive loss period
- **Sharpe Ratio**: Risk-adjusted returns

### **Optimization Process:**
1. **Historical Data Collection**: 6-12 months NQ options data
2. **Weight Calibration**: Test different factor weightings
3. **Threshold Tuning**: Optimize quality filters
4. **Out-of-Sample Testing**: Validate on unseen data
5. **Walk-Forward Analysis**: Rolling optimization periods

### **Validation Metrics:**
```python
def backtest_performance(historical_results):
    total_trades = len(historical_results)
    winners = sum(1 for trade in historical_results if trade.hit_target)
    win_rate = winners / total_trades
    
    total_ev = sum(trade.actual_pnl for trade in historical_results)
    avg_ev = total_ev / total_trades
    
    return {
        'win_rate': win_rate,
        'total_ev': total_ev,
        'avg_ev_per_trade': avg_ev,
        'total_trades': total_trades
    }
```