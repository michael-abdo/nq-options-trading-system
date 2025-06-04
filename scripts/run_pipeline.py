#!/usr/bin/env python3
"""
Main pipeline runner for modular trading analysis system
"""

import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.pipeline import AnalysisPipeline
from utils.logging_config import get_logger

logger = get_logger(__name__)


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Run trading analysis pipeline")
    
    # Pipeline options
    parser.add_argument("--pipeline", "-p", type=str, 
                       help="Pipeline name to run (from config/pipeline.yaml)")
    parser.add_argument("--list", "-l", action="store_true",
                       help="List available pipelines and components")
    
    # Single analysis options
    parser.add_argument("--source", "-s", type=str,
                       help="Data source name")
    parser.add_argument("--strategies", "-st", nargs="+",
                       help="Strategy names to run")
    
    # Configuration
    parser.add_argument("--config", "-c", type=str, default="config",
                       help="Configuration directory path")
    
    args = parser.parse_args()
    
    try:
        # Initialize pipeline
        logger.info("🚀 Initializing Trading Analysis Pipeline...")
        pipeline = AnalysisPipeline(config_path=args.config)
        
        # List components if requested
        if args.list:
            pipeline.list_available_components()
            return
        
        # Run specific pipeline
        if args.pipeline:
            logger.info(f"📊 Running pipeline: {args.pipeline}")
            results = pipeline.run_pipeline(args.pipeline)
            
            # Display results summary
            print_results_summary(results)
            
        # Run single analysis
        elif args.source and args.strategies:
            logger.info(f"🎯 Running single analysis: {args.source} → {args.strategies}")
            results = pipeline.run_single_analysis(args.source, args.strategies)
            
            # Display results summary
            print_results_summary(results)
            
        else:
            # Show help if no valid options provided
            parser.print_help()
            print("\nExamples:")
            print("  # List available components")
            print("  python scripts/run_pipeline.py --list")
            print()
            print("  # Run main analysis pipeline")
            print("  python scripts/run_pipeline.py --pipeline main_analysis")
            print()
            print("  # Run specific strategy on data source")
            print("  python scripts/run_pipeline.py --source barchart_saved --strategies expected_value")
            print()
            print("  # Compare multiple strategies")
            print("  python scripts/run_pipeline.py --pipeline strategy_comparison")
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Pipeline execution failed: {e}")
        logger.exception("Full traceback:")
        return 1
    
    return 0


def print_results_summary(results):
    """Print a summary of analysis results"""
    if not results:
        print("\n❌ No analysis results generated")
        return
    
    print("\n" + "="*80)
    print(f"ANALYSIS RESULTS SUMMARY - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    for result in results:
        print(f"\n🧮 Strategy: {result.strategy_name}")
        print(f"   Underlying: {result.underlying_symbol} @ ${result.underlying_price:,.2f}")
        print(f"   Signals: {len(result.signals)}")
        print(f"   Metrics: {len(result.metrics)}")
        
        # Show top signal if available
        if result.signals:
            top_signal = result.signals[0]
            print(f"   Top Signal: {top_signal.get('type', 'unknown')} "
                  f"(confidence: {top_signal.get('confidence', 0):.1%})")
            
            if 'direction' in top_signal:
                direction = top_signal['direction'].upper()
                target = top_signal.get('target_price', 0)
                stop = top_signal.get('stop_loss', 0)
                ev = top_signal.get('expected_value', 0)
                print(f"   Recommendation: {direction} NQ, Target: ${target:,.0f}, "
                      f"Stop: ${stop:,.0f}, EV: {ev:+.1f}")
        
        # Show key metrics
        if result.metrics:
            key_metrics = ['best_ev', 'best_probability', 'total_opportunities', 'pcr_volume']
            metric_strs = []
            for metric in key_metrics:
                if metric in result.metrics:
                    value = result.metrics[metric]
                    if metric == 'best_probability':
                        metric_strs.append(f"{metric}: {value:.1%}")
                    elif metric == 'total_opportunities':
                        metric_strs.append(f"{metric}: {int(value)}")
                    else:
                        metric_strs.append(f"{metric}: {value:.2f}")
            
            if metric_strs:
                print(f"   Key Metrics: {', '.join(metric_strs)}")
        
        # Show warnings
        if result.warnings:
            print(f"   ⚠️ Warnings: {len(result.warnings)}")
            for warning in result.warnings[:2]:  # Show first 2 warnings
                print(f"      • {warning}")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    exit(main())