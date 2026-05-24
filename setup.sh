#!/bin/bash
echo "🚀 INITIATING OMNIAGENT OS: TURNKEY SETUP..."

# 1. Environment Verification
python3 --version || { echo "❌ Python 3 is required"; exit 1; }

# 2. Directory Structure
echo "📁 Creating workspace architecture..."
mkdir -p plugins knowledge exports logs tests

# 3. Dependencies
echo "📦 Installing neural and system dependencies..."
pip install -r requirements.txt

# 4. Default Context
echo "🧠 Initializing default knowledge profile..."
cat > knowledge/default.json <<EOF
{
  "user_name": "Human",
  "preferred_shell": "zsh",
  "operating_system": "macOS",
  "m1_optimization": true
}
EOF

# 5. Permissions Guidance
echo "--------------------------------------------------"
echo "✅ SYSTEM READY FOR DAILY OPERATION."
echo ""
echo "⚠️  CRITICAL: macOS SECURITY SETUP"
echo "1. Go to: System Settings > Privacy & Security > Accessibility"
echo "2. Add and Enable your Terminal (e.g., iTerm2 or Terminal.app)"
echo ""
echo "🚀 TO START: python3 main.py"
echo "--------------------------------------------------"
