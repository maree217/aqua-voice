#!/bin/bash
# Aqua Voice Runner
# Run this script to start Aqua Voice

cd "$(dirname "$0")"

# Create venv if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Check for .env
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    echo "Create one with: echo 'DEEPGRAM_API_KEY=your_key' > .env"
    exit 1
fi

echo ""
echo "=================================================="
echo "  Aqua Voice - System-Wide Voice Typing"
echo "=================================================="
echo ""
echo "  Double-tap Right Option (⌥): Start recording"
echo "  Single tap Right Option: Stop & keep text"
echo "  Escape: Cancel & delete text"
echo ""
echo "  Press Ctrl+C to quit"
echo "=================================================="
echo ""

python3 aqua_voice.py
