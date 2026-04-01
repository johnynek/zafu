---
issue: 179
priority: 3
touch_paths:
  - docs/design/166-benchmarksgame-suite.md
depends_on: []
estimated_size: M
generated_at: 2026-04-01T23:20:50Z
---

# Design doc for #179: Materialize the concrete benchmark game suite spec artifact on main

_Issue: #179 (https://github.com/johnynek/zafu/issues/179)_

## Summary

Plan the doc-only addition of `docs/design/166-benchmarksgame-suite.md` on `main` by transcribing the merged `#176` reference doc into the default-branch suite contract that downstream benchmark nodes will consume.

## Context
Issue `#179` is the final reference-doc step for roadmap `#166`. Its job is to place the concrete suite-spec artifact at `docs/design/166-benchmarksgame-suite.md` on `main`, using `docs/design/176-create-the-missing-concrete-benchmark-game-suite-spec-artifact.md` as the sole direct source of truth. Downstream benchmark nodes need one stable default-branch contract file instead of a corrective planning doc, so this issue stays doc-only and artifact-focused.

## Goals
1. Add `docs/design/166-benchmarksgame-suite.md` as the authoritative phase-1 benchmark-suite contract on `main`.
2. Preserve the exact phase-1 benchmark list, deferred-benchmark rationale, pinned benchmarksgame URLs, validation rules, repository layout conventions, and single-machine comparison protocol reviewed in `#176`.
3. Make the new file self-contained so later workers can implement against `docs/design/166-benchmarksgame-suite.md` alone.
4. Keep the PR limited to the missing concrete artifact, with only minimal doc cross-links if they are strictly necessary for clarity.

## Non-Goals
1. Re-open benchmark selection, baseline selection rules, or performance methodology.
2. Modify `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or baseline result artifacts as part of issue `#179`.
3. Vendor external sources or fixtures, implement benchmark programs, or capture measurements.
4. Introduce any new benchmarksgame references, filenames, or layout conventions beyond what `#176` already approved.

## Artifact Architecture
The implementation should add a single operational contract file at `docs/design/166-benchmarksgame-suite.md`. It should read like a final consumer-facing spec, not like a planning note, and it should preserve this section order:
1. `## Phase-1 Benchmark Set`
2. `## Deferred Benchmarks`
3. `## Benchmark Contract Matrix`
4. `## Repository Layout Conventions`
5. `## Single-Machine Comparison Protocol`
6. `## Planned Downstream Touch Paths`

The phase-1 benchmark set must remain exactly `n-body`, `spectral-norm`, `binary-trees`, `fannkuch-redux`, and `mandelbrot`. The deferred set must remain exactly `k-nucleotide`, `reverse-complement`, `regex-redux`, `fasta`, and `pidigits`, with the same rationale already reviewed in `#176`.

The benchmark contract matrix must preserve the exact columns from `#176`: `Benchmark`, `Why it is in phase 1`, `Benchmarksgame description`, `Official validation source`, `Large-N performance input`, `Required CLI/output contract`, `Pinned Java reference`, and `Pinned C reference`. Each benchmark row should carry forward the reviewed URLs, validation behavior, performance input, CLI or output contract, and pinned Java and C reference pages without reinterpretation.

The repository layout section must list this exact downstream path set. These names are part of the contract surface and should not be normalized, renamed, or simplified in issue `#179`:
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

The corrected filenames matter. `fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm` keeps the `n200` suffix because the validation rule is tied to that exact sample input. The vendored C filenames retain the source identifier in the basename so the local filename, pinned benchmarksgame page, and `vendor/benchmarksgame/manifest.json` provenance entry stay unambiguous. The Java entries intentionally keep the simpler `.java` basenames because their source identity is already carried by the containing directory and the manifest metadata.

