---
issue: 173
priority: 3
touch_paths:
  - docs/design/166-benchmarksgame-suite.md
depends_on: []
estimated_size: M
generated_at: 2026-04-01T17:53:16Z
---

# Reference doc for #173: Author the concrete benchmark game suite spec document

_Issue: #173 (https://github.com/johnynek/zafu/issues/173)_

## Summary

Plan the doc-only creation of `docs/design/166-benchmarksgame-suite.md` by transcribing the reviewed suite contract from #168 into a self-contained phase-1 benchmark specification for downstream benchmark nodes.

## Context
Issue #173 is the `suite_contract_doc` node for roadmap #166. The upstream design contract at `docs/design/168-write-the-benchmark-game-suite-spec-and-comparison-contract.md` has already chosen the phase-1 benchmark set, pinned the benchmarksgame reference pages, defined the repo layout, and specified the local comparison protocol. This issue should turn that reviewed design into the concrete artifact at `docs/design/166-benchmarksgame-suite.md` that downstream implementation nodes will consume directly.

Because later nodes depend on the final file path rather than the higher-level design doc, the new suite spec should read like an operational contract. It should be self-contained, preserve the reviewed decisions verbatim where practical, and avoid introducing new benchmark choices, new baselines, or extra implementation scope.

## Goals
1. Add `docs/design/166-benchmarksgame-suite.md` as the single source of truth for the phase-1 benchmark game suite.
2. Preserve the exact five-benchmark phase-1 selection and the explicit rationale for deferring the text-heavy and big-integer benchmarks.
3. Copy forward the pinned benchmarksgame URLs, validation rules, performance inputs, and Java/C baseline references without reinterpretation.
4. Name the exact repo paths and comparison protocol that downstream nodes will implement against.
5. Keep the issue doc-only.

## Non-goals
1. Re-open the phase-1 benchmark selection or baseline selection rule.
2. Vendor sources, fixtures, or comparison artifacts in this issue.
3. Modify `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or any generated results.
4. Change the command contract or performance methodology already approved in `#168`.

## Artifact Architecture
The new `docs/design/166-benchmarksgame-suite.md` should be written as the concrete contract file, not as a design discussion. It should have these substantive sections, in this order:
1. `## Phase-1 Benchmark Set`
2. `## Deferred Benchmarks`
3. `## Benchmark Contract Matrix`
4. `## Repository Layout Conventions`
5. `## Single-Machine Comparison Protocol`
6. `## Planned Downstream Touch Paths`

Each section should be written so a later worker can implement against `docs/design/166-benchmarksgame-suite.md` alone. Cross-links back to `#168` are optional and should be minimal; the main document must stand on its own.

## Content Contract
### Phase-1 Benchmark Set
The doc should name these phase-1 benchmarks and keep the inclusion rationale aligned with the upstream contract:
- `n-body`: small fixed floating-point model with simple text output and no external fixtures.
- `spectral-norm`: pure numeric kernel with one scalar result and minimal I/O.
- `binary-trees`: allocation and recursion stress test with deterministic text output.
- `fannkuch-redux`: permutation and array-mutation kernel with deterministic small text output.
- `mandelbrot`: exact-output bitmap benchmark that complements the numeric and structural kernels.

### Deferred Benchmarks
The doc should explicitly mark these out of scope for phase 1 and preserve the reviewed rationale:

| Benchmark | Rationale |
| --- | --- |
| `k-nucleotide` | Depends on larger FASTA-oriented text handling and would pull phase 1 toward hash-heavy streaming support before the core kernel suite lands. |
| `reverse-complement` | Dominated by streaming byte I/O and line-wrapping behavior rather than the phase-1 kernel and harness support layer. |
| `regex-redux` | Would mostly measure regex engine or FFI or library behavior, which the repo does not yet abstract cleanly for Bosatsu comparison. |
| `fasta` | Primarily RNG plus large text emission and mainly serves the deferred text benchmarks; `mandelbrot` already covers exact-output streaming in phase 1. |
| `pidigits` | Bosatsu `Int` already supports arbitrary precision, but `pidigits` would widen phase 1 beyond the reviewed five-program suite and shift the benchmark mix toward big-integer digit-streaming work instead of the numeric, structural, and bitmap kernels this contract is pinning first. |

