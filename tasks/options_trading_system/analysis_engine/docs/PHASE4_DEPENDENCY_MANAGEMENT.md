# Phase 4 Dependency Management System

## Overview

Phase 4 introduced a comprehensive dependency management system that maintains 100% functionality without external dependencies while offering enhanced features when optional packages are installed.

## Key Features

### 1. Multi-Tier Dependency Structure
- **Base** (`requirements/base.txt`): Core Python stdlib only - zero dependencies
- **Phase 4** (`requirements/phase4.txt`): Recommended enhancements for Phase 4 features
- **Optional** (`requirements/optional.txt`): All 17+ optional packages with descriptions
- **Full** (`requirements/full.txt`): Everything including development tools
- **Dev** (`requirements/dev.txt`): 50+ development and testing tools

### 2. Intelligent Fallback System
Every Phase 4 component includes fallback implementations:
- **pandas** → Basic dict/list operations
- **matplotlib** → Text-based logging
- **scipy** → Python statistics module
- **scikit-learn** → Rule-based optimization
- **numpy** → Built-in math operations
- **pytz** → Basic UTC operations

### 3. Enhanced Dependency Checker
```bash
python scripts/check_dependencies.py
```
Features:
- Category grouping (Phase 4 Core, Visualization, etc.)
- Installation status with versions
- Feature availability reporting
- Installation recommendations

### 4. Interactive Installation Script
```bash
./scripts/install_phase4.sh
```
Options:
1. Phase 4 core dependencies only
2. All optional dependencies
3. Development dependencies
4. Everything (full installation)
5. Check current status
6. Exit

### 5. CI/CD Integration
`.github/workflows/test-dependencies.yml` provides:
- Testing across Python 3.8-3.11
- Multiple OS support (Ubuntu, Windows, macOS)
- Dependency level testing (minimal, phase4, optional, full)
- Gradual dependency addition testing

## Quick Start

### Minimal Installation (Default)
```bash
# Just run - no dependencies needed!
python integration.py
```

### Phase 4 Features
```bash
pip install -r requirements/phase4.txt
```

### Full Features
```bash
pip install -r requirements/optional.txt
```

### Development Environment
```bash
pip install -r requirements/full.txt
```

## Virtual Environment Setup
See `docs/VIRTUAL_ENV_SETUP.md` for comprehensive setup instructions.

## Testing
- **Minimal**: `python scripts/test_minimal.py`
- **With dependencies**: Run standard test suite

## Architecture Benefits
1. **Zero-dependency baseline** ensures reliability
2. **Progressive enhancement** based on available packages
3. **Clear separation** between required and optional
4. **Robust fallbacks** prevent feature loss
5. **Easy deployment** in restricted environments

## Migration Path
1. Start with minimal (no dependencies)
2. Add Phase 4 dependencies for enhanced features
3. Optionally add visualization packages
4. Add development tools only for contributors

This approach ensures the system works everywhere while allowing power users to unlock enhanced functionality.
