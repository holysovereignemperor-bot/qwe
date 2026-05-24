#!/bin/bash
echo "🚀 OMNIAGENT OS: GENESIS EDITION SETUP..."

# 1. Environment Verification
python3 --version || { echo "❌ Python 3 is required"; exit 1; }

# 2. Directory Structure
echo "📁 Creating Genesis Architecture..."
mkdir -p plugins knowledge/docs logs/history exports tests

# 3. Dependencies
echo "📦 Installing Genesis dependencies..."
pip install -r requirements.txt
pip install py2app # For packaging support

# 4. Default Context
echo "🧠 Initializing Genesis knowledge..."
cat > knowledge/default.json <<EOF
{
  "user_name": "Human",
  "operating_system": "macOS",
  "m1_optimization": true,
  "edition": "Genesis"
}
EOF

# 5. Native Packaging Concept (Concept only, run manually if needed)
cat > setup_app.py <<EOF
from setuptools import setup
APP = ['main.py']
DATA_FILES = ['knowledge', 'plugins']
OPTIONS = {
    'argv_emulation': True,
    'plist': {
        'LSUIElement': True,
    },
    'packages': ['customtkinter', 'PIL', 'openai', 'fastapi', 'uvicorn'],
}
setup(app=APP, data_files=DATA_FILES, options={'py2app': OPTIONS}, setup_requires=['py2app'])
EOF

echo "✅ GENESIS SYSTEM READY."
echo ""
echo "🚀 TO START: python3 main.py"
echo "📦 TO PACKAGE: python3 setup_app.py py2app"
echo "--------------------------------------------------"
