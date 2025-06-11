# Institutional Flow Detection v3.0 Architecture Design

## Overview
IFD v3.0 represents a major evolution from v1.0 (basic volume/premium) to v2.0 (relative analysis) by adding real-time bid/ask pressure analysis using MBO streaming data from Phase 1.

## System Integration with MBO Streaming

### Data Flow Architecture
```
MBO Stream → Pressure Metrics → IFD v3.0 Analysis → Institutional Signals
     ↓              ↓                 ↓                      ↓
Phase 1        Real-time         Historical           Enhanced
Streaming      Aggregation       Baselines           Confidence
```

### Component Integration
```python
# Phase 1 Output (MBO Streaming)
PressureMetrics = {
    'strike': 21900.0,
    'option_type': 'C',
    'time_window': '2025-06-10T13:05:00Z',
    'bid_volume': 150,
    'ask_volume': 320,
    'pressure_ratio': 2.13,
    'total_trades': 25,
    'dominant_side': 'BUY',
    'confidence': 0.85
}

# Phase 2 Input (IFD v3.0 Analysis)
InstitutionalSignalV3 = {
    'pressure_metrics': PressureMetrics,
    'historical_context': BaselineData,
    'market_making_probability': 0.15,
    'coordination_score': 0.92,
    'final_confidence': 0.78,
    'signal_strength': 'VERY_HIGH'
}
```

## Core Components Architecture

### 1. IFDv3Engine - Main Analysis Engine
```python
class IFDv3Engine:
    """
    Main engine coordinating all v3.0 analysis components
    
    Responsibilities:
    - Consume MBO pressure metrics from Phase 1
    - Apply historical baseline analysis
    - Detect market making patterns
    - Generate institutional flow signals
    - Calculate enhanced confidence scores
    """
    
    def __init__(self, config):
        self.pressure_analyzer = PressureRatioAnalyzer(config)
        self.baseline_manager = HistoricalBaselineManager(config)
        self.market_making_detector = MarketMakingDetector(config)
        self.confidence_scorer = EnhancedConfidenceScorer(config)
        
    def analyze_pressure_event(self, pressure_metrics: PressureMetrics) -> Optional[InstitutionalSignalV3]:
        """Main analysis pipeline for each pressure event"""
```

### 2. PressureRatioAnalyzer - Real-time Analysis
```python
class PressureRatioAnalyzer:
    """
    Analyzes real-time pressure ratios against thresholds and patterns
    
    Key Features:
    - Real-time pressure ratio validation
    - Minimum volume/confidence thresholds
    - Trend analysis over multiple windows
    - Strike clustering detection
    """
    
    def analyze_pressure_signal(self, metrics: PressureMetrics) -> PressureAnalysis:
        """
        Analyze pressure metrics for institutional activity
        
        Returns:
        - pressure_significance: How unusual this pressure is
        - trend_strength: Multi-window trend analysis
        - cluster_coordination: Related strikes activity
        """
```

### 3. HistoricalBaselineManager - 20-Day Context
```python
class HistoricalBaselineManager:
    """
    Manages historical baselines for pressure ratio context
    
    Key Features:
    - 20-day rolling baselines per strike
    - Statistical distribution analysis (mean, std, percentiles)
    - Anomaly detection (z-score calculation)
    - Adaptive baseline updates
    """
    
    def get_baseline_context(self, strike: float, option_type: str) -> BaselineContext:
        """
        Get historical context for pressure analysis
        
        Returns:
        - mean_pressure_ratio: 20-day average
        - pressure_std: Standard deviation
        - current_zscore: How many std devs from normal
        - percentile_rank: Current pressure vs historical distribution
        """
        
    def update_baselines(self, pressure_metrics: PressureMetrics):
        """Update rolling baselines with new data"""
```

### 4. MarketMakingDetector - False Positive Filter
```python
class MarketMakingDetector:
    """
    Detects market making activity to filter false positives
    
    Key Features:
    - Straddle coordination detection
    - Volatility crush pattern recognition
    - Time-coordinated call/put activity
    - Statistical market making probability
    """
    
    def detect_market_making_patterns(self, 
                                    current_metrics: PressureMetrics,
                                    recent_activity: List[PressureMetrics]) -> MarketMakingAnalysis:
        """
        Analyze for market making patterns
        
        Returns:
        - straddle_probability: Likelihood of straddle activity
        - volatility_crush_detected: Price decline coordination
        - market_making_score: Overall MM probability (0-1)
        """
```

