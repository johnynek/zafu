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

mode_of() {
  local path="$1"
  if stat -f '%Lp' "$path" >/dev/null 2>&1; then
    stat -f '%Lp' "$path"
  else
    stat -c '%a' "$path"
  fi
}

compare_symbolic_mode_case() {
  local mode="$1"
  local case_dir="$WORKDIR/symbolic_$(printf '%s' "$mode" | od -An -tx1 | tr -d ' \n')"
  mkdir -p "$case_dir/system" "$case_dir/zafu"

  (
    cd "$case_dir/system"
    umask 022
    mkdir -m "$mode" d
    mode_of d >mode
    chmod -R u+rwx d >/dev/null 2>&1 || true
  )

  (
    cd "$case_dir/zafu"
    umask 022
    "$EXE_PATH" -m "$mode" d >stdout 2>stderr
    printf '%s' "$?" >exit_code
    mode_of d >mode
    chmod -R u+rwx d >/dev/null 2>&1 || true
  )

  assert_eq "symbolic mode exit code ($mode)" "0" "$(cat "$case_dir/zafu/exit_code")"
  assert_eq "symbolic mode stdout ($mode)" "" "$(cat "$case_dir/zafu/stdout")"
  assert_eq "symbolic mode stderr ($mode)" "" "$(cat "$case_dir/zafu/stderr")"
  assert_eq "symbolic mode diff ($mode)" "$(cat "$case_dir/system/mode")" "$(cat "$case_dir/zafu/mode")"
}

compare_case_against_system() {
  local case_name="$1"
  shift
  local case_dir="$WORKDIR/$case_name"
  mkdir -p "$case_dir/system" "$case_dir/zafu"

  (
    cd "$case_dir/system"
    command mkdir "$@" >stdout 2>stderr
    printf '%s' "$?" >exit_code
  ) || (
    cd "$case_dir/system"
    printf '%s' "$?" >exit_code
  )

  (
    cd "$case_dir/zafu"
    "$EXE_PATH" "$@" >stdout 2>stderr
    printf '%s' "$?" >exit_code
  ) || (
    cd "$case_dir/zafu"
    printf '%s' "$?" >exit_code
  )

  assert_eq "$case_name exit code" "$(cat "$case_dir/system/exit_code")" "$(cat "$case_dir/zafu/exit_code")"
  assert_eq "$case_name stdout" "$(cat "$case_dir/system/stdout")" "$(cat "$case_dir/zafu/stdout")"
  assert_eq "$case_name stderr" "$(cat "$case_dir/system/stderr")" "$(cat "$case_dir/zafu/stderr")"
}

./bosatsu build --main_pack Zafu/Tool/Mkdir --exe_out "$EXE_PATH" >/dev/null

run_case missing_parent bar/baz
assert_eq "missing parent exit code" "1" "$(cat "$WORKDIR/missing_parent/exit_code")"
assert_eq "missing parent stdout" "" "$(cat "$WORKDIR/missing_parent/stdout")"
assert_eq "missing parent stderr" "mkdir: bar: No such file or directory" "$(cat "$WORKDIR/missing_parent/stderr")"
assert_dir_missing "missing parent should not create bar" "$WORKDIR/missing_parent/bar"

compare_case_against_system empty_mode_arg -m "" d
assert_dir_missing "empty mode argument should not create d" "$WORKDIR/empty_mode_arg/zafu/d"

run_case trailing_p_operand foo -p
assert_eq "trailing -p operand exit code" "0" "$(cat "$WORKDIR/trailing_p_operand/exit_code")"
assert_eq "trailing -p operand stdout" "" "$(cat "$WORKDIR/trailing_p_operand/stdout")"
assert_eq "trailing -p operand stderr" "" "$(cat "$WORKDIR/trailing_p_operand/stderr")"
assert_dir_exists "trailing -p should create foo" "$WORKDIR/trailing_p_operand/foo"
assert_dir_exists "trailing -p should create -p" "$WORKDIR/trailing_p_operand/-p"

run_case trailing_m_operand foo -m 700
assert_eq "trailing -m operand exit code" "0" "$(cat "$WORKDIR/trailing_m_operand/exit_code")"
assert_eq "trailing -m operand stdout" "" "$(cat "$WORKDIR/trailing_m_operand/stdout")"
assert_eq "trailing -m operand stderr" "" "$(cat "$WORKDIR/trailing_m_operand/stderr")"
assert_dir_exists "trailing -m should create foo" "$WORKDIR/trailing_m_operand/foo"
assert_dir_exists "trailing -m should create -m" "$WORKDIR/trailing_m_operand/-m"
assert_dir_exists "trailing -m should create 700" "$WORKDIR/trailing_m_operand/700"

