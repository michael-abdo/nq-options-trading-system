#!/bin/bash
# Wrapper script to run the daily options pipeline with venv

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
source "$DIR/venv/bin/activate"

# Run the pipeline with all arguments passed through
python3 "$DIR/daily_options_pipeline.py" "$@"

# Deactivate virtual environment
deactivate