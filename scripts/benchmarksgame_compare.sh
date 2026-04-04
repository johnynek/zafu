#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

python_is_compatible() {
  "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1
}

if command -v python3 >/dev/null 2>&1 && python_is_compatible python3; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1 && python_is_compatible python; then
  PYTHON=python
else
  echo "scripts/benchmarksgame_compare.sh: Python 3.10+ is required" >&2
  exit 1
fi

exec "$PYTHON" "$REPO_ROOT/scripts/benchmarksgame_compare.py" "$@"
