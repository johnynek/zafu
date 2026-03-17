#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

./scripts/test_launcher_passthrough.sh
./bosatsu --fetch > /dev/null
./bosatsu lib fetch
./bosatsu lib check
./bosatsu lib test

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
