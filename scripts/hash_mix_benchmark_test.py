import json
import pathlib
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
BASELINE_DIR = REPO_ROOT / "docs/hash-mix-61"
JSON_PATH = BASELINE_DIR / "baseline-local.json"
CSV_PATH = BASELINE_DIR / "baseline-local.csv"
NOTE_PATH = BASELINE_DIR / "README.md"
README_PATH = REPO_ROOT / "README.md"


class HashMix61BenchmarkTests(unittest.TestCase):
    def test_baseline_artifacts_exist(self) -> None:
        self.assertTrue(JSON_PATH.is_file())
        self.assertTrue(CSV_PATH.is_file())
        self.assertTrue(NOTE_PATH.is_file())

    def test_baseline_artifact_covers_required_workloads_and_decision(self) -> None:
        artifact = json.loads(JSON_PATH.read_text(encoding="utf-8"))

        summary = artifact["strategy_summary"]
        self.assertEqual(summary["chosen_strategy"], "int64_limb_31")
        self.assertEqual(summary["candidate_strategy"], "int64_limb_31")

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


if __name__ == "__main__":
    unittest.main()
