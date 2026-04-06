import contextlib
import csv
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MODULE_PATH = REPO_ROOT / "scripts/benchmarksgame_compare.py"
SPEC = importlib.util.spec_from_file_location("benchmarksgame_compare", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)
WRAPPER_PATH = REPO_ROOT / "scripts/benchmarksgame_compare.sh"


class BenchmarksgameCompareTests(unittest.TestCase):
    def setUp(self) -> None:
        self.specs = MODULE.load_manifest(REPO_ROOT)
        self.version = MODULE.read_text(REPO_ROOT / ".bosatsu_version")

    def test_manifest_covers_all_phase1_benchmarks(self) -> None:
        self.assertEqual(
            [spec.benchmark for spec in self.specs],
            [
                "n-body",
                "spectral-norm",
                "binary-trees",
                "fannkuch-redux",
                "mandelbrot",
            ],
        )

    def test_manifest_paths_exist(self) -> None:
        for spec in self.specs:
            self.assertTrue((REPO_ROOT / spec.validation.fixture_path).is_file())
            self.assertTrue((REPO_ROOT / spec.java.source_path).is_file())
            self.assertTrue((REPO_ROOT / spec.c.source_path).is_file())

    def test_explicit_jvm_plan_uses_repo_accurate_eval_commands(self) -> None:
        plan = MODULE.expand_execution_matrix(self.specs, ["bosatsu_jvm", "c"], 2, self.version)
        validations = {
            (entry["benchmark"], entry["target"]): entry
            for entry in plan["sample_validations"]
        }
        self.assertEqual(
            validations[("n-body", "bosatsu_jvm")]["command"],
            f"java -jar .bosatsuc/cli/{self.version}/bosatsu.jar eval --main Zafu/Benchmark/Game/NBody::main --run 1000",
        )
        self.assertEqual(
            validations[("mandelbrot", "bosatsu_jvm")]["command"],
            f"java -jar .bosatsuc/cli/{self.version}/bosatsu.jar eval --main Zafu/Benchmark/Game/Mandelbrot::main --run 200 > {MODULE.TEMP_PBM_PLACEHOLDER}",
        )
        self.assertEqual(
            validations[("mandelbrot", "bosatsu_jvm")]["capture_stdout_to"],
            MODULE.TEMP_PBM_PLACEHOLDER,
        )

    def test_subset_plan_only_includes_selected_setup_commands(self) -> None:
        jvm_plan = MODULE.expand_execution_matrix(self.specs[:1], ["bosatsu_jvm"], 1, self.version)
        self.assertEqual(
            jvm_plan["setup_commands"],
            [
                f"mkdir -p .bosatsuc/cli/{self.version}",
                f"curl -fL https://github.com/johnynek/bosatsu/releases/download/v{self.version}/bosatsu.jar -o .bosatsuc/cli/{self.version}/bosatsu.jar",
                f"java -jar .bosatsuc/cli/{self.version}/bosatsu.jar fetch",
            ],
        )

        bosatsu_c_plan = MODULE.expand_execution_matrix(self.specs[:1], ["bosatsu_c"], 1, self.version)
        self.assertEqual(
            bosatsu_c_plan["setup_commands"],
            [
                "./bosatsu --fetch",
                "./bosatsu fetch",
            ],
        )

        c_plan = MODULE.expand_execution_matrix(self.specs[:1], ["c"], 1, self.version)
        self.assertEqual(c_plan["setup_commands"], [])

    def test_bosatsu_c_plan_uses_repo_relative_exe_out_path(self) -> None:
        plan = MODULE.expand_execution_matrix(self.specs[:1], ["bosatsu_c"], 1, self.version)
        builds = {
            (entry["benchmark"], entry["target"]): entry["command"]
            for entry in plan["builds"]
        }
        self.assertEqual(
            builds[("n-body", "bosatsu_c")],
            "./bosatsu build --main_pack Zafu/Benchmark/Game/NBody --outdir .bosatsu_bench/game/n-body --exe_out .bosatsu_bench/game/n-body/n-body",
        )

    def test_bosatsu_c_setup_runs_native_install_then_dependency_fetch(self) -> None:
        with mock.patch.object(MODULE, "run_checked") as run_checked:
            MODULE.ensure_repo_setup(REPO_ROOT, self.version, ["bosatsu_c"])

        self.assertEqual(
            run_checked.call_args_list,
            [
                mock.call(REPO_ROOT, ["./bosatsu", "--fetch"]),
                mock.call(REPO_ROOT, ["./bosatsu", "fetch"]),
            ],
        )

    def test_rotation_preserves_target_set(self) -> None:
        targets = ["bosatsu_jvm", "bosatsu_c", "java", "c"]
        rotations = [MODULE.rotate_targets(targets, index) for index in range(len(targets))]
        self.assertEqual([rotation[0] for rotation in rotations], targets)
        for rotation in rotations:
            self.assertCountEqual(rotation, targets)

    def test_wrapper_requires_python_3_9_or_better(self) -> None:
        cases = [
            (
                "falls_back_to_compatible_python",
                {"python3": (1, 23), "python": (0, 0)},
                0,
                "python",
                None,
            ),
            (
                "fails_when_no_compatible_python_exists",
                {"python3": (1, 23), "python": (1, 24)},
                1,
                None,
                "Python 3.9+ is required",
            ),
        ]
        for name, interpreters, expected_code, expected_log, expected_stderr in cases:
            with self.subTest(name=name):
                with tempfile.TemporaryDirectory() as tmpdir:
                    temp_dir = pathlib.Path(tmpdir)
                    log_path = temp_dir / "wrapper.log"
                    for executable, (version_exit, exec_exit) in interpreters.items():
                        script_path = temp_dir / executable
                        script_path.write_text(
                            "\n".join(
                                [
                                    "#!/usr/bin/env bash",
                                    "set -euo pipefail",
                                    'if [ "${1-}" = "-c" ]; then',
                                    f"  exit {version_exit}",
                                    "fi",
                                    f'printf "%s\\n" "{executable}" >> "{log_path}"',
                                    f"exit {exec_exit}",
                                    "",
                                ]
                            ),
                            encoding="utf-8",
                        )
                        script_path.chmod(0o755)

                    env = os.environ.copy()
                    env["PATH"] = f"{temp_dir}{os.pathsep}{env['PATH']}"
                    completed = subprocess.run(
                        [str(WRAPPER_PATH), "--print-plan"],
                        cwd=REPO_ROOT,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        env=env,
                    )

                    self.assertEqual(completed.returncode, expected_code)
                    if expected_log is None:
                        self.assertFalse(log_path.exists())
                    else:
                        self.assertEqual(log_path.read_text(encoding="utf-8").splitlines(), [expected_log])
                    if expected_stderr is None:
                        self.assertEqual(completed.stderr, "")
                    else:
                        self.assertIn(expected_stderr, completed.stderr)

    def test_java_only_validate_skip_setup_does_not_probe_gcc(self) -> None:
        version_calls: list[tuple[str, ...]] = []

        def fake_run_version(command: list[str]) -> str:
            version_calls.append(tuple(command))
            if command[0] == "java":
                return 'openjdk version "21.0.2"'
            raise FileNotFoundError("gcc missing")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = pathlib.Path(tmpdir) / "java-only.json"
            argv = [
                "benchmarksgame_compare.py",
                "--benchmarks",
                "n-body",
                "--targets",
                "java",
                "--validate-only",
                "--skip-setup",
                "--output-json",
                str(out_path),
            ]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(
                    MODULE.shutil,
                    "which",
                    side_effect=lambda command: None if command == "gcc" else f"/usr/bin/{command}",
                ), \
                mock.patch.object(MODULE, "build_targets", return_value={}), \
                mock.patch.object(
                    MODULE,
                    "run_sample_validations",
                    return_value=[
                        MODULE.ValidationRow("n-body", "java", 1000, 0, True, None, None),
                    ],
                ), \
                mock.patch.object(MODULE, "run_version_command", side_effect=fake_run_version), \
                mock.patch.object(MODULE, "run_text_command", return_value="dc2da6cf"), \
                mock.patch.object(MODULE.platform, "platform", return_value="test-os"), \
                mock.patch.object(MODULE, "read_cpu_model", return_value="test-cpu"), \
                contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(MODULE.main(), 0)

        self.assertEqual(version_calls, [("java", "-version")])

    def test_c_only_validate_skips_java_setup(self) -> None:
        version_calls: list[tuple[str, ...]] = []

        def fake_run_version(command: list[str]) -> str:
            version_calls.append(tuple(command))
            if command[0] == "gcc":
                return "gcc (GCC) 14.2.0"
            raise FileNotFoundError("java missing")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = pathlib.Path(tmpdir) / "c-only.json"
            argv = [
                "benchmarksgame_compare.py",
                "--benchmarks",
                "n-body",
                "--targets",
                "c",
                "--validate-only",
                "--output-json",
                str(out_path),
            ]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(
                    MODULE.shutil,
                    "which",
                    side_effect=lambda command: None if command in ("java", "javac") else f"/usr/bin/{command}",
                ), \
                mock.patch.object(MODULE, "build_targets", return_value={}), \
                mock.patch.object(
                    MODULE,
                    "run_sample_validations",
                    return_value=[
                        MODULE.ValidationRow("n-body", "c", 1000, 0, True, None, None),
                    ],
                ), \
                mock.patch.object(MODULE, "run_version_command", side_effect=fake_run_version), \
                mock.patch.object(MODULE, "run_text_command", return_value="dc2da6cf"), \
                mock.patch.object(MODULE.platform, "platform", return_value="test-os"), \
                mock.patch.object(MODULE, "read_cpu_model", return_value="test-cpu"), \
                mock.patch.object(MODULE, "run_checked", side_effect=FileNotFoundError("java missing")), \
                contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(MODULE.main(), 0)

        self.assertEqual(version_calls, [("gcc", "--version")])

    def test_bosatsu_c_only_validate_records_gcc_version(self) -> None:
        version_calls: list[tuple[str, ...]] = []

        def fake_run_version(command: list[str]) -> str:
            version_calls.append(tuple(command))
            if command[0] == "gcc":
                return "gcc (GCC) 14.2.0"
            raise AssertionError(f"unexpected version probe: {command}")

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = pathlib.Path(tmpdir) / "bosatsu-c-only.json"
            argv = [
                "benchmarksgame_compare.py",
                "--benchmarks",
                "n-body",
                "--targets",
                "bosatsu_c",
                "--validate-only",
                "--skip-setup",
                "--output-json",
                str(out_path),
            ]
            with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(MODULE.shutil, "which", side_effect=lambda command: f"/usr/bin/{command}"), \
                mock.patch.object(MODULE, "build_targets", return_value={}), \
                mock.patch.object(
                    MODULE,
                    "run_sample_validations",
                    return_value=[
                        MODULE.ValidationRow("n-body", "bosatsu_c", 1000, 0, True, None, None),
                    ],
                ), \
                mock.patch.object(MODULE, "run_version_command", side_effect=fake_run_version), \
                mock.patch.object(MODULE, "run_text_command", return_value="fd94ebd2"), \
                mock.patch.object(MODULE.platform, "platform", return_value="test-os"), \
                mock.patch.object(MODULE, "read_cpu_model", return_value="test-cpu"), \
                contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(MODULE.main(), 0)

            artifact = json.loads(out_path.read_text(encoding="utf-8"))

        self.assertEqual(artifact["run_metadata"]["gcc_version"], "gcc (GCC) 14.2.0")
        self.assertEqual(version_calls, [("gcc", "--version")])

    def test_bosatsu_c_only_validate_requires_gcc_up_front(self) -> None:
        argv = [
            "benchmarksgame_compare.py",
            "--benchmarks",
            "n-body",
            "--targets",
            "bosatsu_c",
            "--validate-only",
            "--skip-setup",
        ]
        with mock.patch.object(sys, "argv", argv), \
            mock.patch.object(
                MODULE.shutil,
                "which",
                side_effect=lambda command: None if command == "gcc" else f"/usr/bin/{command}",
            ), \
            mock.patch.object(MODULE, "run_version_command", side_effect=AssertionError("version probe should not run")), \
            contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(MODULE.HarnessError, "required command not found on PATH: gcc"):
                MODULE.main()

    def test_bosatsu_jvm_text_validation_trims_eval_trailer_newline(self) -> None:
        spectral = next(spec for spec in self.specs if spec.benchmark == "spectral-norm")
        fixture = (REPO_ROOT / spectral.validation.fixture_path).read_bytes()
        self.assertEqual(
            MODULE.normalize_validation_output(spectral, "bosatsu_jvm", fixture + b"\n"),
            fixture,
        )

    def test_exact_byte_run_command_uses_placeholder_path(self) -> None:
        mandelbrot = next(spec for spec in self.specs if spec.benchmark == "mandelbrot")
        fixture = (REPO_ROOT / mandelbrot.validation.fixture_path).read_bytes()

        def fake_run(command: list[str], cwd: pathlib.Path, stdout, stderr, timeout=None):
            stdout.write(fixture)
            return subprocess.CompletedProcess(command, 0, b"", b"")

        with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
            execution = MODULE.execute_command_capture(REPO_ROOT, mandelbrot, "bosatsu_jvm", mandelbrot.sample_input, self.version)

        self.assertEqual(execution.output_bytes, fixture)
        self.assertIn(MODULE.TEMP_PBM_PLACEHOLDER, execution.run_command)
        self.assertNotIn("/tmp/", execution.run_command)

    def test_execute_command_capture_marks_text_timeout(self) -> None:
        spectral = next(spec for spec in self.specs if spec.benchmark == "spectral-norm")

        def fake_run(command: list[str], cwd: pathlib.Path, stdout, stderr, timeout=None):
            raise subprocess.TimeoutExpired(command, timeout or 1.0, output=b"8.880000000\n", stderr=b"")

        with mock.patch.object(MODULE.subprocess, "run", side_effect=fake_run):
            execution = MODULE.execute_command_capture(
                REPO_ROOT,
                spectral,
                "java",
                spectral.performance_input,
                self.version,
                1.0,
            )

        self.assertTrue(execution.timed_out)
        self.assertEqual(execution.exit_code, 124)
        self.assertEqual(execution.output_bytes, b"8.880000000\n")

    def test_run_warmups_records_time_budget_skips(self) -> None:
        spectral = next(spec for spec in self.specs if spec.benchmark == "spectral-norm")

        with mock.patch.object(
            MODULE,
            "execute_command_capture",
            return_value=MODULE.ExecutionOutput(124, 1, b"", "cmd", timed_out=True),
        ):
            skipped = MODULE.run_warmups(
                REPO_ROOT,
                [spectral],
                ["java"],
                {(spectral.benchmark, "java")},
                self.version,
                None,
            )

        self.assertEqual(
            skipped,
            [
                MODULE.SkippedMeasurement(
                    benchmark="spectral-norm",
                    target="java",
                    phase="warmup",
                    reason="time budget exhausted during warmup",
                )
            ],
        )

    def test_run_measured_repeats_records_timeout_rows_and_future_skips(self) -> None:
        spectral = next(spec for spec in self.specs if spec.benchmark == "spectral-norm")
        validation_rows = [
            MODULE.ValidationRow("spectral-norm", "java", 100, 0, True, None, None),
        ]
        build_commands = {("spectral-norm", "java"): "javac -d .build/benchmarksgame/java/spectral-norm ..."}
        toolchain = MODULE.ToolchainInfo(
            git_sha="abc123",
            bosatsu_version=self.version,
            java_version='openjdk version "21.0.2"',
            gcc_version="unavailable",
            os="test-os",
            cpu_model="test-cpu",
            repo_uri="https://github.com/johnynek/zafu",
        )

        with mock.patch.object(
            MODULE,
            "execute_command_capture",
            side_effect=[
                MODULE.ExecutionOutput(0, 1, b"", "java -cp ..."),
                MODULE.ExecutionOutput(0, 1, b"", "java -cp ..."),
                MODULE.ExecutionOutput(124, 1, b"", "java -cp ...", timed_out=True),
            ],
        ), mock.patch.object(
            MODULE,
            "source_provenance",
            return_value=("spectralnorm-graalvmaot-8", "https://example.invalid/spectral"),
        ), mock.patch.object(MODULE, "utc_now", return_value="2026-04-06T22:00:00Z"):
            records, skipped = MODULE.run_measured_repeats(
                REPO_ROOT,
                [spectral],
                ["java"],
                {(spectral.benchmark, "java")},
                2,
                self.version,
                build_commands,
                validation_rows,
                toolchain,
                None,
            )

        self.assertEqual(len(records), 1)
        self.assertTrue(records[0].timed_out)
        self.assertEqual(records[0].failure_reason, "time budget exhausted during measured run")
        self.assertEqual(
            skipped,
            [
                MODULE.SkippedMeasurement(
                    benchmark="spectral-norm",
                    target="java",
                    phase="measure",
                    reason="time budget exhausted during measured run",
                )
            ],
        )

    def test_canonical_baseline_artifacts_exist_and_match(self) -> None:
        baseline_dir = REPO_ROOT / "docs/benchmarksgame"
        json_path = baseline_dir / "baseline-local.json"
        csv_path = baseline_dir / "baseline-local.csv"
        self.assertTrue(json_path.is_file(), f"missing canonical baseline artifact: {json_path}")
        self.assertTrue(csv_path.is_file(), f"missing canonical baseline artifact: {csv_path}")

        artifact = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("run_metadata", artifact)
        self.assertIn("results", artifact)
        metadata = artifact["run_metadata"]
        self.assertFalse(metadata["validation_only"])
        self.assertEqual(metadata["measured_repeats"], 1)
        self.assertIsNone(metadata["time_budget_seconds"])
        self.assertEqual(
            metadata["selected_benchmarks"],
            ["fannkuch-redux"],
        )
        self.assertEqual(
            metadata["selected_targets"],
            ["c", "java"],
        )
        # A checked-in artifact records the commit it was generated from, which
        # should stay reachable from HEAD instead of matching the commit that
        # later stores the artifact itself.
        artifact_git_sha = metadata["git_sha"]
        self.assertRegex(artifact_git_sha, r"^[0-9a-f]{40}$")
        commit_present = (
            subprocess.run(
                ["git", "cat-file", "-e", f"{artifact_git_sha}" + "^{commit}"],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).returncode
            == 0
        )
        if commit_present:
            self.assertEqual(
                subprocess.run(
                    ["git", "merge-base", "--is-ancestor", artifact_git_sha, "HEAD"],
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ).returncode,
                0,
            )
        else:
            self.assertEqual(
                subprocess.run(
                    ["git", "rev-parse", "--is-shallow-repository"],
                    cwd=REPO_ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                ).stdout.strip(),
                "true",
                "baseline artifact git_sha should only be unavailable in shallow clones",
            )
        validation_rows = metadata["validation_results"]
        selected_benchmarks = metadata["selected_benchmarks"]
        selected_targets = metadata["selected_targets"]
        self.assertEqual(len(validation_rows), len(selected_benchmarks) * len(selected_targets))
        self.assertTrue(all(row["validation_passed"] for row in validation_rows))
        self.assertCountEqual(
            [(row["benchmark"], row["target"]) for row in validation_rows],
            [
                (spec.benchmark, target)
                for spec in self.specs
                if spec.benchmark in selected_benchmarks
                for target in selected_targets
            ],
        )
        self.assertFalse(metadata["time_budget_exhausted"])
        self.assertEqual(metadata["skipped_measurements"], [])
        self.assertCountEqual(
            [(row["benchmark"], row["target"]) for row in artifact["results"]],
            [
                (benchmark, target)
                for benchmark in selected_benchmarks
                for target in selected_targets
            ],
        )

        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle)
            header = next(reader)
            rows = list(reader)

        self.assertEqual(header, MODULE.CSV_COLUMNS)
        self.assertEqual(len(rows), len(artifact["results"]))

    def test_readme_uses_canonical_baseline_artifact_paths(self) -> None:
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("docs/benchmarksgame/baseline-local.json", readme)
        self.assertIn("docs/benchmarksgame/baseline-local.csv", readme)
        self.assertIn("--benchmarks fannkuch-redux", readme)
        self.assertIn("--targets c,java", readme)

    def test_nbody_validation_rejects_surplus_blank_lines(self) -> None:
        nbody = next(spec for spec in self.specs if spec.benchmark == "n-body")
        fixture = (REPO_ROOT / nbody.validation.fixture_path).read_bytes()
        with self.assertRaisesRegex(MODULE.HarnessError, "expected 2 lines, got 3"):
            MODULE.validate_sample_output(REPO_ROOT, nbody, "java", fixture + b"\n")

    def test_nbody_validation_reports_blank_decimal_lines_as_harness_errors(self) -> None:
        nbody = next(spec for spec in self.specs if spec.benchmark == "n-body")
        malformed_cases = [
            ("blank_first_line", b"\n-0.169087605\n", "line 1: actual output must use exactly 9 fractional digits"),
            ("blank_second_line", b"-0.169075164\n\n", "line 2: actual output must use exactly 9 fractional digits"),
        ]
        for name, actual, message in malformed_cases:
            with self.subTest(name=name):
                with self.assertRaisesRegex(MODULE.HarnessError, message):
                    MODULE.validate_sample_output(REPO_ROOT, nbody, "java", actual)

    def test_csv_projection_stays_stable(self) -> None:
        record = MODULE.RunRecord(
            benchmark="n-body",
            target="bosatsu_jvm",
            input=50000000,
            repeat_index=3,
            elapsed_ns=123456789,
            exit_code=0,
            validation_passed=True,
            source_id="Zafu/Benchmark/Game/NBody",
            source_url="https://example.invalid/nbody",
            build_command="java -jar .bosatsuc/cli/0.0.64/bosatsu.jar fetch",
            run_command="java -jar .bosatsuc/cli/0.0.64/bosatsu.jar eval --main Zafu/Benchmark/Game/NBody::main --run 50000000",
            git_sha="abc123",
            bosatsu_version="0.0.64",
            java_version="openjdk version \"21.0.2\"",
            gcc_version="gcc (Ubuntu 14.2.0-4ubuntu2) 14.2.0",
            os="macOS-15.4-arm64",
            cpu_model="Apple M4",
            timestamp_utc="2026-04-04T00:00:00Z",
            output_byte_count=None,
            output_sha256=None,
        )
        self.assertEqual(
            MODULE.render_csv([record]),
            (
                "benchmark,target,input,repeat_index,elapsed_ns,exit_code,validation_passed,source_id,git_sha,timestamp_utc\n"
                "n-body,bosatsu_jvm,50000000,3,123456789,0,true,Zafu/Benchmark/Game/NBody,abc123,2026-04-04T00:00:00Z\n"
            ),
        )


if __name__ == "__main__":
    unittest.main()
