#!/usr/bin/env python3
"""
Single Entry Point for Hierarchical Pipeline Analysis Framework
Clean, simple interface to the new NQ Options Trading System
"""

import sys
import os
from datetime import datetime

# Add pipeline system to path
pipeline_path = os.path.join(os.path.dirname(__file__), 'tasks', 'options_trading_system')
sys.path.insert(0, pipeline_path)

from integration import run_complete_nq_trading_system

def main():
    """Single entry point for the pipeline system"""
    print("🚀 NQ Options Hierarchical Pipeline Analysis Framework")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Run the complete pipeline system
        result = run_complete_nq_trading_system()
        
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