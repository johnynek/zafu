---
issue: 176
priority: 3
touch_paths:
  - docs/design/166-benchmarksgame-suite.md
depends_on: []
estimated_size: M
generated_at: 2026-04-01T19:17:40Z
---

# Design doc for #176: Create the missing concrete benchmark game suite spec artifact

_Issue: #176 (https://github.com/johnynek/zafu/issues/176)_

## Summary

Plan the doc-only addition of `docs/design/166-benchmarksgame-suite.md` by transcribing the merged #173 reference doc into the self-contained phase-1 benchmark suite contract that downstream nodes will consume from `main`.

## Context
Issue #176 is the corrective follow-on for roadmap #166 that materializes the promised suite-spec artifact at `docs/design/166-benchmarksgame-suite.md`. The merged direct input for this issue is `docs/design/173-author-the-concrete-benchmark-game-suite-spec-document.md`, which already captured the reviewed phase-1 benchmark matrix, deferred benchmark rationale, pinned benchmarksgame pages, repository layout conventions, validation rules, and single-machine comparison protocol.

Downstream benchmark nodes need one stable contract file on `main` instead of reconstructing intent from earlier design docs. This issue is therefore doc-only and narrowly corrective: create the missing concrete artifact, keep it self-contained, and avoid widening scope beyond the content already approved in `#173`.

## Goals
1. Create `docs/design/166-benchmarksgame-suite.md` as the authoritative phase-1 benchmark suite contract on `main`.
2. Preserve the reviewed five-benchmark selection, deferred benchmark rationale, pinned URLs, validation rules, layout conventions, and comparison protocol from the merged `#173` reference doc.
3. Make the new file self-contained enough that later nodes can implement against that path alone.
4. Keep the change limited to the missing suite-spec artifact unless a minimal doc cross-link is strictly necessary.

## Non-Goals
1. Re-open the phase-1 benchmark list, baseline selection rule, or measurement methodology.
2. Add or modify `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or benchmark result artifacts as part of issue #176.
3. Vendor sources or fixtures, implement Bosatsu benchmark packages, or capture baseline measurements.
4. Introduce new benchmarksgame references or downstream requirements beyond the merged `#173` contract.

## Artifact Architecture
The implementation should add a single concrete file, `docs/design/166-benchmarksgame-suite.md`, written as an operational contract rather than a planning note. The document should keep the section order already reviewed in `#173`:
1. `## Phase-1 Benchmark Set`
2. `## Deferred Benchmarks`
3. `## Benchmark Contract Matrix`
4. `## Repository Layout Conventions`
5. `## Single-Machine Comparison Protocol`
6. `## Planned Downstream Touch Paths`

The phase-1 benchmark set should remain exactly `n-body`, `spectral-norm`, `binary-trees`, `fannkuch-redux`, and `mandelbrot`. The deferred set should remain exactly `k-nucleotide`, `reverse-complement`, `regex-redux`, `fasta`, and `pidigits`, with the same rationale already reviewed in the dependency doc.

The benchmark matrix must preserve the exact columns from `#173`: `Benchmark`, `Why it is in phase 1`, `Benchmarksgame description`, `Official validation source`, `Large-N performance input`, `Required CLI/output contract`, `Pinned Java reference`, and `Pinned C reference`. Each row should carry forward the reviewed URLs, validation behavior, performance input, and CLI/output contract without reinterpretation.

The repository layout section must name the exact downstream paths reserved by the contract. The concrete artifact should list this path set exactly:
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

These names are intentional parts of the pinned contract, not cleanup targets for issue `#176`. The `mandelbrot` fixture keeps the `n200` suffix because the checked-in PBM sample is tied to the exact validation input used by the byte-compare rule, while the text fixtures reuse the benchmark-specific output names already reviewed in `#173`.

The vendored C filenames also retain the source identifier in the basename so the local file name, pinned benchmarksgame page, and `vendor/benchmarksgame/manifest.json` provenance entry stay unambiguous. The Java entries keep the simpler `.java` basenames because their source identity is already carried by the containing directory plus the manifest metadata.