### Benchmark Contract Matrix
The doc should reproduce the benchmark matrix from `#168` with these exact columns: `Benchmark`, `Why it is in phase 1`, `Benchmarksgame description`, `Official validation source`, `Large-N performance input`, `Required CLI/output contract`, `Pinned Java reference`, and `Pinned C reference`.

| Benchmark | Why it is in phase 1 | Benchmarksgame description | Official validation source | Large-N performance input | Required CLI/output contract | Pinned Java reference | Pinned C reference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n-body` | Small fixed model, pure floating-point kernel, simple text output, no external fixtures. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/nbody.html#nbody` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/nbody-output.txt`, validated at `N=1000` with tolerance equivalent to `ndiff -abserr 1.0e-8`. | `50000000` | One required positional integer `N`. Stdout must be exactly two newline-terminated decimal lines: initial energy, then final energy, both formatted to 9 fractional digits. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-graalvmaot-4.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-gcc-6.html` |
| `spectral-norm` | Pure numeric kernel with a single scalar result and minimal I/O. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/spectralnorm.html#spectralnorm` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/spectralnorm-output.txt`, validated at `N=100` with exact text compare. | `5500` | One required positional integer `N`. Stdout must be exactly one newline-terminated decimal line formatted to 9 fractional digits. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-graalvmaot-8.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-gcc-8.html` |
| `binary-trees` | Allocation and recursion stress test with deterministic text output and no external input fixture. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/binarytrees.html#binarytrees` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/binarytrees-output.txt`, validated at `N=10` with exact text compare. | `21` | One required positional integer `N`. Stdout must match the official line-oriented report exactly: stretch-tree line, per-depth aggregate lines, then long-lived-tree line. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-graalvmaot-3.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-gcc-1.html` |
| `fannkuch-redux` | Permutation and array-mutation kernel with deterministic small text output. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/fannkuchredux.html#fannkuchredux` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/fannkuchredux-output.txt`, validated at `N=7` with exact text compare. | `12` | One required positional integer `N`. Stdout must be exactly two lines: checksum on line 1 and `Pfannkuchen(N) = maxflips` on line 2. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-graalvmaot-2.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-gcc-3.html` |
| `mandelbrot` | Exact-output byte benchmark that complements the numeric and structural kernels. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/mandelbrot.html#mandelbrot` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/mandelbrot-output.txt`, validated at `N=200` with exact byte compare via `cmp`. | `16000` | One required positional integer `N`. Stdout must be binary PBM with header `P4\nN N\n` followed by correctly packed bitmap bytes. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-graalvmaot-8.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-gcc-8.html` |

### Repository Layout Conventions
The concrete suite spec should carry forward these conventions explicitly:
- `src/zafu_conf.json` remains the package-level build configuration entrypoint. Downstream benchmark-game work should update it to expose any new `Zafu/Benchmark/Game/*` packages and keep the Bosatsu dependency or build metadata needed for both JVM and C benchmark entrypoints centralized in one file.
- Each Bosatsu benchmark package lives in its own `src/Zafu/Benchmark/Game/*.bosatsu` file and exports a thin `main` with pure helpers kept testable alongside a paired `*Tests` file.
- `src/Zafu/Benchmark/Game/Harness.bosatsu` owns CLI normalization, stable result rows, validation helpers, and shared formatting so later benchmark nodes do not duplicate that logic.
- `fixtures/benchmarksgame/` stores the official small-input validation artifacts exactly as downloaded. `n-body` is the only tolerance-based validator; the other four benchmarks validate by exact text or byte compare.
- `vendor/benchmarksgame/manifest.json` records provenance for every vendored baseline: source page URL, date pinned, local source path, expected main class or binary name, thread model, local build flags, and required libraries.
- `docs/benchmarksgame/baseline-local.json` is the checked-in canonical baseline artifact. `docs/benchmarksgame/baseline-local.csv` is the flat companion export for quick comparisons.

