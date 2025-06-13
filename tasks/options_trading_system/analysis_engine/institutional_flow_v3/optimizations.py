"""
IFD v3.0 Performance Optimizations

Optimizations to reduce latency for processing 100+ strikes:
- Batch database operations
- Parallel processing
- Enhanced caching
- Pre-calculation of baselines
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import threading

from .solution import (
    PressureMetrics, BaselineContext, InstitutionalSignalV3,
    PressureAnalyzer, MarketMakingDetector,
    ConfidenceScorer, IFDv3Analyzer, create_ifd_v3_analyzer,
    HistoricalBaselineManager
)

logger = logging.getLogger(__name__)


class OptimizedBaselineManager(HistoricalBaselineManager):
    """
    Optimized baseline manager with batch operations and enhanced caching
    """

    def __init__(self, config: Dict[str, Any]):
        # Extract db_path from config or use default
        db_path = config.get('db_path', 'outputs/ifd_v3_baselines.db')
        lookback_days = config.get('lookback_days', 20)
        super().__init__(db_path, lookback_days)
        self._cache_lock = threading.Lock()
        self._batch_cache = {}

    def batch_get_baseline_contexts(self, strikes_and_types: List[Tuple[float, str]]) -> Dict[str, BaselineContext]:
        """
        Get baseline contexts for multiple strikes in a single batch

        Args:
            strikes_and_types: List of (strike, option_type) tuples

        Returns:
            Dictionary mapping "strike_type" to BaselineContext
        """
        results = {}
        uncached_keys = []

        # Check cache first
        with self._cache_lock:
            for strike, option_type in strikes_and_types:
                cache_key = f"{strike}_{option_type}"

                if cache_key in self.baseline_cache:
                    cached_data, cache_time = self.baseline_cache[cache_key]
                    if datetime.now() - cache_time < self.cache_expiry:
                        results[cache_key] = cached_data
                        continue

                uncached_keys.append((strike, option_type))

        # Batch calculate uncached baselines
        if uncached_keys:
            batch_baselines = self._batch_calculate_baseline_stats(uncached_keys)

            # Update cache and results
            with self._cache_lock:
                for (strike, option_type), baseline in batch_baselines.items():
                    cache_key = f"{strike}_{option_type}"
                    self.baseline_cache[cache_key] = (baseline, datetime.now())
                    results[cache_key] = baseline

        return results

    def _batch_calculate_baseline_stats(self, strikes_and_types: List[Tuple[float, str]]) -> Dict[Tuple[float, str], BaselineContext]:
        """
        Calculate baseline statistics for multiple strikes in a single database query
        """
        results = {}
        cutoff_date = (datetime.now() - timedelta(days=self.lookback_days)).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            # Build query for all strikes
            placeholders = []
            params = []

            for strike, option_type in strikes_and_types:
                placeholders.append("(strike = ? AND option_type = ?)")
                params.extend([strike, option_type])

            where_clause = " OR ".join(placeholders)
            params.append(cutoff_date)

            query = f"""
                SELECT strike, option_type, pressure_ratio, volume_total, confidence
                FROM historical_pressure
                WHERE ({where_clause}) AND date >= ?
                ORDER BY strike, option_type, date
            """

            cursor = conn.cursor()
            cursor.execute(query, params)

            # Group results by strike/type
            data_by_key = defaultdict(list)
            for row in cursor.fetchall():
                strike, option_type, pressure_ratio, volume_total, confidence = row
                key = (strike, option_type)
                data_by_key[key].append({
                    'pressure_ratio': pressure_ratio,
                    'volume_total': volume_total,
                    'confidence': confidence
                })

            # Calculate baseline for each strike/type
            for (strike, option_type), data in data_by_key.items():
                baseline = self._calculate_baseline_from_data(data)
                results[(strike, option_type)] = baseline

            # Handle strikes with no historical data
            for strike, option_type in strikes_and_types:
                if (strike, option_type) not in results:
                    results[(strike, option_type)] = self._create_default_baseline()

        return results

    def _calculate_baseline_from_data(self, data: List[Dict[str, Any]]) -> BaselineContext:
        """
        Calculate baseline context from historical data points
        
        Args:
            data: List of historical data points with pressure_ratio, volume_total, confidence
            
        Returns:
            BaselineContext object with statistical measures
        """
        if not data:
            return self._create_default_baseline()
        
        # Extract pressure ratios for statistical calculation
        pressure_ratios = [d['pressure_ratio'] for d in data]
        volume_totals = [d['volume_total'] for d in data]
        confidences = [d['confidence'] for d in data]
        
        # Calculate statistics
        mean_pressure = sum(pressure_ratios) / len(pressure_ratios)
        squared_diffs = [(p - mean_pressure) ** 2 for p in pressure_ratios]
        std_pressure = (sum(squared_diffs) / len(squared_diffs)) ** 0.5
        
        mean_volume = sum(volume_totals) / len(volume_totals)
        mean_confidence = sum(confidences) / len(confidences)
        
        # Create baseline context (using dataclass fields)
        from .solution import BaselineContext
        return BaselineContext(
            strike=0.0,  # Will be set by caller
            option_type="call",  # Will be set by caller
            lookback_days=self.lookback_days,
            mean_pressure_ratio=mean_pressure,
            pressure_std=std_pressure,
            pressure_percentiles={50: mean_pressure, 95: mean_pressure + 2 * std_pressure},
            current_zscore=0.0,  # Will be calculated later
            percentile_rank=0.0,  # Will be calculated later
            anomaly_detected=False,  # Will be calculated later
            data_quality=min(len(data) / 20.0, 1.0),  # 20 days for full quality
            confidence=mean_confidence
        )
    
    def _create_default_baseline(self) -> BaselineContext:
        """
        Create a default baseline context when no historical data is available
        
        Returns:
            BaselineContext with default statistical measures
        """
        from .solution import BaselineContext
        return BaselineContext(
            strike=0.0,  # Will be set by caller
            option_type="call",  # Will be set by caller
            lookback_days=self.lookback_days,
            mean_pressure_ratio=1.0,
            pressure_std=0.2,
            pressure_percentiles={50: 1.0, 95: 1.5},
            current_zscore=0.0,  # Will be calculated later
            percentile_rank=0.0,  # Will be calculated later
            anomaly_detected=False,  # Will be calculated later
            data_quality=0.1,  # Low quality due to no historical data
            confidence=0.5
        )

    def batch_update_historical_data(self, pressure_metrics_list: List[PressureMetrics]):
        """
        Update historical data for multiple pressure metrics in a single transaction
        """
        if not pressure_metrics_list:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            data_to_insert = []
            for pm in pressure_metrics_list:
                date_str = pm.time_window.strftime('%Y-%m-%d')
                total_volume = pm.bid_volume + pm.ask_volume

                data_to_insert.append((
                    pm.strike,
                    pm.option_type,
                    date_str,
                    pm.pressure_ratio,
                    total_volume,
                    pm.confidence,
                    datetime.now().isoformat()
                ))

            cursor.executemany("""
                INSERT OR REPLACE INTO historical_pressure
                (strike, option_type, date, pressure_ratio, volume_total, confidence, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)

            conn.commit()


