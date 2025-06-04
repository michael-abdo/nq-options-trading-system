# Modular Trading Analysis System Architecture

## Current Problems
1. **Tight Coupling**: Data retrieval and analysis are mixed in single scripts
2. **Limited Extensibility**: Hard to add new data sources or strategies
3. **Code Duplication**: Similar logic repeated across scripts
4. **No Standard Format**: Each data source uses different structures

## Proposed Architecture

### Core Principles
1. **Separation of Concerns**: Data ingestion ↔ Analysis ↔ Output
2. **Plugin Architecture**: Pluggable data sources and analysis strategies
3. **Common Data Schema**: Standardized internal data format
4. **Configuration-Driven**: Easy addition of new sources/strategies
5. **Pipeline Pattern**: Data flows through defined stages

### Directory Structure
```
EOD/
├── core/                              # Core framework
│   ├── __init__.py
│   ├── data_models.py                 # Common data schemas
│   ├── pipeline.py                    # Orchestration engine
│   ├── interfaces.py                  # Abstract base classes
│   └── config_manager.py              # Configuration management
├── plugins/                           # Plugin implementations
│   ├── data_sources/                  # Data ingestion plugins
│   │   ├── __init__.py
│   │   ├── base.py                    # Base data source class
│   │   ├── barchart_api.py           # Barchart API source
│   │   ├── tradovate_api.py          # Tradovate API source
│   │   ├── csv_file.py               # CSV file source
│   │   └── saved_data.py             # Saved JSON source
│   ├── strategies/                    # Analysis strategy plugins
│   │   ├── __init__.py
│   │   ├── base.py                   # Base strategy class
│   │   ├── expected_value.py         # Current EV strategy
│   │   ├── momentum_analysis.py      # Momentum strategy
│   │   ├── volatility_analysis.py   # Volatility strategy
│   │   ├── gamma_exposure.py         # Gamma exposure strategy
│   │   └── flow_analysis.py          # Options flow strategy
│   └── outputs/                       # Output formatters
│       ├── __init__.py
│       ├── base.py                   # Base output class
│       ├── json_output.py            # JSON export
│       ├── csv_output.py             # CSV export
│       └── report_output.py          # Formatted reports
├── config/                           # Configuration files
│   ├── data_sources.yaml            # Data source configurations
│   ├── strategies.yaml               # Strategy configurations
│   └── pipeline.yaml                # Pipeline definitions
├── data/                            # Standardized data storage
│   ├── raw/                         # Raw data from sources
│   ├── normalized/                  # Standardized format
│   └── results/                     # Analysis results
├── scripts/                         # Execution scripts
│   ├── run_pipeline.py              # Main pipeline runner
│   ├── run_single_strategy.py       # Single strategy runner
│   └── data_quality_check.py        # Data validation
└── tests/                           # Comprehensive testing
    ├── test_data_sources.py
    ├── test_strategies.py
    └── test_pipeline.py
```

## Data Flow Pipeline

### Stage 1: Data Ingestion
```
Data Source → Raw Data → Validation → Normalization → Standard Format
```

### Stage 2: Analysis Engine
```
Standard Format → Strategy Selection → Analysis Execution → Results
```

### Stage 3: Output Generation  
```
Results → Output Formatter → Reports/Exports
```

## Common Data Schema

### StandardizedOptionsData
```python
@dataclass
class OptionsContract:
    symbol: str
    strike: float
    expiration: datetime
    option_type: str  # 'call' or 'put'
    volume: Optional[int]
    open_interest: Optional[int]
    bid: Optional[float]
    ask: Optional[float]
    last_price: Optional[float]
    underlying_price: float
    timestamp: datetime

@dataclass
class OptionsChain:
    underlying_symbol: str
    underlying_price: float
    timestamp: datetime
    contracts: List[OptionsContract]
    metadata: Dict[str, Any]
```

## Plugin Interfaces

### Data Source Interface
```python
class DataSourceInterface(ABC):
    @abstractmethod
    def fetch_data(self) -> OptionsChain:
        """Fetch raw data and return standardized format"""
        pass
    
    @abstractmethod
    def validate_data(self, data: OptionsChain) -> bool:
        """Validate data quality"""
        pass
```

### Strategy Interface
```python
class StrategyInterface(ABC):
    @abstractmethod
    def analyze(self, data: OptionsChain) -> AnalysisResult:
        """Perform analysis and return results"""
        pass
    
    @abstractmethod
    def get_requirements(self) -> DataRequirements:
        """Return data requirements for this strategy"""
        pass
```

## Configuration Examples

### data_sources.yaml
```yaml
sources:
  barchart:
    class: plugins.data_sources.barchart_api.BarchartAPI
    config:
      endpoint: "https://www.barchart.com/proxies/core-api/v1/quotes/get"
      symbol: "MC6M25"
  
  tradovate:
    class: plugins.data_sources.tradovate_api.TradovateAPI
    config:
      cid: "6540"
      secret: "f7a2b8f5-8348-424f-8ffa-047ab7502b7c"
      demo: true
  
  saved_data:
    class: plugins.data_sources.saved_data.SavedDataSource
    config:
      file_path: "data/api_responses/options_data_20250602_141553.json"
```

### strategies.yaml
```yaml
strategies:
  expected_value:
    class: plugins.strategies.expected_value.ExpectedValueStrategy
    config:
      weights:
        oi_factor: 0.35
        vol_factor: 0.25
        pcr_factor: 0.25
        distance_factor: 0.15
      min_ev: 15
      min_probability: 0.60
  
  momentum_analysis:
    class: plugins.strategies.momentum_analysis.MomentumStrategy
    config:
      lookback_period: 20
      momentum_threshold: 0.1
  
  gamma_exposure:
    class: plugins.strategies.gamma_exposure.GammaExposureStrategy
    config:
      strike_range: 0.05
      time_decay_factor: 0.8
```

### pipeline.yaml
```yaml
pipelines:
  full_analysis:
    data_source: "barchart"
    strategies:
      - "expected_value"
      - "momentum_analysis"
      - "gamma_exposure"
    outputs:
      - "json_output"
      - "report_output"
  
  ev_only:
    data_source: "saved_data"
    strategies:
      - "expected_value"
    outputs:
      - "report_output"
```

## Benefits of This Architecture

1. **Modularity**: Add new data sources or strategies without touching core code
2. **Testability**: Each component can be tested independently
3. **Reusability**: Same data can feed multiple analysis strategies
4. **Maintainability**: Clear separation of concerns
5. **Extensibility**: Easy to add new features via plugins
6. **Configuration-Driven**: No code changes for new combinations

## Implementation Strategy

### Phase 1: Core Framework
1. Implement data models and interfaces
2. Create pipeline orchestration engine
3. Build configuration management

### Phase 2: Migration
1. Convert existing scripts to plugins
2. Implement data source plugins
3. Convert EV analysis to strategy plugin

### Phase 3: Extension
1. Add new analysis strategies
2. Implement additional data sources
3. Enhanced output formatters

This architecture will transform your system from a collection of scripts into a powerful, extensible trading analysis platform.