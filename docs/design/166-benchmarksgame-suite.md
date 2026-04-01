---
issue: 166
priority: 3
touch_paths:
  - docs/design/166-benchmarksgame-suite.md
depends_on: []
estimated_size: M
generated_at: 2026-04-01T23:28:28Z
---

# Benchmarksgame Suite Contract

_Roadmap issue: #166 (https://github.com/johnynek/zafu/issues/166)_

## Phase-1 Benchmark Set
Phase 1 standardizes a five-benchmark suite that covers numeric kernels, allocation-heavy structural work, and exact-output bitmap generation while staying within the current Bosatsu support surface.

Pinned baseline selection rules:
- C: prefer the fastest extant benchmarksgame C page that avoids the benchmarksgame `*` marker when a clean alternative exists, avoids OpenMP, pthreads, APR, or other non-default allocator or runtime dependencies, and still has a live program page.
- Java: prefer the fastest extant live Java source page without obvious parallel execution in the source page, then run that exact vendored `.java` source with `javac` and `java` locally. The source provenance remains the benchmarksgame `graalvmaot` page, but the local target is HotSpot JVM, not `native-image`.

The phase-1 benchmarks are:
- `n-body`: small fixed floating-point model with simple text output and no external fixtures.
- `spectral-norm`: pure numeric kernel with one scalar result and minimal I/O.
- `binary-trees`: allocation and recursion stress test with deterministic text output.
- `fannkuch-redux`: permutation and array-mutation kernel with deterministic small text output.
- `mandelbrot`: exact-output bitmap benchmark that complements the numeric and structural kernels.

## Deferred Benchmarks
These benchmarks are intentionally out of scope for phase 1:

| Benchmark | Rationale |
| --- | --- |
| `k-nucleotide` | Depends on larger FASTA-oriented text handling and would pull phase 1 toward hash-heavy streaming support before the core kernel suite lands. |
| `reverse-complement` | Dominated by streaming byte I/O and line-wrapping behavior rather than the phase-1 kernel and harness support layer. |
| `regex-redux` | Would mostly measure regex engine or FFI or library behavior, which the repo does not yet abstract cleanly for Bosatsu comparison. |
| `fasta` | Primarily RNG plus large text emission and mainly serves the deferred text benchmarks; `mandelbrot` already covers exact-output streaming in phase 1. |
| `pidigits` | Bosatsu `Int` already supports arbitrary precision, but `pidigits` would widen phase 1 beyond the reviewed five-program suite and shift the benchmark mix toward big-integer digit-streaming work instead of the numeric, structural, and bitmap kernels this contract is pinning first. |

## Benchmark Contract Matrix
| Benchmark | Why it is in phase 1 | Benchmarksgame description | Official validation source | Large-N performance input | Required CLI/output contract | Pinned Java reference | Pinned C reference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n-body` | Small fixed model, pure floating-point kernel, simple text output, no external fixtures. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/nbody.html#nbody` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/nbody-output.txt`, validated at `N=1000` with tolerance equivalent to `ndiff -abserr 1.0e-8`. | `50000000` | One required positional integer `N`. Stdout must be exactly two newline-terminated decimal lines: initial energy, then final energy, both formatted to 9 fractional digits. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-graalvmaot-4.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-gcc-6.html` |
| `spectral-norm` | Pure numeric kernel with a single scalar result and minimal I/O. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/spectralnorm.html#spectralnorm` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/spectralnorm-output.txt`, validated at `N=100` with exact text compare. | `5500` | One required positional integer `N`. Stdout must be exactly one newline-terminated decimal line formatted to 9 fractional digits. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-graalvmaot-8.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-gcc-8.html` |
| `binary-trees` | Allocation and recursion stress test with deterministic text output and no external input fixture. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/binarytrees.html#binarytrees` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/binarytrees-output.txt`, validated at `N=10` with exact text compare. | `21` | One required positional integer `N`. Stdout must match the official line-oriented report exactly: stretch-tree line, per-depth aggregate lines, then long-lived-tree line. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-graalvmaot-3.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-gcc-1.html` |
| `fannkuch-redux` | Permutation and array-mutation kernel with deterministic small text output. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/fannkuchredux.html#fannkuchredux` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/fannkuchredux-output.txt`, validated at `N=7` with exact text compare. | `12` | One required positional integer `N`. Stdout must be exactly two lines: checksum on line 1 and `Pfannkuchen(N) = maxflips` on line 2. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-graalvmaot-2.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-gcc-3.html` |
| `mandelbrot` | Exact-output byte benchmark that complements the numeric and structural kernels. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/mandelbrot.html#mandelbrot` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/mandelbrot-output.txt`, validated at `N=200` with exact byte compare via `cmp`. | `16000` | One required positional integer `N`. Stdout must be binary PBM with header `P4\nN N\n` followed by correctly packed bitmap bytes. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-graalvmaot-8.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-gcc-8.html` |

