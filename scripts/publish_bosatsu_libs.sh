#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/publish_bosatsu_libs.sh [--dry-run]

Options:
  --dry-run  Validate that publish succeeds without mutating *_conf.json files
  --help     Show this help text
EOF
}

DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -n "${REPO_ROOT:-}" ]]; then
  REPO_ROOT="${REPO_ROOT%/}"
else
  if REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    :
  else
    REPO_ROOT="$(pwd)"
  fi
fi

OUTDIR="${OUTDIR:-"$REPO_ROOT/.bosatsu_lib_publish"}"
if GIT_SHA_DEFAULT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null)"; then
  :
else
  GIT_SHA_DEFAULT="local"
fi
GIT_SHA="${GIT_SHA:-"$GIT_SHA_DEFAULT"}"

if [[ -z "${URI_BASE:-}" ]]; then
  echo "ERROR: URI_BASE must be set (e.g. https://github.com/OWNER/REPO/releases/download/TAG/)" >&2
  exit 1
fi

mkdir -p "$OUTDIR"
find "$OUTDIR" -maxdepth 1 -type f -name '*.bosatsu_lib' -delete

echo "bosatsu lib publish:"
echo "  repo_root = $REPO_ROOT"
echo "  outdir    = $OUTDIR"
echo "  git_sha   = $GIT_SHA"
echo "  uri-base  = $URI_BASE"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "  mode      = dry-run (no *_conf.json updates)"
fi

cd "$REPO_ROOT"

echo "bosatsu lib fetch:"
LIB_NAMES=()
LIBS_JSON="$REPO_ROOT/bosatsu_libs.json"
if [[ -f "$LIBS_JSON" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
  elif command -v python >/dev/null 2>&1; then
    PYTHON=python
  else
    PYTHON=""
  fi

  if [[ -n "$PYTHON" ]]; then
    while IFS= read -r name; do
      LIB_NAMES+=("$name")
    done < <(
      "$PYTHON" - "$LIBS_JSON" <<'PY'
import json, sys
with open(sys.argv[1]) as f:
    data = json.load(f)
for name in sorted(data.keys()):
    print(name)
PY
    )
  else
    echo "WARNING: python not found; falling back to fetch without --name" >&2
  fi
fi

if [[ ${#LIB_NAMES[@]} -gt 0 ]]; then
  for name in "${LIB_NAMES[@]}"; do
    echo "  name = $name"
    ./bosatsu lib fetch \
      --repo_root "$REPO_ROOT" \
      --name "$name"
  done
else
  ./bosatsu lib fetch \
    --repo_root "$REPO_ROOT"
fi

publish_repo_root="$REPO_ROOT"
cas_arg=()
tmp_repo=""
if [[ "$DRY_RUN" -eq 1 ]]; then
  tmp_repo="$(mktemp -d "${TMPDIR:-/tmp}/bosatsu-publish-dry-run.XXXXXX")"
  trap 'rm -rf "$tmp_repo"' EXIT
  tmp_publish_root="$tmp_repo/repo"
  mkdir -p "$tmp_publish_root"

  # Copy source into a temporary workspace so publish can run without mutating
  # repository conf files.
  tar -C "$REPO_ROOT" \
    --exclude='.git' \
    --exclude='.bosatsuc' \
    --exclude='.bosatsu_lib_publish' \
    --exclude='.bosatsu_lib_publish_dry_run' \
    -cf - . | tar -C "$tmp_publish_root" -xf -

  publish_repo_root="$tmp_publish_root"
  cas_arg=(--cas_dir "$REPO_ROOT/.bosatsuc/cas")
fi

./bosatsu lib publish \
  --repo_root "$publish_repo_root" \
  "${cas_arg[@]}" \
  --outdir "$OUTDIR" \
  --git_sha "$GIT_SHA" \
  --uri-base "$URI_BASE"

echo
echo "Generated .bosatsu_lib files:"
ls -1 "$OUTDIR"/*.bosatsu_lib || {
  echo "No .bosatsu_lib files found in $OUTDIR" >&2
  exit 1
}
