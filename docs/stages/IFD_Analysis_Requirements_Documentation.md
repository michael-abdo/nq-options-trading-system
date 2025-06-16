# IFD v3.0 Analysis Requirements and Data Formats

## Input Requirements

### **Primary Input: PressureMetrics**
```python
@dataclass
class PressureMetrics:
    """Real-time pressure metrics from MBO streaming aggregation"""

    # Core identification
    strike: float                   # Option strike price (e.g., 21900.0)
    option_type: str               # 'C' for calls, 'P' for puts
    time_window: datetime          # 5-minute aggregation window (UTC timezone)

    # Volume analysis
    bid_volume: int               # Volume hitting bid (SELL trades)
    ask_volume: int               # Volume hitting ask (BUY trades)
    pressure_ratio: float         # ask_volume / bid_volume (institutional interest indicator)

    # Trade characteristics
    total_trades: int             # Number of trades in 5-minute window
    avg_trade_size: float         # Average trade size (contracts)
    dominant_side: str            # 'BUY', 'SELL', 'NEUTRAL'

    # Quality metrics
    confidence: float             # Aggregation confidence (0.0-1.0)
```

### **Input Validation Requirements**
- **strike**: Must be positive float (> 0)
- **option_type**: Must be 'C' or 'P'
- **time_window**: Must be timezone-aware datetime object
- **pressure_ratio**: Must be positive (>= 0), can be infinity for all-buy scenarios
- **total_trades**: Must be non-negative integer
- **confidence**: Must be between 0.0 and 1.0

### **Minimum Thresholds for Analysis**
```python
DEFAULT_THRESHOLDS = {
    'min_pressure_ratio': 2.0,      # Minimum pressure for signal consideration
    'min_total_volume': 100,        # Minimum combined volume (bid + ask)
    'min_confidence': 0.8,          # Minimum aggregation confidence
    'min_final_confidence': 0.6     # Minimum final signal confidence for output
}
```

## Configuration Schema

### **Complete Configuration Structure**
```python
CONFIG_SCHEMA = {
    # Database configuration
    'baseline_db_path': str,        # SQLite database path for historical baselines

    # Pressure analysis settings
    'pressure_analysis': {
        'min_pressure_ratio': float,      # Minimum pressure ratio for consideration (default: 2.0)
        'min_total_volume': int,          # Minimum total volume threshold (default: 100)
        'min_confidence': float,          # Minimum pressure confidence (default: 0.8)
        'lookback_windows': int           # Number of windows for pattern analysis (default: 3)
    },

    # Historical baseline settings
    'historical_baselines': {
        'lookback_days': int             # Days of history for baseline (default: 20)
    },

    # Market making detection
    'market_making_detection': {
        'straddle_time_window': int,              # Seconds for straddle coordination (default: 300)
        'max_market_making_probability': float    # Max MM probability to allow (default: 0.3)
    },

    # Confidence scoring weights
    'confidence_scoring': {
        'pressure_weight': float,        # Weight for pressure analysis (default: 0.4)
        'baseline_weight': float,        # Weight for baseline context (default: 0.3)
        'market_making_weight': float,   # Weight for MM detection (default: 0.2)
        'coordination_weight': float     # Weight for coordination analysis (default: 0.1)
    },

    # Final output thresholds
    'min_final_confidence': float       # Minimum confidence for signal output (default: 0.6)
}
```

### **Default Production Configuration**
```python
PRODUCTION_CONFIG = {
    'baseline_db_path': 'outputs/ifd_v3_baselines.db',
    'pressure_analysis': {
        'min_pressure_ratio': 2.0,
        'min_total_volume': 100,
        'min_confidence': 0.8
    },
    'historical_baselines': {
        'lookback_days': 20
    },
    'market_making_detection': {
        'straddle_time_window': 300,
        'max_market_making_probability': 0.3
    },
    'confidence_scoring': {
        'pressure_weight': 0.4,
        'baseline_weight': 0.3,
        'market_making_weight': 0.2,
        'coordination_weight': 0.1
    },
    'min_final_confidence': 0.6
}
```

