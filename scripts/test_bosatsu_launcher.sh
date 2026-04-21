#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

WORKDIR="$(mktemp -d "${TMPDIR:-/tmp}/zafu-bosatsu-launcher.XXXXXX")"
TEST_REPO="$WORKDIR/repo"
LOG_PATH="$WORKDIR/stub.log"
NATIVE_STUB_ARTIFACT="$WORKDIR/bosatsu-stub-native"
NODE_STUB_ARTIFACT="$WORKDIR/bosatsu-stub-node.js"
JAVA_STUB_ARTIFACT="$WORKDIR/bosatsu-stub.jar"

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

native_artifact_name() {
  case "$(uname -s)" in
    Darwin)
      printf '%s\n' "bosatsu-macos"
      ;;
    Linux)
      printf '%s\n' "bosatsu-linux"
      ;;
    *)
      fail "unsupported OS for native platform launcher test"
      ;;
  esac
}

prepare_native_stub() {
  cat >"$NATIVE_STUB_ARTIFACT" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

: "${BOSATSU_STUB_LOG:?missing BOSATSU_STUB_LOG}"
printf '%s\n' "$0" > "${BOSATSU_STUB_LOG}.path"
printf '%s\n' "$PWD" > "${BOSATSU_STUB_LOG}.pwd"
printf '%s\n' "$@" > "${BOSATSU_STUB_LOG}.args"
EOF
  chmod +x "$NATIVE_STUB_ARTIFACT"
}

prepare_node_stub() {
  cat >"$NODE_STUB_ARTIFACT" <<'EOF'
const fs = require("node:fs");

const logPath = process.env.BOSATSU_STUB_LOG;
if (!logPath) {
  throw new Error("missing BOSATSU_STUB_LOG");
}

fs.writeFileSync(`${logPath}.path`, `${fs.realpathSync(process.argv[1])}\n`);
fs.writeFileSync(`${logPath}.pwd`, `${fs.realpathSync(process.cwd())}\n`);
fs.writeFileSync(`${logPath}.args`, process.argv.slice(2).join("\n"));
EOF
}

prepare_java_stub() {
  local src_dir="$WORKDIR/java-src"
  local classes_dir="$WORKDIR/java-classes"
  mkdir -p "$src_dir" "$classes_dir"

  cat >"$src_dir/Stub.java" <<'EOF'
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;

public final class Stub {
  private static void write(String path, String value) throws Exception {
    Files.writeString(Path.of(path), value, StandardCharsets.UTF_8);
  }

  public static void main(String[] args) throws Exception {
    String logPath = System.getenv("BOSATSU_STUB_LOG");
    if (logPath == null) {
      throw new IllegalStateException("missing BOSATSU_STUB_LOG");
    }

    String jarPath =
        Path.of(Stub.class.getProtectionDomain().getCodeSource().getLocation().toURI())
            .toRealPath()
            .toString();
    String pwd = Path.of("").toRealPath().toString();
    write(logPath + ".path", jarPath + "\n");
    write(logPath + ".pwd", pwd + "\n");
    write(logPath + ".args", String.join("\n", Arrays.asList(args)));
  }
}
EOF

  javac -d "$classes_dir" "$src_dir/Stub.java"
  jar --create --file "$JAVA_STUB_ARTIFACT" --main-class Stub -C "$classes_dir" .
}

mkdir -p "$TEST_REPO"
cp "$REPO_ROOT/bosatsu" "$TEST_REPO/bosatsu"
cp "$REPO_ROOT/.bosatsu_version" "$TEST_REPO/.bosatsu_version"
chmod +x "$TEST_REPO/bosatsu"
# Exercise the wrapper in isolation so the contract stays pinned without
# downloading the real CLI or building the real C runtime.
git -C "$TEST_REPO" init -q
mkdir -p "$TEST_REPO/nested/work"

run_case() {
  local case_name="$1"
  local artifact_src="$2"
  shift 2

  local stdout_path="$WORKDIR/${case_name}.stdout"
  local stderr_path="$WORKDIR/${case_name}.stderr"

  rm -f "$stdout_path" "$stderr_path" "${LOG_PATH}.args" "${LOG_PATH}.pwd" "${LOG_PATH}.path"
  if ! (
    cd "$TEST_REPO/nested/work"
    BOSATSU_STUB_LOG="$LOG_PATH" "$TEST_REPO/bosatsu" --artifact "$artifact_src" "$@" >"$stdout_path" 2>"$stderr_path"
  ); then
    fail "$case_name command failed: $(cat "$stderr_path")"
  fi

  assert_eq "$case_name stdout" "" "$(cat "$stdout_path")"
  assert_eq "$case_name stderr" "" "$(cat "$stderr_path")"
}

run_platform_contract() {
  local platform="$1"
  local artifact_name="$2"
  local artifact_src="$3"
  local expected_artifact_path="$TEST_REPO/.bosatsuc/cli/$version/$artifact_name"
  local expected_invocation_dir="$TEST_REPO/nested/work"

  printf '%s\n' "$platform" > "$TEST_REPO/.bosatsu_platform"

  run_case "${platform}_implicit_fetch" "$artifact_src" --fetch
  assert_file_exists "${platform} implicit fetch installs the stub artifact at the repo root" "$expected_artifact_path"
  assert_eq \
    "${platform} implicit fetch runs the installed artifact" \
    "$(physical_path "$expected_artifact_path")" \
    "$(physical_path "$(cat "${LOG_PATH}.path")")"
  assert_eq \
    "${platform} implicit fetch preserves the caller working directory" \
    "$(physical_path "$expected_invocation_dir")" \
    "$(physical_path "$(cat "${LOG_PATH}.pwd")")"
  assert_eq \
    "${platform} implicit fetch pins the release bootstrap args" \
    "$(printf 'c-runtime\ninstall\n--profile\nrelease')" \
    "$(cat "${LOG_PATH}.args")"

  run_case "${platform}_explicit_passthrough" "$artifact_src" --fetch version
  assert_eq \
    "${platform} explicit subcommands still run the installed artifact" \
    "$(physical_path "$expected_artifact_path")" \
    "$(physical_path "$(cat "${LOG_PATH}.path")")"
  assert_eq \
    "${platform} explicit subcommands preserve the caller working directory" \
    "$(physical_path "$expected_invocation_dir")" \
    "$(physical_path "$(cat "${LOG_PATH}.pwd")")"
  assert_eq "${platform} explicit subcommands pass through unchanged" "version" "$(cat "${LOG_PATH}.args")"
}

prepare_native_stub
run_platform_contract native "$(native_artifact_name)" "$NATIVE_STUB_ARTIFACT"

if command -v java >/dev/null 2>&1 && command -v javac >/dev/null 2>&1 && command -v jar >/dev/null 2>&1; then
  prepare_java_stub
  run_platform_contract java "bosatsu.jar" "$JAVA_STUB_ARTIFACT"
fi

if command -v node >/dev/null 2>&1; then
  prepare_node_stub
  run_platform_contract node "bosatsu_node.js" "$NODE_STUB_ARTIFACT"
fi
