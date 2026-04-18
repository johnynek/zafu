#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/zafu-bosatsu-launcher.XXXXXX")"
TEST_REPO="$WORKDIR/repo"
STUB_ARTIFACT="$WORKDIR/bosatsu-stub"
LOG_PATH="$WORKDIR/stub.log"

cleanup() {
  chmod -R u+rwx "$WORKDIR" >/dev/null 2>&1 || true
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

fail() {
  printf 'bosatsu launcher test failed: %s\n' "$1" >&2
  exit 1
}

assert_eq() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" != "$expected" ]]; then
    printf 'bosatsu launcher test failed: %s\nexpected: <%s>\nactual:   <%s>\n' "$label" "$expected" "$actual" >&2
    exit 1
  fi
}

assert_file_exists() {
  local label="$1"
  local path="$2"
  if [[ ! -f "$path" ]]; then
    printf 'bosatsu launcher test failed: %s\nmissing file: %s\n' "$label" "$path" >&2
    exit 1
  fi
}

physical_path() {
  local path="$1"
  if [[ -d "$path" ]]; then
    (
      cd "$path"
      pwd -P
    )
  else
    local dir_name
    local base_name
    dir_name="$(dirname "$path")"
    base_name="$(basename "$path")"
    printf '%s/%s\n' "$(
      cd "$dir_name"
      pwd -P
    )" "$base_name"
  fi
}

version="$(tr -d '[:space:]' < "$REPO_ROOT/.bosatsu_version")"
platform="$(tr -d '[:space:]' < "$REPO_ROOT/.bosatsu_platform")"

case "$platform" in
  native)
    case "$(uname -s)" in
      Darwin)
        artifact_name="bosatsu-macos"
        ;;
      Linux)
        artifact_name="bosatsu-linux"
        ;;
      *)
        fail "unsupported OS for native platform launcher test"
        ;;
    esac
    ;;
  *)
    fail "launcher regression expects native platform, found: $platform"
    ;;
esac

mkdir -p "$TEST_REPO"
cp "$REPO_ROOT/bosatsu" "$TEST_REPO/bosatsu"
cp "$REPO_ROOT/.bosatsu_version" "$TEST_REPO/.bosatsu_version"
cp "$REPO_ROOT/.bosatsu_platform" "$TEST_REPO/.bosatsu_platform"
chmod +x "$TEST_REPO/bosatsu"
# Exercise the wrapper in isolation so the contract stays pinned without
# downloading the real CLI or building the real C runtime.
git -C "$TEST_REPO" init -q
mkdir -p "$TEST_REPO/nested/work"

cat >"$STUB_ARTIFACT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

: "${BOSATSU_STUB_LOG:?missing BOSATSU_STUB_LOG}"
printf '%s\n' "$0" > "${BOSATSU_STUB_LOG}.path"
printf '%s\n' "$PWD" > "${BOSATSU_STUB_LOG}.pwd"
printf '%s\n' "$@" > "${BOSATSU_STUB_LOG}.args"
EOF
chmod +x "$STUB_ARTIFACT"

run_case() {
  local case_name="$1"
  shift

  local stdout_path="$WORKDIR/${case_name}.stdout"
  local stderr_path="$WORKDIR/${case_name}.stderr"

  rm -f "$stdout_path" "$stderr_path" "${LOG_PATH}.args" "${LOG_PATH}.pwd" "${LOG_PATH}.path"
  if ! (
    cd "$TEST_REPO/nested/work"
    BOSATSU_STUB_LOG="$LOG_PATH" "$TEST_REPO/bosatsu" --artifact "$STUB_ARTIFACT" "$@" >"$stdout_path" 2>"$stderr_path"
  ); then
    fail "$case_name command failed: $(cat "$stderr_path")"
  fi

  assert_eq "$case_name stdout" "" "$(cat "$stdout_path")"
  assert_eq "$case_name stderr" "" "$(cat "$stderr_path")"
}

expected_artifact_path="$TEST_REPO/.bosatsuc/cli/$version/$artifact_name"
expected_invocation_dir="$TEST_REPO/nested/work"

run_case implicit_fetch --fetch
assert_file_exists "implicit fetch installs the stub artifact at the repo root" "$expected_artifact_path"
assert_eq \
  "implicit fetch runs the installed artifact" \
  "$(physical_path "$expected_artifact_path")" \
  "$(physical_path "$(cat "${LOG_PATH}.path")")"
assert_eq \
  "implicit fetch preserves the caller working directory" \
  "$(physical_path "$expected_invocation_dir")" \
  "$(physical_path "$(cat "${LOG_PATH}.pwd")")"
assert_eq \
  "implicit fetch pins the release bootstrap args" \
  "$(printf 'c-runtime\ninstall\n--profile\nrelease')" \
  "$(cat "${LOG_PATH}.args")"

run_case explicit_passthrough --fetch version
assert_eq \
  "explicit subcommands still run the installed artifact" \
  "$(physical_path "$expected_artifact_path")" \
  "$(physical_path "$(cat "${LOG_PATH}.path")")"
assert_eq \
  "explicit subcommands preserve the caller working directory" \
  "$(physical_path "$expected_invocation_dir")" \
  "$(physical_path "$(cat "${LOG_PATH}.pwd")")"
assert_eq "explicit subcommands pass through unchanged" "version" "$(cat "${LOG_PATH}.args")"