## Output Format

### **Primary Output: InstitutionalSignalV3**
```python
@dataclass
class InstitutionalSignalV3:
    """Enhanced v3.0 institutional signal with comprehensive analysis"""

    # Core identification
    strike: float                      # Option strike price
    option_type: str                   # 'C' for calls, 'P' for puts
    timestamp: datetime                # Signal generation time (UTC)

    # v3.0 Pressure Analysis
    pressure_ratio: float              # Current ask/bid pressure ratio
    bid_volume: int                    # Volume hitting bid
    ask_volume: int                    # Volume hitting ask
    dominant_side: str                 # 'BUY', 'SELL', 'NEUTRAL'
    pressure_confidence: float         # Pressure analysis confidence (0-1)

    # Historical Context
    baseline_pressure_ratio: float     # 20-day historical baseline
    pressure_zscore: float             # Standard deviations from baseline
    percentile_rank: float             # Percentile rank vs historical data
    anomaly_detected: bool             # True if significant anomaly detected

    # Market Making Analysis
    market_making_probability: float   # Probability this is market making (0-1)
    straddle_coordination: bool        # True if straddle coordination detected
    volatility_crush_detected: bool    # True if vol crush pattern detected

    # Enhanced Confidence Scoring
    raw_confidence: float              # Base pressure confidence
    baseline_confidence: float         # Baseline context confidence
    market_making_penalty: float      # Penalty for MM probability
    coordination_bonus: float         # Bonus for coordination patterns
    final_confidence: float           # Final weighted confidence (0-1)

    # Signal Classification
    signal_strength: str              # 'EXTREME', 'VERY_HIGH', 'HIGH', 'MODERATE'
    institutional_probability: float  # Probability of institutional flow
    recommended_action: str           # 'STRONG_BUY', 'BUY', 'MONITOR', 'IGNORE'

    # Risk Assessment
    risk_score: float                 # Risk assessment (0-1, lower is safer)
    position_size_multiplier: float   # Recommended position scaling
    max_position_risk: float          # Maximum recommended risk exposure
```

### **Signal Strength Classifications**
```python
SIGNAL_STRENGTH_THRESHOLDS = {
    'EXTREME': final_confidence >= 0.9,      # Very high confidence institutional flow
    'VERY_HIGH': final_confidence >= 0.8,    # High confidence with strong indicators
    'HIGH': final_confidence >= 0.7,         # Good confidence with multiple factors
    'MODERATE': final_confidence >= 0.6      # Minimum threshold for output
}
```

### **Recommended Action Mappings**
```python
RECOMMENDED_ACTIONS = {
    'STRONG_BUY': {
        'criteria': 'final_confidence >= 0.85 AND dominant_side == "BUY"',
        'description': 'High-confidence institutional buying detected'
    },
    'BUY': {
        'criteria': 'final_confidence >= 0.7 AND dominant_side == "BUY"',
        'description': 'Institutional buying interest detected'
    },
    'MONITOR': {
        'criteria': 'final_confidence >= 0.6 OR anomaly_detected == True',
        'description': 'Elevated activity requiring monitoring'
    },
    'IGNORE': {
        'criteria': 'market_making_probability > 0.5',
        'description': 'Likely market making activity'
    }
}
```

## Analysis Pipeline Stages

### **Stage 1: Pressure Analysis**
```python
# Input: PressureMetrics
# Processing: Basic pressure ratio analysis, volume validation
# Output: PressureAnalysis
# Criteria: min_pressure_ratio, min_total_volume, min_confidence
```

### **Stage 2: Baseline Context**
```python
# Input: PressureMetrics + Historical Database
# Processing: 20-day historical baseline calculation, z-score analysis
# Output: BaselineContext
# Features: Anomaly detection, percentile ranking, statistical context
```

