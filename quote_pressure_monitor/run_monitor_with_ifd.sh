#!/bin/bash
# Run the enhanced quote pressure monitor with IFD v3 integration

echo "🚀 Starting Enhanced NQ Options Quote Pressure Monitor with IFD v3"
echo "================================================================"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the enhanced monitor
python nq_options_quote_pressure_with_ifd.py
