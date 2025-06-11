#!/usr/bin/env python3
"""
Dependency Checker for Analysis Engine
Checks which optional dependencies are installed and reports feature availability
"""

import sys
import importlib
from typing import Dict, Tuple, List

def check_module(module_name: str) -> Tuple[bool, str]:
    """Check if a module is installed and return version if available"""
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, '__version__', 'unknown')
        return True, version
    except ImportError:
        return False, None

def main():
    """Check all optional dependencies and report status"""
    print("=" * 60)
    print("ANALYSIS ENGINE DEPENDENCY CHECK")
    print("=" * 60)
    
    # Define dependencies and their features
    dependencies = {
        'pandas': {
            'features': [
                'Advanced data analysis',
                'DataFrame operations', 
                'Efficient data aggregation'
            ],
            'fallback': 'Basic dict/list operations'
        },
        'numpy': {
            'features': [
                'Fast numerical computations',
                'Statistical calculations',
                'Array operations'
            ],
            'fallback': 'Python built-in math operations'
        },
        'matplotlib': {
            'features': [
                'Budget visualization dashboards',
                'Performance charts',
                'Real-time monitoring plots'
            ],
            'fallback': 'Text-based logging only'
        },
        'scipy': {
            'features': [
                'Statistical significance testing',
                'A/B test p-value calculations',
                'Advanced statistical functions'
            ],
            'fallback': 'Basic statistical calculations'
        },
        'sklearn': {
            'features': [
                'ML-based threshold optimization',
                'Adaptive learning algorithms',
                'Multi-objective optimization'
            ],
            'fallback': 'Rule-based threshold adjustments'
        },
        'pytz': {
            'features': [
                'Accurate timezone conversions',
                'Market hours handling',
                'DST awareness'
            ],
            'fallback': 'Basic UTC operations'
        }
    }
    
    # Check each dependency
    installed = []
    missing = []
    
    print("\nChecking dependencies...\n")
    
    for module, info in dependencies.items():
        installed_status, version = check_module(module)
        
        if installed_status:
            installed.append(module)
            print(f"✅ {module:<12} {version:<10} - INSTALLED")
            print(f"   Features enabled:")
            for feature in info['features']:
                print(f"   • {feature}")
        else:
            missing.append(module)
            print(f"❌ {module:<12} {'N/A':<10} - NOT INSTALLED")
            print(f"   Fallback: {info['fallback']}")
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Installed: {len(installed)}/{len(dependencies)}")
    print(f"Missing:   {len(missing)}/{len(dependencies)}")
    
    # Feature availability
    print("\n🚀 SYSTEM STATUS:")
    if len(installed) == len(dependencies):
        print("✅ All features enabled - Full functionality available!")
    elif len(installed) == 0:
        print("⚠️  Running in minimal mode - All features using fallbacks")
        print("   The system is fully functional but with basic implementations")
    else:
        print("🔧 Mixed mode - Some enhanced features available")
        print(f"   Enhanced: {', '.join(installed)}")
        print(f"   Fallback: {', '.join(missing)}")
    
    # Installation instructions
    if missing:
        print("\n📦 TO ENABLE ALL FEATURES:")
        print("pip install -r requirements/phase4.txt")
        print("\nOr install specific packages:")
        for module in missing:
            print(f"pip install {module}")
    
    print("\n✨ NOTE: The system works perfectly without optional dependencies!")
    print("Optional packages only enhance functionality, not core operations.")
    
    return 0 if len(installed) >= len(dependencies) // 2 else 1

if __name__ == "__main__":
    sys.exit(main())