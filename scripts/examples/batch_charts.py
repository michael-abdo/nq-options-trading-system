#!/usr/bin/env python3
"""
Batch Charts - Generate multiple chart configurations
Creates charts with different configurations for comparison
"""

import sys
import os
from pathlib import Path
import argparse

# Add parent directories to path
script_dir = Path(__file__).parent
sys.path.append(str(script_dir.parent))
sys.path.append(str(script_dir.parent.parent))

from nq_5m_chart import NQFiveMinuteChart
from chart_config_manager import ChartConfigManager
from utils.timezone_utils import format_eastern_timestamp

def generate_chart_batch(output_dir="outputs/batch_charts", symbol="NQM5"):
    """Generate multiple charts with different configurations"""

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    config_manager = ChartConfigManager()
    configs_to_generate = ["default", "scalping", "swing_trading", "minimal"]

    timestamp = format_eastern_timestamp()
    results = []

    print(f"🔄 Generating {len(configs_to_generate)} chart configurations...")
    print(f"📁 Output directory: {output_dir}")
    print(f"📊 Symbol: {symbol}")
    print("=" * 50)

    for config_name in configs_to_generate:
        try:
            print(f"⚡ Generating {config_name} chart...")

            # Load configuration
            config = config_manager.load_config(config_name)

            # Override symbol if specified
            if symbol != "NQM5":
                config["data"]["symbol"] = symbol

            # Create chart
            chart = NQFiveMinuteChart(config=config)

            # Generate filename
            filename = f"{output_dir}/{config_name}_chart_{timestamp}.html"

            # Save chart
            result = chart.save_chart(filename)

            if result:
                results.append({
                    "config": config_name,
                    "filename": result,
                    "status": "success"
                })
                print(f"  ✅ {config_name}: {result}")
            else:
                results.append({
                    "config": config_name,
                    "filename": None,
                    "status": "failed"
                })
                print(f"  ❌ {config_name}: Failed")

        except Exception as e:
            results.append({
                "config": config_name,
                "filename": None,
                "status": "error",
                "error": str(e)
            })
            print(f"  ❌ {config_name}: Error - {e}")

    # Generate summary
    print("\n" + "=" * 50)
    print("📋 BATCH GENERATION SUMMARY")
    print("=" * 50)

    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]

    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")

    if successful:
        print("\n📁 Generated files:")
        for result in successful:
            print(f"  - {result['config']}: {result['filename']}")

    if failed:
        print("\n⚠️ Failed generations:")
        for result in failed:
            error_info = f" ({result.get('error', 'Unknown error')})" if 'error' in result else ""
            print(f"  - {result['config']}{error_info}")

    # Create index HTML file
    create_index_html(successful, output_dir, timestamp)

    return results

def create_index_html(successful_charts, output_dir, timestamp):
    """Create an index HTML file linking to all generated charts"""

    index_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>NQ 5-Minute Charts - Batch {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; text-align: center; }}
        .chart-link {{ display: block; padding: 15px; margin: 10px 0; background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 5px; text-decoration: none; color: #333; }}
        .chart-link:hover {{ background: #e9ecef; }}
        .config-name {{ font-weight: bold; font-size: 18px; }}
        .config-desc {{ color: #666; margin-top: 5px; }}
        .timestamp {{ text-align: center; color: #888; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 NQ 5-Minute Charts</h1>
        <p style="text-align: center;">Batch generated on {timestamp}</p>

        <div class="charts">
"""

    # Configuration descriptions
    descriptions = {
        "default": "Standard 4-hour view with SMA indicators - ideal for day trading",
        "scalping": "High-frequency 2-hour view with EMA and VWAP - optimized for scalping",
        "swing_trading": "Extended 8-hour view with multiple SMAs - perfect for swing analysis",
        "minimal": "Lightweight 4-hour view with no indicators - minimal resource usage"
    }

    for chart in successful_charts:
        config = chart["config"]
        filename = os.path.basename(chart["filename"])
        description = descriptions.get(config, "Custom configuration")

        index_content += f"""
            <a href="{filename}" class="chart-link">
                <div class="config-name">{config.replace('_', ' ').title()}</div>
                <div class="config-desc">{description}</div>
            </a>
        """

    index_content += f"""
        </div>

        <div class="timestamp">
            Generated: {timestamp} Eastern Time
        </div>
    </div>
</body>
</html>
"""

    index_file = f"{output_dir}/index_{timestamp}.html"
    with open(index_file, 'w') as f:
        f.write(index_content)

    print(f"\n🌐 Index file created: {index_file}")
    print(f"🌐 Open in browser: file://{os.path.abspath(index_file)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Generate batch charts with different configurations")
    parser.add_argument("--output", default="outputs/batch_charts", help="Output directory")
    parser.add_argument("--symbol", default="NQM5", help="Contract symbol")

    args = parser.parse_args()

    print("🚀 NQ 5-Minute Batch Chart Generator")
    print("=" * 50)

    try:
        results = generate_chart_batch(args.output, args.symbol)

        # Exit with error code if all failed
        successful = [r for r in results if r["status"] == "success"]
        if not successful:
            print("\n❌ All chart generations failed")
            return 1

        print(f"\n✅ Batch generation completed successfully!")
        return 0

    except Exception as e:
        print(f"\n❌ Batch generation failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
