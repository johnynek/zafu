#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import dataclasses
import hashlib
import io
import json
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from typing import Sequence

CSV_COLUMNS = [
    "benchmark",
    "target",
    "input",
    "repeat_index",
    "elapsed_ns",
    "exit_code",
    "validation_passed",
    "source_id",
    "git_sha",
    "timestamp_utc",
]

DEFAULT_TARGET_ORDER = ("bosatsu_jvm", "bosatsu_c", "java", "c")
VALIDATION_KINDS = {"float_lines", "exact_text", "exact_bytes"}
TEMP_PBM_PLACEHOLDER = "<temporary-pbm-path>"


class HarnessError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class ValidationSpec:
    kind: str
    fixture_path: str
    abs_tolerance: float | None = None


@dataclasses.dataclass(frozen=True)
class LanguageSpec:
    source_id: str
    source_url: str
    source_path: str
    thread_model: str
    pinned_at: str
    launch_caveat: str
    main_class: str | None = None
    local_compile_flags: tuple[str, ...] = ()
    local_run_flags: tuple[str, ...] = ()
    local_libraries: tuple[str, ...] = ()


@dataclasses.dataclass(frozen=True)
class BenchmarkSpec:
    benchmark: str
    slug: str
    bosatsu_package: str
    bosatsu_main: str
    sample_input: int
    performance_input: int
    validation: ValidationSpec
    java: LanguageSpec
    c: LanguageSpec


@dataclasses.dataclass(frozen=True)
class BuildPlan:
    benchmark: str
    target: str
    command: str


@dataclasses.dataclass(frozen=True)
class RunPlan:
    benchmark: str
    target: str
    phase: str
    input: int
    repeat_index: int | None
    warmup_count: int
    command: str
    capture_stdout_to: str | None
    validation_kind: str


@dataclasses.dataclass(frozen=True)
class ValidationRow:
    benchmark: str
    target: str
    input: int
    exit_code: int
    validation_passed: bool
    output_byte_count: int | None
    output_sha256: str | None


@dataclasses.dataclass(frozen=True)
class RunRecord:
    benchmark: str
    target: str
    input: int
    repeat_index: int
    elapsed_ns: int
    exit_code: int
    validation_passed: bool
    source_id: str
    source_url: str
    build_command: str
    run_command: str
    git_sha: str
    bosatsu_version: str
    java_version: str
    gcc_version: str
    os: str
    cpu_model: str
    timestamp_utc: str
    output_byte_count: int | None
    output_sha256: str | None


@dataclasses.dataclass(frozen=True)
class ExecutionOutput:
    exit_code: int
    elapsed_ns: int
    output_bytes: bytes
    run_command: str


