#!/usr/bin/env bash
set -euo pipefail

DOCS_DIR="${1:?usage: validate_doc_source_urls.sh <docs-dir> <repo> <ref>}"
SOURCE_REPO="${2:?usage: validate_doc_source_urls.sh <docs-dir> <repo> <ref>}"
SOURCE_REF="${3:?usage: validate_doc_source_urls.sh <docs-dir> <repo> <ref>}"

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$REPO_ROOT"

source_urls=()
while IFS= read -r source_url; do
  source_urls+=("$source_url")
done < <(
  grep -RhoE '\(https://github.com/[^)]*\)' "$DOCS_DIR" --include='*.md' \
    | tr -d '()' \
    | sort -u
)

if [[ "${#source_urls[@]}" -eq 0 ]]; then
  echo "No source URLs were generated in markdown docs." >&2
  exit 1
fi

checked_source_urls=0
for source_url in "${source_urls[@]}"; do
  if [[ ! "$source_url" =~ ^https://github\.com/([^/]+/[^/]+)/blob/([^/]+)/(.+)$ ]]; then
    continue
  fi

  url_repo="${BASH_REMATCH[1]}"
  url_ref="${BASH_REMATCH[2]}"
  url_path="${BASH_REMATCH[3]}"
  url_path="${url_path%%#*}"

  if [[ "$url_repo" != "$SOURCE_REPO" ]]; then
    continue
  fi

  checked_source_urls=$((checked_source_urls + 1))

  if [[ "$url_ref" != "$SOURCE_REF" ]]; then
    echo "Unexpected source ref in generated docs: $source_url" >&2
    exit 1
  fi

  # Validate same-repo links against the checked-out tree so CI does not rely
  # on GitHub's blob endpoints being healthy during doc generation.
  if ! git -C "$REPO_ROOT" ls-files --error-unmatch -- "$url_path" >/dev/null 2>&1; then
    echo "Generated source URL points at a missing tracked path: $source_url" >&2
    exit 1
  fi
done

if [[ "$checked_source_urls" -eq 0 ]]; then
  echo "No in-repo source URLs were generated in markdown docs." >&2
  exit 1
fi