## Repository Layout Conventions
- `src/zafu_conf.json` remains the package-level build configuration entrypoint. Downstream benchmark-game work should update it to expose any new `Zafu/Benchmark/Game/*` packages and keep the Bosatsu dependency or build metadata needed for both JVM and C benchmark entrypoints centralized in one file.
- Each Bosatsu benchmark package lives in its own `src/Zafu/Benchmark/Game/*.bosatsu` file and exports a thin `main` with pure helpers kept testable alongside a paired `*Tests` file.
- `src/Zafu/Benchmark/Game/Harness.bosatsu` owns CLI normalization, stable result rows, validation helpers, and shared formatting so later benchmark nodes do not duplicate that logic.
- `fixtures/benchmarksgame/` stores the official small-input validation artifacts exactly as downloaded. `n-body` is the only tolerance-based validator; the other four benchmarks validate by exact text or byte compare.
- `vendor/benchmarksgame/manifest.json` records provenance for every vendored baseline: source page URL, date pinned, local source path, expected main class or binary name, thread model, local build flags, and required libraries.
- `docs/benchmarksgame/baseline-local.json` is the checked-in canonical baseline artifact. `docs/benchmarksgame/baseline-local.csv` is the flat companion export for quick comparisons.

These path names are intentional parts of the contract, not cleanup targets. `fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm` keeps the `n200` suffix because the checked-in PBM sample is tied to the exact validation input used by the byte-compare rule. The vendored C filenames retain the source identifier in the basename so the local filename, pinned benchmarksgame page, and `vendor/benchmarksgame/manifest.json` provenance entry stay unambiguous. The Java entries intentionally keep the simpler `.java` basenames because their source identity is already carried by the containing directory and the manifest metadata.

## Single-Machine Comparison Protocol
Command contract by target:
- `bosatsu_jvm`: `./bosatsu eval --main Zafu/Benchmark/Game/<Package>::main --run <N>`
- `bosatsu_c`: `./bosatsu build --main_pack Zafu/Benchmark/Game/<Package> --outdir .bosatsu_bench/game/<slug> --exe_out .bosatsu_bench/game/<slug>/<slug>` and then run the produced executable with `<N>`
- `java`: `javac -d .build/benchmarksgame/java/<slug> vendor/benchmarksgame/java/<source-id>/<main>.java` and then `java -cp .build/benchmarksgame/java/<slug> <mainclass> <N>`
- `c`: `gcc -O3 -fomit-frame-pointer -march=native ... vendor/benchmarksgame/c/<source-id>/<file>.c` plus only the libraries listed in `vendor/benchmarksgame/manifest.json`

