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
        echo "✅ Ollama daemon is running on http://127.0.0.1:11434"
        
        # Check / Build models with 32k context optimization
        if [ -f "scripts/modelfiles/Modelfile.qwen3.5-4b" ]; then
            echo "ℹ️  Building / Optimizing qwen3.5:4b (32k context)..."
            ollama pull qwen3.5:4b || true
            ollama create qwen3.5:4b -f scripts/modelfiles/Modelfile.qwen3.5-4b || true
        fi
        if [ -f "scripts/modelfiles/Modelfile.qwen3.5-2b" ]; then
            echo "ℹ️  Building / Optimizing qwen3.5:2b (32k context)..."
            ollama pull qwen3.5:2b || true
            ollama create qwen3.5:2b -f scripts/modelfiles/Modelfile.qwen3.5-2b || true
        fi
    else
        echo "⚠️  Ollama daemon does not seem to be running on http://127.0.0.1:11434"
        echo "   Please start Ollama with 'ollama serve'."
    fi
else
    echo "⚠️  Ollama not found. Install from https://ollama.com if you plan to run local SLM swarms."
fi

# 3. Fast Proxy Check / Setup
if [ -f "scripts/ollama_fast_proxy.py" ]; then
    echo "----------------------------------------------------------"
    echo "Checking Ollama Fast Proxy (Port 11435)..."
    if curl -s http://127.0.0.1:11435/v1/models > /dev/null 2>&1; then
        echo "✅ Fast Proxy is active on http://127.0.0.1:11435 (No-Think / 32k context enforced)"
    else
        echo "ℹ️  Fast Proxy not running on port 11435."
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "   Installing background LaunchAgent..."
            python3 scripts/ollama_fast_proxy.py --install-daemon || true
        else
            echo "   To start the proxy in the background, run:"
            echo "   nohup python3 scripts/ollama_fast_proxy.py > /dev/null 2>&1 &"
        fi
    fi
fi

# 4. Check TypeSafe API Key
echo "----------------------------------------------------------"
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

# 5. Run connection test
echo "----------------------------------------------------------"
echo "Testing TypeSafe API Connection..."
python3 scripts/test_connection.py || true

echo "=========================================================="
echo " Setup complete! Ready to evaluate code and run swarms."
echo "=========================================================="