class OptimizedIFDv3Analyzer(IFDv3Analyzer):
    """
    Optimized IFD v3 analyzer with parallel processing capabilities
    """

    def __init__(self, config: Dict[str, Any]):
        # Initialize base components
        self.config = config
        # Pass the entire config to baseline manager so it can extract db_path
        baseline_config = config.copy()
        if 'baseline_config' in config:
            baseline_config.update(config['baseline_config'])
        self.baseline_manager = OptimizedBaselineManager(baseline_config)
        self.pressure_analyzer = PressureAnalyzer(config.get('pressure_thresholds', {}))
        self.market_making_detector = MarketMakingDetector(config.get('market_making_config', {}))
        self.confidence_scorer = ConfidenceScorer(config.get('confidence_thresholds', {}))

        # Threading configuration
        self.max_workers = config.get('max_workers', 4)

        # Initialize tracking
        self.recent_signals = []
        self.total_signals = 0
        self.total_events = 0

    def batch_analyze_pressure_events(self, pressure_metrics_list: List[PressureMetrics]) -> List[Optional[InstitutionalSignalV3]]:
        """
        Analyze multiple pressure events with optimized batch processing

        Args:
            pressure_metrics_list: List of pressure metrics to analyze

        Returns:
            List of signals (None for metrics that don't generate signals)
        """
        if not pressure_metrics_list:
            return []

        # Step 1: Batch update historical data
        self.baseline_manager.batch_update_historical_data(pressure_metrics_list)

        # Step 2: Batch get baseline contexts
        strikes_and_types = [(pm.strike, pm.option_type) for pm in pressure_metrics_list]
        baseline_contexts = self.baseline_manager.batch_get_baseline_contexts(strikes_and_types)

        # Step 3: Process each metric in parallel
        signals = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit analysis tasks
            future_to_metric = {}

            for pm in pressure_metrics_list:
                cache_key = f"{pm.strike}_{pm.option_type}"
                baseline_context = baseline_contexts.get(cache_key)

                if baseline_context:
                    future = executor.submit(
                        self._analyze_single_metric,
                        pm,
                        baseline_context
                    )
                    future_to_metric[future] = pm

            # Collect results in order using index-based mapping
            metric_to_signal = {}
            for future in as_completed(future_to_metric):
                pm = future_to_metric[future]
                try:
                    signal = future.result()
                    # Use a hashable key instead of the object itself
                    cache_key = f"{pm.strike}_{pm.option_type}_{id(pm)}"
                    metric_to_signal[cache_key] = signal
                except Exception as e:
                    logger.error(f"Error analyzing metric {pm.strike}{pm.option_type}: {e}")
                    cache_key = f"{pm.strike}_{pm.option_type}_{id(pm)}"
                    metric_to_signal[cache_key] = None

            # Return signals in original order
            for pm in pressure_metrics_list:
                cache_key = f"{pm.strike}_{pm.option_type}_{id(pm)}"
                signals.append(metric_to_signal.get(cache_key))

        # Update tracking
        valid_signals = [s for s in signals if s is not None]
        self.recent_signals.extend(valid_signals)
        self.total_signals += len(valid_signals)
        self.total_events += len(pressure_metrics_list)

        return signals

    def _analyze_single_metric(self,
                             pressure_metrics: PressureMetrics,
                             baseline_context: BaselineContext) -> Optional[InstitutionalSignalV3]:
        """
        Analyze a single metric with pre-fetched baseline context
        """
        try:
            # Calculate pressure context against baseline
            baseline_context = self.baseline_manager.calculate_pressure_context(
                pressure_metrics.pressure_ratio, baseline_context
            )

            # Analyze pressure patterns
            pressure_analysis = self.pressure_analyzer.analyze_pressure_signal(pressure_metrics)

            # Detect market making patterns
            market_making_analysis = self.market_making_detector.detect_market_making_patterns(pressure_metrics)

            # Calculate enhanced confidence
            raw_conf, baseline_conf, mm_penalty, coord_bonus, final_conf = self.confidence_scorer.calculate_confidence(
                pressure_analysis, baseline_context, market_making_analysis
            )

            # Check if signal meets minimum criteria
            min_confidence = self.config.get('min_final_confidence', 0.7)
            if final_conf < min_confidence:
                return None

            # Generate institutional signal
            signal = self._create_institutional_signal(
                pressure_metrics, baseline_context, market_making_analysis,
                raw_conf, baseline_conf, mm_penalty, coord_bonus, final_conf
            )

            return signal

        except Exception as e:
            logger.error(f"Error analyzing single metric: {e}")
            return None


