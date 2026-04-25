# Code Plan #212

> Generated from code plan JSON.
> Edit the `.json` file, not this `.md` file.

## Metadata

- Flow: `small_job`
- Issue: `#212` update to bosatsu 0.0.66
- Pending steps: `0`
- Completed steps: `3`
- Total steps: `3`
- State: `implemented`

## Summary

Update this repo to Bosatsu 0.0.66 by moving the repo-local Bosatsu version pin and the `core_alpha` public dependency to the matching release artifact, then verify that the existing library, tools, benchmarks, and publish dry run still pass the configured `scripts/test.sh` gate.

## Current State

The repo now pins the Bosatsu wrapper version in `.bosatsu_version` to `0.0.66`. `src/zafu_conf.json` declares public dependency `core_alpha` at library version `8.0.1`, with the URI `https://github.com/johnynek/bosatsu/releases/download/v0.0.66/core_alpha-v8.0.1.bosatsu_lib` and Blake3 hash `blake3:a54095ec9b31a305bd0729ad213ae12b40e3013cbec9779e85eb712261eaa2d0`. Exported packages, package globs, repo metadata, and unrelated dependency configuration are unchanged. `scripts/test.sh` now requests a larger native stack limit before running the Bosatsu checks because the updated 0.0.66 native compiler path hit a stack overflow in CI with the previous 16 MB request. `./bosatsu --fetch`, `./bosatsu fetch`, `./bosatsu check --warn`, `./bosatsu test --warn`, and the configured `scripts/test.sh` gate pass under the updated metadata.

## Problem

Issue #212 asked to update to Bosatsu 0.0.66 and explicitly called out bumping the `core_alpha` library. The repo metadata now points at the requested compiler/runtime and matching core library, and the required verification gate passes.

## Steps

1. [x] `bump-bosatsu-and-core-alpha-pins` Update Bosatsu and core_alpha release metadata

Update `.bosatsu_version` from `0.0.65` to `0.0.66`. Update `src/zafu_conf.json` so `public_deps.core_alpha.version` is `8.0.1`, its URI is `https://github.com/johnynek/bosatsu/releases/download/v0.0.66/core_alpha-v8.0.1.bosatsu_lib`, and its Blake3 hash is `blake3:a54095ec9b31a305bd0729ad213ae12b40e3013cbec9779e85eb712261eaa2d0`. Keep exported packages, package globs, repo metadata, and unrelated dependency configuration unchanged.

#### Invariants

- The repo-local wrapper downloads and runs Bosatsu release `0.0.66`.
- The `core_alpha` dependency version, URI, and hash all refer to the same `v0.0.66` release artifact.
- No public Zafu package exports or package discovery settings change as part of the metadata bump.

#### Property Tests

- None recorded.

#### Assertion Tests

- After the edit, `src/zafu_conf.json` contains `public_deps.core_alpha.version` equal to `8.0.1`.
- After the edit, `src/zafu_conf.json` contains only the full `https://github.com/johnynek/bosatsu/releases/download/v0.0.66/core_alpha-v8.0.1.bosatsu_lib` URI for `core_alpha`.
- After the edit, `.bosatsu_version` contains exactly `0.0.66`.

#### Completion Notes

Updated `.bosatsu_version` to `0.0.66` and updated `src/zafu_conf.json` so `public_deps.core_alpha` uses version `8.0.1`, the `https://github.com/johnynek/bosatsu/releases/download/v0.0.66/core_alpha-v8.0.1.bosatsu_lib` URI, and Blake3 hash `blake3:a54095ec9b31a305bd0729ad213ae12b40e3013cbec9779e85eb712261eaa2d0`. No exported packages, package globs, repo metadata, or unrelated dependency configuration changed.

2. [x] `repair-compatibility-breakages-if-any` Handle 0.0.66 compatibility fallout

Run the normal fast feedback commands after the metadata bump: `./bosatsu --fetch`, `./bosatsu fetch`, `./bosatsu check --warn`, and `./bosatsu test --warn`. If Bosatsu 0.0.66 or `core_alpha` 8.0.1 exposes compile, lint, or test failures, make the smallest source changes needed to preserve existing Zafu behavior and public API intent. Keep any required code edits idiomatic Bosatsu per `coding_style.md`, with special care for stack safety, public surface discipline, and existing collection/parser/generator/test helper patterns.

#### Invariants

- Existing exported Zafu APIs remain intentional; do not expose internal helpers just to satisfy the upgrade.
- Any source changes required by the dependency bump preserve the behavior already covered by the repo's library tests, tool regressions, and benchmark smoke checks.
- Stack-safety-sensitive paths remain implemented with `loop` where iterative execution is required.
- Any compatibility fix is scoped to the concrete compiler/core library change that caused it.

#### Property Tests

- If a compatibility fix changes collection, parser, traversal, hashing, generator, or shrinking behavior, add or update property-style tests that state the preserved contract rather than only checking one example.
- If no source behavior changes are needed, rely on the existing Bosatsu property-style suites and do not add artificial tests for a pure dependency metadata bump.

#### Assertion Tests

- `./bosatsu check --warn` succeeds after the dependency fetch.
- `./bosatsu test --warn` succeeds after the dependency fetch.
- No focused compatibility regressions were added because the metadata bump did not require source behavior changes.

#### Completion Notes

Ran `./bosatsu --fetch`, `./bosatsu fetch`, `./bosatsu check --warn`, and `./bosatsu test --warn` successfully with Bosatsu `0.0.66` and `core_alpha` `8.0.1`. No compatibility source changes or new tests were needed.

3. [x] `run-required-gate` Verify with required_tests

Run the configured pre-PR gate `scripts/test.sh` after the metadata bump and any required compatibility fixes. Treat this as the merge-blocking verification for the branch; do not consider the work reviewable until this script passes or a concrete environmental blocker is documented.

#### Invariants

- `scripts/test.sh` remains the single required pre-PR gate for this repo version.
- The gate exercises the updated Bosatsu wrapper version and updated `core_alpha` dependency, not cached 0.0.65 state.
- The publish dry run still succeeds with the updated dependency metadata.

#### Property Tests

- None recorded.

#### Assertion Tests

- `scripts/test.sh` passes from the repository root.
- The gate included successful dependency fetch, `./bosatsu check`, `./bosatsu test`, tool regressions, benchmark smoke checks, Python unit tests, and publish dry run under the updated Bosatsu 0.0.66 setup.

#### Completion Notes

Raised the `scripts/test.sh` soft stack request from 16 MB to 64 MB, with a 32 MB fallback when the host rejects the larger value, after CI reported a native Bosatsu compiler `StackOverflowError` under the updated 0.0.66 setup. Ran `scripts/test.sh` successfully from the repository root after the metadata bump, compatibility checks, and stack-limit hardening.
