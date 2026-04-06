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

## Benchmarksgame compare harness

Phase-1 cross-language comparison needs Python 3.9+, `curl`, `java`, `javac`, and `gcc`.

Bootstrap both Bosatsu entrypoints once from a clean checkout:

```bash
BOSATSU_VERSION="$(tr -d '[:space:]' < .bosatsu_version)"
mkdir -p ".bosatsuc/cli/${BOSATSU_VERSION}"
curl -fL "https://github.com/johnynek/bosatsu/releases/download/v${BOSATSU_VERSION}/bosatsu.jar" -o ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar"
java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" fetch
./bosatsu --fetch
./bosatsu fetch
```

`java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" fetch` prepares the explicit JVM CLI path used by `bosatsu_jvm`. `./bosatsu --fetch` and `./bosatsu fetch` prepare the default native wrapper and dependency cache used by `bosatsu_c`.

Use the harness wrapper to inspect or run the documented command matrix:

```bash
scripts/benchmarksgame_compare.sh --print-plan
scripts/benchmarksgame_compare.sh --validate-only
scripts/benchmarksgame_compare.sh --benchmarks fannkuch-redux,binary-trees,mandelbrot,spectral-norm --targets c,java,bosatsu_c,bosatsu_jvm --repeats 1 --time-budget-seconds 300 --output-json docs/benchmarksgame/baseline-local.json --output-csv docs/benchmarksgame/baseline-local.csv
```

The harness reads `vendor/benchmarksgame/manifest.json`, builds the Bosatsu C, Java, and C targets automatically, validates each target on the official sample input, and then records measured runs in the stable JSON/CSV formats. The checked-in baseline now preserves the intended post-`n-body` matrix over `fannkuch-redux`, `binary-trees`, `mandelbrot`, and `spectral-norm` for `c`, `java`, `bosatsu_c`, and `bosatsu_jvm`, but it does so under a five-minute time budget. That means `validation_results` cover the whole selected matrix, `results` contains whichever measured runs completed before the budget expired, and `skipped_measurements` records the benchmark/target pairs that ran out of time before or during warmup or measurement. The full Bosatsu C and Bosatsu JVM command matrix remains documented below so another engineer can rerun slower targets locally. Omit `--repeats 1` to use the harness default of five measured repeats, drop the `--benchmarks ...` or `--targets ...` filters to expand the matrix, and add `--skip-setup` after the one-time bootstrap above to reuse the fetched CLIs and caches.

The explicit Bosatsu JVM commands are:

```bash
BOSATSU_VERSION="$(tr -d '[:space:]' < .bosatsu_version)"
java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/NBody::main --run 50000000
java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/SpectralNorm::main --run 5500
java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/BinaryTrees::main --run 21
java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/FannkuchRedux::main --run 12
java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/Mandelbrot::main --run 16000 > /tmp/mandelbrot.pbm
```

For sample validation, use the same commands with the manifest inputs `1000`, `100`, `10`, `7`, and `200`. `mandelbrot` must stay byte-exact: redirect stdout to a temporary `.pbm` file, compare it against `fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm`, and avoid text decoding or newline normalization.

The checked-in baseline lives at `docs/benchmarksgame/baseline-local.json` and `docs/benchmarksgame/baseline-local.csv`. The JSON artifact captures host and toolchain metadata, validation results, exact build and run commands, per-run timings for completed measurements, and explicit skipped-work records for benchmark/target pairs that exhausted the time budget. The CSV is the flat projection for quick diffs or spreadsheet import.

Interpret the results as local, single-machine measurements only:

- They are informational and do not gate CI.
- They are not directly comparable to benchmarksgame BenchExec numbers, because compiler, runtime, and machine setup differ.
- The `java` target runs the vendored benchmarksgame `graalvmaot` sources on the local HotSpot JVM, not on `native-image`.
- `mandelbrot` rows include PBM byte count and SHA-256 from raw stdout capture so the Bosatsu JVM path stays replayable and byte-exact.

## CI, docs, and release

- CI (`.github/workflows/ci.yml`) runs check/test/dry-run publish and validates docs generation plus markdown-to-HTML conversion with Pandoc on pull requests.
- Benchmark compare (`.github/workflows/benchmarksgame-spectral-norm.yml`) runs a measured `spectral-norm` compare on demand or on PRs labeled `run-benchmarks`, prints the CSV in logs, writes a job summary table, and uploads the JSON/CSV artifacts.
- Docs (`.github/workflows/docs-pages.yml`) runs on each push to `main`, generates markdown docs with `./bosatsu doc`, converts them to HTML with Pandoc, and deploys to GitHub Pages.
- Release (`.github/workflows/release.yml`) triggers on `vX.Y.Z` tags, verifies the tagged commit is on `main`, publishes `.bosatsu_lib` files, and uploads them to the GitHub Release page.

## API docs

- [Zafu library docs](https://johnynek.github.io/zafu/)
