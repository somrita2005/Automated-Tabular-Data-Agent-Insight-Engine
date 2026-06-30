#!/bin/bash
# QueryAgent — Development Startup Script
# Usage: chmod +x start_dev.sh && ./start_dev.sh

set -e

echo "╔═══════════════════════════════════════╗"
echo "║        QueryAgent Dev Server          ║"
echo "╚═══════════════════════════════════════╝"

# Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "⚠️  ANTHROPIC_API_KEY not set."
  echo "   Run: export ANTHROPIC_API_KEY=sk-ant-..."
  exit 1
fi

# Generate sample data if missing
if [ ! -f "sample_data/survey_data.csv" ]; then
  echo "📊 Generating sample dataset..."
  python3 sample_data/generate_sample.py
fi

# Install Python deps if needed
echo "🐍 Checking Python dependencies..."
pip install -r backend/requirements.txt -q

# Install Node deps if needed
if [ ! -d "frontend/node_modules" ]; then
  echo "📦 Installing Node dependencies..."
  cd frontend && npm install && cd ..
fi

# Start Flask in background
echo "🚀 Starting Flask backend on :5000..."
python3 backend/app.py &
FLASK_PID=$!

# Start Vite dev server
echo "⚡ Starting Vite frontend on :5173..."
cd frontend && npm run dev &
VITE_PID=$!

echo ""
echo "✅ QueryAgent running!"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop both servers."

# Wait and handle shutdown
trap "kill $FLASK_PID $VITE_PID 2>/dev/null; echo 'Stopped.'" INT TERM
wait
