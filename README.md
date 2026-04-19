# zafu

Useful Bosatsu code, starting with a `Vector` implementation.

## Layout

- `src/Zafu/Collection/Vector.bosatsu`: vector implementation and property tests.
- `src/zafu_conf.json`: Bosatsu library configuration.
- `bosatsu_libs.json`: maps library name to source root.
- `scripts/test.sh`: runs `lib check`, `lib test`, and dry-run `lib publish`.

## Setup

1. Fetch Bosatsu CLI/runtime:

```bash
./bosatsu --fetch
```

## Local validation

```bash
scripts/test.sh
```

This runs:

1. `./bosatsu check`
2. `./bosatsu test`
3. A validate-only `mandelbrot` benchmark harness smoke across `bosatsu_jvm`, `bosatsu_c`, `java`, and `c`
4. Dry-run style publish via `scripts/publish_bosatsu_libs.sh --dry-run` with `URI_BASE=https://example.invalid/`

## Benchmarking vector

Run the vector microbenchmarks with:

```bash
scripts/benchmark_vector.sh
```

The script prints two sections:

1. `JVM benchmarks:` from `./bosatsu eval --main Zafu/Benchmark/Vector::main --run`
2. `C benchmarks:` from a built native executable via `./bosatsu build --main_pack Zafu/Benchmark/Vector --exe_out ...`

Or directly:

```bash
./bosatsu eval --main Zafu/Benchmark/Vector::main --run
```

The benchmark prints CSV with header:

`case,size,iterations,ops,elapsed_us,ops_per_us,sink`

`ops_per_us` is most useful for comparing runs of the same `case` across different sizes.

## Benchmarking `mix_61`

Regenerate the checked-in local `mix_61` strategy baseline with:

```bash
scripts/benchmark_hash_mix61.sh
```

The current local benchmark artifacts live at:

- `docs/hash-mix-61/baseline-local.json`
- `docs/hash-mix-61/baseline-local.csv`

The summary note in `docs/hash-mix-61/README.md` explains the recorded tradeoff:
the Int fallback wins on the JVM cases, but the 31-bit Int64 limb strategy wins
decisively on the native `bosatsu_c` workloads, so `Hash.mix_61` follows the
benchmarked Int64 limb path.

## Benchmarksgame compare harness

Phase-1 cross-language comparison needs Python 3.9+, `curl`, `java`, `javac`, and `gcc` in addition to the Bosatsu wrapper setup.

Use the checked-in harness wrapper to vendor-aware validate or measure the full suite:

```bash
scripts/benchmarksgame_compare.sh --validate-only
scripts/benchmarksgame_compare.sh --output-json docs/benchmarksgame/baseline-local.json --output-csv docs/benchmarksgame/baseline-local.csv
```

The harness reads `vendor/benchmarksgame/manifest.json`, fetches the explicit JVM CLI jar under `.bosatsuc/cli/$BOSATSU_VERSION/bosatsu.jar`, and uses the repo-accurate `java -jar ... eval --main Zafu/Benchmark/Game/*::main --run` commands for `bosatsu_jvm`.

## CI, docs, and release

- CI (`.github/workflows/ci.yml`) runs check/test/dry-run publish and validates docs generation plus markdown-to-HTML conversion with Pandoc on pull requests.
- Benchmark compare (`.github/workflows/benchmarksgame-spectral-norm.yml`) runs a measured `spectral-norm` compare on demand or on PRs labeled `run-benchmarks`, prints the CSV in logs, writes a job summary table, and uploads the JSON/CSV artifacts.
- Docs (`.github/workflows/docs-pages.yml`) runs on each push to `main`, generates markdown docs with `./bosatsu doc`, converts them to HTML with Pandoc, and deploys to GitHub Pages.
- Release (`.github/workflows/release.yml`) triggers on `vX.Y.Z` tags, verifies the tagged commit is on `main`, publishes `.bosatsu_lib` files, and uploads them to the GitHub Release page.

## API docs

- [Zafu library docs](https://johnynek.github.io/zafu/)
