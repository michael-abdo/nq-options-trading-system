#!/usr/bin/env python3
"""Test IFD v3 SQLite database setup for baselines"""

import os
import sys
import json
import sqlite3
from datetime import datetime
from pathlib import Path

# Add paths
sys.path.append('.')
sys.path.append('tasks/options_trading_system')

def test_ifd_v3_database():
    """Test IFD v3 database initialization"""
    print("=" * 50)
    print("Testing IFD v3 Database Setup")
    print("=" * 50)

    # Database configuration
    db_path = 'outputs/ifd_v3_baselines.db'

    try:
        # Import IFD v3 components
        from analysis_engine.institutional_flow_v3.solution import HistoricalBaselineManager

        print(f"✅ IFD v3 module imported successfully")

        # Create output directory if needed
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # Initialize baseline manager (this creates the database)
        print(f"\n📊 Initializing baseline manager...")
        baseline_manager = HistoricalBaselineManager(db_path, lookback_days=20)

        print(f"✅ Baseline manager initialized")
        print(f"   Database path: {db_path}")
        print(f"   Lookback days: 20")

        # Verify database was created
        if os.path.exists(db_path):
            print(f"✅ Database file created: {db_path}")

            # Check database schema
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()

                # Get table names
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()

                print(f"\n📋 Database tables:")
                for table in tables:
                    print(f"   - {table[0]}")

                    # Get column info for each table
                    cursor.execute(f"PRAGMA table_info({table[0]});")
                    columns = cursor.fetchall()
                    for col in columns:
                        print(f"     • {col[1]} ({col[2]})")

                # Check indexes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
                indexes = cursor.fetchall()

                if indexes:
                    print(f"\n🔍 Database indexes:")
                    for idx in indexes:
                        print(f"   - {idx[0]}")
        else:
            print(f"❌ Database file not created")
            return False

        # Test baseline functionality
        print(f"\n🧪 Testing baseline functionality...")

        # Create a test baseline context
        baseline_context = baseline_manager.get_baseline_context(21900.0, 'C')

        print(f"✅ Baseline context retrieved:")
        print(f"   Strike: {baseline_context.strike}")
        print(f"   Type: {baseline_context.option_type}")
        print(f"   Mean pressure ratio: {baseline_context.mean_pressure_ratio:.2f}")
        print(f"   Data quality: {baseline_context.data_quality:.1%}")

        # Save test results
        results = {
            "timestamp": datetime.now().isoformat(),
            "database_created": True,
            "database_path": db_path,
            "tables_created": [t[0] for t in tables],
            "indexes_created": [i[0] for i in indexes] if indexes else [],
            "baseline_test": {
                "strike": baseline_context.strike,
                "option_type": baseline_context.option_type,
                "mean_pressure_ratio": baseline_context.mean_pressure_ratio,
                "data_quality": baseline_context.data_quality
            },
            "test_status": "PASSED"
        }

        with open("outputs/ifd_v3_database_test.json", "w") as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ IFD v3 database setup successful!")
        print(f"📝 Results saved to outputs/ifd_v3_database_test.json")
        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")

        results = {
            "timestamp": datetime.now().isoformat(),
            "database_created": False,
            "error": str(e),
            "test_status": "FAILED"
        }

        with open("outputs/ifd_v3_database_test.json", "w") as f:
            json.dump(results, f, indent=2)

        return False

if __name__ == "__main__":
    test_ifd_v3_database()
