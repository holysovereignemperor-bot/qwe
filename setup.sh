#!/bin/bash
echo "🚀 Bootstrapping OmniAgent OS..."

# Check Python version
python3 --version || { echo "Python 3 is required"; exit 1; }

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p plugins knowledge exports logs

echo "✅ Environment ready."
echo "⚠️  IMPORTANT: Please ensure 'Accessibility' permissions are granted to your Terminal/IDE in System Settings > Privacy & Security."
echo "To run: python3 main.py"