## Single-Machine Comparison Protocol
The suite spec should define these local targets and command shapes:
- `bosatsu_jvm`: `./bosatsu eval --main Zafu/Benchmark/Game/<Package>::main --run <N>`
- `bosatsu_c`: `./bosatsu build --main_pack Zafu/Benchmark/Game/<Package> --outdir .bosatsu_bench/game/<slug> --exe_out .bosatsu_bench/game/<slug>/<slug>` and then run the produced executable with `<N>`
- `java`: `javac -d .build/benchmarksgame/java/<slug> vendor/benchmarksgame/java/<source-id>/<main>.java` and then `java -cp .build/benchmarksgame/java/<slug> <mainclass> <N>`
- `c`: `gcc -O3 -fomit-frame-pointer -march=native ... vendor/benchmarksgame/c/<source-id>/<file>.c` plus only the libraries listed in `vendor/benchmarksgame/manifest.json`

The execution policy should be copied from `#168` without changing semantics:
1. Build all four targets before any measured run.
2. For each benchmark and target, run the official sample validation input first. Only targets that pass validation are eligible for performance runs.
3. Warmup policy: 2 untimed warmup executions at the performance input for `bosatsu_jvm` and `java`; 1 untimed warmup execution at the performance input for `bosatsu_c` and `c`.
4. Repeat policy: 5 measured runs per benchmark and target at the official large-N input. Record each run individually and derive summaries later; do not collapse the raw artifact to a single min or mean.
5. Ordering: run the suite in this fixed benchmark order: `n-body`, `spectral-norm`, `binary-trees`, `fannkuch-redux`, `mandelbrot`. Within each repetition, rotate target order so the same target is not always first after an idle period.
6. Output handling: capture stdout directly for the four text benchmarks. For `mandelbrot`, write stdout to a temporary file, record byte count and SHA-256, validate sample `N=200` against the checked-in PBM fixture, and delete the temporary file after each measured run.
7. Timing source: use one repo-controlled monotonic timer around subprocess execution. Do not make platform-specific `/usr/bin/time` output part of the contract.
8. Metadata capture: at minimum record `benchmark`, `target`, `input`, `repeat_index`, `elapsed_ns`, `exit_code`, `validation_passed`, `source_id`, `source_url`, `build_command`, `run_command`, `git_sha`, `bosatsu_version`, `java_version`, `gcc_version`, `os`, `cpu_model`, and `timestamp_utc`.
9. Result artifact shape: `docs/benchmarksgame/baseline-local.json` should contain a top-level `run_metadata` object plus a `results` array. `docs/benchmarksgame/baseline-local.csv` should flatten the measured rows with stable columns `benchmark,target,input,repeat_index,elapsed_ns,exit_code,validation_passed,source_id,git_sha,timestamp_utc`.

The suite spec should also preserve these caveats explicitly:
- benchmarksgame BenchExec numbers are not directly comparable to the local harness output because compiler, runtime, and machine setup differ.
- The pinned Java source pages are current benchmarksgame `graalvmaot` submissions, but the local `java` target in phase 1 is HotSpot JVM from the same vendored source, not `native-image`.
- Phase-1 results are informational only and should not gate CI or be framed as language-wide claims.

## Planned Downstream Touch Paths
The new suite spec should list the authoritative downstream paths exactly, using repo-relative paths:

