import databento as db
from datetime import datetime, timedelta, timezone
import pandas as pd

# API key
import os
api_key = os.environ.get("DATABENTO_API_KEY", "your-api-key-here")
client = db.Historical(api_key)

print("📊 NQM5 VOLUME ANALYSIS")
print("=" * 70)
print(f"Current Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
print("=" * 70)

# Get data for the full trading session (including extended hours)
# June 13, 2025 - from previous day close to latest available
end = datetime(2025, 6, 13, 13, 30, 0, tzinfo=timezone.utc)  # 9:30 AM ET
start = datetime(2025, 6, 12, 20, 0, 0, tzinfo=timezone.utc)  # Previous day 4:00 PM ET

try:
    # Get all trades for volume analysis
    print("\nFetching NQM5 trading data...")
    data = client.timeseries.get_range(
        dataset="GLBX.MDP3",
        symbols=["NQM5"],
        schema="trades",
        start=start,
        end=end,
        limit=50000  # Get more data for volume analysis
    )

    df = data.to_df()

    if not df.empty:
        print(f"✅ Retrieved {len(df):,} trades")

        # Convert timestamps to ET
        df['ts_et'] = df['ts_event'].dt.tz_convert('US/Eastern')
        df['hour'] = df['ts_et'].dt.hour
        df['date'] = df['ts_et'].dt.date

        # Overall statistics
        print(f"\n📈 OVERALL STATISTICS (June 12 4PM - June 13 9:30AM ET)")
        print("-" * 60)
        print(f"Total Volume: {df['size'].sum():,} contracts")
        print(f"Total Trades: {len(df):,}")
        print(f"Average Trade Size: {df['size'].mean():.1f} contracts")
        print(f"Largest Trade: {df['size'].max()} contracts")
        print(f"Price Range: ${df['price'].min():,.2f} - ${df['price'].max():,.2f}")
        print(f"Price Change: ${df['price'].iloc[-1] - df['price'].iloc[0]:+,.2f}")

        # Volume by hour
        print(f"\n⏰ VOLUME BY HOUR (ET)")
        print("-" * 60)
        hourly_volume = df.groupby(['date', 'hour'])['size'].agg(['sum', 'count'])
        hourly_volume.columns = ['Volume', 'Trades']

        for (date, hour), row in hourly_volume.iterrows():
            time_label = f"{hour:02d}:00-{hour:02d}:59"
            if hour >= 9 and hour < 16:
                session = "RTH"  # Regular Trading Hours
            else:
                session = "ETH"  # Extended Trading Hours
            print(f"{date} {time_label} ({session}): {row['Volume']:>8,} contracts ({row['Trades']:>6,} trades)")

        # Session breakdown
        print(f"\n📊 SESSION BREAKDOWN")
        print("-" * 60)

        # Define sessions
        rth_mask = (df['hour'] >= 9) & (df['hour'] < 16) & (df['date'] == df['date'].max())
        eth_mask = ~rth_mask

        rth_volume = df[rth_mask]['size'].sum()
        eth_volume = df[eth_mask]['size'].sum()
        total_volume = df['size'].sum()

        print(f"Regular Trading Hours (RTH): {rth_volume:,} contracts ({rth_volume/total_volume*100:.1f}%)")
        print(f"Extended Trading Hours (ETH): {eth_volume:,} contracts ({eth_volume/total_volume*100:.1f}%)")

        # Price levels with volume
        print(f"\n💰 VOLUME AT PRICE LEVELS")
        print("-" * 60)

        # Round prices to nearest $5 for grouping
        df['price_level'] = (df['price'] / 5).round() * 5
        price_volume = df.groupby('price_level')['size'].sum().sort_values(ascending=False).head(10)

        print("Top 10 Price Levels by Volume:")
        for price, volume in price_volume.items():
            pct = volume / total_volume * 100
            print(f"  ${price:,.0f}: {volume:>8,} contracts ({pct:>4.1f}%)")

        # Recent activity (last hour)
        recent_cutoff = df['ts_event'].max() - pd.Timedelta(hours=1)
        recent_df = df[df['ts_event'] > recent_cutoff]

        print(f"\n🔥 LAST HOUR ACTIVITY")
        print("-" * 60)
        print(f"Volume: {recent_df['size'].sum():,} contracts")
        print(f"Trades: {len(recent_df):,}")
        print(f"Avg Trade Size: {recent_df['size'].mean():.1f} contracts")
        print(f"Price Range: ${recent_df['price'].min():,.2f} - ${recent_df['price'].max():,.2f}")

        # Large trades (>= 10 contracts)
        large_trades = df[df['size'] >= 10].copy()
        if not large_trades.empty:
            print(f"\n🐋 LARGE TRADES (≥10 contracts)")
            print("-" * 60)
            print(f"Count: {len(large_trades)} trades")
            print(f"Total Volume: {large_trades['size'].sum():,} contracts")
            print(f"Largest 5 trades:")

            largest = large_trades.nlargest(5, 'size')
            for _, trade in largest.iterrows():
                print(f"  {trade['size']:>3} contracts @ ${trade['price']:,.2f} at {trade['ts_et'].strftime('%I:%M:%S %p')}")

        # VWAP calculation
        df['value'] = df['price'] * df['size']
        vwap = df['value'].sum() / df['size'].sum()

        print(f"\n📊 VOLUME-WEIGHTED METRICS")
        print("-" * 60)
        print(f"VWAP: ${vwap:,.2f}")
        print(f"Current Price: ${df['price'].iloc[-1]:,.2f}")
        print(f"Price vs VWAP: ${df['price'].iloc[-1] - vwap:+.2f} ({(df['price'].iloc[-1] / vwap - 1) * 100:+.1f}%)")

    else:
        print("❌ No trading data found")

except Exception as e:
    print(f"Error: {e}")

print("\n" + "=" * 70)
