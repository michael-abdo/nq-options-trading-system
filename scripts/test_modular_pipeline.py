#!/usr/bin/env python3
"""
Test the modular pipeline without external dependencies
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plugins.data_sources.saved_data import SavedDataSource
from plugins.strategies.expected_value import ExpectedValueStrategy


def test_modular_pipeline():
    """Test the modular pipeline components directly"""
    print("="*80)
    print("MODULAR PIPELINE TEST")
    print("="*80)
    
    try:
        # 1. Test Data Source
        print("\n📊 Testing Data Source...")
        data_config = {
            "file_path": "data/api_responses/options_data_20250602_141553.json"
        }
        
        data_source = SavedDataSource(data_config)
        
        if not data_source.validate_connection():
            print("❌ Data source connection failed")
            return False
        
        print("✅ Data source connection validated")
        
        # 2. Fetch Data
        print("\n📡 Fetching data...")
        chain = data_source.fetch_data()
        
        quality = chain.data_quality_metrics
        print(f"✅ Data loaded: {quality['total_contracts']} contracts")
        print(f"   Volume coverage: {quality['volume_coverage']:.1%}")
        print(f"   OI coverage: {quality['oi_coverage']:.1%}")
        print(f"   Calls/Puts: {quality['call_count']}/{quality['put_count']}")
        
        # 3. Test Strategy
        print("\n🧮 Testing Strategy...")
        strategy_config = {
            "weights": {
                "oi_factor": 0.35,
                "vol_factor": 0.25,
                "pcr_factor": 0.25,
                "distance_factor": 0.15
            },
            "min_ev": 15,
            "min_probability": 0.60,
            "max_risk": 150,
            "min_risk_reward": 1.0
        }
        
        strategy = ExpectedValueStrategy(strategy_config)
        
        # Validate data requirements
        is_valid, errors = strategy.validate_data(chain)
        if not is_valid:
            print(f"⚠️ Data validation issues: {errors}")
        else:
            print("✅ Data meets strategy requirements")
        
        # 4. Run Analysis
        print("\n⚡ Running analysis...")
        result = strategy.analyze(chain)
        
        print(f"✅ Analysis complete!")
        print(f"   Strategy: {result.strategy_name}")
        print(f"   Signals: {len(result.signals)}")
        print(f"   Metrics: {len(result.metrics)}")
        print(f"   Warnings: {len(result.warnings)}")
        
        # 5. Display Results
        print("\n📋 RESULTS SUMMARY:")
        print("-" * 50)
        
        if result.signals:
            print(f"\n🎯 Top 3 Trading Opportunities:")
            for i, signal in enumerate(result.signals[:3], 1):
                direction = signal['direction'].upper()
                target = signal['target_price']
                stop = signal['stop_loss']
                ev = signal['expected_value']
                confidence = signal['confidence']
                rr = signal['risk_reward_ratio']
                
                print(f"{i}. {direction} NQ")
                print(f"   Target: ${target:,.0f}, Stop: ${stop:,.0f}")
                print(f"   EV: {ev:+.1f}, Confidence: {confidence:.1%}, R/R: {rr:.1f}")
        
        if result.metrics:
            print(f"\n📊 Key Metrics:")
            key_metrics = ['best_ev', 'best_probability', 'total_opportunities', 'pcr_volume', 'pcr_oi']
            for metric in key_metrics:
                if metric in result.metrics:
                    value = result.metrics[metric]
                    if 'probability' in metric or 'pcr' in metric:
                        print(f"   {metric}: {value:.1%}")
                    elif 'opportunities' in metric:
                        print(f"   {metric}: {int(value)}")
                    else:
                        print(f"   {metric}: {value:.2f}")
        
        if result.warnings:
            print(f"\n⚠️ Warnings:")
            for warning in result.warnings:
                print(f"   • {warning}")
        
        print("\n" + "="*80)
        print("✅ MODULAR PIPELINE TEST SUCCESSFUL!")
        print("="*80)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def demonstrate_modularity():
    """Demonstrate the modularity by running different strategy configurations"""
    print("\n" + "="*80)
    print("MODULARITY DEMONSTRATION - MULTIPLE STRATEGY CONFIGS")
    print("="*80)
    
    # Load data once
    data_source = SavedDataSource({
        "file_path": "data/api_responses/options_data_20250602_141553.json"
    })
    chain = data_source.fetch_data()
    
    # Define different strategy configurations
    strategy_configs = {
        "Conservative": {
            "weights": {"oi_factor": 0.40, "vol_factor": 0.30, "pcr_factor": 0.20, "distance_factor": 0.10},
            "min_ev": 25, "min_probability": 0.70, "max_risk": 100, "min_risk_reward": 1.5
        },
        "Balanced": {
            "weights": {"oi_factor": 0.35, "vol_factor": 0.25, "pcr_factor": 0.25, "distance_factor": 0.15},
            "min_ev": 15, "min_probability": 0.60, "max_risk": 150, "min_risk_reward": 1.0
        },
        "Aggressive": {
            "weights": {"oi_factor": 0.30, "vol_factor": 0.20, "pcr_factor": 0.30, "distance_factor": 0.20},
            "min_ev": 10, "min_probability": 0.55, "max_risk": 200, "min_risk_reward": 0.8
        }
    }
    
    results = {}
    
    # Run each strategy configuration
    for name, config in strategy_configs.items():
        print(f"\n🧮 Running {name} Strategy...")
        
        strategy = ExpectedValueStrategy(config)
        result = strategy.analyze(chain)
        results[name] = result
        
        print(f"   Signals: {len(result.signals)}")
        if result.signals:
            top_signal = result.signals[0]
            print(f"   Best EV: {top_signal['expected_value']:+.1f}")
            print(f"   Best Confidence: {top_signal['confidence']:.1%}")
    
    # Compare results
    print(f"\n📊 STRATEGY COMPARISON:")
    print("-" * 60)
    print(f"{'Strategy':<12} {'Signals':<8} {'Best EV':<10} {'Best Conf':<10}")
    print("-" * 60)
    
    for name, result in results.items():
        signals = len(result.signals)
        best_ev = result.signals[0]['expected_value'] if result.signals else 0
        best_conf = result.signals[0]['confidence'] if result.signals else 0
        
        print(f"{name:<12} {signals:<8} {best_ev:<10.1f} {best_conf:<10.1%}")
    
    print("\n✅ Modularity demonstration complete!")


if __name__ == "__main__":
    success = test_modular_pipeline()
    
    if success:
        demonstrate_modularity()
    
    exit(0 if success else 1)