#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

./bosatsu --fetch > /dev/null
./bosatsu lib fetch
./bosatsu lib eval --main Zafu/Benchmark/Vector::main --run "$@"
