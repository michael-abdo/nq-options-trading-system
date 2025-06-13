#!/usr/bin/env python3
"""
Single Entry Point for Hierarchical Pipeline Analysis Framework
Clean, simple interface to the new NQ Options Trading System

Usage:
  python3 run_pipeline.py                    # Run with Databento NQ options data
  python3 run_pipeline.py [DEPRECATED]       # Contract args no longer used (Databento auto-fetches)

Note: Now uses Databento for Standard E-mini NQ options (20x multiplier)
"""

import sys
import os
import argparse
from datetime import datetime

# Add pipeline system to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
pipeline_path = os.path.join(parent_dir, 'tasks', 'options_trading_system')
sys.path.insert(0, pipeline_path)

from integration import run_complete_nq_trading_system

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='NQ Options Hierarchical Pipeline Analysis Framework',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 run_pipeline.py                    # Run with Databento NQ options (Standard E-mini)

Note: Contract arguments are deprecated. Databento automatically fetches
      current Standard E-mini NQ options data ($20 per point).
        """
    )

    parser.add_argument(
        'contract',
        nargs='?',
        help='Options contract symbol (e.g., MC7M25, MC1M25). If not provided, uses today\'s EOD contract.'
    )

    parser.add_argument(
        '--contract',
        dest='contract_flag',
        help='Options contract symbol (alternative syntax)'
    )

    return parser.parse_args()

def get_target_contract(args):
    """Determine target contract from arguments"""
    # Priority: positional argument > --contract flag > None (auto-calculate)
    if args.contract:
        return args.contract.upper()
    elif args.contract_flag:
        return args.contract_flag.upper()
    else:
        return None

def main():
    """Single entry point for the pipeline system"""
    args = parse_arguments()
    target_contract = get_target_contract(args)

    print("🚀 NQ Options Hierarchical Pipeline Analysis Framework")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    print("Primary Data Source: Databento (Standard E-mini NQ Options)")
    print()

    try:
        # Import configuration manager
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'tasks', 'options_trading_system'))
        from config_manager import get_config_manager

        # Use configuration manager with databento_only profile
        config_manager = get_config_manager()

        # Create standard profiles if they don't exist
        try:
            config = config_manager.load_profile("all_sources")
            print("📋 Loaded 'all_sources' configuration profile")
        except FileNotFoundError:
            print("📋 Creating standard configuration profiles...")
            config_manager.create_standard_profiles()
            config = config_manager.load_profile("all_sources")
            print("📋 Created and loaded 'all_sources' configuration profile")

        # Validate configuration
        validation_issues = config_manager.validate_config(config)
        if validation_issues:
            print("⚠️ Configuration validation issues:")
            for issue in validation_issues:
                print(f"   - {issue}")

        # Show configuration summary
        summary = config_manager.get_config_summary(config)
        print(f"📊 Configuration: {len(summary['enabled_sources'])} sources enabled")
        for source in summary['enabled_sources']:
            print(f"   ✓ {source}")

        # The config is already complete from config_manager

        # Run the complete pipeline system
        result = run_complete_nq_trading_system(config)

        if result['status'] == 'success':
            # Show the key result
            if 'system_summary' in result and 'trading_summary' in result['system_summary']:
                trading_summary = result['system_summary']['trading_summary']
                if 'primary_recommendation' in trading_summary and trading_summary['primary_recommendation']:
                    rec = trading_summary['primary_recommendation']
                    print(f"\n✅ PIPELINE RESULT:")
                    print(f"   {rec['direction']} @ ${rec['entry']:,.2f}")
                    print(f"   Target: ${rec['target']:,.0f}")
                    print(f"   Stop: ${rec['stop']:,.0f}")
                    print(f"   Expected Value: {rec['expected_value']:+.1f} points")
                    print(f"   Probability: {rec['probability']:.1%}")
                else:
                    print(f"\n✅ PIPELINE COMPLETE: No trades met quality criteria")
            else:
                print(f"\n✅ PIPELINE COMPLETE: {result['status']}")
        else:
            print(f"\n❌ PIPELINE FAILED: {result.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"\n❌ PIPELINE ERROR: {str(e)}")
        return 1

    print()
    print("=" * 60)
    return 0

if __name__ == "__main__":
    exit(main())