### 5. EnhancedConfidenceScorer - Multi-Factor Validation
```python
class EnhancedConfidenceScorer:
    """
    Calculates enhanced confidence scores using multiple validation factors
    
    Factors:
    - Pressure significance (how unusual)
    - Historical context (baseline deviation)
    - Market making probability (lower = better)
    - Cross-strike coordination
    - Volume concentration
    - Time persistence
    """
    
    def calculate_confidence(self, 
                           pressure_analysis: PressureAnalysis,
                           baseline_context: BaselineContext,
                           market_making_analysis: MarketMakingAnalysis) -> ConfidenceScore:
        """
        Multi-factor confidence calculation
        
        Returns:
        - raw_confidence: Base confidence from pressure
        - baseline_adjustment: Historical context modifier
        - market_making_penalty: MM probability penalty
        - coordination_bonus: Cross-strike bonus
        - final_confidence: Risk-adjusted final score
        """
```

## Data Structures

### Enhanced Signal Structure
```python
@dataclass
class InstitutionalSignalV3:
    """Enhanced v3.0 institutional signal with pressure analysis"""
    
    # Core identification
    strike: float
    option_type: str
    timestamp: datetime
    
    # v3.0 Pressure Analysis
    pressure_ratio: float
    bid_volume: int
    ask_volume: int
    dominant_side: str
    
    # Historical Context
    baseline_pressure_ratio: float
    pressure_zscore: float
    percentile_rank: float
    
    # Market Making Analysis
    market_making_probability: float
    straddle_coordination: bool
    volatility_crush_detected: bool
    
    # Enhanced Confidence
    raw_confidence: float
    baseline_confidence: float
    market_making_penalty: float
    coordination_bonus: float
    final_confidence: float
    
    # Signal Classification
    signal_strength: str  # 'EXTREME', 'VERY_HIGH', 'HIGH', 'MODERATE'
    institutional_probability: float
    recommended_action: str  # 'STRONG_BUY', 'BUY', 'MONITOR', 'IGNORE'
    
    # Risk Assessment
    risk_score: float
    position_size_multiplier: float
    max_position_risk: float

@dataclass
class BaselineContext:
    """Historical baseline data for pressure analysis"""
    strike: float
    option_type: str
    lookback_days: int
    
    mean_pressure_ratio: float
    pressure_std: float
    pressure_percentiles: Dict[int, float]  # 10th, 25th, 50th, 75th, 90th, 95th, 99th
    
    current_zscore: float
    percentile_rank: float
    anomaly_detected: bool
    
    data_quality: float  # 0-1, based on data completeness
    confidence: float    # Statistical confidence in baseline

@dataclass
class MarketMakingAnalysis:
    """Market making detection results"""
    
    # Straddle Detection
    straddle_call_volume: int
    straddle_put_volume: int
    straddle_time_coordination: float  # seconds between activity
    straddle_probability: float
    
    # Volatility Crush Detection
    call_price_decline: float
    put_price_decline: float
    both_sides_declining: bool
    volatility_crush_probability: float
    
    # Overall Assessment
    market_making_score: float  # 0-1 probability
    institutional_likelihood: float  # 1 - market_making_score
    filter_recommendation: str  # 'ACCEPT', 'MONITOR', 'REJECT'
```

## Integration with Existing Pipeline

