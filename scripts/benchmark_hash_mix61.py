import argparse
import csv
import hashlib
import json
import pathlib
import platform
import statistics
import subprocess
from datetime import datetime, timezone


REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_BASELINE_DIR = REPO_ROOT / "docs/hash-mix-61"
DEFAULT_JSON_PATH = DEFAULT_BASELINE_DIR / "baseline-local.json"
DEFAULT_CSV_PATH = DEFAULT_BASELINE_DIR / "baseline-local.csv"
BUILD_DIR = REPO_ROOT / ".bosatsu_bench" / "hash-mix-61"
EXE_PATH = BUILD_DIR / "hash-mix-61"
TARGETS = ("bosatsu_jvm", "bosatsu_c")
STRATEGIES = ("int_fallback", "int64_limb_31")
WORKLOADS = ("collection_hash", "hash_map_hash", "hash_set_hash")
WIN_THRESHOLD = 1.02
BENCH_SOURCE_PATHS = (
    pathlib.Path("scripts/benchmark_hash_mix61.py"),
    pathlib.Path("src/Zafu/Abstract/Internal/Hash61.bosatsu"),
    pathlib.Path("src/Zafu/Abstract/Hash.bosatsu"),
    pathlib.Path("src/Zafu/Benchmark/HashMix61.bosatsu"),
    pathlib.Path("src/Zafu/Collection/HashMap.bosatsu"),
    pathlib.Path("src/Zafu/Collection/HashSet.bosatsu"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the mix_61 strategy benchmark on JVM and C backends and write a checked-in local baseline artifact."
    )
    parser.add_argument("--output-json", default=str(DEFAULT_JSON_PATH))
    parser.add_argument("--output-csv", default=str(DEFAULT_CSV_PATH))
    return parser.parse_args()


def run_checked(command: list[str], *, capture_stdout: bool = False) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture_stdout else None,
        stderr=subprocess.PIPE if capture_stdout else None,
    )
    if capture_stdout:
        return completed.stdout
    return ""


def run_version_command(command: list[str]) -> str:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip().splitlines()[0]


