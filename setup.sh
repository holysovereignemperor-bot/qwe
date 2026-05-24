#!/bin/bash
echo "🚀 OMNIAGENT OS: TRANSCENDENCE EDITION SETUP..."

# 1. Verification
python3 --version || { echo "❌ Python 3 required"; exit 1; }

# 2. Workspace
mkdir -p plugins knowledge/docs logs/history exports tests

# 3. Dependencies
pip install -r requirements.txt
pip install py2app psutil numpy

# 4. Neural Initializers
cat > knowledge/default.json <<EOF
{
  "user_name": "Explorer",
  "operating_system": "macOS",
  "m1_optimization": true,
  "edition": "Transcendence"
}
EOF

# 5. Native Linked Verification
python3 -c "import Cocoa; import Quartz; print('✅ Native macOS Neural Engines Linked')"

echo "✅ TRANSCENDENCE SYSTEM READY."
echo "🚀 TO START: python3 main.py"
echo "--------------------------------------------------"