### Analysis Engine Integration
```python
# In analysis_engine/integration.py
def run_analysis_engine(data_config: Dict, analysis_config: Dict) -> Dict:
    """Enhanced to include IFD v3.0"""
    
    results = {}
    
    # Existing analyses (v1.0, risk, etc.)
    if "volume_spike_dead_simple" in analysis_config:
        results["volume_spike_v1"] = run_volume_spike_analysis(data_config)
    
    # NEW: IFD v3.0 Analysis
    if "institutional_flow_v3" in analysis_config:
        results["institutional_flow_v3"] = run_ifd_v3_analysis(data_config, analysis_config)
    
    return results

def run_ifd_v3_analysis(data_config: Dict, analysis_config: Dict) -> Dict:
    """
    Run IFD v3.0 analysis using MBO pressure data
    
    Process:
    1. Connect to MBO streaming database
    2. Retrieve recent pressure metrics
    3. Apply IFD v3.0 analysis
    4. Generate institutional signals
    5. Return enhanced results
    """
```

### Configuration Integration
```python
# Enhanced configuration for IFD v3.0
ifd_v3_config = {
    "pressure_analysis": {
        "min_pressure_ratio": 2.0,
        "min_total_volume": 100,
        "min_confidence": 0.8,
        "lookback_windows": 3  # Number of 5-min windows to analyze
    },
    
    "historical_baselines": {
        "lookback_days": 20,
        "min_data_quality": 0.9,
        "zscore_threshold": 2.0,
        "percentile_threshold": 95
    },
    
    "market_making_detection": {
        "straddle_time_window": 300,  # 5 minutes
        "volatility_crush_threshold": -5.0,  # 5% decline
        "max_market_making_probability": 0.3
    },
    
    "confidence_scoring": {
        "baseline_weight": 0.3,
        "pressure_weight": 0.4,
        "market_making_weight": 0.2,
        "coordination_weight": 0.1
    }
}
```

## Implementation Phases

### Phase 2A: Core Pressure Analysis (Week 2)
1. **IFDv3Engine**: Main coordination engine
2. **PressureRatioAnalyzer**: Real-time pressure analysis
3. **Basic signal generation**: Without baselines/MM detection
4. **Integration testing**: With existing pipeline

### Phase 2B: Historical Context (Week 2-3)
1. **HistoricalBaselineManager**: 20-day baseline system
2. **Baseline database schema**: Efficient storage/retrieval
3. **Statistical analysis**: Z-scores, percentiles, anomaly detection
4. **Context integration**: Enhanced signal confidence

### Phase 2C: Market Making Detection (Week 3)
1. **MarketMakingDetector**: Pattern recognition system
2. **Straddle detection**: Call/put coordination analysis
3. **Volatility crush detection**: Price decline patterns
4. **False positive filtering**: Improved signal quality

### Phase 2D: Enhanced Confidence (Week 3)
1. **EnhancedConfidenceScorer**: Multi-factor scoring
2. **Risk-adjusted confidence**: Market making penalties
3. **Coordination bonuses**: Cross-strike validation
4. **Final signal classification**: Actionable recommendations

## Performance Targets

### Signal Quality Improvements
- **Accuracy**: >75% (vs 65% for v1.0)
- **False Positive Rate**: <30% (50% reduction via MM filtering)
- **Signal Confidence**: Statistical significance >0.8
- **Detection Latency**: <30 seconds from pressure event

### Technical Performance
- **Processing Latency**: <100ms per pressure event
- **Memory Usage**: <200MB for 6.5-hour trading day
- **Database Queries**: <10ms average response time
- **Baseline Updates**: <1 second daily routine

### Integration Requirements
- **Backward Compatibility**: v1.0 remains functional
- **Pipeline Integration**: Standard interface compliance
- **Configuration**: Seamless switching between versions
- **Monitoring**: Enhanced logging and metrics

## Success Metrics

### Quantitative Targets
- **Win Rate**: >70% on IFD v3.0 signals
- **Average Win/Loss**: >1.8 ratio
- **Sharpe Ratio**: >2.0 on signal-based strategy
- **Maximum Drawdown**: <5% on 30-day rolling basis

### Qualitative Improvements
- **Signal Clarity**: Clear institutional vs market making distinction
- **Actionable Insights**: Specific entry/exit recommendations
- **Risk Awareness**: Position sizing and risk assessment
- **Real-time Capability**: Live trading system integration

This architecture provides a robust foundation for institutional flow detection that leverages the real-time MBO streaming infrastructure while adding sophisticated analysis capabilities for enhanced signal quality and reduced false positives.