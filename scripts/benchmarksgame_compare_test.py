import contextlib
import importlib.util
import io
import pathlib
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

    def test_rotation_preserves_target_set(self) -> None:
        targets = ["bosatsu_jvm", "bosatsu_c", "java", "c"]
        rotations = [MODULE.rotate_targets(targets, index) for index in range(len(targets))]
        self.assertEqual([rotation[0] for rotation in rotations], targets)
        for rotation in rotations:
            self.assertCountEqual(rotation, targets)

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

    def test_bosatsu_jvm_text_validation_trims_eval_trailer_newline(self) -> None:
        spectral = next(spec for spec in self.specs if spec.benchmark == "spectral-norm")
        fixture = (REPO_ROOT / spectral.validation.fixture_path).read_bytes()
        self.assertEqual(
            MODULE.normalize_validation_output(spectral, "bosatsu_jvm", fixture + b"\n"),
            fixture,
        )

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
