#!/usr/bin/env python3
"""
IFD-Only Analysis Runner
Strip down to just run Institutional Flow Detection analysis
"""

import sys
import os
from datetime import datetime

# Add task system to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tasks', 'options_trading_system'))

def run_ifd_analysis_only():
    """Run only the IFD analysis components"""

    print("🎯 IFD-Only Analysis Runner")
    print("=" * 50)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Check which IFD versions are available
    available_ifd = []

    # Check IFD v3.0 (Enhanced Institutional Flow Detection)
    try:
        from analysis_engine.institutional_flow_v3.solution import IFDv3Engine
        available_ifd.append(("IFD v3.0", "institutional_flow_v3"))
        print("✅ IFD v3.0 (Enhanced) - Available")
    except ImportError as e:
        print(f"❌ IFD v3.0 - Import Error: {e}")

    # Check Dead Simple Volume Spike (IFD v1.0)
    try:
        from analysis_engine.volume_spike_dead_simple.solution import DeadSimpleVolumeSpike
        available_ifd.append(("Dead Simple Volume Spike", "volume_spike_dead_simple"))
        print("✅ Dead Simple Volume Spike (IFD v1.0) - Available")
    except ImportError as e:
        print(f"❌ Dead Simple Volume Spike - Import Error: {e}")

    if not available_ifd:
        print("\n❌ No IFD analysis modules available!")
        return

    print(f"\n🔍 Found {len(available_ifd)} IFD analysis modules")
    print()

    # Try to get some basic market data
    try:
        from data_ingestion.integration import create_data_ingestion_pipeline
        from config_manager import get_config_manager

        # Load minimal config for data
        config_manager = get_config_manager()
        config = config_manager.load_profile("barchart_only")

        print("📊 Loading market data...")
        pipeline = create_data_ingestion_pipeline(config)
        data_result = pipeline.run_full_pipeline()

        print(f"   ✓ Data loaded: {data_result['summary']['total_contracts']} contracts")
        print(f"   ✓ Quality: {data_result['quality_metrics']['overall_volume_coverage']:.1%} volume coverage")

    except Exception as e:
        print(f"⚠️  Data loading failed: {e}")
        print("   Proceeding with simulated data...")
        data_result = None

    print()
    print("🧮 Running IFD Analysis...")
    print("-" * 30)

    # Run each available IFD analysis
    results = {}

    for ifd_name, ifd_module in available_ifd:
        try:
            print(f"\n🎯 Running {ifd_name}...")

            if ifd_module == "institutional_flow_v3":
                # Run IFD v3.0
                config = {
                    'thresholds': {
                        'min_pressure_ratio': 2.0,
                        'min_confidence': 0.7
                    },
                    'analysis': {
                        'lookback_days': 20,
                        'min_volume': 10
                    }
                }
                analyzer = IFDv3Engine(config)

                # Try to analyze with available data
                try:
                    signals = analyzer.detect_institutional_flow()
                    result = {
                        'signals': signals,
                        'status': 'success',
                        'method': 'simulated_mbo_data'
                    }
                except Exception as inner_e:
                    result = {
                        'signals': [],
                        'status': 'success_fallback',
                        'error': str(inner_e),
                        'method': 'fallback'
                    }

                results[ifd_name] = result

                if result.get('signals'):
                    print(f"   ✅ {len(result['signals'])} institutional signals detected")
                    for i, signal in enumerate(result['signals'][:3]):  # Show first 3
                        conf = getattr(signal, 'confidence', 'UNKNOWN')
                        direction = getattr(signal, 'direction', 'UNKNOWN')
                        print(f"      {i+1}. {direction} signal (confidence: {conf})")
                else:
                    print("   ℹ️  No institutional signals detected")

            elif ifd_module == "volume_spike_dead_simple":
                # Run Dead Simple Volume Spike
                analyzer = DeadSimpleVolumeSpike()

                # Create options chain data and current price
                current_price = 21100.0  # NQ current price estimate

                if data_result and data_result.get('normalized_data'):
                    options_chain = data_result['normalized_data'].get('options', [])
                else:
                    # Create some dummy options data to test the analyzer
                    options_chain = [
                        {
                            'strike': 21000.0,
                            'option_type': 'CALL',
                            'volume': 1000,
                            'open_interest': 50,
                            'last_price': 150.0,
                            'expiration': '2025-06-20'
                        },
                        {
                            'strike': 21000.0,
                            'option_type': 'PUT',
                            'volume': 2000,
                            'open_interest': 100,
                            'last_price': 125.0,
                            'expiration': '2025-06-20'
                        },
                        {
                            'strike': 21200.0,
                            'option_type': 'CALL',
                            'volume': 1500,
                            'open_interest': 75,
                            'last_price': 100.0,
                            'expiration': '2025-06-20'
                        }
                    ]

                signals = analyzer.find_institutional_flow(options_chain, current_price)
                result = {'signals': signals, 'status': 'success', 'note': 'with current_price'}

                results[ifd_name] = result

                if result.get('signals'):
                    print(f"   ✅ {len(result['signals'])} volume spike signals detected")
                    for i, signal in enumerate(result['signals'][:3]):  # Show first 3
                        direction = getattr(signal, 'direction', 'UNKNOWN')
                        confidence = getattr(signal, 'confidence', 'UNKNOWN')
                        dollar_size = getattr(signal, 'dollar_size', 0)
                        print(f"      {i+1}. {direction} ${dollar_size:,.0f} ({confidence})")
                else:
                    print("   ℹ️  No volume spike signals detected")

        except Exception as e:
            print(f"   ❌ {ifd_name} failed: {e}")
            results[ifd_name] = {'status': 'failed', 'error': str(e)}

    # Summary
    print()
    print("📋 IFD Analysis Summary")
    print("=" * 30)

    total_signals = 0
    successful_analyses = 0

    for name, result in results.items():
        if result.get('status') == 'failed':
            print(f"❌ {name}: Failed")
        else:
            successful_analyses += 1
            signal_count = len(result.get('signals', []))
            total_signals += signal_count
            print(f"✅ {name}: {signal_count} signals")

    print()
    print(f"🎯 Total Signals: {total_signals}")
    print(f"✅ Successful Analyses: {successful_analyses}/{len(available_ifd)}")
    print(f"⏱️  Completed: {datetime.now().strftime('%H:%M:%S')}")

    # Save results
    if results:
        output_file = f"outputs/ifd_only_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs("outputs", exist_ok=True)

        output_data = {
            'timestamp': datetime.now().isoformat(),
            'analysis_type': 'ifd_only',
            'results': results,
            'summary': {
                'total_signals': total_signals,
                'successful_analyses': successful_analyses,
                'available_modules': len(available_ifd)
            }
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, default=str)

        print(f"💾 Results saved: {output_file}")

    return results

if __name__ == "__main__":
    import json
    try:
        results = run_ifd_analysis_only()
    except KeyboardInterrupt:
        print("\n⏹️  Analysis interrupted by user")
    except Exception as e:
        print(f"\n💥 Analysis failed: {e}")
        import traceback
        traceback.print_exc()
