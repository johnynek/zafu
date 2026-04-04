import importlib.util
import pathlib
import sys
import unittest


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

    def test_rotation_preserves_target_set(self) -> None:
        targets = ["bosatsu_jvm", "bosatsu_c", "java", "c"]
        rotations = [MODULE.rotate_targets(targets, index) for index in range(len(targets))]
        self.assertEqual([rotation[0] for rotation in rotations], targets)
        for rotation in rotations:
            self.assertCountEqual(rotation, targets)

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
