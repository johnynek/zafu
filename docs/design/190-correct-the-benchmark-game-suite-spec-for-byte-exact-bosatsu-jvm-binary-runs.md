---
issue: 190
priority: 3
touch_paths:
  - docs/design/166-benchmarksgame-suite.md
depends_on: []
estimated_size: M
generated_at: 2026-04-03T00:34:26Z
---

# Design doc for #190: Correct the benchmark game suite spec for byte-exact Bosatsu JVM binary runs

_Issue: #190 (https://github.com/johnynek/zafu/issues/190)_

## Summary

Plan a doc-only correction to `docs/design/166-benchmarksgame-suite.md` that splits the Bosatsu JVM contract into a text-oriented path for the four line-output benchmarks and a byte-exact JVM path for `mandelbrot`, while preserving the rest of the approved suite specification.

## Context
Issue `#179` materialized `docs/design/166-benchmarksgame-suite.md` on `main` as the default-branch suite contract for roadmap `#166`. That contract currently gives a single `bosatsu_jvm` command template, `./bosatsu eval --main Zafu/Benchmark/Game/<Package>::main --run <N>`, for every phase-1 benchmark.

That single-template contract is no longer precise enough. The phase-1 suite mixes four line-oriented text benchmarks with one byte-exact bitmap benchmark, `mandelbrot`. Downstream workers now need one corrected default-branch document that tells them exactly which Bosatsu JVM path is valid for which output mode.

## Problem
- The current suite contract treats text-output and binary-output Bosatsu JVM runs as if they shared the same execution and stdout-capture behavior.
- Bosatsu CLI `eval --run` is a text-reporting path: it materializes `Main` stdout as text before writing it to the process stdout stream. That is acceptable for the four text benchmarks, but it is not a safe byte-exact contract for `mandelbrot`.
- The current contract is written through the repo wrapper `./bosatsu`, which follows `.bosatsu_platform`; that leaves the `bosatsu_jvm` target under-specified because the wrapper may resolve to a native CLI artifact instead of the Bosatsu jar.
- `compare_harness_v5` and the baseline-documentation node both depend on a corrected per-benchmark JVM command matrix. If `#190` leaves the distinction implicit, downstream workers will have to rediscover the contract from tool behavior instead of from the approved suite spec.

## Goals
1. Narrowly correct `docs/design/166-benchmarksgame-suite.md` so the Bosatsu JVM contract distinguishes text benchmarks from byte-exact binary benchmarks.
2. Make the `mandelbrot` Bosatsu JVM build and run path explicit enough that a downstream worker can implement it without guessing about stdout encoding or capture behavior.
3. Preserve the approved phase-1 benchmark list, benchmark matrix rows, repository layout conventions, warmup and repeat policy, metadata schema, and every non-Bosatsu-JVM target contract.
4. Keep issue `#190` doc-only.

## Non-Goals
1. Re-open benchmark selection, validation sources, performance inputs, or pinned Java and C baselines.
2. Implement the byte-exact Bosatsu JVM runner, modify the harness, or change any Bosatsu benchmark program in this issue.
3. Touch `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or baseline result artifacts.
4. Change the `bosatsu_c`, `java`, or `c` command contracts.

## Proposed Doc Architecture
The implementation should keep `docs/design/166-benchmarksgame-suite.md` structurally intact and make the correction in the smallest possible surface area.

The main change belongs in `## Single-Machine Comparison Protocol`, specifically the `Command contract by target` portion. Replace the single `bosatsu_jvm` bullet with an explicit two-path contract keyed by output mode:
- Text benchmarks: `n-body`, `spectral-norm`, `binary-trees`, and `fannkuch-redux` may continue to use the Bosatsu eval path, but the corrected doc should define it as an explicit JVM jar invocation rather than `./bosatsu`. The normative command template should resolve the Bosatsu version from `.bosatsu_version` and use `.bosatsuc/cli/<version>/bosatsu.jar`, for example `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --repo_root . --main Zafu/Benchmark/Game/<Package>::main --run <N>`.
- Binary benchmarks: `mandelbrot` must not inherit the text-oriented `eval --run` path as its byte-exact contract. The corrected doc should require a JVM byte runner built against the same Bosatsu jar and should show both the helper build step and the helper run step explicitly. The command template should use stable ephemeral output paths under `.bosatsu_bench/game/<slug>/jvm/` and should run the same Bosatsu `main` entrypoint with the same `<N>` argument, but with raw stdout redirected directly to a temporary file.

The doc should also add one explicit caveat that `mandelbrot` is the only phase-1 benchmark that uses the binary Bosatsu JVM path. The other four benchmarks remain on the text path unless a later suite revision explicitly changes that contract.