@dataclasses.dataclass(frozen=True)
class ToolchainInfo:
    git_sha: str
    bosatsu_version: str
    java_version: str
    gcc_version: str
    os: str
    cpu_model: str
    repo_uri: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build and compare the phase-1 Bosatsu, Java, and C benchmarksgame "
            "implementations. Prerequisites: python3 or python, curl, java, "
            "javac, gcc, and network access for the version-matched bosatsu.jar."
        )
    )
    parser.add_argument(
        "--benchmarks",
        help="Comma-separated benchmark subset. Default: all phase-1 benchmarks in suite order.",
    )
    parser.add_argument(
        "--targets",
        help="Comma-separated target subset from bosatsu_jvm,bosatsu_c,java,c. Default: all targets.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=5,
        help="Measured repeats per benchmark/target after warmups. Default: 5.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run setup, build, and sample validation only; skip warmups and measured runs.",
    )
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="Print the expanded setup/build/run matrix as JSON and exit.",
    )
    parser.add_argument(
        "--output-json",
        help="Write the full JSON artifact to this path instead of stdout.",
    )
    parser.add_argument(
        "--output-csv",
        help="Write the stable CSV projection to this path.",
    )
    parser.add_argument(
        "--skip-setup",
        action="store_true",
        help="Assume the native CLI, JVM CLI jar, and dependency caches are already prepared.",
    )
    parser.add_argument(
        "--repo-root",
        help="Override the repository root. Defaults to the parent of this script.",
    )
    args = parser.parse_args()

    if args.repeats < 1:
        raise HarnessError("--repeats must be at least 1")

    repo_root = resolve_repo_root(args.repo_root)
    specs = load_manifest(repo_root)
    selected_specs = select_benchmarks(specs, args.benchmarks)
    selected_targets = select_targets(args.targets)
    bosatsu_version = read_text(repo_root / ".bosatsu_version")

    if args.print_plan:
        plan = expand_execution_matrix(selected_specs, selected_targets, args.repeats, bosatsu_version)
        emit_text(render_json(plan), args.output_json)
        return 0

    ensure_prerequisites(selected_targets, args.skip_setup)
    if not args.skip_setup:
        ensure_repo_setup(repo_root, bosatsu_version, selected_targets)

    build_commands = build_targets(repo_root, selected_specs, selected_targets, bosatsu_version)
    toolchain = read_toolchain_info(repo_root, bosatsu_version, selected_targets)
    validation_rows = run_sample_validations(repo_root, selected_specs, selected_targets, bosatsu_version)

    if args.validate_only:
        results: list[RunRecord] = []
    else:
        run_warmups(repo_root, selected_specs, selected_targets, bosatsu_version)
        results = run_measured_repeats(
            repo_root,
            selected_specs,
            selected_targets,
            args.repeats,
            bosatsu_version,
            build_commands,
            validation_rows,
            toolchain,
        )

    artifact = {
        "run_metadata": {
            "format_version": 1,
            "generated_at_utc": utc_now(),
            "git_sha": toolchain.git_sha,
            "bosatsu_version": toolchain.bosatsu_version,
            "java_version": toolchain.java_version,
            "gcc_version": toolchain.gcc_version,
            "os": toolchain.os,
            "cpu_model": toolchain.cpu_model,
            "selected_benchmarks": [spec.benchmark for spec in selected_specs],
            "selected_targets": list(selected_targets),
            "validation_only": args.validate_only,
            "measured_repeats": args.repeats,
            "validation_results": [dataclasses.asdict(row) for row in validation_rows],
        },
        "results": [dataclasses.asdict(row) for row in results],
    }

    if args.output_json:
        emit_text(render_json(artifact), args.output_json)
    if args.output_csv:
        emit_text(render_csv(results), args.output_csv)
    if not args.output_json and not args.output_csv:
        sys.stdout.write(render_json(artifact))

    return 0


def resolve_repo_root(value: str | None) -> pathlib.Path:
    if value is not None:
        return pathlib.Path(value).resolve()
    return pathlib.Path(__file__).resolve().parent.parent


def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def load_manifest(repo_root: pathlib.Path) -> list[BenchmarkSpec]:
    manifest_path = repo_root / "vendor/benchmarksgame/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw_specs = manifest.get("benchmarks")
    if not isinstance(raw_specs, list):
        raise HarnessError("vendor/benchmarksgame/manifest.json is missing the benchmarks array")

    specs = [parse_benchmark_spec(item) for item in raw_specs]
    validate_manifest(repo_root, specs)
    return specs


def parse_benchmark_spec(raw: object) -> BenchmarkSpec:
    if not isinstance(raw, dict):
        raise HarnessError("manifest benchmarks entries must be objects")
    bosatsu = expect_dict(raw, "bosatsu")
    validation = expect_dict(raw, "validation")
    return BenchmarkSpec(
        benchmark=expect_string(raw, "benchmark"),
        slug=expect_string(raw, "slug"),
        bosatsu_package=expect_string(bosatsu, "package"),
        bosatsu_main=expect_string(bosatsu, "main"),
        sample_input=expect_int(raw, "sample_input"),
        performance_input=expect_int(raw, "performance_input"),
        validation=parse_validation_spec(validation),
        java=parse_language_spec(expect_dict(raw, "java")),
        c=parse_language_spec(expect_dict(raw, "c")),
    )


def parse_validation_spec(raw: dict[str, object]) -> ValidationSpec:
    kind = expect_string(raw, "kind")
    if kind not in VALIDATION_KINDS:
        raise HarnessError(f"unsupported validation kind in manifest: {kind}")
    abs_tolerance = raw.get("abs_tolerance")
    return ValidationSpec(
        kind=kind,
        fixture_path=expect_string(raw, "fixture_path"),
        abs_tolerance=float(abs_tolerance) if abs_tolerance is not None else None,
    )


