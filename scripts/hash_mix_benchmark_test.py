import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE_DIR = REPO_ROOT / "docs/hash-mix-61"
JSON_PATH = BASELINE_DIR / "baseline-local.json"
CSV_PATH = BASELINE_DIR / "baseline-local.csv"
NOTE_PATH = BASELINE_DIR / "README.md"
README_PATH = REPO_ROOT / "README.md"
HASH61_PATH = REPO_ROOT / "src/Zafu/Abstract/Internal/Hash61.bosatsu"
HASH_PATH = REPO_ROOT / "src/Zafu/Abstract/Hash.bosatsu"
HASHMAP_PATH = REPO_ROOT / "src/Zafu/Collection/HashMap.bosatsu"
HASHSET_PATH = REPO_ROOT / "src/Zafu/Collection/HashSet.bosatsu"
BENCH_PATH = REPO_ROOT / "src/Zafu/Benchmark/HashMix61.bosatsu"
BENCH_SOURCE_PATHS = [
    pathlib.Path("scripts/benchmark_hash_mix61.py"),
    pathlib.Path("src/Zafu/Abstract/Internal/Hash61.bosatsu"),
    pathlib.Path("src/Zafu/Abstract/Hash.bosatsu"),
    pathlib.Path("src/Zafu/Benchmark/HashMix61.bosatsu"),
    pathlib.Path("src/Zafu/Collection/HashMap.bosatsu"),
    pathlib.Path("src/Zafu/Collection/HashSet.bosatsu"),
]
class HashMix61BenchmarkTests(unittest.TestCase):
    def test_baseline_artifacts_exist(self) -> None:
        self.assertTrue(JSON_PATH.is_file())
        self.assertTrue(CSV_PATH.is_file())
        self.assertTrue(NOTE_PATH.is_file())

    def test_baseline_artifact_covers_required_workloads_and_decision(self) -> None:
        artifact = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        metadata = artifact["run_metadata"]
        source = metadata["source_provenance"]

        summary = artifact["strategy_summary"]
        self.assertEqual(summary["chosen_strategy"], "int64_limb_31")
        self.assertEqual(summary["candidate_strategy"], "int64_limb_31")
        self.assertNotIn("git_sha", metadata)
        self.assertNotIn("git_dirty", metadata)
        self.assertEqual(source["kind"], "source_fingerprint")
        self.assertEqual(source["algorithm"], "sha256")
        self.assertEqual(source["files"], [path.as_posix() for path in BENCH_SOURCE_PATHS])
        self.assertRegex(source["digest"], r"^[0-9a-f]{64}$")

        comparisons = summary["comparisons"]
        self.assertEqual(
            {row["target"] for row in comparisons},
            {"bosatsu_jvm", "bosatsu_c"},
        )
        self.assertEqual(
            {row["workload"] for row in comparisons},
            {"collection_hash", "hash_map_hash", "hash_set_hash"},
        )
        self.assertTrue(
            all(row["winner"] == "int64_limb_31" for row in comparisons if row["target"] == "bosatsu_c")
        )

        results = artifact["results"]
        self.assertEqual(
            {row["strategy"] for row in results},
            {"int_fallback", "int64_limb_31"},
        )

    def test_docs_reference_the_checked_in_baseline(self) -> None:
        readme = README_PATH.read_text(encoding="utf-8")
        note = NOTE_PATH.read_text(encoding="utf-8")

        self.assertIn("scripts/benchmark_hash_mix61.sh", readme)
        self.assertIn("docs/hash-mix-61/baseline-local.json", readme)
        self.assertIn("docs/hash-mix-61/baseline-local.csv", readme)

        self.assertIn("int_fallback", note)
        self.assertIn("int64_limb_31", note)
        self.assertIn("Zafu/Abstract/Internal/Hash61", note)

    def test_benchmark_and_production_share_the_same_hash61_helpers(self) -> None:
        hash61 = HASH61_PATH.read_text(encoding="utf-8")
        hash_impl = HASH_PATH.read_text(encoding="utf-8")
        hash_map = HASHMAP_PATH.read_text(encoding="utf-8")
        hash_set = HASHSET_PATH.read_text(encoding="utf-8")
        benchmark = BENCH_PATH.read_text(encoding="utf-8")

        self.assertIn("package Zafu/Abstract/Internal/Hash61", hash61)
        self.assertIn("sum_61_i64", hash61)
        self.assertIn("mix_61_limb_31", hash61)

        self.assertIn("from Zafu/Abstract/Internal/Hash61 import (", hash_impl)
        self.assertIn("from Zafu/Abstract/Internal/Hash61 import (", hash_map)
        self.assertIn("from Zafu/Abstract/Internal/Hash61 import (", hash_set)
        self.assertIn("from Zafu/Abstract/Internal/Hash61 import (", benchmark)

        old_sum = "normalize_61(int64_to_Int(add_Int64(left, right)))"
        self.assertNotIn(old_sum, hash_map)
        self.assertNotIn(old_sum, hash_set)


if __name__ == "__main__":
    unittest.main()