```text
docs/design/166-benchmarksgame-suite.md

src/zafu_conf.json
src/Zafu/Benchmark/Game/Harness.bosatsu
src/Zafu/Benchmark/Game/HarnessTests.bosatsu
src/Zafu/Benchmark/Game/NBody.bosatsu
src/Zafu/Benchmark/Game/NBodyTests.bosatsu
src/Zafu/Benchmark/Game/SpectralNorm.bosatsu
src/Zafu/Benchmark/Game/SpectralNormTests.bosatsu
src/Zafu/Benchmark/Game/BinaryTrees.bosatsu
src/Zafu/Benchmark/Game/BinaryTreesTests.bosatsu
src/Zafu/Benchmark/Game/FannkuchRedux.bosatsu
src/Zafu/Benchmark/Game/FannkuchReduxTests.bosatsu
src/Zafu/Benchmark/Game/Mandelbrot.bosatsu
src/Zafu/Benchmark/Game/MandelbrotTests.bosatsu

fixtures/benchmarksgame/nbody/nbody-output.txt
fixtures/benchmarksgame/spectralnorm/spectralnorm-output.txt
fixtures/benchmarksgame/binarytrees/binarytrees-output.txt
fixtures/benchmarksgame/fannkuchredux/fannkuchredux-output.txt
fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm

vendor/benchmarksgame/manifest.json
vendor/benchmarksgame/java/nbody-graalvmaot-4/nbody.java
vendor/benchmarksgame/java/spectralnorm-graalvmaot-8/spectralnorm.java
vendor/benchmarksgame/java/binarytrees-graalvmaot-3/binarytrees.java
vendor/benchmarksgame/java/fannkuchredux-graalvmaot-2/fannkuchredux.java
vendor/benchmarksgame/java/mandelbrot-graalvmaot-8/mandelbrot.java
vendor/benchmarksgame/c/nbody-gcc-6/nbody.gcc-6.c
vendor/benchmarksgame/c/spectralnorm-gcc-8/spectralnorm.gcc-8.c
vendor/benchmarksgame/c/binarytrees-gcc-1/binarytrees.gcc-1.c
vendor/benchmarksgame/c/fannkuchredux-gcc-3/fannkuchredux.gcc-3.c
vendor/benchmarksgame/c/mandelbrot-gcc-8/mandelbrot.gcc-8.c

scripts/benchmarksgame_compare.sh
README.md
docs/benchmarksgame/baseline-local.json
docs/benchmarksgame/baseline-local.csv
```

## Implementation Plan
1. Author `docs/design/166-benchmarksgame-suite.md` by lifting the approved contract from `docs/design/168-write-the-benchmark-game-suite-spec-and-comparison-contract.md` into the final-file structure above.
2. Keep the benchmark matrix, deferred-benchmark rationale, path list, and comparison protocol materially identical to `#168`; only rewrite where needed to make the concrete doc self-contained and easier for downstream workers to consume.
3. Ensure the new file names every downstream touch path and every pinned external source page so later nodes can implement without rediscovering intent.
4. Keep any cross-linking minimal. If extra edits would expand the PR beyond the single concrete suite-spec artifact, skip them.
5. Verify the child issue remains doc-only before merge.

## Acceptance Criteria
1. `docs/design/166-benchmarksgame-suite.md` exists on the default branch and is self-contained enough for downstream workers to consume directly.
2. The doc names the exact five phase-1 benchmarks and explicitly excludes `k-nucleotide`, `reverse-complement`, `regex-redux`, `fasta`, and `pidigits` with the reviewed rationale.
3. Every included benchmark entry records the description URL, validation source, validation rule, performance input, CLI and output contract, and exact pinned Java and C reference pages.
4. The doc names the exact planned source, fixture, vendor, script, and results paths that later nodes will touch.
5. The doc defines the four local comparison targets, build and run command shapes, warmups, measured repeats, ordering, output handling, metadata fields, and result artifact formats.
6. The doc states that benchmarksgame leaderboard numbers are not directly comparable to local measurements and that local Java runs vendored `graalvmaot` sources on HotSpot rather than native-image.
7. The child issue lands only the concrete suite-spec doc artifact.

## Risks and Mitigations
1. Risk: the concrete doc drifts from the already reviewed `#168` contract. Mitigation: treat `#168` as the source text and copy the matrix, path, and protocol sections with only clarity edits.
2. Risk: later implementation nodes still reinterpret the spec. Mitigation: make `docs/design/166-benchmarksgame-suite.md` self-contained and include exact path names, inputs, and command shapes.
3. Risk: scope creeps from doc authoring into implementation or vendoring work. Mitigation: keep the PR doc-only and reject edits to `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or result artifacts.
4. Risk: benchmarksgame pages drift after the doc is authored. Mitigation: preserve the pinned URLs and source identifiers exactly so later vendoring work can freeze them locally.

## Rollout Notes
1. Merge this design doc first.
2. Land issue `#173` as a doc-only change that creates `docs/design/166-benchmarksgame-suite.md`.
3. Use that file as the sole suite contract for `bench_common_v2`, `numeric_kernels_v2`, `structural_kernels_v2`, `bitmap_output_v2`, `compare_harness_v2`, and `docs_baseline_v2`.
4. Vendor baselines and capture first baseline results only in later nodes after the Bosatsu implementations and shared harness support are in place.