### **Stage 3: Market Making Detection**
```python
# Input: PressureMetrics + Recent Activity Window
# Processing: Straddle coordination, volatility crush patterns
# Output: MarketMakingAnalysis
# Purpose: Filter false positives from market maker activity
```

### **Stage 4: Confidence Scoring**
```python
# Input: PressureAnalysis + BaselineContext + MarketMakingAnalysis
# Processing: Weighted multi-factor confidence calculation
# Output: Final confidence scores
# Weights: Pressure (40%), Baseline (30%), MM Detection (20%), Coordination (10%)
```

### **Stage 5: Signal Classification**
```python
# Input: All analysis results + Final confidence
# Processing: Signal strength assignment, action recommendation
# Output: InstitutionalSignalV3
# Thresholds: Configurable confidence levels for different signal strengths
```

## Dependencies and Requirements

### **System Dependencies**
```python
REQUIRED_PACKAGES = [
    'sqlite3',           # Database storage
    'logging',           # System logging
    'datetime',          # Timezone handling
    'statistics',        # Statistical calculations
    'typing',            # Type annotations
    'dataclasses',       # Data structures
    'collections',       # Data containers
    'pathlib'            # Path handling
]
```

### **Database Requirements**
```sql
-- Historical pressure data table
CREATE TABLE historical_pressure (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL,
    date TEXT NOT NULL,
    pressure_ratio REAL NOT NULL,
    volume_total INTEGER NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(strike, option_type, date)
);

-- Baseline statistics cache table
CREATE TABLE baseline_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strike REAL NOT NULL,
    option_type TEXT NOT NULL,
    lookback_days INTEGER NOT NULL,
    mean_pressure REAL NOT NULL,
    std_pressure REAL NOT NULL,
    percentiles TEXT NOT NULL,  -- JSON string
    data_quality REAL NOT NULL,
    last_updated TEXT NOT NULL,
    UNIQUE(strike, option_type, lookback_days)
);
```

### **Memory Requirements**
- **Baseline Cache**: ~10MB for 1000 active strikes
- **Signal History**: ~1MB for 100 recent signals
- **Processing Buffers**: ~5MB for real-time analysis

### **Performance Characteristics**
- **Analysis Latency**: 50-200ms per PressureMetrics input
- **Memory Usage**: ~16MB for full analysis engine
- **Database I/O**: 1-5 queries per analysis (cached baseline lookups)
- **Throughput**: 100+ pressure metrics per minute

## Integration Interface

### **Main Entry Point**
```python
def analyze_pressure_event(self, pressure_metrics: PressureMetrics) -> Optional[InstitutionalSignalV3]:
    """
    Main analysis pipeline for MBO pressure events

    Args:
        pressure_metrics: Real-time pressure metrics from MBO streaming

    Returns:
        InstitutionalSignalV3 if signal detected, None otherwise

    Processing:
        1. Update historical baselines
        2. Calculate baseline context
        3. Analyze pressure patterns
        4. Detect market making patterns
        5. Calculate enhanced confidence
        6. Generate institutional signal (if above threshold)
    """
```

### **Factory Function**
```python
def create_ifd_v3_analyzer(config: Optional[Dict] = None) -> IFDv3Engine:
    """Factory function to create IFD v3.0 analyzer instance"""
    # Returns configured IFDv3Engine ready for real-time analysis
```

### **Batch Processing Function**
```python
def run_ifd_v3_analysis(pressure_data: List[PressureMetrics], config: Dict[str, Any]) -> Dict[str, Any]:
    """Run IFD v3.0 analysis on batch of pressure data"""
    # For historical analysis and backtesting
```

## Error Handling

### **Input Validation Errors**
- Invalid PressureMetrics format
- Missing required fields
- Out-of-range values

### **Processing Errors**
- Database connection failures
- Insufficient historical data
- Configuration errors

### **Graceful Degradation**
- Continue analysis with reduced confidence when baseline data is limited
- Default to conservative thresholds when configuration is incomplete
- Log warnings for data quality issues without stopping analysis