The comparison protocol section should preserve the four local targets `bosatsu_jvm`, `bosatsu_c`, `java`, and `c`; their reviewed build and run command shapes; validation-before-measurement; warmups; five measured repeats; fixed benchmark ordering with rotated target order; `mandelbrot` file-handling rules; required metadata capture; and the JSON plus CSV result artifact format. It should also retain the reviewed caveats that benchmarksgame leaderboard timings are not directly comparable to local results, that the pinned Java sources are benchmarksgame `graalvmaot` submissions run locally on HotSpot, and that phase-1 results are informational rather than CI gates.

The direct source of truth for this issue is `docs/design/173-author-the-concrete-benchmark-game-suite-spec-document.md`. If earlier planning artifacts use slightly different wording or filename spellings, prefer the merged `#173` reference doc for the concrete file created by issue #176.

## Implementation Plan
1. Read `docs/design/173-author-the-concrete-benchmark-game-suite-spec-document.md` as the authoritative input.
2. Author `docs/design/166-benchmarksgame-suite.md` by transcribing the reviewed benchmark matrix, deferred benchmark rationale, layout conventions, comparison protocol, and downstream path list into the final artifact path.
3. Rewrite only enough to make the new file read as a self-contained contract that downstream workers can implement against directly.
4. Keep the change set doc-only and limited to the concrete suite-spec artifact unless a minimal cross-link is required for clarity.
5. Verify that the final file preserves the exact benchmark names, path names, source URLs, validation rules, and local comparison contract from the merged reference doc.

## Acceptance Criteria
1. `docs/design/166-benchmarksgame-suite.md` exists on `main` and is the only required implementation artifact for issue #176.
2. The document is self-contained and materially aligned with `docs/design/173-author-the-concrete-benchmark-game-suite-spec-document.md`.
3. The document preserves the exact phase-1 benchmark list, the exact deferred benchmark list, and the reviewed rationale for both.
4. Each included benchmark records the exact description URL, validation source and rule, large-N performance input, CLI/output contract, and pinned Java and C reference pages from the merged reference doc.
5. The document names the exact planned source, fixture, vendor, script, README, and result artifact paths that downstream nodes are expected to touch.
6. The document preserves the reviewed local comparison protocol, including target command shapes, validation-before-measurement, warmups, repeat count, ordering, output handling, metadata fields, and result artifact schema.
7. No code, fixture, vendor, script, README, or benchmark-result files are changed as part of issue #176.

## Risks
1. Contract drift could change benchmark membership, URLs, validation rules, or filename spellings if the concrete file is re-summarized instead of transcribed. Mitigation: treat the merged `#173` reference doc as source text and copy the reviewed contract forward verbatim where practical.
2. Path ambiguity would create conflicting downstream contracts because later nodes depend on exact filenames. Mitigation: preserve the exact path set listed above and avoid re-deriving filenames from older planning materials.
3. Scope creep could turn a missing-artifact issue into implementation or vendoring work. Mitigation: keep the PR doc-only and reject edits outside `docs/design/166-benchmarksgame-suite.md` unless an extra doc cross-link is strictly necessary.
4. External benchmarksgame pages may drift after the artifact lands. Mitigation: keep all pinned source and validation URLs explicit in the concrete contract so later vendoring work can snapshot them locally.

## Rollout Notes
1. Merge issue #176 before any downstream benchmark implementation or comparison-harness node that expects `docs/design/166-benchmarksgame-suite.md` to exist on `main`.
2. After merge, treat `docs/design/166-benchmarksgame-suite.md` as the sole default-branch suite contract for `bench_common`, the five benchmark implementations, vendored baseline capture, comparison harness work, and baseline documentation.
3. Defer all executable changes, fixture downloads, source vendoring, and baseline result artifacts to the already planned downstream nodes once the concrete suite-spec file is in place.
