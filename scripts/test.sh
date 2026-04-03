#!/usr/bin/env bash
set -euo pipefail

# The native Bosatsu CLI can exhaust smaller default stacks on the growing
# benchmark suite in CI, especially on Linux native-image builds. Raise the
# soft limit aggressively when the host allows it, but keep smaller fallbacks
# for environments that reject the larger values.
ulimit -S -s 65532 2>/dev/null || \
  ulimit -S -s 32768 2>/dev/null || \
  ulimit -S -s 16384 2>/dev/null || \
  true

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

./bosatsu --fetch > /dev/null
./bosatsu fetch
./bosatsu check
./bosatsu test

MANDELBROT_FIXTURE="$REPO_ROOT/fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm"
MANDELBROT_TMPDIR="$(mktemp -d)"
cleanup() {
  rm -rf "$MANDELBROT_TMPDIR"
}
trap cleanup EXIT

MANDELBROT_JVM_OUT="$MANDELBROT_TMPDIR/mandelbrot-jvm.pbm"
./bosatsu eval --main Zafu/Benchmark/Game/Mandelbrot::main --run 200 > "$MANDELBROT_JVM_OUT"
cmp -s "$MANDELBROT_FIXTURE" "$MANDELBROT_JVM_OUT" || {
  echo "mandelbrot bosatsu eval output did not match the checked-in fixture" >&2
  exit 1
}

MANDELBROT_C_OUTDIR="$MANDELBROT_TMPDIR/mandelbrot-c"
MANDELBROT_C_EXE="$MANDELBROT_C_OUTDIR/mandelbrot"
MANDELBROT_C_OUT="$MANDELBROT_TMPDIR/mandelbrot-c.pbm"
./bosatsu build --main_pack Zafu/Benchmark/Game/Mandelbrot --outdir "$MANDELBROT_C_OUTDIR" --exe_out "$MANDELBROT_C_EXE"
"$MANDELBROT_C_EXE" 200 > "$MANDELBROT_C_OUT"
cmp -s "$MANDELBROT_FIXTURE" "$MANDELBROT_C_OUT" || {
  echo "mandelbrot compiled executable output did not match the checked-in fixture" >&2
  exit 1
}

MANDELBROT_NEGATIVE_OUT="$MANDELBROT_TMPDIR/mandelbrot-negative.stdout"
if "$MANDELBROT_C_EXE" -1 > "$MANDELBROT_NEGATIVE_OUT" 2>"$MANDELBROT_TMPDIR/mandelbrot-negative.stderr"; then
  echo "mandelbrot compiled executable accepted a negative size" >&2
  exit 1
else
  MANDELBROT_NEGATIVE_STATUS=$?
fi

if [ "$MANDELBROT_NEGATIVE_STATUS" -ne 2 ]; then
  echo "mandelbrot compiled executable returned $MANDELBROT_NEGATIVE_STATUS for a negative size instead of exit code 2" >&2
  exit 1
fi

if [ -s "$MANDELBROT_NEGATIVE_OUT" ]; then
  echo "mandelbrot compiled executable wrote stdout bytes for a negative size" >&2
  exit 1
fi

OUTDIR="${OUTDIR:-"$REPO_ROOT/.bosatsu_lib_publish_dry_run"}"
URI_BASE="${URI_BASE:-https://example.invalid/}"
if GIT_SHA_DEFAULT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)"; then
  :
else
  GIT_SHA_DEFAULT="local"
fi
GIT_SHA="${GIT_SHA:-"$GIT_SHA_DEFAULT"}"

REPO_ROOT="$REPO_ROOT" \
OUTDIR="$OUTDIR" \
GIT_SHA="$GIT_SHA" \
URI_BASE="$URI_BASE" \
"$REPO_ROOT/scripts/publish_bosatsu_libs.sh" --dry-run
