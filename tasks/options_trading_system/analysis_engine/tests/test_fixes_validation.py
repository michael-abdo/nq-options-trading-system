#!/usr/bin/env python3
"""
Quick validation test for Phase 4 fixes
"""

import sys
import os
import time
from datetime import datetime

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monitoring.performance_dashboard import create_dashboard
from strategies.production_error_handler import create_error_handler


def test_performance_dashboard_fix():
    """Test that the slice error in performance dashboard is fixed"""
    try:
        print("🔧 Testing performance dashboard fix...")
        
        dashboard = create_dashboard()
        dashboard.start_dashboard()
        
        # Record some cost data to populate cost_records
        dashboard.record_cost("DATABENTO", "v1.0", api_calls=100, total_cost=1.50)
        dashboard.record_cost("DATABENTO", "v3.0", api_calls=150, total_cost=2.25)
        
        # This was the line causing the slice error
        comparison = dashboard.get_algorithm_comparison()
        
        dashboard.stop_dashboard()
        
        print("✅ Performance dashboard fix verified")
        return True
        
    except Exception as e:
        print(f"❌ Performance dashboard fix failed: {e}")
        return False


def test_error_handler_basic():
    """Test basic error handler functionality"""
    try:
        print("🔧 Testing error handler basics...")
        
        error_handler = create_error_handler()
        
        # Test basic functionality without stream recovery
        error_id = error_handler.record_error(
            "test_component",
            "TEST_ERROR", 
            "Basic test error"
        )
        
        # Test data quality
        good_data = {"symbol": "NQM25", "strike": 21350, "volume": 1000, "open_interest": 5000}
        score = error_handler.check_data_quality(good_data, "test_source")
        
        # Get health report
        health = error_handler.get_system_health()
        
        checks = [
            error_id is not None,
            score > 0.8,  # Good data should score well
            health["overall_status"] in ["HEALTHY", "DEGRADED"]
        ]
        
        if all(checks):
            print("✅ Error handler basic functionality verified")
            return True
        else:
            print("❌ Error handler basic checks failed")
            return False
        
    except Exception as e:
        print(f"❌ Error handler test failed: {e}")
        return False


def main():
    """Run validation tests"""
    print("🧪 Running Phase 4 fixes validation...")
    print("=" * 50)
    
    tests = [
        ("Performance Dashboard Fix", test_performance_dashboard_fix),
        ("Error Handler Basic", test_error_handler_basic)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 {test_name}")
        print("-" * 30)
        
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"💥 {test_name} error: {e}")
    
    print(f"\n{'='*50}")
    print(f"📊 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All fixes validated successfully!")
        return True
    else:
        print("❌ Some fixes still need attention")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)