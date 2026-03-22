#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

./bosatsu --fetch > /dev/null
./bosatsu fetch

echo "JVM benchmarks:"
./bosatsu eval --main Zafu/Benchmark/Vector::main --run "$@"

echo
echo "C benchmarks:"
BUILD_DIR="${BUILD_DIR:-"$REPO_ROOT/.bosatsu_bench"}"
EXE_PATH="${EXE_PATH:-"$BUILD_DIR/benchmark_vector"}"
mkdir -p "$BUILD_DIR"
./bosatsu build \
  --main_pack Zafu/Benchmark/Vector \
  --outdir "$BUILD_DIR" \
  --exe_out "$EXE_PATH"
"$EXE_PATH" "$@"
