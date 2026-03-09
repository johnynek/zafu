---
issue: 75
priority: 2
touch_paths:
  - docs/design/75-benchmarking-vector.md
  - src/zafu_conf.json
  - src/Zafu/Benchmark/Vector.bosatsu
  - scripts/benchmark_vector.sh
  - README.md
depends_on: []
estimated_size: M
generated_at: 2026-03-09T18:34:17Z
---

# Design: Benchmarking Vector

_Issue: #75 (https://github.com/johnynek/zafu/issues/75)_

## Summary

Add a runnable benchmark main package for `Zafu/Collection/Vector` that exercises common vector patterns on sizes `1000`, `10000`, and `100000`, and prints per-case throughput (`ops/us`) plus raw timing data. This revision also updates the plan to require `core_alpha` `4.3.0` so the benchmark can use `Bosatsu/Prog.observe` as an explicit optimizer barrier.

## Status

Proposed

## Context

1. Issue #75 asks for a benchmark that can run as a main program and report throughput.
2. Review feedback requested merging `main`, updating `core_alpha` to `4.3.0`, and revising the design to use the new `Bosatsu/Prog.observe` API.
3. Existing benchmark design relied on checksum-only observation to prevent pure results from being optimized away.
4. `observe` is a stronger and more explicit mechanism to ensure measured values are retained by Bosatsu and C-level optimization.

## Goals

1. Add a single executable benchmark package focused on vector performance.
2. Benchmark these operations: vector build, random read, fold, append, and concat.
3. Run each operation for sizes `1000`, `10000`, and `100000`.
4. Print machine-readable benchmark rows including elapsed time and `ops/us`.
5. Upgrade `core_alpha` to `4.3.0` and use `Bosatsu/Prog.observe` in the benchmark harness.
6. Keep the change additive and non-breaking for library consumers.

## Non-goals

1. CI performance gating or benchmark thresholds in this issue.
2. Exhaustive benchmarking of every vector API.
3. Cross-language or cross-library comparisons in this initial version.
4. Statistical benchmarking rigor comparable to dedicated harnesses.

## Dependency Update

1. Update `src/zafu_conf.json` `private_deps.core_alpha.version` from `4.2.2` to `4.3.0`.
2. Update `private_deps.core_alpha.uris` to `https://github.com/johnynek/bosatsu/releases/download/v0.0.48/core_alpha-v4.3.0.bosatsu_lib`.
3. Update the corresponding `private_deps.core_alpha.hashes` entry to match that artifact.
4. Run `./bosatsu lib fetch` after the config change.

## Benchmark Scope

Operations to include for each size:

1. `build_from_list`: `from_List_Vector` from a prepared `List[Int]` of length `n`.
2. `random_read`: repeated `index_Vector` or `get_or_Vector` over deterministic pseudo-random indices.
3. `foldl_sum`: `foldl_Vector(vec, 0, add)` on a prepared vector.
4. `append_one`: `append_Vector(vec, value)` on a prepared vector.
5. `concat_pair`: `concat_Vector(left, right)` where `left` and `right` are each size `n / 2`.

Sizes:

1. `1000`
2. `10000`
3. `100000`

## Architecture

### Package Layout

1. Add `src/Zafu/Benchmark/Vector.bosatsu` with package `Zafu/Benchmark/Vector`.
2. Expose a `main: Main` value used by `lib eval --run` and `lib build --main_pack`.
3. Keep benchmark helpers in the same file initially to minimize surface area.

### Runtime Integration

1. Use `Bosatsu/Prog` for effect sequencing (`await`, `map`, `pure`, `recover`).
2. Use `Bosatsu/IO/Core.now_mono` for monotonic timing and `write_utf8(stdout, line)` for output.
3. Use `Bosatsu/Prog.observe` around per-iteration measured values before folding them into the sink.
4. Keep a printed sink value per row for sanity, but rely on `observe` as the primary anti-elimination mechanism.
5. On IO failure, map errors via `Bosatsu/IO/Error.error_to_String` and return a non-zero exit code.

### Measurement Model

1. Each benchmark case defines `name`, `size`, `ops_per_iteration`, and `run_once(iter_seed) -> a`.
2. Execute warmup iterations that are not timed, then execute timed measured iterations.
3. For each measured iteration, apply `observe` to `run_once` output before sink accumulation.
4. Compute `elapsed_nanos = max(1, end_nanos - start_nanos)`.
5. Compute `elapsed_us = max(1, elapsed_nanos / 1000)`.
6. Compute `total_ops = ops_per_iteration * measure_iterations`.
7. Compute `ops_per_us = int_to_Float64(total_ops) / int_to_Float64(elapsed_us)`.

### Iteration Strategy

