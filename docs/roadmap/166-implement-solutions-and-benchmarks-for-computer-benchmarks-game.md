# Roadmap #166

> Generated from roadmap graph JSON.
> Edit the `.graph.json` file, not this `.md` file.
> Regenerate with `python roadmap_json_to_md.py <path/to.graph.json> [--output <path/to.md>]`.

## Metadata

- Roadmap issue: `#166`
- Graph version: `2`
- Node count: `8`

## Dependency Overview

1. `suite_spec` (`reference_doc`): none
2. `suite_contract_doc` (`reference_doc`): `suite_spec` (`planned`)
3. `bench_common_v2` (`small_job`): `suite_contract_doc` (`planned`)
4. `bitmap_output_v2` (`small_job`): `bench_common_v2` (`implemented`), `suite_contract_doc` (`planned`)
5. `numeric_kernels_v2` (`small_job`): `bench_common_v2` (`implemented`), `suite_contract_doc` (`planned`)
6. `structural_kernels_v2` (`small_job`): `bench_common_v2` (`implemented`), `suite_contract_doc` (`planned`)
7. `compare_harness_v2` (`small_job`): `bench_common_v2` (`implemented`), `bitmap_output_v2` (`implemented`), `numeric_kernels_v2` (`implemented`), `structural_kernels_v2` (`implemented`), `suite_contract_doc` (`planned`)
8. `docs_baseline_v2` (`small_job`): `compare_harness_v2` (`implemented`), `suite_contract_doc` (`planned`)

## Nodes

### `suite_spec`

- Kind: `reference_doc`
- Title: Write the benchmark game suite spec and comparison contract
- Depends on: none

#### Body

Write the durable suite specification for issue #166 in `docs/design/166-benchmarksgame-suite.md`.

## Scope
- Choose the phase-1 benchmark set for zafu. The default target should be `n-body`, `spectral-norm`, `binary-trees`, `fannkuch-redux`, and `mandelbrot`, and the doc should explicitly record why `k-nucleotide`, `reverse-complement`, `regex-redux`, `fasta`, and `pidigits` are out of scope for this issue.
- For each chosen benchmark, record the benchmarksgame description URL, the official sample-output validation source, the large-N performance input, the expected CLI contract, and the exact Java and C reference programs we will compare against.
- Define repo conventions for phase-1 code layout under `src/Zafu/Benchmark/Game/`, fixture storage, vendored baseline source storage, and comparison result artifacts.
- Define the single-machine comparison protocol for Bosatsu JVM, Bosatsu C, Java, and C, including warmup policy, repeat policy, metadata capture, and explicit caveats about local runs versus benchmarksgame's BenchExec measurements.

## Acceptance Criteria
- The doc is self-contained enough that downstream workers do not need to rediscover benchmark pages or guess command lines.
- The doc names every planned source path or directory that later nodes will touch.
- The child issue lands only the reviewed doc artifact; no implementation work is mixed into this PR.

### `suite_contract_doc`

- Kind: `reference_doc`
- Title: Author the concrete benchmark game suite spec document
- Depends on: `suite_spec` (`planned`)

#### Body

Produce the concrete suite-spec artifact at `docs/design/166-benchmarksgame-suite.md` so downstream implementation nodes have the exact contract file they are supposed to consume.

## Direct Inputs
- `suite_spec` (`planned`): the merged design contract at `docs/design/168-write-the-benchmark-game-suite-spec-and-comparison-contract.md`.

## Scope
- Author `docs/design/166-benchmarksgame-suite.md` from the merged design contract without widening scope beyond the already reviewed benchmark matrix, deferred-benchmark rationale, pinned Java/C source pages, repo layout conventions, validation rules, and single-machine comparison protocol.
- Keep this issue doc-only: add the concrete suite-spec artifact and any minimal doc cross-links needed for clarity, but do not touch `src/`, `fixtures/`, `vendor/`, `scripts/`, `README.md`, or benchmark result artifacts.
- Make the new suite-spec doc self-contained so later workers can rely on that exact file path instead of reconstructing intent from the higher-level design artifact.

## Acceptance Criteria
- `docs/design/166-benchmarksgame-suite.md` exists on the default branch and contains the full phase-1 benchmark contract needed by downstream implementation nodes.
- The doc names the exact planned source, fixture, vendor, script, and results paths that later nodes will touch.
- The child issue lands only the concrete suite-spec doc artifact.