The corrected protocol should make one more distinction explicit: `./bosatsu --fetch` may remain the local setup step that downloads the CLI artifact, but `./bosatsu` itself should not remain the normative `bosatsu_jvm` benchmark command because it is platform-selected by `.bosatsu_platform`. The suite contract should describe the JVM artifact path directly.

## Output Handling Changes
The `Output handling` rule in `docs/design/166-benchmarksgame-suite.md` should be updated so the Bosatsu JVM binary path is unambiguous:
- Text benchmarks may continue to capture stdout as text from the JVM process.
- `mandelbrot` on `bosatsu_jvm` must capture raw process stdout to a temporary file, then record byte count and SHA-256, and validate the sample `N=200` output with exact byte comparison against the checked-in PBM fixture.
- The corrected doc should explicitly say that no line-ending normalization, terminal display, or text-oriented `eval --run` reporting path is part of the byte-exact Bosatsu JVM contract.

A minimal supporting note can appear either in the `mandelbrot` row or in the protocol caveats section so downstream workers do not miss that `mandelbrot` is a per-benchmark exception inside the `bosatsu_jvm` target.

## Implementation Plan
1. Edit only `docs/design/166-benchmarksgame-suite.md`, concentrating changes in `## Single-Machine Comparison Protocol` and adding only the smallest supporting clarification elsewhere that is needed to keep `mandelbrot`'s JVM caveat easy to find.
2. Replace the current one-line `bosatsu_jvm` command contract with a small per-benchmark or per-output-mode matrix that separates the four text benchmarks from the byte-exact `mandelbrot` path.
3. Change the Bosatsu JVM text path to an explicit jar-based command template rooted in `.bosatsu_version` and `.bosatsuc/cli/<version>/bosatsu.jar`, so the suite contract names an actual JVM invocation rather than a platform-dependent wrapper.
4. Add the binary-path contract for `mandelbrot`, including the exact expectations that the corrected doc must spell out: helper build step, helper run step, raw stdout redirection target, and exact-byte validation workflow.
5. Preserve every other reviewed part of the suite contract verbatim unless a wording tweak is required to keep the Bosatsu JVM split readable.
6. Perform a final diff review focused on contract preservation: benchmark membership, URLs, validation rules, repository layout, warmup count, repeat count, metadata fields, and all non-Bosatsu-JVM command shapes must remain materially unchanged.

## Acceptance Criteria
1. `docs/design/166-benchmarksgame-suite.md` states that `bosatsu_jvm` is not a single command template for all benchmarks and clearly distinguishes the text path from the byte-exact binary path.
2. The corrected doc makes clear whether `n-body`, `spectral-norm`, `binary-trees`, and `fannkuch-redux` retain the Bosatsu eval path, and if they do, it defines that path as an explicit JVM jar invocation rather than `./bosatsu`.
3. The corrected doc gives downstream workers enough information to determine the exact Bosatsu JVM build and run contract for `mandelbrot`, including stdout capture expectations, without guessing around text encoding behavior.
4. The Bosatsu C, Java, and C contracts remain unchanged, and the approved phase-1 benchmark list, repository layout conventions, validation rules, warmup and repeat policy, and result artifact schema are materially preserved.
5. The implementation stays doc-only and changes no source, fixture, vendor, script, README, or benchmark-result files.

## Risks
1. The corrected doc could still be ambiguous if it says `mandelbrot` needs a special path but does not show a concrete command template. Mitigation: require the doc edit to record explicit build and run command shapes, not just prose.
2. The doc could accidentally keep `./bosatsu` as the Bosatsu JVM command, which would continue to blur the platform distinction. Mitigation: explicitly pin the JVM artifact path through `.bosatsu_version` and `.bosatsuc/cli/<version>/bosatsu.jar`.
3. The correction could overreach and churn unrelated parts of the suite contract. Mitigation: constrain edits to the Bosatsu JVM command matrix, the related output-handling language, and the smallest possible supporting note.
4. The helper details for the byte runner could drift from downstream implementation if the contract reaches into internal implementation choices. Mitigation: pin the observable command contract, output path convention, and capture semantics, but avoid unnecessary detail about the helper's internal source layout.

## Rollout Notes
1. Merge `#190` before `compare_harness_v5` and the baseline-documentation node so those workers consume the corrected Bosatsu JVM contract from `main` instead of inventing their own exceptions.
2. After merge, downstream comparison work should treat `bosatsu_jvm` as a small command matrix keyed by benchmark output mode, not as one universal command template.
3. If Bosatsu later gains a first-class binary-safe JVM eval path, that can be adopted in a later suite-spec revision; issue `#190` should not wait on a Bosatsu tool change before documenting the corrected contract.