run_case trailing_dashdash_operand foo -- bar
assert_eq "trailing -- operand exit code" "0" "$(cat "$WORKDIR/trailing_dashdash_operand/exit_code")"
assert_eq "trailing -- operand stdout" "" "$(cat "$WORKDIR/trailing_dashdash_operand/stdout")"
assert_eq "trailing -- operand stderr" "" "$(cat "$WORKDIR/trailing_dashdash_operand/stderr")"
assert_dir_exists "trailing -- should create foo" "$WORKDIR/trailing_dashdash_operand/foo"
assert_dir_exists "trailing -- should create --" "$WORKDIR/trailing_dashdash_operand/--"
assert_dir_exists "trailing -- should create bar" "$WORKDIR/trailing_dashdash_operand/bar"

compare_case_against_system trailing_slash_mode -p -m 700 a/
assert_eq "trailing slash mode diff" "$(mode_of "$WORKDIR/trailing_slash_mode/system/a")" "$(mode_of "$WORKDIR/trailing_slash_mode/zafu/a")"

mkdir -p "$WORKDIR/slash_existing_file/system" "$WORKDIR/slash_existing_file/zafu"
: > "$WORKDIR/slash_existing_file/system/a"
: > "$WORKDIR/slash_existing_file/zafu/a"
(
  cd "$WORKDIR/slash_existing_file/system"
  command mkdir -p a/ >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/slash_existing_file/system"
  printf '%s' "$?" >exit_code
)
(
  cd "$WORKDIR/slash_existing_file/zafu"
  "$EXE_PATH" -p a/ >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/slash_existing_file/zafu"
  printf '%s' "$?" >exit_code
)
assert_eq "slash existing file exit code" "$(cat "$WORKDIR/slash_existing_file/system/exit_code")" "$(cat "$WORKDIR/slash_existing_file/zafu/exit_code")"
assert_eq "slash existing file stdout" "$(cat "$WORKDIR/slash_existing_file/system/stdout")" "$(cat "$WORKDIR/slash_existing_file/zafu/stdout")"
assert_eq "slash existing file stderr" "$(cat "$WORKDIR/slash_existing_file/system/stderr")" "$(cat "$WORKDIR/slash_existing_file/zafu/stderr")"

compare_case_against_system double_slash_missing_parent a//b

run_case nested_missing_parent a/b/c
assert_eq "nested missing parent exit code" "1" "$(cat "$WORKDIR/nested_missing_parent/exit_code")"
assert_eq "nested missing parent stdout" "" "$(cat "$WORKDIR/nested_missing_parent/stdout")"
assert_eq "nested missing parent stderr" "mkdir: a/b: No such file or directory" "$(cat "$WORKDIR/nested_missing_parent/stderr")"
assert_dir_missing "nested missing parent should not create a" "$WORKDIR/nested_missing_parent/a"

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

mkdir -p "$WORKDIR/nested_not_directory"
: > "$WORKDIR/nested_not_directory/a"
(
  cd "$WORKDIR/nested_not_directory"
  "$EXE_PATH" a/b/c >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/nested_not_directory"
  printf '%s' "$?" >exit_code
)
assert_eq "nested not a directory exit code" "1" "$(cat "$WORKDIR/nested_not_directory/exit_code")"
assert_eq "nested not a directory stdout" "" "$(cat "$WORKDIR/nested_not_directory/stdout")"
assert_eq "nested not a directory stderr" "mkdir: a/b: Not a directory" "$(cat "$WORKDIR/nested_not_directory/stderr")"
assert_dir_missing "nested not a directory should not create child" "$WORKDIR/nested_not_directory/a/b/c"

mkdir -p "$WORKDIR/nested_existing_dir/a/b"
(
  cd "$WORKDIR/nested_existing_dir"
  "$EXE_PATH" a/b >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/nested_existing_dir"
  printf '%s' "$?" >exit_code
)
assert_eq "nested existing dir exit code" "1" "$(cat "$WORKDIR/nested_existing_dir/exit_code")"
assert_eq "nested existing dir stdout" "" "$(cat "$WORKDIR/nested_existing_dir/stdout")"
assert_eq "nested existing dir stderr" "mkdir: a/b: File exists" "$(cat "$WORKDIR/nested_existing_dir/stderr")"

mkdir -p "$WORKDIR/nested_existing_file/a"
: > "$WORKDIR/nested_existing_file/a/b"
(
  cd "$WORKDIR/nested_existing_file"
  "$EXE_PATH" -pv a/b >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/nested_existing_file"
  printf '%s' "$?" >exit_code
)
assert_eq "nested existing file pv exit code" "1" "$(cat "$WORKDIR/nested_existing_file/exit_code")"
assert_eq "nested existing file pv stdout" "" "$(cat "$WORKDIR/nested_existing_file/stdout")"
assert_eq "nested existing file pv stderr" "mkdir: a/b: File exists" "$(cat "$WORKDIR/nested_existing_file/stderr")"

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

