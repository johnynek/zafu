---
issue: 168
priority: 3
touch_paths:
  - docs/design/168-write-the-benchmark-game-suite-spec-and-comparison-contract.md
  - docs/design/166-benchmarksgame-suite.md
  - src/zafu_conf.json
  - src/Zafu/Benchmark/Game/Harness.bosatsu
  - src/Zafu/Benchmark/Game/HarnessTests.bosatsu
  - src/Zafu/Benchmark/Game/NBody.bosatsu
  - src/Zafu/Benchmark/Game/NBodyTests.bosatsu
  - src/Zafu/Benchmark/Game/SpectralNorm.bosatsu
  - src/Zafu/Benchmark/Game/SpectralNormTests.bosatsu
  - src/Zafu/Benchmark/Game/BinaryTrees.bosatsu
  - src/Zafu/Benchmark/Game/BinaryTreesTests.bosatsu
  - src/Zafu/Benchmark/Game/FannkuchRedux.bosatsu
  - src/Zafu/Benchmark/Game/FannkuchReduxTests.bosatsu
  - src/Zafu/Benchmark/Game/Mandelbrot.bosatsu
  - src/Zafu/Benchmark/Game/MandelbrotTests.bosatsu
  - fixtures/benchmarksgame/nbody/nbody-output.txt
  - fixtures/benchmarksgame/spectralnorm/spectralnorm-output.txt
  - fixtures/benchmarksgame/binarytrees/binarytrees-output.txt
  - fixtures/benchmarksgame/fannkuchredux/fannkuchredux-output.txt
  - fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm
  - vendor/benchmarksgame/manifest.json
  - vendor/benchmarksgame/java/nbody-graalvmaot-4/nbody.java
  - vendor/benchmarksgame/java/spectralnorm-graalvmaot-8/spectralnorm.java
  - vendor/benchmarksgame/java/binarytrees-graalvmaot-3/binarytrees.java
  - vendor/benchmarksgame/java/fannkuchredux-graalvmaot-2/fannkuchredux.java
  - vendor/benchmarksgame/java/mandelbrot-graalvmaot-8/mandelbrot.java
  - vendor/benchmarksgame/c/nbody-gcc-6/nbody.gcc-6.c
  - vendor/benchmarksgame/c/spectralnorm-gcc-8/spectralnorm.gcc-8.c
  - vendor/benchmarksgame/c/binarytrees-gcc-1/binarytrees.c
  - vendor/benchmarksgame/c/fannkuchredux-gcc-3/fannkuchredux.gcc-3.c
  - vendor/benchmarksgame/c/mandelbrot-gcc-8/mandelbrot.gcc-8.c
  - scripts/benchmarksgame_compare.sh
  - README.md
  - docs/benchmarksgame/baseline-local.json
  - docs/benchmarksgame/baseline-local.csv
depends_on: []
estimated_size: M
generated_at: 2026-04-01T00:29:48Z
---

# Design the Benchmarksgame Suite Spec and Comparison Contract

_Issue: #168 (https://github.com/johnynek/zafu/issues/168)_

## Summary

Define the phase-1 benchmark game suite, pin exact benchmarksgame validation and baseline sources, and specify the repo layout plus single-machine comparison contract that downstream implementation nodes will follow.

## Context
Issue #166 needs a durable suite specification before any benchmark implementation or comparison harness work lands. The spec must pin external benchmarksgame references, local repo conventions, and a single-machine measurement contract so later nodes do not rediscover benchmark pages or invent incompatible commands.

As of 2026-03-31, the benchmarksgame pages still publish the canonical descriptions and validation artifacts, but the visible Java source pages on the current performance tables are `graalvmaot` submissions. Phase 1 should therefore pin exact page URLs now and vendor the referenced source and validation artifacts into the repo so later work is insulated from site drift.

Downstream work already fans out into `bench_common`, `numeric_kernels`, `structural_kernels`, `bitmap_output`, `compare_harness`, and `docs_baseline`. This issue is the contract those nodes will follow.

## Goals
1. Pin the phase-1 benchmark set and the exact benchmarksgame pages that define each benchmark.
2. Record the official validation artifact, large-N performance input, and exact CLI/output contract for each chosen benchmark.
3. Pin one Java and one C baseline source page per benchmark using a reproducible selection rule.
4. Define the repo paths that later implementation nodes will own.
5. Define a local comparison protocol for Bosatsu JVM, Bosatsu C, Java, and C that is reproducible on one machine and honest about its limits.

## Non-goals
1. Implement any benchmark program, fixture, or comparison runner in this issue.
2. Match benchmarksgame's BenchExec environment or published leaderboard numbers.
3. Add multithreaded, OpenMP, APR-backed, or native-image-specific baselines in phase 1.
4. Expand phase 1 to the text-heavy or big-integer benchmarks that need extra support layers.

