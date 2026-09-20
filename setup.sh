#!/usr/bin/env bash
set -e

echo "=========================================================="
echo " TypeSafe AI (Jev) & Local SLM Swarm Setup"
echo "=========================================================="

# 1. Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9+."
    exit 1
fi
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Found Python $PYTHON_VERSION"

# 2. Check Ollama
if command -v ollama &> /dev/null; then
    echo "✅ Found Ollama CLI"
    if curl -s http://127.0.0.1:11434/api/tags > /dev/null; then
        echo "✅ Ollama daemon is running"
        
        # Check / Build models if modelfiles exist
        if [ -f "scripts/modelfiles/Modelfile.2b" ]; then
            echo "ℹ️  Building / Checking huihui-qwen3.5:2b..."
            ollama create huihui-qwen3.5:2b -f scripts/modelfiles/Modelfile.2b || true
        fi
        if [ -f "scripts/modelfiles/Modelfile.08b" ]; then
            echo "ℹ️  Building / Checking huihui-qwen3.5:0.8b..."
            ollama create huihui-qwen3.5:0.8b -f scripts/modelfiles/Modelfile.08b || true
        fi
    else
        echo "⚠️  Ollama daemon does not seem to be running on http://127.0.0.1:11434"
        echo "   Please start Ollama with 'ollama serve'."
    fi
else
    echo "⚠️  Ollama not found. Install from https://ollama.com if you plan to run local SLM swarms."
fi

# 3. Check TypeSafe API Key
if [ -n "$TYPESAFE_API_KEY" ]; then
    echo "✅ TYPESAFE_API_KEY environment variable is set."
elif [[ "$OSTYPE" == "darwin"* ]]; then
    if security find-generic-password -s "network-infra-typesafe-jev" -w &> /dev/null; then
        echo "✅ Found TypeSafe API key in macOS Keychain."
    else
        echo "⚠️  TYPESAFE_API_KEY is not set."
        echo "   Export it using: export TYPESAFE_API_KEY=\"your_key_here\""
    fi
else
    echo "⚠️  TYPESAFE_API_KEY is not set."
    echo "   Export it using: export TYPESAFE_API_KEY=\"your_key_here\""
fi

# 4. Run connection test
echo "----------------------------------------------------------"
echo "Testing TypeSafe API Connection..."
python3 scripts/test_connection.py || true

echo "=========================================================="
echo " Setup complete! Ready to evaluate code and run swarms."
echo "=========================================================="