def parse_language_spec(raw: dict[str, object]) -> LanguageSpec:
    return LanguageSpec(
        source_id=expect_string(raw, "source_id"),
        source_url=expect_string(raw, "source_url"),
        source_path=expect_string(raw, "source_path"),
        thread_model=expect_string(raw, "thread_model"),
        pinned_at=expect_string(raw, "pinned_at"),
        launch_caveat=expect_string(raw, "launch_caveat"),
        main_class=expect_optional_string(raw, "main_class"),
        local_compile_flags=tuple(expect_string_list(raw.get("local_compile_flags", []), "local_compile_flags")),
        local_run_flags=tuple(expect_string_list(raw.get("local_run_flags", []), "local_run_flags")),
        local_libraries=tuple(expect_string_list(raw.get("local_libraries", []), "local_libraries")),
    )


def expect_dict(raw: dict[str, object], key: str) -> dict[str, object]:
    value = raw.get(key)
    if not isinstance(value, dict):
        raise HarnessError(f"manifest field {key} must be an object")
    return value


def expect_string(raw: dict[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise HarnessError(f"manifest field {key} must be a non-empty string")
    return value


def expect_optional_string(raw: dict[str, object], key: str) -> str | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise HarnessError(f"manifest field {key} must be null or a non-empty string")
    return value


def expect_int(raw: dict[str, object], key: str) -> int:
    value = raw.get(key)
    if not isinstance(value, int):
        raise HarnessError(f"manifest field {key} must be an integer")
    return value


def expect_string_list(raw: object, key: str) -> list[str]:
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise HarnessError(f"manifest field {key} must be a list of strings")
    return list(raw)


def validate_manifest(repo_root: pathlib.Path, specs: Sequence[BenchmarkSpec]) -> None:
    seen_benchmarks: set[str] = set()
    seen_slugs: set[str] = set()
    for spec in specs:
        if spec.benchmark in seen_benchmarks:
            raise HarnessError(f"duplicate benchmark in manifest: {spec.benchmark}")
        if spec.slug in seen_slugs:
            raise HarnessError(f"duplicate slug in manifest: {spec.slug}")
        seen_benchmarks.add(spec.benchmark)
        seen_slugs.add(spec.slug)

        if spec.validation.kind == "float_lines" and spec.validation.abs_tolerance is None:
            raise HarnessError(f"{spec.benchmark} is missing abs_tolerance for float_lines validation")
        if spec.validation.kind != "float_lines" and spec.validation.abs_tolerance is not None:
            raise HarnessError(f"{spec.benchmark} has an unexpected abs_tolerance for {spec.validation.kind}")

        for path_str in (
            spec.validation.fixture_path,
            spec.java.source_path,
            spec.c.source_path,
        ):
            if not (repo_root / path_str).exists():
                raise HarnessError(f"manifest path does not exist: {path_str}")

        if spec.java.main_class is None:
            raise HarnessError(f"{spec.benchmark} is missing java.main_class")


def select_benchmarks(specs: Sequence[BenchmarkSpec], raw_selection: str | None) -> list[BenchmarkSpec]:
    if raw_selection is None:
        return list(specs)

    requested = [item.strip() for item in raw_selection.split(",") if item.strip()]
    if not requested:
        raise HarnessError("--benchmarks requires at least one benchmark name")

    by_name = {spec.benchmark: spec for spec in specs}
    missing = [name for name in requested if name not in by_name]
    if missing:
        raise HarnessError(f"unknown benchmark(s): {', '.join(missing)}")
    return [by_name[name] for name in requested]


def select_targets(raw_selection: str | None) -> list[str]:
    if raw_selection is None:
        return list(DEFAULT_TARGET_ORDER)

    requested = [item.strip() for item in raw_selection.split(",") if item.strip()]
    if not requested:
        raise HarnessError("--targets requires at least one target name")
    missing = [name for name in requested if name not in DEFAULT_TARGET_ORDER]
    if missing:
        raise HarnessError(f"unknown target(s): {', '.join(missing)}")
    return requested


def expand_execution_matrix(
    specs: Sequence[BenchmarkSpec],
    targets: Sequence[str],
    repeats: int,
    bosatsu_version: str,
) -> dict[str, object]:
    setup_commands = bosatsu_setup_commands(bosatsu_version, targets)
    build_commands: list[BuildPlan] = []
    validation_runs: list[RunPlan] = []
    warmup_runs: list[RunPlan] = []
    measured_runs: list[RunPlan] = []

    for spec in specs:
        for target in targets:
            build_command = build_command_for_plan(spec, target, bosatsu_version)
            if build_command is not None:
                build_commands.append(BuildPlan(spec.benchmark, target, build_command))
            validation_runs.append(
                RunPlan(
                    benchmark=spec.benchmark,
                    target=target,
                    phase="validation",
                    input=spec.sample_input,
                    repeat_index=None,
                    warmup_count=0,
                    command=render_run_command(spec, target, spec.sample_input, bosatsu_version, TEMP_PBM_PLACEHOLDER),
                    capture_stdout_to=TEMP_PBM_PLACEHOLDER if spec.validation.kind == "exact_bytes" else None,
                    validation_kind=spec.validation.kind,
                )
            )
            warmup_runs.append(
                RunPlan(
                    benchmark=spec.benchmark,
                    target=target,
                    phase="warmup",
                    input=spec.performance_input,
                    repeat_index=None,
                    warmup_count=warmup_count(target),
                    command=render_run_command(spec, target, spec.performance_input, bosatsu_version, TEMP_PBM_PLACEHOLDER),
                    capture_stdout_to=TEMP_PBM_PLACEHOLDER if spec.validation.kind == "exact_bytes" else None,
                    validation_kind=spec.validation.kind,
                )
            )

    for repeat_index in range(repeats):
        rotated = rotate_targets(targets, repeat_index)
        for spec in specs:
            for target in rotated:
                measured_runs.append(
                    RunPlan(
                        benchmark=spec.benchmark,
                        target=target,
                        phase="measure",
                        input=spec.performance_input,
                        repeat_index=repeat_index + 1,
                        warmup_count=0,
                        command=render_run_command(spec, target, spec.performance_input, bosatsu_version, TEMP_PBM_PLACEHOLDER),
                        capture_stdout_to=TEMP_PBM_PLACEHOLDER if spec.validation.kind == "exact_bytes" else None,
                        validation_kind=spec.validation.kind,
                    )
                )

    return {
        "setup_commands": setup_commands,
        "builds": [dataclasses.asdict(item) for item in build_commands],
        "sample_validations": [dataclasses.asdict(item) for item in validation_runs],
        "warmups": [dataclasses.asdict(item) for item in warmup_runs],
        "measurements": [dataclasses.asdict(item) for item in measured_runs],
    }


def rotate_targets(targets: Sequence[str], offset: int) -> list[str]:
    if not targets:
        return []
    pivot = offset % len(targets)
    return list(targets[pivot:]) + list(targets[:pivot])


def warmup_count(target: str) -> int:
    return 2 if target in ("bosatsu_jvm", "java") else 1


def bosatsu_jar_rel_path(version: str) -> str:
    return f".bosatsuc/cli/{version}/bosatsu.jar"


def bosatsu_setup_commands(version: str, targets: Sequence[str]) -> list[str]:
    jar_rel = bosatsu_jar_rel_path(version)
    jar_dir = str(pathlib.PurePosixPath(jar_rel).parent)
    jar_url = f"https://github.com/johnynek/bosatsu/releases/download/v{version}/bosatsu.jar"
    commands: list[str] = []
    if "bosatsu_jvm" in targets:
        commands.extend(
            [
                shlex.join(["mkdir", "-p", jar_dir]),
                shlex.join(["curl", "-fL", jar_url, "-o", jar_rel]),
                shlex.join(["java", "-jar", jar_rel, "fetch"]),
            ]
        )
    if "bosatsu_c" in targets:
        commands.extend(
            [
                shlex.join(["./bosatsu", "--fetch"]),
                shlex.join(["./bosatsu", "fetch"]),
            ]
        )
    return commands


def build_command_for_plan(spec: BenchmarkSpec, target: str, bosatsu_version: str) -> str | None:
    if target == "bosatsu_jvm":
        return shlex.join(["java", "-jar", bosatsu_jar_rel_path(bosatsu_version), "fetch"])
    if target == "bosatsu_c":
        return shlex.join(bosatsu_c_build_command(spec))
    if target == "java":
        return shlex.join(java_build_command(spec))
    if target == "c":
        return shlex.join(c_build_command(spec))
    raise HarnessError(f"unsupported target: {target}")


def render_run_command(
    spec: BenchmarkSpec,
    target: str,
    input_value: int,
    bosatsu_version: str,
    temp_pbm_path: str | None,
) -> str:
    command = shlex.join(run_command_for(spec, target, input_value, bosatsu_version))
    if spec.validation.kind == "exact_bytes":
        if temp_pbm_path is None:
            raise HarnessError("binary benchmarks require a temp output path")
        capture_path = (
            temp_pbm_path
            if temp_pbm_path == TEMP_PBM_PLACEHOLDER
            else shlex.quote(temp_pbm_path)
        )
        return f"{command} > {capture_path}"
    return command


def ensure_prerequisites(targets: Sequence[str], skip_setup: bool) -> None:
    required: set[str] = set()
    if not skip_setup and "bosatsu_jvm" in targets:
        required.add("curl")
    if "bosatsu_jvm" in targets or "java" in targets:
        required.add("java")
    if "java" in targets:
        required.add("javac")
    if "bosatsu_c" in targets or "c" in targets:
        required.add("gcc")
    for command in sorted(required):
        if shutil.which(command) is None:
            raise HarnessError(f"required command not found on PATH: {command}")


def ensure_repo_setup(repo_root: pathlib.Path, bosatsu_version: str, targets: Sequence[str]) -> None:
    jar_rel = bosatsu_jar_rel_path(bosatsu_version)
    if "bosatsu_jvm" in targets:
        jar_path = repo_root / jar_rel
        jar_path.parent.mkdir(parents=True, exist_ok=True)
        if not jar_path.exists():
            run_checked(
                repo_root,
                ["curl", "-fL", f"https://github.com/johnynek/bosatsu/releases/download/v{bosatsu_version}/bosatsu.jar", "-o", jar_rel],
            )
        run_checked(repo_root, ["java", "-jar", jar_rel, "fetch"])
    if "bosatsu_c" in targets:
        run_checked(repo_root, ["./bosatsu", "--fetch"])
        run_checked(repo_root, ["./bosatsu", "fetch"])


def build_targets(
    repo_root: pathlib.Path,
    specs: Sequence[BenchmarkSpec],
    targets: Sequence[str],
    bosatsu_version: str,
) -> dict[tuple[str, str], str]:
    build_commands: dict[tuple[str, str], str] = {}
    for spec in specs:
        for target in targets:
            build_string = build_command_for_plan(spec, target, bosatsu_version)
            if build_string is None:
                continue
            build_commands[(spec.benchmark, target)] = build_string

            if target == "bosatsu_jvm":
                continue
            if target == "bosatsu_c":
                outdir = repo_root / ".bosatsu_bench/game" / spec.slug
                outdir.mkdir(parents=True, exist_ok=True)
                run_checked(repo_root, bosatsu_c_build_command(spec))
            elif target == "java":
                outdir = repo_root / ".build/benchmarksgame/java" / spec.slug
                outdir.mkdir(parents=True, exist_ok=True)
                run_checked(repo_root, java_build_command(spec))
            elif target == "c":
                outdir = repo_root / ".build/benchmarksgame/c" / spec.slug
                outdir.mkdir(parents=True, exist_ok=True)
                run_checked(repo_root, c_build_command(spec))
            else:
                raise HarnessError(f"unsupported target: {target}")
    return build_commands


def run_sample_validations(
    repo_root: pathlib.Path,
    specs: Sequence[BenchmarkSpec],
    targets: Sequence[str],
    bosatsu_version: str,
) -> list[ValidationRow]:
    rows: list[ValidationRow] = []
    for spec in specs:
        for target in targets:
            execution = execute_command_capture(repo_root, spec, target, spec.sample_input, bosatsu_version)
            validate_sample_output(repo_root, spec, target, execution.output_bytes)
            rows.append(
                ValidationRow(
                    benchmark=spec.benchmark,
                    target=target,
                    input=spec.sample_input,
                    exit_code=execution.exit_code,
                    validation_passed=True,
                    output_byte_count=len(execution.output_bytes) if spec.validation.kind == "exact_bytes" else None,
                    output_sha256=sha256_hex(execution.output_bytes) if spec.validation.kind == "exact_bytes" else None,
                )
            )
    return rows


def run_warmups(
    repo_root: pathlib.Path,
    specs: Sequence[BenchmarkSpec],
    targets: Sequence[str],
    bosatsu_version: str,
) -> None:
    for spec in specs:
        for target in targets:
            for _ in range(warmup_count(target)):
                execute_command_capture(repo_root, spec, target, spec.performance_input, bosatsu_version)


def run_measured_repeats(
    repo_root: pathlib.Path,
    specs: Sequence[BenchmarkSpec],
    targets: Sequence[str],
    repeats: int,
    bosatsu_version: str,
    build_commands: dict[tuple[str, str], str],
    validation_rows: Sequence[ValidationRow],
    toolchain: ToolchainInfo,
) -> list[RunRecord]:
    validation_ok = {
        (row.benchmark, row.target): row.validation_passed
        for row in validation_rows
    }

    records: list[RunRecord] = []
    for repeat_index in range(repeats):
        rotated_targets = rotate_targets(targets, repeat_index)
        for spec in specs:
            for target in rotated_targets:
                execution = execute_command_capture(repo_root, spec, target, spec.performance_input, bosatsu_version)
                source_id, source_url = source_provenance(repo_root, toolchain, spec, target)
                records.append(
                    RunRecord(
                        benchmark=spec.benchmark,
                        target=target,
                        input=spec.performance_input,
                        repeat_index=repeat_index + 1,
                        elapsed_ns=execution.elapsed_ns,
                        exit_code=execution.exit_code,
                        validation_passed=validation_ok[(spec.benchmark, target)] and execution.exit_code == 0,
                        source_id=source_id,
                        source_url=source_url,
                        build_command=build_commands[(spec.benchmark, target)],
                        run_command=execution.run_command,
                        git_sha=toolchain.git_sha,
                        bosatsu_version=toolchain.bosatsu_version,
                        java_version=toolchain.java_version,
                        gcc_version=toolchain.gcc_version,
                        os=toolchain.os,
                        cpu_model=toolchain.cpu_model,
                        timestamp_utc=utc_now(),
                        output_byte_count=len(execution.output_bytes) if spec.validation.kind == "exact_bytes" else None,
                        output_sha256=sha256_hex(execution.output_bytes) if spec.validation.kind == "exact_bytes" else None,
                    )
                )
    return records


def source_provenance(
    repo_root: pathlib.Path,
    toolchain: ToolchainInfo,
    spec: BenchmarkSpec,
    target: str,
) -> tuple[str, str]:
    if target == "java":
        return spec.java.source_id, spec.java.source_url
    if target == "c":
        return spec.c.source_id, spec.c.source_url

    bosatsu_file = pathlib.PurePosixPath("src") / pathlib.PurePosixPath(f"{spec.bosatsu_package}.bosatsu")
    ref = toolchain.git_sha if toolchain.git_sha != "local" else "main"
    source_url = f"{toolchain.repo_uri.rstrip('/')}/blob/{ref}/{bosatsu_file.as_posix()}"
    return spec.bosatsu_package, source_url


def execute_command_capture(
    repo_root: pathlib.Path,
    spec: BenchmarkSpec,
    target: str,
    input_value: int,
    bosatsu_version: str,
) -> ExecutionOutput:
    command = run_command_for(spec, target, input_value, bosatsu_version)
    if spec.validation.kind == "exact_bytes":
        with tempfile.NamedTemporaryFile(prefix=f"{spec.slug}-{target}-", suffix=".pbm", delete=False) as handle:
            temp_path = pathlib.Path(handle.name)
        try:
            with temp_path.open("wb") as stdout_handle:
                start = time.perf_counter_ns()
                completed = subprocess.run(
                    command,
                    cwd=repo_root,
                    stdout=stdout_handle,
                    stderr=subprocess.PIPE,
                )
                elapsed_ns = time.perf_counter_ns() - start
            output_bytes = temp_path.read_bytes()
        finally:
            temp_path.unlink(missing_ok=True)
        command_string = render_run_command(spec, target, input_value, bosatsu_version, str(temp_path))
    else:
        start = time.perf_counter_ns()
        completed = subprocess.run(
            command,
            cwd=repo_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        elapsed_ns = time.perf_counter_ns() - start
        output_bytes = completed.stdout
        command_string = render_run_command(spec, target, input_value, bosatsu_version, None)

    if completed.returncode != 0 and input_value == spec.sample_input:
        stderr_text = decode_output(completed.stderr, "stderr")
        raise HarnessError(
            f"sample validation command failed for {spec.benchmark}/{target} "
            f"with exit code {completed.returncode}: {stderr_text.strip()}"
        )

    return ExecutionOutput(
        exit_code=completed.returncode,
        elapsed_ns=elapsed_ns,
        output_bytes=output_bytes,
        run_command=command_string,
    )


def normalize_validation_output(spec: BenchmarkSpec, target: str, actual: bytes) -> bytes:
    if target == "bosatsu_jvm" and spec.validation.kind != "exact_bytes" and actual.endswith(b"\n\n"):
        return actual[:-1]
    return actual


def validate_sample_output(
    repo_root: pathlib.Path,
    spec: BenchmarkSpec,
    target: str,
    actual: bytes,
) -> None:
    fixture_path = repo_root / spec.validation.fixture_path
    normalized_actual = normalize_validation_output(spec, target, actual)
    if spec.validation.kind == "exact_bytes":
        expected = fixture_path.read_bytes()
        if expected != normalized_actual:
            raise HarnessError(
                f"{spec.benchmark} validation failed: expected {len(expected)} bytes, got {len(normalized_actual)} bytes"
            )
        return

    expected_text = normalize_fixture_text(fixture_path.read_text(encoding="utf-8"))
    actual_text = decode_output(normalized_actual, "stdout")
    if actual_text and not actual_text.endswith("\n"):
        raise HarnessError(f"{spec.benchmark} validation failed: output must end with a newline")

    if spec.validation.kind == "exact_text":
        if expected_text != actual_text:
            raise HarnessError(
                f"{spec.benchmark} validation failed: expected exact text fixture, got different output"
            )
        return

    if spec.validation.kind == "float_lines":
        validate_float_lines(spec.benchmark, expected_text, actual_text, spec.validation.abs_tolerance or 0.0)
        return

    raise HarnessError(f"unsupported validation kind: {spec.validation.kind}")


def validate_float_lines(label: str, expected_text: str, actual_text: str, abs_tolerance: float) -> None:
    expected_lines = split_lines(expected_text)
    actual_lines = split_lines(actual_text)
    if len(expected_lines) != len(actual_lines):
        raise HarnessError(
            f"{label} validation failed: expected {len(expected_lines)} lines, got {len(actual_lines)}"
        )

    for index, (expected_line, actual_line) in enumerate(zip(expected_lines, actual_lines), start=1):
        if not has_fixed_9_fractional_digits(actual_line):
            raise HarnessError(
                f"{label} validation failed at line {index}: actual output must use exactly 9 fractional digits"
            )
        try:
            expected_value = float(expected_line)
            actual_value = float(actual_line)
        except ValueError as exc:
            raise HarnessError(f"{label} validation failed at line {index}: {exc}") from exc

        if abs(expected_value - actual_value) > abs_tolerance:
            raise HarnessError(
                f"{label} validation failed at line {index}: "
                f"|expected - actual| = {abs(expected_value - actual_value)} exceeds {abs_tolerance}"
            )


def split_lines(value: str) -> list[str]:
    if value == "":
        return []
    # Keep explicit blank lines so float-line validation can reject them,
    # while still treating a single trailing terminator as line punctuation.
    return value.splitlines()


def has_fixed_9_fractional_digits(value: str) -> bool:
    if value == "":
        return False
    sign = value[0] == "-"
    digits = value[1:] if sign else value
    whole, dot, fractional = digits.partition(".")
    return dot == "." and whole.isdigit() and len(fractional) == 9 and fractional.isdigit()


def normalize_fixture_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    if normalized and not normalized.endswith("\n"):
        return normalized + "\n"
    return normalized


def decode_output(output: bytes, label: str) -> str:
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HarnessError(f"failed to decode {label} as UTF-8: {exc}") from exc


def bosatsu_c_build_command(spec: BenchmarkSpec) -> list[str]:
    outdir = f".bosatsu_bench/game/{spec.slug}"
    return [
        "./bosatsu",
        "build",
        "--main_pack",
        spec.bosatsu_package,
        "--outdir",
        outdir,
        "--exe_out",
        spec.slug,
    ]


def java_build_command(spec: BenchmarkSpec) -> list[str]:
    return [
        "javac",
        "-d",
        f".build/benchmarksgame/java/{spec.slug}",
        *spec.java.local_compile_flags,
        spec.java.source_path,
    ]


def c_build_command(spec: BenchmarkSpec) -> list[str]:
    return [
        "gcc",
        *spec.c.local_compile_flags,
        spec.c.source_path,
        "-o",
        f".build/benchmarksgame/c/{spec.slug}/{spec.slug}",
        *spec.c.local_libraries,
    ]


def run_command_for(
    spec: BenchmarkSpec,
    target: str,
    input_value: int,
    bosatsu_version: str,
) -> list[str]:
    if target == "bosatsu_jvm":
        return [
            "java",
            "-jar",
            bosatsu_jar_rel_path(bosatsu_version),
            "eval",
            "--main",
            spec.bosatsu_main,
            "--run",
            str(input_value),
        ]
    if target == "bosatsu_c":
        return [
            f".bosatsu_bench/game/{spec.slug}/{spec.slug}",
            str(input_value),
        ]
    if target == "java":
        if spec.java.main_class is None:
            raise HarnessError(f"{spec.benchmark} is missing the java main class")
        return [
            "java",
            *spec.java.local_run_flags,
            "-cp",
            f".build/benchmarksgame/java/{spec.slug}",
            spec.java.main_class,
            str(input_value),
        ]
    if target == "c":
        return [
            f".build/benchmarksgame/c/{spec.slug}/{spec.slug}",
            str(input_value),
        ]
    raise HarnessError(f"unsupported target: {target}")


def run_checked(repo_root: pathlib.Path, command: Sequence[str]) -> None:
    completed = subprocess.run(
        list(command),
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0:
        stderr = decode_output(completed.stderr, "stderr").strip()
        raise HarnessError(f"command failed ({shlex.join(command)}): {stderr}")


def read_toolchain_info(repo_root: pathlib.Path, bosatsu_version: str, targets: Sequence[str]) -> ToolchainInfo:
    git_sha = run_text_command(repo_root, ["git", "rev-parse", "HEAD"], default="local")
    java_version = "unavailable"
    if "bosatsu_jvm" in targets or "java" in targets:
        java_version = first_nonempty_line(run_version_command(["java", "-version"]))
    gcc_version = "unavailable"
    if "bosatsu_c" in targets or "c" in targets:
        gcc_version = first_nonempty_line(run_version_command(["gcc", "--version"]))
    os_name = platform.platform()
    cpu_model = read_cpu_model()
    repo_uri = read_repo_uri(repo_root)
    return ToolchainInfo(
        git_sha=git_sha,
        bosatsu_version=bosatsu_version,
        java_version=java_version,
        gcc_version=gcc_version,
        os=os_name,
        cpu_model=cpu_model,
        repo_uri=repo_uri,
    )


def read_repo_uri(repo_root: pathlib.Path) -> str:
    conf_path = repo_root / "src/zafu_conf.json"
    conf = json.loads(conf_path.read_text(encoding="utf-8"))
    repo_uri = conf.get("repo_uri")
    if isinstance(repo_uri, str) and repo_uri:
        return repo_uri
    return "https://github.com/johnynek/zafu"


def run_text_command(repo_root: pathlib.Path, command: Sequence[str], default: str) -> str:
    completed = subprocess.run(
        list(command),
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if completed.returncode != 0:
        return default
    return completed.stdout.strip() or default


def run_version_command(command: Sequence[str]) -> str:
    completed = subprocess.run(
        list(command),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    text = completed.stdout.strip()
    if text:
        return text
    return completed.stderr.strip()


def first_nonempty_line(value: str) -> str:
    for line in value.splitlines():
        line = line.strip()
        if line:
            return line
    return "unknown"


def read_cpu_model() -> str:
    if sys.platform == "darwin":
        completed = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if completed.returncode == 0:
            return completed.stdout.strip() or "unknown"

    cpuinfo = pathlib.Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" in line:
                key, value = line.split(":", 1)
                if key.strip() == "model name":
                    return value.strip() or "unknown"

    processor = platform.processor().strip()
    return processor or "unknown"


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def render_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=False) + "\n"


def render_csv(records: Sequence[RunRecord]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(CSV_COLUMNS)
    for record in records:
        writer.writerow([
            record.benchmark,
            record.target,
            record.input,
            record.repeat_index,
            record.elapsed_ns,
            record.exit_code,
            "true" if record.validation_passed else "false",
            record.source_id,
            record.git_sha,
            record.timestamp_utc,
        ])
    return buffer.getvalue()


def emit_text(content: str, path_str: str | None) -> None:
    if path_str is None:
        sys.stdout.write(content)
        return
    path = pathlib.Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except HarnessError as exc:
        print(f"benchmarksgame_compare: {exc}", file=sys.stderr)
        raise SystemExit(1)
