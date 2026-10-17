#!/bin/bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 is required but was not found."
  echo "Install Python 3 from https://www.python.org/downloads/macos/"
  read -r -p "Press Enter to close..."
  exit 1
fi

if [ ! -x ".venv/bin/uvicorn" ]; then
  echo "The project environment is not ready. Running the setup..."
  python3 -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

echo "Starting Shift Handover Briefing..."
echo "Open http://127.0.0.1:8000 in your browser."
echo "Press Ctrl+C to stop the server."

(
  sleep 2
  open "http://127.0.0.1:8000"
) &

PYTHONPATH="$PROJECT_DIR" .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
