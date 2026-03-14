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

1. `./bosatsu lib check`
2. `./bosatsu lib test`
3. Dry-run style publish via `scripts/publish_bosatsu_libs.sh --dry-run` with `URI_BASE=https://example.invalid/`

## Benchmarking vector

Run the vector microbenchmarks with:

```bash
scripts/benchmark_vector.sh
```

The script prints two sections:

1. `JVM benchmarks:` from `./bosatsu lib eval --main Zafu/Benchmark/Vector::main --run`
2. `C benchmarks:` from a built native executable via `./bosatsu lib build --main_pack Zafu/Benchmark/Vector --exe_out ...`

Or directly:

```bash
./bosatsu lib eval --main Zafu/Benchmark/Vector::main --run
```

The benchmark prints CSV with header:

`case,size,iterations,ops,elapsed_us,ops_per_us,sink`

`ops_per_us` is most useful for comparing runs of the same `case` across different sizes.

## CI, docs, and release

- CI (`.github/workflows/ci.yml`) runs check/test/dry-run publish and validates docs generation plus markdown-to-HTML conversion with Pandoc on pull requests.
- Docs (`.github/workflows/docs-pages.yml`) runs on each push to `main`, generates markdown docs with `./bosatsu lib doc`, converts them to HTML with Pandoc, and deploys to GitHub Pages.
- Release (`.github/workflows/release.yml`) triggers on `vX.Y.Z` tags, verifies the tagged commit is on `main`, publishes `.bosatsu_lib` files, and uploads them to the GitHub Release page.

## API docs

- [Zafu library docs](https://johnynek.github.io/zafu/)
