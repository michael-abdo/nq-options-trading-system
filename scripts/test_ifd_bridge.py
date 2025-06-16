#!/usr/bin/env python3
"""
Test script for IFD Chart Bridge component

Tests signal retrieval, time alignment, aggregation logic, and error handling.
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List
import logging

# Add parent directory for imports  
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from scripts.ifd_chart_bridge import IFDChartBridge, create_ifd_chart_bridge, IFDAggregatedSignal

# Import IFD components if available
try:
    from tasks.options_trading_system.analysis_engine.institutional_flow_v3.solution import InstitutionalSignalV3
    IFD_AVAILABLE = True
except ImportError:
    # Create mock for testing
    from dataclasses import dataclass
    
    @dataclass
    class InstitutionalSignalV3:
        strike: float
        option_type: str
        timestamp: datetime
        pressure_ratio: float = 3.0
        bid_volume: int = 100
        ask_volume: int = 300
        dominant_side: str = 'BUY'
        pressure_confidence: float = 0.85
        baseline_pressure_ratio: float = 1.5
        pressure_zscore: float = 2.8
        percentile_rank: float = 95.0
        anomaly_detected: bool = True
        market_making_probability: float = 0.15
        straddle_coordination: bool = False
        volatility_crush_detected: bool = False
        raw_confidence: float = 0.8
        baseline_confidence: float = 0.9
        market_making_penalty: float = 0.1
        coordination_bonus: float = 0.0
        final_confidence: float = 0.85
        signal_strength: str = 'VERY_HIGH'
        institutional_probability: float = 0.88
        recommended_action: str = 'BUY'
        risk_score: float = 0.3
        position_size_multiplier: float = 1.5
        max_position_risk: float = 0.05
        
        def to_dict(self):
            return {'test': 'signal'}
    
    IFD_AVAILABLE = False

logger = logging.getLogger(__name__)

def create_test_signal(timestamp: datetime, confidence: float = 0.85, 
                      strike: float = 21900.0, action: str = 'BUY') -> InstitutionalSignalV3:
    """Create a test IFD signal with specified parameters"""
    if IFD_AVAILABLE:
        # Create complete signal with all required fields
        return InstitutionalSignalV3(
            strike=strike,
            option_type='C',
            timestamp=timestamp,
            pressure_ratio=3.0,
            bid_volume=100,
            ask_volume=300,
            dominant_side='BUY',
            pressure_confidence=0.85,
            baseline_pressure_ratio=1.5,
            pressure_zscore=2.8,
            percentile_rank=95.0,
            anomaly_detected=True,
            market_making_probability=0.15,
            straddle_coordination=False,
            volatility_crush_detected=False,
            raw_confidence=0.8,
            baseline_confidence=0.9,
            market_making_penalty=0.1,
            coordination_bonus=0.0,
            final_confidence=confidence,
            signal_strength='VERY_HIGH' if confidence >= 0.8 else 'HIGH',
            institutional_probability=0.88,
            recommended_action=action,
            risk_score=0.3,
            position_size_multiplier=1.5,
            max_position_risk=0.05
        )
    else:
        # Use mock version
        return InstitutionalSignalV3(
            strike=strike,
            option_type='C',
            timestamp=timestamp,
            final_confidence=confidence,
            signal_strength='VERY_HIGH' if confidence >= 0.8 else 'HIGH',
            recommended_action=action
        )

def test_signal_aggregation():
    """Test signal aggregation within 5-minute windows"""
    print("\n=== Testing Signal Aggregation ===")
    
    # Create bridge with test config
    config = {
        'aggregation': {
            'strategy': 'highest_confidence',
            'min_signal_confidence': 0.6,
            'max_signals_per_window': 10
        },
        'cache': {
            'max_windows': 100,
            'cleanup_interval_hours': 4
        }
    }
    
    bridge = create_ifd_chart_bridge(config)
    
    # Create signals within same 5-minute window
    base_time = datetime(2025, 6, 16, 14, 32, 15, tzinfo=timezone.utc)  # 14:32:15
    
    signals = [
        create_test_signal(base_time, confidence=0.75, action='BUY'),
        create_test_signal(base_time + timedelta(minutes=1), confidence=0.85, action='BUY'),
        create_test_signal(base_time + timedelta(minutes=2), confidence=0.65, action='MONITOR'),
    ]
    
    # Add signals to bridge
    completed_windows = []
    for signal in signals:
        result = bridge.add_signal(signal)
        if result:
            completed_windows.append(result)
    
    print(f"Added {len(signals)} signals to bridge")
    print(f"Completed windows: {len(completed_windows)}")
    
    # Force completion of current window by adding signal in next window
    next_window_signal = create_test_signal(
        base_time + timedelta(minutes=5), confidence=0.90, action='STRONG_BUY'
    )
    
    completed_window = bridge.add_signal(next_window_signal)
    if completed_window:
        completed_windows.append(completed_window)
        
        print(f"\nCompleted Window Analysis:")
        print(f"  Window timestamp: {completed_window.window_timestamp}")
        print(f"  Signal count: {completed_window.signal_count}")
        print(f"  Max confidence: {completed_window.max_confidence:.3f}")
        print(f"  Avg confidence: {completed_window.avg_confidence:.3f}")
        print(f"  Dominant action: {completed_window.dominant_action}")
        print(f"  Window strength: {completed_window.window_strength}")
        print(f"  Primary signal confidence: {completed_window.primary_signal.final_confidence:.3f}")
    
    # Test time range queries
    print(f"\n=== Testing Time Range Queries ===")
    
    start_time = base_time - timedelta(minutes=10)
    end_time = base_time + timedelta(minutes=10)
    
    signals_in_range = bridge.get_ifd_signals_for_chart(start_time, end_time)
    print(f"Signals in range {start_time} to {end_time}: {len(signals_in_range)}")
    
    for signal in signals_in_range:
        print(f"  {signal.window_timestamp}: {signal.signal_count} signals, "
              f"confidence={signal.max_confidence:.3f}")
    
    return bridge

def test_time_alignment():
    """Test 5-minute boundary alignment"""
    print("\n=== Testing Time Alignment ===")
    
    bridge = create_ifd_chart_bridge()
    
    # Test various timestamps and their 5-minute boundaries
    test_times = [
        datetime(2025, 6, 16, 14, 32, 15, tzinfo=timezone.utc),  # Should align to 14:30
        datetime(2025, 6, 16, 14, 34, 45, tzinfo=timezone.utc),  # Should align to 14:30
        datetime(2025, 6, 16, 14, 35, 0, tzinfo=timezone.utc),   # Should align to 14:35
        datetime(2025, 6, 16, 14, 37, 30, tzinfo=timezone.utc),  # Should align to 14:35
    ]
    
    for test_time in test_times:
        boundary = bridge._get_5min_boundary(test_time)
        print(f"  {test_time.strftime('%H:%M:%S')} -> {boundary.strftime('%H:%M:%S')}")
        
        # Verify boundary is correct
        assert boundary.minute % 5 == 0, f"Invalid boundary: {boundary}"
        assert boundary.second == 0, f"Boundary should have 0 seconds: {boundary}"
        assert boundary <= test_time, f"Boundary should be <= original time"

def test_error_handling():
    """Test error handling and fallback modes"""
    print("\n=== Testing Error Handling ===")
    
    bridge = create_ifd_chart_bridge()
    
    # Test None signal
    result = bridge.add_signal(None)
    assert result is None, "Should handle None signal gracefully"
    
    # Test signal with missing attributes
    class BadSignal:
        pass
    
    bad_signal = BadSignal()
    result = bridge.add_signal(bad_signal)
    assert result is None, "Should handle malformed signal gracefully"
    
    # Test signal with None timestamp
    signal_with_none_timestamp = create_test_signal(
        datetime.now(timezone.utc), confidence=0.8
    )
    signal_with_none_timestamp.timestamp = None
    
    result = bridge.add_signal(signal_with_none_timestamp)
    # Should not crash - timestamp should be auto-assigned
    
    # Test health status
    health = bridge.get_health_status()
    print(f"Bridge health status: {health['overall_status']}")
    
    # Test emergency reset
    reset_success = bridge.reset_bridge()
    assert reset_success, "Bridge reset should succeed"
    
    stats_after_reset = bridge.get_bridge_statistics()
    assert stats_after_reset['total_signals_processed'] == 0, "Stats should be reset"
    
    print("  All error handling tests passed!")

def test_performance():
    """Test bridge performance with multiple signals"""
    print("\n=== Testing Performance ===")
    
    bridge = create_ifd_chart_bridge()
    
    # Create many signals across multiple windows
    import time
    start_time = time.time()
    
    base_time = datetime.now(timezone.utc)
    num_signals = 100
    
    for i in range(num_signals):
        signal_time = base_time + timedelta(seconds=i * 30)  # Every 30 seconds
        signal = create_test_signal(signal_time, confidence=0.7 + (i % 3) * 0.1)
        bridge.add_signal(signal)
    
    end_time = time.time()
    processing_time = end_time - start_time
    
    stats = bridge.get_bridge_statistics()
    
    print(f"  Processed {num_signals} signals in {processing_time:.3f} seconds")
    print(f"  Rate: {num_signals/processing_time:.1f} signals/second") 
    print(f"  Windows created: {stats['total_windows_created']}")
    print(f"  Memory usage: {stats['memory_usage']}")
    
    # Test query performance
    start_query_time = time.time()
    signals_in_range = bridge.get_ifd_signals_for_chart(
        base_time - timedelta(hours=1),
        base_time + timedelta(hours=1)
    )
    query_time = time.time() - start_query_time
    
    print(f"  Query returned {len(signals_in_range)} signals in {query_time:.3f} seconds")

def main():
    """Run all bridge tests"""
    print("=== IFD Chart Bridge Comprehensive Test ===")
    
    # Test basic functionality
    bridge = test_signal_aggregation()
    
    # Test time alignment
    test_time_alignment()
    
    # Test error handling
    test_error_handling()
    
    # Test performance
    test_performance()
    
    print("\n=== All Tests Completed Successfully! ===")
    
    # Final bridge status
    final_stats = bridge.get_bridge_statistics()
    print(f"\nFinal Bridge Statistics:")
    for key, value in final_stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    main()