def benchmark_source_fingerprint(paths: tuple[pathlib.Path, ...]) -> str:
    hasher = hashlib.sha256()
    for rel_path in paths:
        hasher.update(rel_path.as_posix().encode("utf-8"))
        hasher.update(b"\0")
        hasher.update((REPO_ROOT / rel_path).read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def parse_benchmark_csv(raw_csv: str, target: str) -> list[dict[str, object]]:
    reader = csv.DictReader(raw_csv.splitlines())
    rows: list[dict[str, object]] = []
    for row in reader:
        rows.append(
            {
                "target": target,
                "workload": row["workload"],
                "strategy": row["strategy"],
                "size": int(row["size"]),
                "iterations": int(row["iterations"]),
                "ops": int(row["ops"]),
                "elapsed_us": int(row["elapsed_us"]),
                "ops_per_us": float(row["ops_per_us"]),
                "sink": row["sink"],
            }
        )
    return rows


def comparison_winner(ratio: float) -> str:
    if ratio >= WIN_THRESHOLD:
        return "int_fallback"
    if ratio <= (1.0 / WIN_THRESHOLD):
        return "int64_limb_31"
    return "tie"


def build_strategy_summary(results: list[dict[str, object]]) -> dict[str, object]:
    comparisons: list[dict[str, object]] = []
    for target in TARGETS:
        for workload in WORKLOADS:
            fallback_rows = [
                row["ops_per_us"]
                for row in results
                if row["target"] == target
                and row["workload"] == workload
                and row["strategy"] == "int_fallback"
            ]
            candidate_rows = [
                row["ops_per_us"]
                for row in results
                if row["target"] == target
                and row["workload"] == workload
                and row["strategy"] == "int64_limb_31"
            ]
            fallback_mean = statistics.mean(fallback_rows)
            candidate_mean = statistics.mean(candidate_rows)
            ratio = fallback_mean / candidate_mean
            comparisons.append(
                {
                    "target": target,
                    "workload": workload,
                    "winner": comparison_winner(ratio),
                    "int_fallback_mean_ops_per_us": fallback_mean,
                    "int64_limb_31_mean_ops_per_us": candidate_mean,
                    "int_fallback_over_candidate_ratio": ratio,
                }
            )

    candidate_wins = sum(1 for row in comparisons if row["winner"] == "int64_limb_31")
    fallback_wins = sum(1 for row in comparisons if row["winner"] == "int_fallback")
    chosen_strategy = "int_fallback" if candidate_wins == 0 else "int64_limb_31"
    decision_rule = (
        "Keep the Int fallback only when the limb candidate is not faster on any "
        "supported backend workload; otherwise choose the Int64 limb strategy."
    )
    rationale = (
        "int64_limb_31 wins at least one supported-backend workload"
        if chosen_strategy == "int64_limb_31"
        else "int_fallback never loses to int64_limb_31 on the measured workloads"
    )

    return {
        "chosen_strategy": chosen_strategy,
        "candidate_strategy": "int64_limb_31",
        "comparison_metric": "mean_ops_per_us",
        "win_threshold_ratio": WIN_THRESHOLD,
        "decision_rule": decision_rule,
        "rationale": rationale,
        "fallback_wins": fallback_wins,
        "candidate_wins": candidate_wins,
        "comparisons": comparisons,
    }


def write_csv(path: pathlib.Path, results: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "target",
                "workload",
                "strategy",
                "size",
                "iterations",
                "ops",
                "elapsed_us",
                "ops_per_us",
                "sink",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(results)


def main() -> int:
    args = parse_args()
    output_json = pathlib.Path(args.output_json)
    output_csv = pathlib.Path(args.output_csv)

    run_checked(["./bosatsu", "--fetch"])
    run_checked(["./bosatsu", "fetch"])

    jvm_command = ["./bosatsu", "eval", "--main", "Zafu/Benchmark/HashMix61::main", "--run"]
    c_build_command = [
        "./bosatsu",
        "build",
        "--main_pack",
        "Zafu/Benchmark/HashMix61",
        "--outdir",
        str(BUILD_DIR),
        "--exe_out",
        str(EXE_PATH),
    ]
    c_command = [str(EXE_PATH)]

    jvm_rows = parse_benchmark_csv(run_checked(jvm_command, capture_stdout=True), "bosatsu_jvm")
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    run_checked(c_build_command)
    c_rows = parse_benchmark_csv(run_checked(c_command, capture_stdout=True), "bosatsu_c")

    results = [*jvm_rows, *c_rows]
    strategy_summary = build_strategy_summary(results)
    source_fingerprint = benchmark_source_fingerprint(BENCH_SOURCE_PATHS)

    artifact = {
        "run_metadata": {
            "format_version": 2,
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source_provenance": {
                "kind": "source_fingerprint",
                "algorithm": "sha256",
                "files": [path.as_posix() for path in BENCH_SOURCE_PATHS],
                "digest": source_fingerprint,
            },
            "bosatsu_version": (REPO_ROOT / ".bosatsu_version").read_text(encoding="utf-8").strip(),
            "java_version": run_version_command(["java", "-version"]),
            "gcc_version": run_version_command(["gcc", "--version"]),
            "os": platform.platform(),
            "cpu_model": platform.machine(),
            "targets": list(TARGETS),
            "strategies": list(STRATEGIES),
            "workloads": list(WORKLOADS),
            "jvm_command": " ".join(jvm_command),
            "c_build_command": " ".join(c_build_command),
            "c_command": str(EXE_PATH.relative_to(REPO_ROOT)),
        },
        "strategy_summary": strategy_summary,
        "results": results,
    }

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    write_csv(output_csv, results)
    print(f"wrote {output_json.relative_to(REPO_ROOT)}")
    print(f"wrote {output_csv.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
