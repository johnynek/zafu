---
issue: 196
priority: 3
touch_paths:
  - docs/design/166-benchmarksgame-suite.md
depends_on: []
estimated_size: M
generated_at: 2026-04-04T03:39:47Z
---

# Design doc for #196: Correct the suite spec to use explicit Bosatsu JVM commands that match the shipped benchmark entrypoints

_Issue: #196 (https://github.com/johnynek/zafu/issues/196)_

## Summary

Plan a doc-only correction to `docs/design/166-benchmarksgame-suite.md` so the `bosatsu_jvm` contract uses explicit `java -jar` commands rooted in `.bosatsu_version`, enumerates the shipped `Zafu/Benchmark/Game/*::main` entrypoints, and documents byte-exact `mandelbrot` capture on the same eval-driven JVM path.

## Context
Issue `#196` is the next doc-only correction for roadmap `#166`. The current default-branch suite contract at `docs/design/166-benchmarksgame-suite.md` still documents `bosatsu_jvm` as `./bosatsu eval --main Zafu/Benchmark/Game/<Package>::main --run <N>`. That wording is no longer precise enough for downstream workers.

The direct inputs for this issue show why. `suite_contract_artifact_v3` materialized the suite spec on `main`, but it preserved the wrapper-based JVM command. `bitmap_output_v4` then shipped the `mandelbrot` benchmark with a JVM run path that still uses `eval --run`, while proving byte-exact PBM output by redirecting stdout to a temporary file instead of inventing a separate helper build or alternate entrypoint.

The suite contract now needs one narrow correction so the default-branch artifact names true JVM commands and matches the benchmark programs that actually ship in the repo.

## Problem
- The current `bosatsu_jvm` contract is under-specified because `./bosatsu` is a platform-selecting wrapper controlled by `.bosatsu_platform`, not a JVM-specific benchmark command.
- The current doc leaves downstream workers to infer whether `mandelbrot` should stay on the same `eval --run` entrypoint as the text benchmarks or use a separate JVM helper flow.
- A generic `<Package>` placeholder is weaker than the issue now requires because downstream workers should be able to lift the exact shipped JVM entrypoints from the artifact alone.
- If the suite spec stays ambiguous, later comparison-harness and baseline-documentation work can drift away from the current shipped benchmark behavior.

## Goals
1. Correct `docs/design/166-benchmarksgame-suite.md` so `bosatsu_jvm` is documented as an explicit jar-based JVM invocation rooted in `.bosatsu_version` and `.bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar`.
2. Enumerate the exact JVM `eval --run` commands for the four text benchmarks using the shipped `Zafu/Benchmark/Game/*::main` entrypoints.
3. Document `mandelbrot` as using the same explicit JVM `eval --run` entrypoint, with raw stdout redirected to a temporary PBM file for validation and metadata capture.
4. Preserve the approved phase-1 benchmark list, pinned Java and C sources, repository layout conventions, validation rules, warmup and repeat policy, metadata schema, and every non-Bosatsu-JVM target contract.
5. Keep issue `#196` doc-only.

## Non-Goals
1. Change any Bosatsu benchmark program, harness implementation, fixture, vendored baseline, or script in this issue.
2. Introduce a separate JVM helper build or alternate `mandelbrot` runtime contract.
3. Change the `bosatsu_c`, `java`, or `c` command contracts.
4. Re-open phase-1 benchmark membership, pinned benchmarksgame URLs, or measurement policy.

## Proposed Doc Changes
Keep `docs/design/166-benchmarksgame-suite.md` structurally intact and limit edits to the smallest contract surface that currently misstates JVM behavior.

In `## Single-Machine Comparison Protocol`, replace the single wrapper-based `bosatsu_jvm` bullet with an explicit JVM subsection that does two things:
1. Defines the JVM CLI location through the checked-in version file, for example `BOSATSU_VERSION="$(tr -d '[:space:]' < .bosatsu_version)"` and `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar"`.
2. Lists the exact per-benchmark JVM run commands rather than a `<Package>` placeholder:
   - `n-body`: `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/NBody::main --run <N>`
   - `spectral-norm`: `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/SpectralNorm::main --run <N>`
   - `binary-trees`: `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/BinaryTrees::main --run <N>`
   - `fannkuch-redux`: `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/FannkuchRedux::main --run <N>`
   - `mandelbrot`: `java -jar ".bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar" eval --main Zafu/Benchmark/Game/Mandelbrot::main --run <N> > <temporary-pbm-path>`

The corrected text should be explicit that `./bosatsu --fetch` may remain a repo-local setup step to populate `.bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar`, but `./bosatsu` is not the normative `bosatsu_jvm` benchmark command because it is selected by `.bosatsu_platform`.