## Deliverable Contract
The current PR is the design artifact only.

The follow-on implementation for issue #168 should still be doc-only. It should add `docs/design/166-benchmarksgame-suite.md` and avoid `src/`, `vendor/`, `fixtures/`, `scripts/`, or `README.md` edits.

That suite-spec doc should contain these sections in order:
1. Phase-1 benchmark selection and out-of-scope rationale.
2. Benchmark contract matrix with URLs, validation sources, performance inputs, CLI contracts, and pinned Java/C baselines.
3. Repo layout and path conventions.
4. Single-machine comparison protocol.
5. Planned touch paths for downstream nodes.

## Phase-1 Suite
Selection rule for pinned baselines:
- C: prefer the fastest extant benchmarksgame C page that avoids the benchmarksgame `*` marker when a clean alternative exists, avoids OpenMP, pthreads, APR, or other non-default allocator/runtime dependencies, and still has a live program page.
- Java: prefer the fastest extant live Java source page without obvious parallel execution in the source page, then run that exact vendored `.java` source with `javac` and `java` locally. The source provenance remains the benchmarksgame `graalvmaot` page, but the local target is HotSpot JVM, not native-image.

| Benchmark | Why it is in phase 1 | Benchmarksgame description | Official validation source | Large-N performance input | Required CLI/output contract | Pinned Java reference | Pinned C reference |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n-body` | Small fixed model, pure floating-point kernel, simple text output, no external fixtures. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/nbody.html#nbody` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/nbody-output.txt` validated at `N=1000` with tolerance equivalent to `ndiff -abserr 1.0e-8`. | `50000000` | One required positional integer `N`. Stdout must be exactly two newline-terminated decimal lines: initial energy, then final energy, both formatted to 9 fractional digits. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-graalvmaot-4.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/nbody-gcc-6.html` |
| `spectral-norm` | Pure numeric kernel with a single scalar result and minimal I/O. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/spectralnorm.html#spectralnorm` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/spectralnorm-output.txt` validated at `N=100` with exact text compare. | `5500` | One required positional integer `N`. Stdout must be exactly one newline-terminated decimal line formatted to 9 fractional digits. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-graalvmaot-8.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/spectralnorm-gcc-8.html` |
| `binary-trees` | Allocation and recursion stress test with deterministic text output and no external input fixture. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/binarytrees.html#binarytrees` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/binarytrees-output.txt` validated at `N=10` with exact text compare. | `21` | One required positional integer `N`. Stdout must match the official line-oriented report exactly: stretch-tree line, per-depth aggregate lines, then long-lived-tree line. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-graalvmaot-3.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/binarytrees-gcc-1.html` |
| `fannkuch-redux` | Permutation and array-mutation kernel with deterministic small text output. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/fannkuchredux.html#fannkuchredux` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/fannkuchredux-output.txt` validated at `N=7` with exact text compare. | `12` | One required positional integer `N`. Stdout must be exactly two lines: checksum on line 1 and `Pfannkuchen(N) = maxflips` on line 2. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-graalvmaot-2.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/fannkuchredux-gcc-3.html` |
| `mandelbrot` | Exact-output byte benchmark that complements the numeric and structural kernels. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/description/mandelbrot.html#mandelbrot` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/download/mandelbrot-output.txt` validated at `N=200` with exact byte compare (`cmp`). | `16000` | One required positional integer `N`. Stdout must be binary PBM with header `P4\nN N\n` followed by correctly packed bitmap bytes. Exit non-zero on invalid args. | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-graalvmaot-8.html` | `https://benchmarksgame-team.pages.debian.net/benchmarksgame/program/mandelbrot-gcc-8.html` |

The chosen C pages are intentionally not always the fastest page on the benchmark list. The suite spec should prefer unstarred, single-process, dependency-light baselines over leaderboard-optimized entries so Bosatsu, Java, and C all run on a closer local contract.

## Deferred Benchmarks
| Benchmark | Why it is out of scope for phase 1 |
| --- | --- |
| `k-nucleotide` | It depends on large FASTA input generation or storage and turns the phase-1 effort into a hash-heavy text pipeline benchmark before the core numeric and structural kernels are landed. |
| `reverse-complement` | It is dominated by streaming byte I/O, buffer management, and exact line wrapping, which is a different support layer from the phase-1 kernel and harness work. |
| `regex-redux` | It would primarily measure regex engine or FFI/library behavior, and the current repo has no regex abstraction that makes this a clean Bosatsu comparison yet. |
| `fasta` | It is mostly RNG plus large text emission and is mainly a fixture producer for the deferred text benchmarks; `mandelbrot` already covers exact-output streaming in phase 1. |
| `pidigits` | It requires arbitrary-precision integer support that does not exist in the current repo or the planned shared benchmark harness. |