The comparison protocol section must preserve the four local targets `bosatsu_jvm`, `bosatsu_c`, `java`, and `c`; the reviewed build and run command shapes; validation-before-measurement; warmups; five measured repeats; the fixed benchmark order `n-body`, `spectral-norm`, `binary-trees`, `fannkuch-redux`, `mandelbrot`; rotated target order; `mandelbrot` file-handling rules; required metadata capture; and the JSON plus CSV result artifact shapes. It must also keep the caveats that benchmarksgame leaderboard timings are not directly comparable to local results, the pinned Java sources are benchmarksgame `graalvmaot` submissions run locally on HotSpot, and phase-1 results are informational only.

If older planning materials disagree on wording or filenames, prefer `docs/design/176-create-the-missing-concrete-benchmark-game-suite-spec-artifact.md` for the concrete artifact produced by issue `#179`.

## Implementation Plan
1. Read `docs/design/176-create-the-missing-concrete-benchmark-game-suite-spec-artifact.md` as the only direct input and use it as source text rather than re-deriving the contract.
2. Author `docs/design/166-benchmarksgame-suite.md` by transcribing the reviewed benchmark matrix, deferred-benchmark rationale, layout conventions, comparison protocol, and downstream path list into the final artifact path.
3. Rewrite only enough to make the new file self-contained and readable as a concrete contract on `main`; do not change semantics, filenames, benchmark membership, URLs, validation rules, or command shapes.
4. Perform an explicit review pass for the corrected path spellings and validation details, especially `binarytrees.gcc-1.c`, `mandelbrot-output-n200.pbm`, the `n-body` tolerance rule, and the fixed target and benchmark ordering.
5. Keep the PR doc-only. Skip any extra edits unless a minimal doc cross-link is required for clarity.

## Acceptance Criteria
1. `docs/design/166-benchmarksgame-suite.md` exists on the default branch after merge and is the only required implementation artifact for issue `#179`.
2. The document is self-contained and materially aligned with `docs/design/176-create-the-missing-concrete-benchmark-game-suite-spec-artifact.md`.
3. The doc preserves the exact phase-1 benchmark list and exact deferred benchmark list from `#176`.
4. Each benchmark entry preserves the exact description URL, validation source and rule, performance input, CLI or output contract, and pinned Java and C reference pages reviewed in `#176`.
5. The doc names the exact planned source, fixture, vendor, script, README, and result-artifact paths that downstream nodes will consume.
6. The doc preserves the reviewed local comparison protocol, including targets, command shapes, validation-before-measurement, warmups, repeat count, ordering, output handling, metadata fields, and result-artifact schema.
7. No code, fixture, vendor, script, README, or benchmark-result files are changed as part of issue `#179`.

## Risks
1. Contract drift could reintroduce filename or rule mismatches if the final artifact is re-summarized instead of transcribed from `#176`. Mitigation: treat `#176` as the canonical source text and verify the new file against it section by section.
2. Path drift would break downstream consumers because later nodes depend on exact repo-relative names. Mitigation: preserve the exact path set above and call out corrected filenames explicitly during review.
3. Scope creep could turn a doc-materialization issue into implementation or vendoring work. Mitigation: keep the PR limited to `docs/design/166-benchmarksgame-suite.md` unless a minimal cross-link is strictly required.
4. External benchmarksgame pages can change after the artifact lands. Mitigation: keep every pinned URL and source identifier explicit in the concrete contract so later vendoring work can snapshot them locally.

## Rollout Notes
1. Merge issue `#179` before any downstream benchmark or harness node that expects `docs/design/166-benchmarksgame-suite.md` to exist on `main`.
2. After merge, treat `docs/design/166-benchmarksgame-suite.md` as the sole default-branch suite contract for shared harness work, the five benchmark implementations, vendored baseline capture, comparison-harness work, and baseline documentation.
3. Defer all executable changes, fixture downloads, source vendoring, and baseline artifacts to the already planned downstream nodes after the concrete suite-spec file is present on `main`.
