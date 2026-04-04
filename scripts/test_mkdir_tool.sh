#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/zafu-mkdir-tool.XXXXXX")"
EXE_PATH="$WORKDIR/zafu-mkdir"

cleanup() {
  chmod -R u+rwx "$WORKDIR" >/dev/null 2>&1 || true
  rm -rf "$WORKDIR"
}
trap cleanup EXIT

assert_eq() {
  local label="$1"
  local expected="$2"
  local actual="$3"
  if [[ "$actual" != "$expected" ]]; then
    printf 'mkdir tool test failed: %s\nexpected: <%s>\nactual:   <%s>\n' "$label" "$expected" "$actual" >&2
    exit 1
  fi
}

assert_dir_exists() {
  local label="$1"
  local path="$2"
  if [[ ! -d "$path" ]]; then
    printf 'mkdir tool test failed: %s\nmissing directory: %s\n' "$label" "$path" >&2
    exit 1
  fi
}

assert_dir_missing() {
  local label="$1"
  local path="$2"
  if [[ -d "$path" ]]; then
    printf 'mkdir tool test failed: %s\nunexpected directory: %s\n' "$label" "$path" >&2
    exit 1
  fi
}

run_case() {
  local case_name="$1"
  shift
  local case_dir="$WORKDIR/$case_name"
  mkdir -p "$case_dir"
  (
    cd "$case_dir"
    "$EXE_PATH" "$@" >stdout 2>stderr
    printf '%s' "$?" >exit_code
  ) || (
    cd "$case_dir"
    printf '%s' "$?" >exit_code
  )
}

compare_symbolic_mode_case() {
  local mode="$1"
  local case_dir="$WORKDIR/symbolic_$(printf '%s' "$mode" | od -An -tx1 | tr -d ' \n')"
  mkdir -p "$case_dir/system" "$case_dir/zafu"

  (
    cd "$case_dir/system"
    umask 022
    mkdir -m "$mode" d
    stat -f '%p' d >mode
    chmod -R u+rwx d >/dev/null 2>&1 || true
  )

  (
    cd "$case_dir/zafu"
    umask 022
    "$EXE_PATH" -m "$mode" d >stdout 2>stderr
    printf '%s' "$?" >exit_code
    stat -f '%p' d >mode
    chmod -R u+rwx d >/dev/null 2>&1 || true
  )

  assert_eq "symbolic mode exit code ($mode)" "0" "$(cat "$case_dir/zafu/exit_code")"
  assert_eq "symbolic mode stdout ($mode)" "" "$(cat "$case_dir/zafu/stdout")"
  assert_eq "symbolic mode stderr ($mode)" "" "$(cat "$case_dir/zafu/stderr")"
  assert_eq "symbolic mode diff ($mode)" "$(cat "$case_dir/system/mode")" "$(cat "$case_dir/zafu/mode")"
}

./bosatsu build --main_pack Zafu/Tool/Mkdir --exe_out "$EXE_PATH" >/dev/null

run_case missing_parent bar/baz
assert_eq "missing parent exit code" "1" "$(cat "$WORKDIR/missing_parent/exit_code")"
assert_eq "missing parent stdout" "" "$(cat "$WORKDIR/missing_parent/stdout")"
assert_eq "missing parent stderr" "mkdir: bar: No such file or directory" "$(cat "$WORKDIR/missing_parent/stderr")"
assert_dir_missing "missing parent should not create bar" "$WORKDIR/missing_parent/bar"

mkdir -p "$WORKDIR/not_directory"
: > "$WORKDIR/not_directory/file"
(
  cd "$WORKDIR/not_directory"
  "$EXE_PATH" file/subdir >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/not_directory"
  printf '%s' "$?" >exit_code
)
assert_eq "not a directory exit code" "1" "$(cat "$WORKDIR/not_directory/exit_code")"
assert_eq "not a directory stdout" "" "$(cat "$WORKDIR/not_directory/stdout")"
assert_eq "not a directory stderr" "mkdir: file: Not a directory" "$(cat "$WORKDIR/not_directory/stderr")"
assert_dir_missing "not a directory should not create child" "$WORKDIR/not_directory/file/subdir"

mkdir -p "$WORKDIR/verbose_continue"
: > "$WORKDIR/verbose_continue/file"
(
  cd "$WORKDIR/verbose_continue"
  "$EXE_PATH" -pv file/subdir ok >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/verbose_continue"
  printf '%s' "$?" >exit_code
)
assert_eq "verbose continue exit code" "1" "$(cat "$WORKDIR/verbose_continue/exit_code")"
assert_eq "verbose continue stdout" "ok" "$(cat "$WORKDIR/verbose_continue/stdout")"
assert_eq "verbose continue stderr" "mkdir: file: Not a directory" "$(cat "$WORKDIR/verbose_continue/stderr")"
assert_dir_exists "verbose continue should create later operand" "$WORKDIR/verbose_continue/ok"

for mode in \
  '-X' \
  '+X' \
  '=X' \
  '=uX' \
  '=uoX' \
  '-wX' \
  '-gXx' \
  'u=or' \
  'u=ro' \
  'u=os' \
  'u=so' \
  'u=gr' \
  'u=rg' \
  'u=ow' \
  'u=wo' \
  'u=orx' \
  'u=rog'
do
  compare_symbolic_mode_case "$mode"
done