## Repo Layout Conventions
The suite-spec doc should reserve the following downstream touch paths and treat them as the authoritative phase-1 layout:

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
vendor/benchmarksgame/c/binarytrees-gcc-1/binarytrees.c
vendor/benchmarksgame/c/fannkuchredux-gcc-3/fannkuchredux.gcc-3.c
vendor/benchmarksgame/c/mandelbrot-gcc-8/mandelbrot.gcc-8.c

scripts/benchmarksgame_compare.sh
README.md
docs/benchmarksgame/baseline-local.json
docs/benchmarksgame/baseline-local.csv
```

Conventions the suite-spec doc should state explicitly:
- Each Bosatsu benchmark package lives in its own `src/Zafu/Benchmark/Game/*.bosatsu` file and exports a thin `main` with pure helpers kept testable alongside a paired `*Tests` file.
- `Harness.bosatsu` owns CLI normalization, stable result rows, validation helpers, and shared formatting so later benchmark nodes do not duplicate that logic.
- `fixtures/benchmarksgame/` stores the official small-input validation artifacts exactly as downloaded. `n-body` is the only tolerance-based validator; the other four benchmarks validate by exact text or byte compare.
- `vendor/benchmarksgame/manifest.json` records provenance for every vendored baseline: source page URL, date pinned, local source path, expected main class or binary name, thread model, local build flags, and required libraries.
- `docs/benchmarksgame/baseline-local.json` is the checked-in canonical baseline artifact. `docs/benchmarksgame/baseline-local.csv` is the flat companion export for quick comparisons.

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

The suite-spec doc should call out these caveats explicitly:
- benchmarksgame publishes BenchExec measurements taken under its own compiler, runtime, and machine setup; those published `secs` numbers are not directly comparable to the local harness output.
- the pinned Java source pages are current benchmarksgame `graalvmaot` submissions, but the local `java` target in phase 1 is HotSpot JVM from the same vendored source, not `native-image`.
- phase-1 results are informational only. They should not gate CI and should not be framed as language-wide claims.

## Implementation Plan
1. Author `docs/design/166-benchmarksgame-suite.md` using the exact benchmark matrix, deferred-benchmark rationale, repo layout, and comparison contract defined here.
2. Use that suite-spec doc to unblock `bench_common`, which should centralize CLI parsing, validation, and result formatting before any individual benchmark implementation lands.
3. Land `numeric_kernels`, `structural_kernels`, and `bitmap_output` against the pinned contract rather than rediscovering benchmarksgame details from scratch.
4. Land `compare_harness` only after the five Bosatsu programs and the vendored baseline manifest paths above are stable.
5. Land `docs_baseline` last, using the checked-in result artifact paths defined here.

## Acceptance Criteria
1. The design doc pins the five phase-1 benchmarks above and excludes `k-nucleotide`, `reverse-complement`, `regex-redux`, `fasta`, and `pidigits` with explicit rationale.
2. Every included benchmark entry records the description URL, official validation source, validation input, performance input, CLI/output contract, and exact pinned Java/C reference pages.
3. The doc names every planned repo path listed under `Repo Layout Conventions`.
4. The doc defines the four local comparison targets, warmups, measured repeats, ordering, metadata fields, and result artifact formats.
5. The doc states that benchmarksgame leaderboard numbers are not directly comparable to local measurements and that local Java is HotSpot from vendored `graalvmaot` sources.
6. The current PR remains design-only, and the follow-on implementation for issue #168 remains doc-only as well.

## Risks
1. Benchmarksgame pages can change or disappear after the doc is reviewed. Mitigation: later nodes must vendor the exact sources and validation artifacts named here and preserve them with a provenance manifest.
2. Local benchmark results will vary with CPU governor, thermal state, background load, and host operating system. Mitigation: use fixed warmups, five measured repeats, rotating order, and host metadata capture; do not use CI thresholds.
3. Baseline selection can be debated because faster benchmarksgame entries exist with OpenMP, APR, pthreads, or more aggressive implementation techniques. Mitigation: this contract intentionally prefers simpler, dependency-light local baselines and makes that choice explicit.
4. `n-body` is validated with a floating-point tolerance rather than exact bytes. Mitigation: the shared harness should implement a tolerance-aware validator that mirrors the official `ndiff -abserr 1.0e-8` rule.

## Rollout Notes
1. Merge this design doc first.
2. The immediate follow-on implementation should add `docs/design/166-benchmarksgame-suite.md` only.
3. After the suite spec merges, implement `bench_common` before any benchmark-specific node so the CLI and result contract stay centralized.
4. Land the five Bosatsu benchmark implementations before vendoring baselines and adding the comparison runner.
5. Capture the first checked-in baseline only after all five Bosatsu programs and all pinned Java/C baselines validate on the same machine.
6. Revisit threaded C, OpenMP, APR-backed allocators, or Java native-image only as a separate later phase.
