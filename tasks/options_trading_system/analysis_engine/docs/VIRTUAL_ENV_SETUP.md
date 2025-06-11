# Virtual Environment Setup Guide

This guide provides step-by-step instructions for setting up a Python virtual environment for the IFD v3.0 Analysis Engine.

## Table of Contents
- [Why Use a Virtual Environment?](#why-use-a-virtual-environment)
- [Quick Start](#quick-start)
- [Detailed Setup Instructions](#detailed-setup-instructions)
- [Dependency Installation Options](#dependency-installation-options)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## Why Use a Virtual Environment?

Virtual environments provide isolated Python installations for your project:
- **Dependency Isolation**: Avoid conflicts with system-wide packages
- **Version Control**: Pin specific package versions for reproducibility
- **Clean Development**: Easy to reset or recreate environments
- **Multiple Projects**: Different projects can use different package versions

**Note**: The Analysis Engine works perfectly without any external dependencies! Virtual environments are only needed if you want to install optional enhancement packages.

## Quick Start

For experienced users, here's the quick setup:

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (choose one)
pip install -r requirements/phase4.txt    # Phase 4 features only
pip install -r requirements/optional.txt  # All optional features
pip install -r requirements/full.txt      # Everything

# Verify installation
python scripts/check_dependencies.py

# Deactivate when done
deactivate
```

## Detailed Setup Instructions

### Step 1: Check Python Version

Ensure you have Python 3.8 or higher:

```bash
python3 --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/).

### Step 2: Create Virtual Environment

Navigate to the analysis engine directory:

```bash
cd /path/to/tasks/options_trading_system/analysis_engine
```

Create a new virtual environment:

```bash
# Using venv (built into Python 3)
python3 -m venv venv

# Alternative: using virtualenv
pip install virtualenv
virtualenv venv
```

This creates a `venv` directory containing the isolated Python environment.

### Step 3: Activate Virtual Environment

**On macOS/Linux:**
```bash
source venv/bin/activate
```

**On Windows (Command Prompt):**
```cmd
venv\Scripts\activate.bat
```

**On Windows (PowerShell):**
```powershell
venv\Scripts\Activate.ps1
```

You should see `(venv)` in your terminal prompt, indicating the virtual environment is active.

### Step 4: Upgrade pip (Optional but Recommended)

```bash
pip install --upgrade pip
```

### Step 5: Install Dependencies

Choose your installation level based on your needs:

#### Option A: Minimal Installation (Default)
```bash
# No installation needed! The system works out of the box.
# Just run the code with Python standard library.
```

#### Option B: Phase 4 Core Features
```bash
pip install -r requirements/phase4.txt
```
Includes: pandas, numpy, matplotlib, scipy, scikit-learn, pytz

#### Option C: All Optional Features
```bash
pip install -r requirements/optional.txt
```
Includes: All enhancement packages for maximum functionality

#### Option D: Full Development Environment
```bash
pip install -r requirements/full.txt
```
Includes: Everything + development tools (pytest, black, mypy)

### Step 6: Verify Installation

Check which dependencies are installed:

```bash
python scripts/check_dependencies.py
```

Run a quick test:

```bash
python -c "from integration import AnalysisEngine; print('✅ Setup successful!')"
```

## Dependency Installation Options

### Using the Install Script

We provide an interactive installation script:

```bash
# Make it executable (first time only)
chmod +x scripts/install_phase4.sh

# Run the installer
./scripts/install_phase4.sh
```

The script offers these options:
1. Phase 4 core dependencies only
2. All optional dependencies
3. Development dependencies
4. Everything
5. Check current status

### Manual Installation

Install specific packages as needed:

```bash
# Data analysis
pip install pandas numpy

# Visualization
pip install matplotlib seaborn plotly

# Machine learning
pip install scikit-learn scipy

# Development tools
pip install pytest black mypy
```

## Troubleshooting

### Common Issues

#### 1. "pip: command not found"
```bash
# Install pip
python3 -m ensurepip

# Or on Ubuntu/Debian
sudo apt-get install python3-pip
```

#### 2. Permission Errors
Never use `sudo pip install`. Always use virtual environments or `--user` flag:
```bash
pip install --user package_name
```

#### 3. Virtual Environment Not Activating

**On Windows PowerShell:**
```powershell
# Enable script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Wrong Python Version:**
```bash
# Specify Python version explicitly
python3.8 -m venv venv
```

#### 4. Package Installation Fails

**Clear pip cache:**
```bash
pip cache purge
```

**Upgrade pip and setuptools:**
```bash
pip install --upgrade pip setuptools wheel
```

#### 5. Import Errors After Installation

**Ensure venv is activated:**
```bash
which python  # Should show path inside venv directory
```

**Reinstall package:**
```bash
pip uninstall package_name
pip install package_name
```

### Platform-Specific Issues

#### macOS
- If using system Python, consider installing Python via Homebrew
- For M1/M2 Macs, some packages may need special flags:
  ```bash
  pip install pandas --no-binary :all:
  ```

#### Windows
- Use Command Prompt or PowerShell as Administrator if needed
- Install Visual C++ Build Tools for packages with C extensions

#### Linux
- Install python3-dev package for building C extensions:
  ```bash
  sudo apt-get install python3-dev  # Debian/Ubuntu
  sudo yum install python3-devel     # RHEL/CentOS
  ```

## Best Practices

### 1. Always Use Virtual Environments
- One virtual environment per project
- Name it consistently (e.g., `venv`, `.venv`)
- Add `venv/` to `.gitignore`

### 2. Document Dependencies
- Keep requirements files up to date
- Use version pinning for production
- Separate dev and production dependencies

### 3. Regular Maintenance
```bash
# Check for outdated packages
pip list --outdated

# Update all packages
pip install --upgrade -r requirements/phase4.txt

# Freeze current versions
pip freeze > requirements/frozen.txt
```

### 4. Development Workflow
```bash
# Start work session
cd /path/to/analysis_engine
source venv/bin/activate

# Work on code...

# Install new package if needed
pip install new_package
echo "new_package>=1.0.0" >> requirements/optional.txt

# End work session
deactivate
```

### 5. Clean Environment Reset
```bash
# Deactivate if active
deactivate

# Remove old environment
rm -rf venv/

# Create fresh environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/phase4.txt
```

## IDE Integration

### VS Code
1. Open Command Palette (Cmd/Ctrl + Shift + P)
2. Select "Python: Select Interpreter"
3. Choose the interpreter from `./venv/bin/python`

### PyCharm
1. File → Settings → Project → Python Interpreter
2. Click gear icon → Add
3. Select "Existing Environment"
4. Browse to `venv/bin/python`

### Jupyter Notebooks
```bash
# Install ipykernel in venv
pip install ipykernel

# Add venv as Jupyter kernel
python -m ipykernel install --user --name=analysis_engine
```

## Conclusion

Remember: **The Analysis Engine works perfectly without any dependencies!** This guide is for users who want to enable optional enhancements like:
- Advanced visualizations (matplotlib)
- Faster data processing (pandas)
- Machine learning optimizations (scikit-learn)

For minimal usage, just run the code with Python 3.8+ standard library - no setup needed!