def run_optimized_ifd_v3_analysis(pressure_data: List[PressureMetrics], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run optimized IFD v3.0 analysis with batch processing and parallelization

    Args:
        pressure_data: List of pressure metrics from MBO streaming
        config: Analysis configuration

    Returns:
        Analysis results with institutional signals
    """
    try:
        # Add optimization config if not present
        if 'max_workers' not in config:
            config['max_workers'] = min(4, max(1, len(pressure_data) // 25))  # 1 worker per 25 metrics, minimum 1

        # Initialize optimized analyzer
        analyzer = OptimizedIFDv3Analyzer(config)

        # Batch analyze all pressure events
        signals = analyzer.batch_analyze_pressure_events(pressure_data)

        # Filter out None values
        valid_signals = [s for s in signals if s is not None]

        # Get analysis summary
        summary = analyzer.get_analysis_summary()

        return {
            'status': 'success',
            'signals': [signal.to_dict() for signal in valid_signals],
            'summary': summary,
            'total_events_processed': len(pressure_data),
            'signals_generated': len(valid_signals),
            'signal_rate': len(valid_signals) / max(len(pressure_data), 1)
        }

    except Exception as e:
        logger.error(f"Optimized IFD v3.0 analysis failed: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'signals': [],
            'summary': {},
            'total_events_processed': 0,
            'signals_generated': 0,
            'signal_rate': 0.0
        }
