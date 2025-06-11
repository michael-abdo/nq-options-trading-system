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
            'fallback': 'Basic dict/list operations',
            'category': 'Phase 4 Core'
        },
        'numpy': {
            'features': [
                'Fast numerical computations',
                'Statistical calculations',
                'Array operations'
            ],
            'fallback': 'Python built-in math operations',
            'category': 'Phase 4 Core'
        },
        'matplotlib': {
            'features': [
                'Budget visualization dashboards',
                'Performance charts',
                'Real-time monitoring plots'
            ],
            'fallback': 'Text-based logging only',
            'category': 'Phase 4 Core'
        },
        'scipy': {
            'features': [
                'Statistical significance testing',
                'A/B test p-value calculations',
                'Advanced statistical functions'
            ],
            'fallback': 'Basic statistical calculations',
            'category': 'Phase 4 Core'
        },
        'sklearn': {
            'features': [
                'ML-based threshold optimization',
                'Adaptive learning algorithms',
                'Multi-objective optimization'
            ],
            'fallback': 'Rule-based threshold adjustments',
            'category': 'Phase 4 Core'
        },
        'pytz': {
            'features': [
                'Accurate timezone conversions',
                'Market hours handling',
                'DST awareness'
            ],
            'fallback': 'Basic UTC operations',
            'category': 'Phase 4 Core'
        },
        'seaborn': {
            'features': [
                'Statistical visualizations',
                'A/B testing result plots',
                'Correlation heatmaps'
            ],
            'fallback': 'Basic matplotlib or text output',
            'category': 'Enhanced Visualization'
        },
        'plotly': {
            'features': [
                'Interactive web dashboards',
                'Real-time streaming plots',
                '3D volatility surfaces'
            ],
            'fallback': 'Static plots or text output',
            'category': 'Enhanced Visualization'
        },
        'pydantic': {
            'features': [
                'Runtime type validation',
                'Configuration validation',
                'Better error messages'
            ],
            'fallback': 'Manual validation with dataclasses',
            'category': 'Data Validation'
        },
        'psutil': {
            'features': [
                'System resource monitoring',
                'Process performance metrics',
                'Network I/O statistics'
            ],
            'fallback': 'Basic os module tracking',
            'category': 'Performance Monitoring'
        },
        'sqlalchemy': {
            'features': [
                'Advanced database ORM',
                'Connection pooling',
                'Database migrations'
            ],
            'fallback': 'Direct sqlite3 operations',
            'category': 'Database Enhancement'
        },
        'requests': {
            'features': [
                'Robust HTTP client',
                'Connection pooling',
                'Retry logic'
            ],
            'fallback': 'urllib for basic HTTP',
            'category': 'API Enhancement'
        },
        'websocket-client': {
            'features': [
                'Enhanced WebSocket management',
                'Auto-reconnection',
                'Better error handling'
            ],
            'fallback': 'Basic WebSocket implementation',
            'category': 'API Enhancement'
        },
        'structlog': {
            'features': [
                'Structured JSON logging',
                'Context-aware logs',
                'Better log aggregation'
            ],
            'fallback': 'Standard logging module',
            'category': 'Logging Enhancement'
        },
        'pytest': {
            'features': [
                'Advanced test discovery',
                'Parallel test execution',
                'Better test reporting'
            ],
            'fallback': 'unittest module',
            'category': 'Testing'
        },
        'black': {
            'features': [
                'Automatic code formatting',
                'Consistent code style'
            ],
            'fallback': 'Manual formatting',
            'category': 'Development'
        },
        'mypy': {
            'features': [
                'Static type checking',
                'Early bug detection'
            ],
            'fallback': 'Runtime type checking only',
            'category': 'Development'
        }
    }
    
    # Check each dependency
    installed = []
    missing = []
    categories = {}
    
    print("\nChecking dependencies...\n")
    
    # Group by category
    for module, info in dependencies.items():
        category = info.get('category', 'Other')
        if category not in categories:
            categories[category] = []
        categories[category].append((module, info))
    
    # Display by category
    for category in ['Phase 4 Core', 'Enhanced Visualization', 'Data Validation', 
                     'Performance Monitoring', 'Database Enhancement', 'API Enhancement',
                     'Logging Enhancement', 'Testing', 'Development']:
        if category not in categories:
            continue
            
        print(f"\n{'='*60}")
        print(f"{category.upper()}")
        print(f"{'='*60}")
        
        for module, info in categories[category]:
            installed_status, version = check_module(module)
            
            if installed_status:
                installed.append(module)
                print(f"✅ {module:<20} {version:<10} - INSTALLED")
                print(f"   Features enabled:")
                for feature in info['features']:
                    print(f"   • {feature}")
            else:
                missing.append(module)
                print(f"❌ {module:<20} {'N/A':<10} - NOT INSTALLED")
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
        print("\n📦 INSTALLATION OPTIONS:")
        
        # Check which are Phase 4 core
        phase4_missing = [m for m in missing if any(
            mod == m and info.get('category') == 'Phase 4 Core' 
            for mod, info in dependencies.items()
        )]
        
        if phase4_missing:
            print("\n1. Install Phase 4 core dependencies:")
            print("   pip install -r requirements/phase4.txt")
        
        print("\n2. Install ALL optional dependencies:")
        print("   pip install -r requirements/optional.txt")
        
        print("\n3. Install specific packages:")
        for module in missing[:5]:  # Show first 5
            print(f"   pip install {module}")
        if len(missing) > 5:
            print(f"   ... and {len(missing)-5} more")
    
    print("\n✨ NOTE: The system works perfectly without optional dependencies!")
    print("Optional packages only enhance functionality, not core operations.")
    
    # Detailed status
    print("\n📊 DEPENDENCY CATEGORIES:")
    for category in ['Phase 4 Core', 'Enhanced Visualization', 'Testing', 'Development']:
        cat_mods = [m for m, i in dependencies.items() if i.get('category') == category]
        cat_installed = [m for m in cat_mods if m in installed]
        print(f"   {category}: {len(cat_installed)}/{len(cat_mods)} installed")
    
    return 0 if len(installed) >= len(dependencies) // 2 else 1

if __name__ == "__main__":
    sys.exit(main())