Execution policy:
1. Build all four targets before any measured run.
2. For each benchmark and target, run the official sample validation input first. Only targets that pass validation are eligible for performance runs.
3. Warmup policy: 2 untimed warmup executions at the performance input for `bosatsu_jvm` and `java`; 1 untimed warmup execution at the performance input for `bosatsu_c` and `c`.
4. Repeat policy: 5 measured runs per benchmark and target at the official large-N input. Record each run individually and derive summaries later; do not collapse the raw artifact to a single min or mean.
5. Ordering: run the suite in this fixed benchmark order: `n-body`, `spectral-norm`, `binary-trees`, `fannkuch-redux`, `mandelbrot`. Within each repetition, rotate target order so the same target is not always first after an idle period.
6. Output handling: capture stdout directly for the four text benchmarks. For `mandelbrot`, write stdout to a temporary file, record byte count and SHA-256, validate sample `N=200` against the checked-in PBM fixture, and delete the temporary file after each measured run.
7. Timing source: use one repo-controlled monotonic timer around subprocess execution. Do not make platform-specific `/usr/bin/time` output part of the contract.
8. Metadata capture: at minimum record `benchmark`, `target`, `input`, `repeat_index`, `elapsed_ns`, `exit_code`, `validation_passed`, `source_id`, `source_url`, `build_command`, `run_command`, `git_sha`, `bosatsu_version`, `java_version`, `gcc_version`, `os`, `cpu_model`, and `timestamp_utc`.
9. Result artifact shape: `docs/benchmarksgame/baseline-local.json` should contain a top-level `run_metadata` object plus a `results` array. `docs/benchmarksgame/baseline-local.csv` should flatten the measured rows with stable columns `benchmark,target,input,repeat_index,elapsed_ns,exit_code,validation_passed,source_id,git_sha,timestamp_utc`.

The following caveats are part of the contract:
- benchmarksgame BenchExec numbers are not directly comparable to the local harness output because compiler, runtime, and machine setup differ.
- The pinned Java source pages are current benchmarksgame `graalvmaot` submissions, but the local `java` target in phase 1 is HotSpot JVM from the same vendored source, not `native-image`.
- Phase-1 results are informational only and should not gate CI or be framed as language-wide claims.

## Planned Downstream Touch Paths
- `docs/design/166-benchmarksgame-suite.md`
- `src/zafu_conf.json`
- `src/Zafu/Benchmark/Game/Harness.bosatsu`
- `src/Zafu/Benchmark/Game/HarnessTests.bosatsu`
- `src/Zafu/Benchmark/Game/NBody.bosatsu`
- `src/Zafu/Benchmark/Game/NBodyTests.bosatsu`
- `src/Zafu/Benchmark/Game/SpectralNorm.bosatsu`
- `src/Zafu/Benchmark/Game/SpectralNormTests.bosatsu`
- `src/Zafu/Benchmark/Game/BinaryTrees.bosatsu`
- `src/Zafu/Benchmark/Game/BinaryTreesTests.bosatsu`
- `src/Zafu/Benchmark/Game/FannkuchRedux.bosatsu`
- `src/Zafu/Benchmark/Game/FannkuchReduxTests.bosatsu`
- `src/Zafu/Benchmark/Game/Mandelbrot.bosatsu`
- `src/Zafu/Benchmark/Game/MandelbrotTests.bosatsu`
- `fixtures/benchmarksgame/nbody/nbody-output.txt`
- `fixtures/benchmarksgame/spectralnorm/spectralnorm-output.txt`
- `fixtures/benchmarksgame/binarytrees/binarytrees-output.txt`
- `fixtures/benchmarksgame/fannkuchredux/fannkuchredux-output.txt`
- `fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm`
- `vendor/benchmarksgame/manifest.json`
- `vendor/benchmarksgame/java/nbody-graalvmaot-4/nbody.java`
- `vendor/benchmarksgame/java/spectralnorm-graalvmaot-8/spectralnorm.java`
- `vendor/benchmarksgame/java/binarytrees-graalvmaot-3/binarytrees.java`
- `vendor/benchmarksgame/java/fannkuchredux-graalvmaot-2/fannkuchredux.java`
- `vendor/benchmarksgame/java/mandelbrot-graalvmaot-8/mandelbrot.java`
- `vendor/benchmarksgame/c/nbody-gcc-6/nbody.gcc-6.c`
- `vendor/benchmarksgame/c/spectralnorm-gcc-8/spectralnorm.gcc-8.c`
- `vendor/benchmarksgame/c/binarytrees-gcc-1/binarytrees.gcc-1.c`
- `vendor/benchmarksgame/c/fannkuchredux-gcc-3/fannkuchredux.gcc-3.c`
- `vendor/benchmarksgame/c/mandelbrot-gcc-8/mandelbrot.gcc-8.c`
- `scripts/benchmarksgame_compare.sh`
- `README.md`
- `docs/benchmarksgame/baseline-local.json`
- `docs/benchmarksgame/baseline-local.csv`