The `mandelbrot` change should stay focused on the external contract. The doc should not describe internal implementation details for how the program preserves raw bytes under `eval`; it should only pin the observable entrypoint and capture semantics that downstream workers must honor.

## Output Handling Changes
Update the `Output handling` rule so the Bosatsu JVM contract is aligned with the shipped `bitmap_output_v4` behavior:
- The four text benchmarks continue to capture stdout directly from the explicit JVM `eval --run` command as text.
- `mandelbrot` also uses the explicit JVM `eval --run` command, but its stdout must be redirected to a harness-owned temporary `.pbm` file before validation or measurement metadata is computed.
- The temporary PBM file is the source of truth for the `mandelbrot` `bosatsu_jvm` row: record byte count and SHA-256 from that file, validate sample `N=200` by exact byte compare against `fixtures/benchmarksgame/mandelbrot/mandelbrot-output-n200.pbm`, and perform no newline conversion, text decoding, or other normalization.
- The doc should make clear that `mandelbrot` does not use a separate helper build, alternate JVM executable, or non-`eval` Bosatsu entrypoint.

## Implementation Plan
1. Edit only `docs/design/166-benchmarksgame-suite.md`, keeping the existing section order and changing only the `bosatsu_jvm` command description plus the related `mandelbrot` output-handling language.
2. Replace the current wrapper-based `bosatsu_jvm` template with explicit jar-based commands rooted in `.bosatsu_version` and `.bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar`.
3. Expand the JVM contract from a generic `<Package>` template to exact per-benchmark commands so the artifact alone names the shipped `Main` entrypoints.
4. Preserve `mandelbrot` on the same `eval --run` JVM path as the other benchmarks, but spell out the required temporary-file capture contract and byte-exact validation workflow.
5. Review the final doc for strict non-regression: phase-1 benchmark membership, benchmark matrix rows, validation sources, performance inputs, layout conventions, warmup and repeat policy, metadata fields, and all non-Bosatsu-JVM targets must remain materially unchanged.
6. Keep the PR doc-only. Do not modify `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or result artifacts.

## Acceptance Criteria
1. `docs/design/166-benchmarksgame-suite.md` names a true JVM `bosatsu_jvm` command rooted in `.bosatsu_version` and `.bosatsuc/cli/${BOSATSU_VERSION}/bosatsu.jar` instead of the platform-selected `./bosatsu` wrapper.
2. The corrected doc enumerates the exact JVM `eval --run` entrypoints for `n-body`, `spectral-norm`, `binary-trees`, and `fannkuch-redux`.
3. The corrected doc states that `mandelbrot` uses the same explicit JVM `eval --run` entrypoint and specifies the byte-exact temporary-file capture contract, including byte-count and SHA-256 recording and the absence of text normalization.
4. The corrected doc remains consistent with the shipped `bitmap_output_v4` behavior and does not invent a separate helper build or run contract for `mandelbrot`.
5. The phase-1 benchmark list, pinned Java and C sources, repository layout conventions, validation rules, warmup and repeat policy, metadata schema, and every non-Bosatsu-JVM target contract are materially preserved.
6. The implementation stays doc-only.

## Risks
1. The doc could still drift from the shipped benchmark entrypoints if it keeps a generic placeholder or adds JVM flags that the shipped commands do not use. Mitigation: enumerate the exact `Zafu/Benchmark/Game/*::main` commands and mirror the shipped `eval --run` shape.
2. `mandelbrot` could become ambiguous again if the doc describes byte-exact capture only as prose and not as part of the run contract. Mitigation: make the temporary-file redirection and post-run byte accounting explicit in the `bosatsu_jvm` protocol.
3. The correction could overreach into internal runtime details, such as how `mandelbrot` preserves binary stdout under `eval`. Mitigation: document only the external command and observable output semantics, not the internal implementation mechanism.
4. Downstream workers could treat `./bosatsu` as the benchmark command out of habit. Mitigation: leave `./bosatsu --fetch` as an optional setup note if needed, but clearly state that the normative JVM benchmark command is the explicit jar invocation.

## Rollout Notes
1. Merge `#196` before downstream comparison-harness or baseline-documentation work that consumes the suite contract from `main`.
2. After merge, downstream workers should treat the explicit jar-based `eval --run` commands as the only approved `bosatsu_jvm` benchmark entrypoints for phase 1.
3. `mandelbrot` should continue to be measured through the same JVM entrypoint as the text benchmarks, with the only special handling being byte-exact stdout capture to a temporary PBM file.
