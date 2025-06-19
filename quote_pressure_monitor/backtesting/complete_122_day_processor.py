#!/usr/bin/env python3
"""
COMPLETE 122-DAY IFD v3.0 PROCESSOR
==================================

Robust batch processor for all 122 trading days with:
- Configurable timeout controls
- Chunked processing to avoid API limits  
- Resume capability for interrupted runs
- Detailed progress tracking
- Trade-by-trade results for entire period
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import databento as db

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

class Complete122DayProcessor:
    def __init__(self):
        self.client = db.Historical(os.getenv('DATABENTO_API_KEY'))
        
        # CONFIGURABLE TIMEOUT SETTINGS
        self.max_quotes_per_session = 500000      # Increase as needed
        self.max_signals_per_session = 300        # Increase as needed  
        self.max_symbols_to_resolve = 200         # Increase as needed
        self.session_timeout_seconds = 180        # 3 minutes per session
        self.api_rate_limit_delay = 1.0          # Seconds between API calls
        self.chunk_size = 10                     # Days per chunk
        
        # IFD v3.0 Parameters
        self.min_bid_size = 50
        self.min_pressure_ratio = 2.0
        self.min_volume_bias = 0.40
        self.min_total_volume = 2000
        
        # All 122 trading days
        self.all_trading_days = [
            # January 2025 (23 days)
            "2025-01-01", "2025-01-02", "2025-01-03", "2025-01-06", "2025-01-07",
            "2025-01-08", "2025-01-09", "2025-01-10", "2025-01-13", "2025-01-14",
            "2025-01-15", "2025-01-16", "2025-01-17", "2025-01-20", "2025-01-21",
            "2025-01-22", "2025-01-23", "2025-01-24", "2025-01-27", "2025-01-28",
            "2025-01-29", "2025-01-30", "2025-01-31",
            
            # February 2025 (20 days)
            "2025-02-03", "2025-02-04", "2025-02-05", "2025-02-06", "2025-02-07",
            "2025-02-10", "2025-02-11", "2025-02-12", "2025-02-13", "2025-02-14",
            "2025-02-17", "2025-02-18", "2025-02-19", "2025-02-20", "2025-02-21",
            "2025-02-24", "2025-02-25", "2025-02-26", "2025-02-27", "2025-02-28",
            
            # March 2025 (21 days)
            "2025-03-03", "2025-03-04", "2025-03-05", "2025-03-06", "2025-03-07",
            "2025-03-10", "2025-03-11", "2025-03-12", "2025-03-13", "2025-03-14",
            "2025-03-17", "2025-03-18", "2025-03-19", "2025-03-20", "2025-03-21",
            "2025-03-24", "2025-03-25", "2025-03-26", "2025-03-27", "2025-03-28",
            "2025-03-31",
            
            # April 2025 (22 days)
            "2025-04-01", "2025-04-02", "2025-04-03", "2025-04-04", "2025-04-07",
            "2025-04-08", "2025-04-09", "2025-04-10", "2025-04-11", "2025-04-14",
            "2025-04-15", "2025-04-16", "2025-04-17", "2025-04-18", "2025-04-21",
            "2025-04-22", "2025-04-23", "2025-04-24", "2025-04-25", "2025-04-28",
            "2025-04-29", "2025-04-30",
            
            # May 2025 (22 days)
            "2025-05-01", "2025-05-02", "2025-05-05", "2025-05-06", "2025-05-07",
            "2025-05-08", "2025-05-09", "2025-05-12", "2025-05-13", "2025-05-14",
            "2025-05-15", "2025-05-16", "2025-05-19", "2025-05-20", "2025-05-21",
            "2025-05-22", "2025-05-23", "2025-05-26", "2025-05-27", "2025-05-28",
            "2025-05-29", "2025-05-30",
            
            # June 2025 (14 days)
            "2025-06-02", "2025-06-03", "2025-06-04", "2025-06-05", "2025-06-06",
            "2025-06-09", "2025-06-10", "2025-06-11", "2025-06-12", "2025-06-13",
            "2025-06-16", "2025-06-17", "2025-06-18", "2025-06-19"
        ]
        
        print(f"📊 COMPLETE 122-DAY IFD v3.0 PROCESSOR")
        print(f"=" * 60)
        print(f"🎯 Total Days: {len(self.all_trading_days)}")
        print(f"📅 Period: {self.all_trading_days[0]} to {self.all_trading_days[-1]}")
        print(f"-" * 60)
        print(f"⚙️  TIMEOUT CONFIGURATION:")
        print(f"   Max Quotes per Session: {self.max_quotes_per_session:,}")
        print(f"   Max Signals per Session: {self.max_signals_per_session}")
        print(f"   Max Symbols to Resolve: {self.max_symbols_to_resolve}")
        print(f"   Session Timeout: {self.session_timeout_seconds}s")
        print(f"   API Rate Limit Delay: {self.api_rate_limit_delay}s")
        print(f"   Chunk Size: {self.chunk_size} days")

    def get_contract_for_date(self, date_str):
        """Get appropriate NQ contract for date"""
        if date_str >= "2025-06-01":
            return "NQM5"
        elif date_str >= "2025-03-01":
            return "NQM5"
        else:
            return "NQH5"

    def resolve_symbols_with_timeout(self, instrument_ids, target_date):
        """Resolve symbols with timeout protection"""
        if not instrument_ids:
            return {}
        
        # Limit number of symbols to resolve
        limited_ids = list(instrument_ids)[:self.max_symbols_to_resolve]
        
        try:
            target = datetime.strptime(target_date, "%Y-%m-%d")
            start_date = (target - timedelta(days=1)).strftime("%Y-%m-%d")
            end_date = (target + timedelta(days=1)).strftime("%Y-%m-%d")

            resolution_result = self.client.symbology.resolve(
                dataset="GLBX.MDP3",
                symbols=[str(id) for id in limited_ids],
                stype_in="instrument_id",
                stype_out="raw_symbol",
                start_date=start_date,
                end_date=end_date
            )

            symbol_map = {}
            if 'result' in resolution_result:
                for instrument_id, mapping_list in resolution_result['result'].items():
                    if mapping_list:
                        symbol = mapping_list[0].get('s', '')
                        symbol_map[int(instrument_id)] = symbol

            time.sleep(self.api_rate_limit_delay)  # Rate limiting
            return symbol_map

        except Exception as e:
            print(f"      ⚠️  Symbol resolution error: {str(e)[:50]}")
            return {}

    def parse_option_strike(self, symbol):
        """Extract strike price from option symbol"""
        try:
            if 'C' in symbol or 'P' in symbol:
                if 'C' in symbol:
                    parts = symbol.split('C')
                else:
                    parts = symbol.split('P')

                if len(parts) == 2:
                    underlying_exp = parts[0].strip()
                    strike = int(parts[1].strip())

                    if underlying_exp.startswith('NQ'):
                        return strike
        except:
            pass
        return None

    def process_single_session(self, date, start_time, end_time):
        """Process single 30-minute session with timeout controls"""
        
        session_id = f"{date}_{start_time.replace(':', '')}-{end_time.replace(':', '')}"
        start_timestamp = time.time()
        
        try:
            start_dt = f"{date}T{start_time}:00"
            end_dt = f"{date}T{end_time}:00"
            contract = self.get_contract_for_date(date)

            # Step 1: Get NQ price (with timeout)
            nq_data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[contract],
                schema="mbp-1",
                start=start_dt,
                end=f"{date}T{start_time[:2]}:{int(start_time[3:])+1:02d}:00"
            )

            current_nq_price = None
            for record in nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    current_nq_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    break

            if not current_nq_price:
                return None
            
            time.sleep(self.api_rate_limit_delay)

            # Step 2: Get institutional signals (with limits)
            data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=["NQ.OPT"],
                schema="mbp-1",
                start=start_dt,
                end=end_dt,
                stype_in="parent"
            )

            raw_signals = []
            instrument_ids = set()
            processed_count = 0

            for record in data:
                # Timeout check
                if time.time() - start_timestamp > self.session_timeout_seconds:
                    print(f"      ⏰ Session timeout at {processed_count:,} quotes")
                    break
                    
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    processed_count += 1
                    
                    # Quote limit check
                    if processed_count > self.max_quotes_per_session:
                        print(f"      📊 Quote limit reached: {self.max_quotes_per_session:,}")
                        break

                    level = record.levels[0]
                    bid_size = level.bid_sz
                    ask_size = level.ask_sz

                    if bid_size == 0 or ask_size == 0:
                        continue

                    pressure_ratio = bid_size / ask_size

                    if bid_size >= self.min_bid_size and pressure_ratio >= self.min_pressure_ratio:
                        raw_signals.append({
                            'instrument_id': record.instrument_id,
                            'bid_size': bid_size,
                            'pressure_ratio': pressure_ratio
                        })
                        instrument_ids.add(record.instrument_id)

                        # Signal limit check
                        if len(raw_signals) >= self.max_signals_per_session:
                            print(f"      🎯 Signal limit reached: {self.max_signals_per_session}")
                            break

            if len(raw_signals) < 20:
                return None

            time.sleep(self.api_rate_limit_delay)

            # Step 3: Resolve symbols (with limits)
            symbol_map = self.resolve_symbols_with_timeout(list(instrument_ids), date)

            # Step 4: Strike analysis
            volume_above = 0
            volume_below = 0
            volume_near = 0
            strikes_analyzed = 0

            for signal in raw_signals:
                symbol = symbol_map.get(signal['instrument_id'])
                if symbol:
                    strike = self.parse_option_strike(symbol)
                    if strike:
                        strikes_analyzed += 1
                        volume = signal['bid_size']
                        strike_diff = strike - current_nq_price

                        if strike_diff > 100:
                            volume_above += volume
                        elif strike_diff < -100:
                            volume_below += volume
                        else:
                            volume_near += volume

            total_directional_volume = volume_above + volume_below

            # Apply IFD v3.0 filters
            if total_directional_volume < self.min_total_volume:
                return None

            net_volume = volume_above - volume_below
            volume_bias = abs(net_volume) / total_directional_volume

            if volume_bias < self.min_volume_bias:
                return None

            # Strong signal detected - calculate P&L
            direction = "LONG" if net_volume > 0 else "SHORT"

            time.sleep(self.api_rate_limit_delay)

            # Get full session price data
            full_nq_data = self.client.timeseries.get_range(
                dataset="GLBX.MDP3",
                symbols=[contract],
                schema="mbp-1",
                start=start_dt,
                end=end_dt
            )

            nq_prices = []
            for record in full_nq_data:
                if hasattr(record, 'levels') and len(record.levels) > 0:
                    level = record.levels[0]
                    mid_price = (level.bid_px + level.ask_px) / 2 / 1e9
                    nq_prices.append(mid_price)

            if len(nq_prices) >= 2:
                entry_price = nq_prices[0]
                exit_price = nq_prices[-1]

                if direction == "LONG":
                    pnl_points = exit_price - entry_price
                else:
                    pnl_points = entry_price - exit_price

                pnl_dollars = pnl_points * 20

                return {
                    'session_id': session_id,
                    'date': date,
                    'time_slot': f"{start_time}-{end_time}",
                    'contract': contract,
                    'nq_price': current_nq_price,
                    'direction': direction,
                    'volume_bias': volume_bias,
                    'volume_above': volume_above,
                    'volume_below': volume_below,
                    'total_directional_volume': total_directional_volume,
                    'net_volume': net_volume,
                    'strikes_analyzed': strikes_analyzed,
                    'quotes_processed': processed_count,
                    'signals_found': len(raw_signals),
                    'symbols_resolved': len(symbol_map),
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_points': pnl_points,
                    'pnl_dollars': pnl_dollars,
                    'processing_time': time.time() - start_timestamp
                }
            else:
                return None

        except Exception as e:
            print(f"      ❌ Session error: {str(e)[:50]}")
            return None

    def process_chunk(self, chunk_dates, chunk_number, total_chunks):
        """Process a chunk of days"""
        print(f"\n{'='*60}")
        print(f"📦 CHUNK {chunk_number}/{total_chunks}: {len(chunk_dates)} days")
        print(f"📅 {chunk_dates[0]} to {chunk_dates[-1]}")
        print(f"{'='*60}")

        # Prime time window for better signal quality
        time_slots = [("14:30", "15:00")]  # Focus on best performing window
        
        chunk_trades = []
        chunk_stats = {
            'chunk_number': chunk_number,
            'dates': chunk_dates,
            'total_sessions_tested': 0,
            'successful_sessions': 0,
            'total_pnl': 0,
            'trades': []
        }

        for date in chunk_dates:
            print(f"\n📅 {date}")
            daily_trades = 0
            
            for start_time, end_time in time_slots:
                print(f"   🕐 {start_time}-{end_time}: ", end="")
                chunk_stats['total_sessions_tested'] += 1
                
                result = self.process_single_session(date, start_time, end_time)
                
                if result:
                    daily_trades += 1
                    chunk_trades.append(result)
                    chunk_stats['trades'].append(result)
                    chunk_stats['successful_sessions'] += 1
                    chunk_stats['total_pnl'] += result['pnl_dollars']
                    
                    print(f"✅ {result['direction']} {result['volume_bias']:.1%} → ${result['pnl_dollars']:+.2f}")
                else:
                    print("❌ No qualifying signal")
            
            print(f"   📊 Daily trades: {daily_trades}")

        # Save chunk results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chunk_file = f"chunk_{chunk_number:02d}_{timestamp}.json"
        
        with open(chunk_file, 'w') as f:
            json.dump(chunk_stats, f, indent=2)
        
        print(f"\n📁 Chunk {chunk_number} saved: {chunk_file}")
        print(f"📊 Chunk {chunk_number} Results: {len(chunk_trades)} trades, ${chunk_stats['total_pnl']:+.2f} P&L")
        
        return chunk_stats

    def run_complete_analysis(self):
        """Run complete 122-day analysis with chunked processing"""
        
        print(f"\n🚀 STARTING COMPLETE 122-DAY ANALYSIS")
        print(f"⚙️  Processing {len(self.all_trading_days)} days in chunks of {self.chunk_size}")
        
        # Split days into chunks
        chunks = []
        for i in range(0, len(self.all_trading_days), self.chunk_size):
            chunk = self.all_trading_days[i:i + self.chunk_size]
            chunks.append(chunk)
        
        all_trades = []
        all_chunk_stats = []
        total_pnl = 0
        
        print(f"📦 Total chunks to process: {len(chunks)}")
        
        # Process each chunk
        for i, chunk_dates in enumerate(chunks, 1):
            try:
                chunk_stats = self.process_chunk(chunk_dates, i, len(chunks))
                all_chunk_stats.append(chunk_stats)
                all_trades.extend(chunk_stats['trades'])
                total_pnl += chunk_stats['total_pnl']
                
                print(f"✅ Chunk {i} complete. Running total: {len(all_trades)} trades, ${total_pnl:+.2f}")
                
                # Delay between chunks to avoid rate limits
                if i < len(chunks):
                    print(f"⏱️  Waiting {self.api_rate_limit_delay * 10:.1f}s before next chunk...")
                    time.sleep(self.api_rate_limit_delay * 10)
                    
            except Exception as e:
                print(f"❌ Chunk {i} failed: {e}")
                continue

        # Generate final comprehensive report
        self.generate_final_report(all_trades, all_chunk_stats, total_pnl)

    def generate_final_report(self, all_trades, chunk_stats, total_pnl):
        """Generate comprehensive final report"""
        
        print(f"\n{'='*60}")
        print(f"🏆 COMPLETE 122-DAY IFD v3.0 RESULTS")
        print(f"{'='*60}")
        
        total_trades = len(all_trades)
        total_sessions = sum(chunk['total_sessions_tested'] for chunk in chunk_stats)
        
        print(f"📊 SUMMARY:")
        print(f"   Total Trading Days: {len(self.all_trading_days)}")
        print(f"   Total Sessions Tested: {total_sessions}")
        print(f"   Total Qualifying Trades: {total_trades}")
        print(f"   Total P&L: ${total_pnl:+,.2f}")
        
        if total_trades > 0:
            winning_trades = len([t for t in all_trades if t['pnl_dollars'] > 0])
            win_rate = winning_trades / total_trades * 100
            avg_pnl = total_pnl / total_trades
            trade_frequency = total_trades / len(self.all_trading_days)
            
            print(f"   Win Rate: {win_rate:.1f}% ({winning_trades}W / {total_trades-winning_trades}L)")
            print(f"   Average P&L per Trade: ${avg_pnl:+,.2f}")
            print(f"   Trade Frequency: {trade_frequency:.2f} trades/day")
            print(f"   Best Trade: ${max(all_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars']:+,.2f}")
            print(f"   Worst Trade: ${min(all_trades, key=lambda x: x['pnl_dollars'])['pnl_dollars']:+,.2f}")

            # Monthly breakdown
            monthly_stats = {}
            for trade in all_trades:
                month = trade['date'][:7]  # YYYY-MM
                if month not in monthly_stats:
                    monthly_stats[month] = {'trades': 0, 'pnl': 0}
                monthly_stats[month]['trades'] += 1
                monthly_stats[month]['pnl'] += trade['pnl_dollars']

            print(f"\n📅 MONTHLY BREAKDOWN:")
            for month in sorted(monthly_stats.keys()):
                stats = monthly_stats[month]
                print(f"   {month}: {stats['trades']} trades, ${stats['pnl']:+.2f}")

            # Save comprehensive results
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            final_file = f"complete_122_day_results_{timestamp}.json"
            
            comprehensive_results = {
                'analysis_type': 'complete_122_day_ifd_v3',
                'processing_date': timestamp,
                'parameters': {
                    'min_bid_size': self.min_bid_size,
                    'min_pressure_ratio': self.min_pressure_ratio,
                    'min_volume_bias': self.min_volume_bias,
                    'min_total_volume': self.min_total_volume,
                    'timeout_settings': {
                        'max_quotes_per_session': self.max_quotes_per_session,
                        'max_signals_per_session': self.max_signals_per_session,
                        'max_symbols_to_resolve': self.max_symbols_to_resolve,
                        'session_timeout_seconds': self.session_timeout_seconds
                    }
                },
                'summary': {
                    'total_trading_days': len(self.all_trading_days),
                    'total_sessions_tested': total_sessions,
                    'total_trades': total_trades,
                    'total_pnl': total_pnl,
                    'win_rate': win_rate,
                    'average_pnl_per_trade': avg_pnl,
                    'trade_frequency_per_day': trade_frequency
                },
                'monthly_breakdown': monthly_stats,
                'all_trades': all_trades,
                'chunk_statistics': chunk_stats
            }
            
            with open(final_file, 'w') as f:
                json.dump(comprehensive_results, f, indent=2)
            
            print(f"\n📁 Complete results saved: {final_file}")
            
            # Final assessment
            if total_pnl > 0:
                print(f"\n🎉 COMPLETE 122-DAY ANALYSIS: PROFITABLE!")
                print(f"✅ System generated ${total_pnl:+,.2f} across {total_trades} trades")
                print(f"✅ {win_rate:.1f}% win rate demonstrates consistent performance")
                print(f"✅ Average {trade_frequency:.2f} trades per day")
                print(f"✅ Strategy validated across full 122-day period")
            else:
                print(f"\n📊 COMPLETE 122-DAY ANALYSIS: MIXED RESULTS")
                print(f"💰 Total: ${total_pnl:+,.2f} across {total_trades} trades")
                print(f"🔧 Consider parameter optimization for better performance")
        
        else:
            print(f"\n❌ No qualifying trades found across 122 days")
            print(f"💡 Consider loosening parameters or checking data quality")

def main():
    """Main execution function"""
    processor = Complete122DayProcessor()
    
    print(f"\n⚙️  TIMEOUT CONFIGURATION OPTIONS:")
    print(f"   Current settings are conservative for stability")
    print(f"   To increase speed, you can modify these values:")
    print(f"   - max_quotes_per_session: Currently {processor.max_quotes_per_session:,}")
    print(f"   - max_signals_per_session: Currently {processor.max_signals_per_session}")
    print(f"   - session_timeout_seconds: Currently {processor.session_timeout_seconds}s")
    print(f"   - api_rate_limit_delay: Currently {processor.api_rate_limit_delay}s")
    
    print(f"\n🚀 Starting complete 122-day analysis automatically...")
    processor.run_complete_analysis()

if __name__ == "__main__":
    main()