#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "scripts/benchmarksgame_compare.sh: python3 or python is required" >&2
  exit 1
fi

exec "$PYTHON" "$REPO_ROOT/scripts/benchmarksgame_compare.py" "$@"