run_case p_empty -p ""
assert_eq "p empty exit code" "1" "$(cat "$WORKDIR/p_empty/exit_code")"
assert_eq "p empty stdout" "" "$(cat "$WORKDIR/p_empty/stdout")"
assert_eq "p empty stderr" "mkdir: : No such file or directory" "$(cat "$WORKDIR/p_empty/stderr")"

run_case plain_empty ""
assert_eq "plain empty exit code" "1" "$(cat "$WORKDIR/plain_empty/exit_code")"
assert_eq "plain empty stdout" "" "$(cat "$WORKDIR/plain_empty/stdout")"
assert_eq "plain empty stderr" "mkdir: .: No such file or directory" "$(cat "$WORKDIR/plain_empty/stderr")"

run_case dash_empty -- ""
assert_eq "dash empty exit code" "1" "$(cat "$WORKDIR/dash_empty/exit_code")"
assert_eq "dash empty stdout" "" "$(cat "$WORKDIR/dash_empty/stdout")"
assert_eq "dash empty stderr" "mkdir: .: No such file or directory" "$(cat "$WORKDIR/dash_empty/stderr")"

mkdir -p "$WORKDIR/verbose_empty"
: > "$WORKDIR/verbose_empty/file"
(
  cd "$WORKDIR/verbose_empty"
  "$EXE_PATH" -pv file/sub ok "" >stdout 2>stderr
  printf '%s' "$?" >exit_code
) || (
  cd "$WORKDIR/verbose_empty"
  printf '%s' "$?" >exit_code
)
assert_eq "verbose empty exit code" "1" "$(cat "$WORKDIR/verbose_empty/exit_code")"
assert_eq "verbose empty stdout" "ok" "$(cat "$WORKDIR/verbose_empty/stdout")"
assert_eq "verbose empty stderr" $'mkdir: file: Not a directory\nmkdir: : No such file or directory' "$(cat "$WORKDIR/verbose_empty/stderr")"
assert_dir_exists "verbose empty should create ok" "$WORKDIR/verbose_empty/ok"

run_case verbose_dot -pv x/.
assert_eq "verbose dot exit code" "0" "$(cat "$WORKDIR/verbose_dot/exit_code")"
assert_eq "verbose dot stdout" "x" "$(cat "$WORKDIR/verbose_dot/stdout")"
assert_eq "verbose dot stderr" "" "$(cat "$WORKDIR/verbose_dot/stderr")"
assert_dir_exists "verbose dot should create x" "$WORKDIR/verbose_dot/x"

run_case verbose_double_slash -pv a//b
assert_eq "verbose double slash exit code" "0" "$(cat "$WORKDIR/verbose_double_slash/exit_code")"
assert_eq "verbose double slash stdout" $'a\na//b' "$(cat "$WORKDIR/verbose_double_slash/stdout")"
assert_eq "verbose double slash stderr" "" "$(cat "$WORKDIR/verbose_double_slash/stderr")"
assert_dir_exists "verbose double slash should create a/b" "$WORKDIR/verbose_double_slash/a/b"

run_case verbose_parent_ref -pv x/../y
assert_eq "verbose parent ref exit code" "0" "$(cat "$WORKDIR/verbose_parent_ref/exit_code")"
assert_eq "verbose parent ref stdout" $'x\nx/../y' "$(cat "$WORKDIR/verbose_parent_ref/stdout")"
assert_eq "verbose parent ref stderr" "" "$(cat "$WORKDIR/verbose_parent_ref/stderr")"
assert_dir_exists "verbose parent ref should create x" "$WORKDIR/verbose_parent_ref/x"
assert_dir_exists "verbose parent ref should create y" "$WORKDIR/verbose_parent_ref/y"

for mode in \
  '+' \
  '--' \
  'u+' \
  'a-' \
  'u++x' \
  'u+s+t' \
  '+t' \
  'a+t' \
  'ugo+t' \
  'u+t' \
  '=t' \
  'a=t' \
  'ugo=t' \
  'u=tu' \
  'u=gt' \
  'g=ot' \
  'g=ut' \
  'u=got' \
  'u=ogt' \
  'o=os' \
  'o=gs' \
  'o=ut' \
  'o=uXs' \
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

for prefix in s t st ts; do
  for copy in o u g; do
    for suffix in '' s t st oo; do
      compare_symbolic_mode_case "o=${prefix}${copy}${suffix}"
    done
  done
done

compare_symbolic_mode_case 'o=sost,g='