### `bench_common_v2`

- Kind: `small_job`
- Title: Add shared benchmark game harness utilities
- Depends on: `suite_contract_doc` (`planned`)

#### Body

Build the shared benchmark-game support layer that all benchmark implementations will use.

## Direct Inputs
- `suite_contract_doc` (`planned`): the merged suite spec doc at `docs/design/166-benchmarksgame-suite.md`.

## Scope
- Add shared Bosatsu support under `src/Zafu/Benchmark/Game/` for command-line argument normalization, structured benchmark results, CSV row rendering, and reusable validation or output helpers required by the suite spec.
- Keep algorithm kernels and I/O wrappers separate so later benchmark nodes can reach full test coverage with thin `main` values and heavily tested pure helpers.
- Add focused tests for every new helper, including CLI parsing, row formatting, fixture normalization, and error-reporting paths.
- Do not implement any specific benchmarksgame algorithm in this node.

## Acceptance Criteria
- Later benchmark nodes can depend on a shipped common layer instead of duplicating CLI or result-format logic.
- New common modules are fully exercised by repo tests and fit existing Bosatsu style.
- `scripts/test.sh` passes.

### `bitmap_output_v2`

- Kind: `small_job`
- Title: Implement the mandelbrot benchmark program
- Depends on: `bench_common_v2` (`implemented`), `suite_contract_doc` (`planned`)

#### Body

Implement `mandelbrot` with exact portable-bitmap output.

## Direct Inputs
- `suite_contract_doc` (`planned`): the merged suite spec doc at `docs/design/166-benchmarksgame-suite.md`.
- `bench_common_v2` (`implemented`): the shipped shared benchmark-game helpers from the common harness node.

## Scope
- Add a pure pixel and row-generation core plus a thin runnable `main` entrypoint under `src/Zafu/Benchmark/Game/`.
- Match the benchmarksgame rectangle, escape limit, CLI contract, and byte-for-byte PBM output format from the suite spec.
- Keep byte packing and header emission testable as pure functions; use checked-in fixtures for validation instead of ad hoc shell diff logic.
- Add sample-output tests covering header formatting, row packing, and the official validation case.

## Acceptance Criteria
- Output matches the official validation fixture for the chosen sample input.
- The executable runs on both Bosatsu JVM and C targets.
- Changed Bosatsu modules reach the repo's 100% coverage target and `scripts/test.sh` passes.

### `numeric_kernels_v2`

- Kind: `small_job`
- Title: Implement n-body and spectral-norm benchmark programs
- Depends on: `bench_common_v2` (`implemented`), `suite_contract_doc` (`planned`)

#### Body

Implement the numeric phase-1 benchmarks: `n-body` and `spectral-norm`.

## Direct Inputs
- `suite_contract_doc` (`planned`): the merged suite spec doc at `docs/design/166-benchmarksgame-suite.md`.
- `bench_common_v2` (`implemented`): the shipped shared benchmark-game helpers from the common harness node.

## Scope
- Add pure kernel modules plus thin runnable `main` entrypoints for `n-body` and `spectral-norm` under `src/Zafu/Benchmark/Game/`.
- Match the benchmarksgame algorithms, CLI shape, validation output, and large-N performance inputs recorded in the suite spec.
- Prefer pure helpers for state stepping, matrix-vector math, formatting, and output verification so behavior is testable without shelling out.
- Add exact sample-output tests for the official small-N validation cases, plus targeted tests for numerical invariants and formatting paths.

## Acceptance Criteria
- Both programs produce the expected benchmarksgame sample output.
- Both programs run through `./bosatsu eval --run` and `./bosatsu build` on the chosen entrypoints.
- Changed Bosatsu modules reach the repo's 100% coverage target and `scripts/test.sh` stays green.

### `structural_kernels_v2`

- Kind: `small_job`
- Title: Implement binary-trees and fannkuch-redux benchmark programs
- Depends on: `bench_common_v2` (`implemented`), `suite_contract_doc` (`planned`)

#### Body

Implement the allocation and permutation phase-1 benchmarks: `binary-trees` and `fannkuch-redux`.