1. Default warmup iterations use a small fixed count, for example `3`.
2. Measured iterations are calibrated per case to target a minimum useful runtime window, for example about `200ms`, with min and max clamps.
3. Calibration remains deterministic and local to each `(operation, size)` pair.

### Deterministic Read Pattern

1. Precompute a fixed list of indices per size using an LCG-style formula.
2. Keep read-count per measured iteration fixed, for example `4096` lookups, clamped by size when needed.
3. Avoid runtime randomness so repeated runs are comparable.

### Output Format

1. Print a header plus one CSV row per case.
2. Use header `case,size,iterations,ops,elapsed_us,ops_per_us,sink`.
3. Use row shape like `foldl_sum,10000,120,1200000,8450,142.01,60000000`.
4. Document that `ops_per_us` is primarily comparable within the same operation across sizes.
5. For constant-time operations such as `append_one` and `concat_pair`, define `ops` as API-call count.

### Execution Entry Points

1. Direct command is `./bosatsu lib eval --main Zafu/Benchmark/Vector::main --run`.
2. Add helper script `scripts/benchmark_vector.sh` to standardize local execution.
3. Document benchmark usage in `README.md` under a benchmark section.

## Implementation Plan

Phase 1: dependency and skeleton

1. Update `src/zafu_conf.json` to `core_alpha` `4.3.0` URI and hash.
2. Run `./bosatsu lib fetch`.
3. Create `src/Zafu/Benchmark/Vector.bosatsu` with `main: Main`.
4. Add pure data builders for source lists, vectors, and deterministic read indices.

Phase 2: measurement harness

1. Implement a generic timing helper around `now_mono`.
2. Implement five benchmark cases: `build_from_list`, `random_read`, `foldl_sum`, `append_one`, and `concat_pair`.
3. Thread each measured value through `Bosatsu/Prog.observe` before sink accumulation.
4. Add throughput computation (`ops/us`) with `Bosatsu/Num/Float64` formatting.
5. Print CSV rows for all operation and size combinations.

Phase 3: UX and validation

1. Add `scripts/benchmark_vector.sh`.
2. Update `README.md` with benchmark run instructions and output column definitions.
3. Validate with `./bosatsu lib check`.
4. Validate with `./bosatsu lib test`.
5. Validate with `./bosatsu lib eval --main Zafu/Benchmark/Vector::main --run`.
6. Validate pre-push with `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/75-benchmarking-vector.md` is added with this updated plan.
2. `src/zafu_conf.json` is updated to `core_alpha` version `4.3.0` with the `v0.0.48` release URI and matching hash.
3. `src/Zafu/Benchmark/Vector.bosatsu` defines a runnable `main: Main`.
4. Running `./bosatsu lib eval --main Zafu/Benchmark/Vector::main --run` prints benchmark output without manual code edits.
5. Output includes benchmark rows for `build_from_list`.
6. Output includes benchmark rows for `random_read`.
7. Output includes benchmark rows for `foldl_sum`.
8. Output includes benchmark rows for `append_one`.
9. Output includes benchmark rows for `concat_pair`.
10. Output includes benchmark rows for sizes `1000`, `10000`, and `100000`.
11. Output includes `ops_per_us` and underlying timing columns.
12. Timing uses monotonic clock (`now_mono`), not wall clock.
13. Measured values are passed through `Bosatsu/Prog.observe` before sink folding.
14. `scripts/benchmark_vector.sh` exists and runs the benchmark entrypoint.
15. `README.md` includes a concise benchmark usage section.
16. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: microbenchmark noise from CPU scheduling, thermal throttling, and GC variance. Mitigation: warmup pass, calibrated iteration counts, and reporting raw elapsed time with throughput.
2. Risk: values are still accidentally dropped if `observe` is not applied in all measured loops. Mitigation: require `observe` in the central timing helper and cover with benchmark-harness tests where possible.
3. Risk: very fast cases produce unstable `ops/us` due to timer granularity. Mitigation: clamp minimum elapsed time and increase iterations via calibration with a minimum runtime target.
4. Risk: benchmark runtime becomes too long on slower machines. Mitigation: enforce min and max iteration caps and keep the case matrix fixed.

## Rollout Notes

1. Land as additive functionality with no migration required.
2. Do not gate CI on benchmark numbers in this issue.
3. After merge, record one baseline run in issue comments or PR notes for future comparison.
4. Follow-up issue option: add optional CLI tuning flags such as `--quick` and `--target-ms`.
5. Follow-up issue option: add additional vector scenarios such as `slice`, `map`, `flat_map`, and `filter`.
6. Follow-up issue option: add comparison baselines against `List` and `Array`.
7. Keep `scripts/test.sh` as the required pre-push validation command for benchmark-related changes.
