#!/usr/bin/env python3
"""
DATA AVAILABILITY CHECKER
=========================

Check what data we actually have available across the 122-day period
Test data quality and coverage without running full analysis
"""

import os
import sys
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

def check_data_availability():
    """Check data availability across 122 days"""
    
    print("📊 DATA AVAILABILITY CHECKER")
    print("=" * 50)
    
    client = db.Historical(os.getenv('DATABENTO_API_KEY'))
    
    # Sample dates across the 122-day period
    sample_dates = [
        # January samples
        "2025-01-02", "2025-01-15", "2025-01-30",
        # February samples  
        "2025-02-05", "2025-02-14", "2025-02-26",
        # March samples
        "2025-03-05", "2025-03-17", "2025-03-28",
        # April samples
        "2025-04-03", "2025-04-15", "2025-04-29",
        # May samples
        "2025-05-05", "2025-05-16", "2025-05-30",
        # June samples
        "2025-06-03", "2025-06-12", "2025-06-18"
    ]
    
    data_summary = {
        'dates_tested': len(sample_dates),
        'dates_with_data': 0,
        'dates_no_data': 0,
        'total_quotes_found': 0,
        'results_by_date': []
    }
    
    def get_contract_for_date(date_str):
        """Get appropriate contract for date"""
        if date_str >= "2025-06-01":
            return "NQM5"
        elif date_str >= "2025-03-01":
            return "NQM5"
        else:
            return "NQH5"
    
    def check_single_date(date):
        """Check data availability for single date"""
        print(f"\n📅 {date}")
        
        try:
            contract = get_contract_for_date(date)
            start_time = f"{date}T14:30:00"
            end_time = f"{date}T15:00:00"
            
            print(f"   Contract: {contract}")
            print(f"   Time: 14:30-15:00")
            
            # Test NQ futures data
            print("   🔍 NQ Futures: ", end="")
            nq_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[contract],
                schema="mbp-1", 
                start=start_time,
                end=f"{date}T14:31:00"  # Just 1 minute sample
            )
            
            nq_records = 0
            nq_price = None
            for record in nq_data:
                nq_records += 1
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break
            
            if nq_records > 0:
                print(f"✅ {nq_records} records, price ${nq_price:.2f}")
            else:
                print("❌ No data")
                return {
                    'date': date,
                    'contract': contract,
                    'nq_available': False,
                    'options_available': False,
                    'total_quotes': 0,
                    'data_quality': 'none'
                }
            
            # Test options data
            print("   🔍 NQ Options: ", end="")
            options_data = client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_time,
                end=f"{date}T14:35:00",  # 5 minute sample
                stype_in="parent"
            )
            
            options_records = 0
            institutional_signals = 0
            
            for record in options_data:
                options_records += 1
                if options_records > 10000:  # Limit for quick check
                    break
                    
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    if level.bid_sz >= 50 and level.ask_sz > 0:
                        if level.bid_sz / level.ask_sz >= 2.0:
                            institutional_signals += 1
            
            if options_records > 0:
                print(f"✅ {options_records:,} quotes, {institutional_signals} signals")
                data_quality = 'excellent' if options_records > 5000 else 'good' if options_records > 1000 else 'limited'
            else:
                print("❌ No data")
                data_quality = 'none'
            
            return {
                'date': date,
                'contract': contract,
                'nq_available': nq_records > 0,
                'options_available': options_records > 0,
                'nq_records': nq_records,
                'options_records': options_records,
                'institutional_signals': institutional_signals,
                'total_quotes': nq_records + options_records,
                'data_quality': data_quality,
                'nq_price': nq_price
            }
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}")
            return {
                'date': date,
                'contract': get_contract_for_date(date),
                'error': str(e),
                'nq_available': False,
                'options_available': False,
                'total_quotes': 0,
                'data_quality': 'error'
            }
    
    print(f"🔄 Testing {len(sample_dates)} sample dates across 122-day period...")
    
    # Check each sample date
    for date in sample_dates:
        result = check_single_date(date)
        data_summary['results_by_date'].append(result)
        
        if result.get('total_quotes', 0) > 0:
            data_summary['dates_with_data'] += 1
            data_summary['total_quotes_found'] += result['total_quotes']
        else:
            data_summary['dates_no_data'] += 1
    
    # Analysis summary
    print(f"\n{'='*50}")
    print(f"📊 DATA AVAILABILITY SUMMARY")
    print(f"{'='*50}")
    
    print(f"📅 Sample Dates Tested: {data_summary['dates_tested']}")
    print(f"✅ Dates with Data: {data_summary['dates_with_data']}")
    print(f"❌ Dates without Data: {data_summary['dates_no_data']}")
    print(f"📈 Data Coverage: {data_summary['dates_with_data']/data_summary['dates_tested']*100:.1f}%")
    print(f"📊 Total Quotes Found: {data_summary['total_quotes_found']:,}")
    
    if data_summary['dates_with_data'] > 0:
        avg_quotes = data_summary['total_quotes_found'] / data_summary['dates_with_data']
        print(f"📈 Average Quotes per Day: {avg_quotes:,.0f}")
    
    # Monthly breakdown
    monthly_coverage = {}
    for result in data_summary['results_by_date']:
        month = result['date'][:7]  # YYYY-MM
        if month not in monthly_coverage:
            monthly_coverage[month] = {'tested': 0, 'available': 0}
        monthly_coverage[month]['tested'] += 1
        if result.get('total_quotes', 0) > 0:
            monthly_coverage[month]['available'] += 1
    
    print(f"\n📅 MONTHLY DATA COVERAGE:")
    for month in sorted(monthly_coverage.keys()):
        stats = monthly_coverage[month]
        coverage_pct = stats['available'] / stats['tested'] * 100
        print(f"   {month}: {stats['available']}/{stats['tested']} ({coverage_pct:.0f}%)")
    
    # Data quality breakdown
    quality_counts = {}
    for result in data_summary['results_by_date']:
        quality = result.get('data_quality', 'unknown')
        quality_counts[quality] = quality_counts.get(quality, 0) + 1
    
    print(f"\n📊 DATA QUALITY BREAKDOWN:")
    for quality in ['excellent', 'good', 'limited', 'none', 'error']:
        count = quality_counts.get(quality, 0)
        if count > 0:
            print(f"   {quality.title()}: {count} days")
    
    # Contract usage
    contract_usage = {}
    for result in data_summary['results_by_date']:
        if result.get('total_quotes', 0) > 0:
            contract = result.get('contract', 'unknown')
            contract_usage[contract] = contract_usage.get(contract, 0) + 1
    
    if contract_usage:
        print(f"\n📈 CONTRACT USAGE (Days with Data):")
        for contract, count in contract_usage.items():
            print(f"   {contract}: {count} days")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if data_summary['dates_with_data'] >= len(sample_dates) * 0.8:
        print("✅ Excellent data coverage - proceed with full 122-day analysis")
        print("✅ Sufficient data quality for reliable backtesting")
    elif data_summary['dates_with_data'] >= len(sample_dates) * 0.5:
        print("⚠️  Moderate data coverage - consider focused analysis on available periods")
        print("🔧 May need to adjust date ranges or parameters")
    else:
        print("❌ Limited data coverage - investigate data access issues")
        print("🔧 Check API authentication and data permissions")
    
    if data_summary['total_quotes_found'] > 0:
        print(f"📊 Estimated full 122-day dataset: {data_summary['total_quotes_found'] * 122 / len(sample_dates):,.0f} quotes")
        print(f"💾 Processing requirements: Plan for high-volume data handling")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"data_availability_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(data_summary, f, indent=2)
    
    print(f"\n📁 Results saved to: {results_file}")
    
    return data_summary

if __name__ == "__main__":
    check_data_availability()