## Direct Inputs
- `suite_contract_doc` (`planned`): the merged suite spec doc at `docs/design/166-benchmarksgame-suite.md`.
- `bench_common_v2` (`implemented`): the shipped shared benchmark-game helpers from the common harness node.

## Scope
- Add pure kernels plus thin runnable `main` entrypoints for `binary-trees` and `fannkuch-redux` under `src/Zafu/Benchmark/Game/`.
- Follow the suite spec and benchmarksgame constraints exactly, including checksum rules, permutation ordering, and binary-tree work requirements; do not introduce custom allocators or benchmark-specific shortcuts that the spec rejects.
- Keep tree building, tree checking, permutation generation, and output formatting testable as pure code.
- Add exact sample-output tests for the official small-N validation cases, plus focused tests for checksum, max-flip, and tree-check behavior.

## Acceptance Criteria
- Both programs produce the expected benchmarksgame sample output.
- Both programs run through `./bosatsu eval --run` and `./bosatsu build` on the chosen entrypoints.
- Changed Bosatsu modules reach the repo's 100% coverage target and `scripts/test.sh` stays green.

### `compare_harness_v2`

- Kind: `small_job`
- Title: Vendor Java and C baselines and add the comparison runner
- Depends on: `bench_common_v2` (`implemented`), `bitmap_output_v2` (`implemented`), `numeric_kernels_v2` (`implemented`), `structural_kernels_v2` (`implemented`), `suite_contract_doc` (`planned`)

#### Body

Vendor the comparison baselines and make local cross-language runs reproducible.

## Direct Inputs
- `suite_contract_doc` (`planned`): the merged suite spec doc at `docs/design/166-benchmarksgame-suite.md`.
- `bench_common_v2` (`implemented`): the shipped benchmark-game result schema and shared helpers.
- `numeric_kernels_v2` (`implemented`): the shipped Bosatsu `n-body` and `spectral-norm` programs.
- `structural_kernels_v2` (`implemented`): the shipped Bosatsu `binary-trees` and `fannkuch-redux` programs.
- `bitmap_output_v2` (`implemented`): the shipped Bosatsu `mandelbrot` program.

## Scope
- Vendor the exact Java and C reference sources named in the suite spec under a checked-in directory, together with a small provenance manifest that records source URLs, date or commit identifiers, required compiler flags, and benchmark arguments.
- Add the local comparison runner, keeping shell logic declarative and minimal. Put command-matrix expansion, result normalization, and output shaping in testable repo code or data so the orchestration is reviewable and not a bag of ad hoc shell conditionals.
- Support Bosatsu JVM, Bosatsu C, Java, and C for the phase-1 benchmark set on a single machine, emitting normalized CSV or JSON with benchmark name, target, input, elapsed time, exit status, and captured provenance.
- Add smoke validation for the manifest or normalization layer and document all required local toolchain prerequisites.

## Acceptance Criteria
- A single checked-in command can build and run all Bosatsu, Java, and C baselines for the chosen suite on one machine.
- Reference program provenance is explicit and reproducible.
- Result normalization is tested, and the repo test suite remains green.

### `docs_baseline_v2`

- Kind: `small_job`
- Title: Document the benchmark workflow and capture a first baseline
- Depends on: `compare_harness_v2` (`implemented`), `suite_contract_doc` (`planned`)

#### Body

Document the workflow and check in a first reproducible local baseline.

## Direct Inputs
- `suite_contract_doc` (`planned`): the merged suite spec doc at `docs/design/166-benchmarksgame-suite.md`.
- `compare_harness_v2` (`implemented`): the shipped comparison runner, vendored baselines, and normalized results format.

## Scope
- Update `README.md` with how to fetch prerequisites, build the Bosatsu benchmark-game programs, run the comparison harness, and interpret the emitted results without over-claiming benchmarksgame significance.
- Add a checked-in baseline artifact under `docs/benchmarksgame/` capturing one local run across Bosatsu JVM, Bosatsu C, Java, and C, including machine or toolchain metadata and the exact command used.
- Keep benchmark results informational only: do not add CI thresholds or fail builds on performance numbers.
- Validate the documented commands once before merging.

## Acceptance Criteria
- README plus the docs artifact are enough for another engineer to rerun the same comparison on a comparable machine.
- The baseline results include provenance, benchmark inputs, and per-target measurements for the whole phase-1 suite.
- `scripts/test.sh` stays green.
