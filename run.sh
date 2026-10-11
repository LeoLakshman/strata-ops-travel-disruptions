#!/usr/bin/env bash
# ==============================================================================
# STRATA OPS - Corporate Travel Disruption Intelligence Prototype
# Launch script for development & evaluation
# ==============================================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "======================================================================"
echo "  STRATA OPS // U.S. Corporate Travel Disruption Intelligence Platform"
echo "======================================================================"

# Check Python environment
if [ -d ".venv" ]; then
    PYTHON_EXEC=".venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON_EXEC="python3"
elif command -v python &>/dev/null; then
    PYTHON_EXEC="python"
else
    echo "Error: Python 3 is required but not found."
    exit 1
fi

echo "Using Python: $($PYTHON_EXEC --version)"

# Check requirements
echo "Checking dependencies..."
$PYTHON_EXEC -c "import fastapi, uvicorn, httpx, pydantic" 2>/dev/null || {
    echo "Installing required Python packages..."
    $PYTHON_EXEC -m pip install -r requirements.txt
}

PORT=${PORT:-8000}
HOST=${HOST:-0.0.0.0}

echo ""
echo "🚀 Starting Strata Ops Web Server on http://localhost:$PORT"
echo "   Live UI: http://localhost:$PORT"
echo "   Interactive API Docs: http://localhost:$PORT/docs"
echo "   Press Ctrl+C to stop the server."
echo ""

exec $PYTHON_EXEC -m uvicorn app.main:app --host "$HOST" --port "$PORT"
