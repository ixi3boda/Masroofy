#!/usr/bin/env bash
# One-time setup for macOS / Linux: create a virtual environment, install the
# requirements (including Whisper speech-to-text) and run the offline smoke test.
#   bash setup.sh
set -e
cd "$(dirname "$0")"

PY=python3
if ! command -v $PY >/dev/null 2>&1; then PY=python; fi
echo "Using $($PY --version)"

if [ ! -d .venv ]; then
  $PY -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-asr.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example (edit it to add API keys or change the Whisper model)."
fi

python scripts/smoke_test.py
echo
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  pytest -q"
echo "  python -m voice_expense.cli text \"صرفت 250 على groceries امبارح\" --now 2026-11-20T14:00"
