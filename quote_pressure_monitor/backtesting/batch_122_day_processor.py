#!/usr/bin/env python3
"""
BATCH 122-DAY PROCESSOR
======================

Process 122 days in small batches to avoid timeouts
Run multiple times to get full results
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def batch_process_122_days():
    """Process 122 days in batches"""

    print("📦 BATCH 122-DAY PROCESSOR")
    print("=" * 40)

    # All 122 dates split into batches
    all_dates = [
        # Batch 1: January 2025 (23 days)
        ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07",
         "2025-01-08", "2025-01-09", "2025-01-10", "2025-01-13", "2025-01-14",
         "2025-01-15", "2025-01-16", "2025-01-17", "2025-01-20", "2025-01-21",
         "2025-01-22", "2025-01-23", "2025-01-24", "2025-01-27", "2025-01-28",
         "2025-01-29", "2025-01-30", "2025-01-31"],

        # Batch 2: February 2025 (20 days)
        ["2025-02-03", "2025-02-04", "2025-02-05", "2025-02-06", "2025-02-07",
         "2025-02-10", "2025-02-11", "2025-02-12", "2025-02-13", "2025-02-14",
         "2025-02-17", "2025-02-18", "2025-02-19", "2025-02-20", "2025-02-21",
         "2025-02-24", "2025-02-25", "2025-02-26", "2025-02-27", "2025-02-28"],

        # Batch 3: March 2025 (21 days)
        ["2025-03-03", "2025-03-04", "2025-03-05", "2025-03-06", "2025-03-07",
         "2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13", "2025-03-14",
         "2025-03-17", "2025-03-18", "2025-03-19", "2025-03-20", "2025-03-21",
         "2025-03-24", "2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28",
         "2025-03-31"],

        # Batch 4: April 2025 (22 days)
        ["2025-04-01", "2025-04-02", "2025-04-03", "2025-04-04", "2025-04-07",
         "2025-04-08", "2025-04-09", "2025-04-10", "2025-04-11", "2025-04-14",
         "2025-04-15", "2025-04-16", "2025-04-17", "2025-04-18", "2025-04-21",
         "2025-04-22", "2025-04-23", "2025-04-24", "2025-04-25", "2025-04-28",
         "2025-04-29", "2025-04-30"],

        # Batch 5: May 2025 (22 days)
        ["2025-05-01", "2025-05-02", "2025-05-05", "2025-05-06", "2025-05-07",
         "2025-05-08", "2025-05-09", "2025-05-12", "2025-05-13", "2025-05-14",
         "2025-05-15", "2025-05-16", "2025-05-19", "2025-05-20", "2025-05-21",
         "2025-05-22", "2025-05-23", "2025-05-26", "2025-05-27", "2025-05-28",
         "2025-05-29", "2025-05-30"],

        # Batch 6: June 2025 (14 days)
        ["2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06",
         "2025-06-09", "2025-06-10", "2025-06-11", "2025-06-12", "2025-06-13",
         "2025-06-16", "2025-06-17", "2025-06-18"]
    ]

    batch_names = ["January", "February", "March", "April", "May", "June"]

    print("Select which batch to process:")
    for i, (name, dates) in enumerate(zip(batch_names, all_dates)):
        print(f"  {i+1}. {name} 2025 ({len(dates)} days)")
    print(f"  7. All batches (full 122 days)")

    choice = input("\nEnter choice (1-7): ").strip()

    if choice == "7":
        print("🚀 Processing ALL 122 days...")
        selected_dates = [date for batch in all_dates for date in batch]
        batch_name = "All_122_Days"
    elif choice in ["1", "2", "3", "4", "5", "6"]:
        batch_idx = int(choice) - 1
        selected_dates = all_dates[batch_idx]
        batch_name = batch_names[batch_idx]
        print(f"🚀 Processing {batch_name} 2025 ({len(selected_dates)} days)...")
    else:
        print("❌ Invalid choice")
        return

    # Process selected batch
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))
    results = []

    def process_single_day(date_str):
        """Process single day quickly"""
        try:
            # Use appropriate contract
            if date_str >= "2025-06-01":
                contract = "NQM5"
            elif date_str >= "2025-03-01":
                contract = "NQM5"
            else:
                contract = "NQH5"

            start_time = f"{date_str}T14:30:00"
            end_time = f"{date_str}T15:00:00"

            # Quick NQ price
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[contract],
                schema="mbp-1",
                start=start_time,
                end=f"{date_str}T14:31:00"
            )

            nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not nq_price:
                return f"no_nq"

            # Quick options scan
            data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=end_time,
                stype_in="parent"
            )

            signals = []
            count = 0

            for record in data:
                count += 1
                if count > 50000:  # Limit for speed
                    break

                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    if level.bid_sz >= 50 and level.ask_sz > 0 and level.bid_sz / level.ask_sz >= 2.0:
                        signals.append({'id': record.instrument_id, 'size': level.bid_sz})
                        if len(signals) >= 50:
                            break

            if len(signals) < 10:
                return f"low_signals"

            # Return basic info without full processing
            return {
                'date': date_str,
                'nq_price': nq_price,
                'signals': len(signals),
                'total_volume': sum(s['size'] for s in signals),
                'contract': contract,
                'status': 'detected'
            }

        except Exception as e:
            return f"error_{str(e)[:20]}"

    print(f"\n📊 Processing {len(selected_dates)} days...")
    print("Progress: ", end="", flush=True)

    for i, date in enumerate(selected_dates):
        if i % 5 == 0:
            print(".", end="", flush=True)

        result = process_single_day(date)
        if isinstance(result, dict):
            results.append(result)

    print(" Done!")

    # Results
    print(f"\n📊 {batch_name.upper()} BATCH RESULTS")
    print("=" * 40)
    print(f"Days Processed: {len(selected_dates)}")
    print(f"Signals Detected: {len(results)}")
    print(f"Hit Rate: {len(results)/len(selected_dates)*100:.1f}%")

    if results:
        total_signals = sum(r['signals'] for r in results)
        total_volume = sum(r['total_volume'] for r in results)
        avg_nq = sum(r['nq_price'] for r in results) / len(results)

        print(f"Total Signals: {total_signals:,}")
        print(f"Total Volume: {total_volume:,}")
        print(f"Average NQ Price: ${avg_nq:,.0f}")

        # Show sample days
        print(f"\nSample Results:")
        for r in results[:10]:
            print(f"  {r['date']}: {r['signals']} signals, {r['total_volume']:,} volume")

        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"batch_{batch_name}_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump({
                'batch': batch_name,
                'total_days': len(selected_dates),
                'successful_days': len(results),
                'hit_rate': len(results)/len(selected_dates)*100,
                'total_signals': total_signals,
                'total_volume': total_volume,
                'results': results
            }, f, indent=2)

        print(f"\n📁 Results saved to: {filename}")

        print(f"\n✅ {batch_name} batch complete!")
        if len(results) > len(selected_dates) * 0.5:
            print("🎉 Good signal detection rate!")
        else:
            print("📊 Consider adjusting parameters")
    else:
        print("❌ No signals detected")

if __name__ == "__main__":
    batch_process_122_days()
