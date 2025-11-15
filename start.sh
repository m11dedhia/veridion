#!/bin/bash
# Startup script for Daytona sandbox
# This ensures the Flask app runs automatically when the sandbox starts

echo "🚀 Starting AI QA Engineer in Daytona sandbox..."

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Installing dependencies..."
    pip install --no-cache-dir -r requirements.txt
fi

# Load environment variables
if [ -f .env ]; then
    echo "✓ Loading environment variables from .env"
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if API keys are set
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "⚠️  Warning: No LLM API keys found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
fi

# Start Flask app
echo "🌐 Starting Flask web server on port 5000..."
echo "   Access the dashboard at: http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

python app.py

