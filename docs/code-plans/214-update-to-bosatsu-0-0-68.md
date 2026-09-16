# Code Plan #214

> Generated from code plan JSON.
> Edit the `.json` file, not this `.md` file.

## Metadata

- Flow: `small_job`
- Issue: `#214` Update to bosatsu 0.0.68
- Pending steps: `1`
- Completed steps: `0`
- Total steps: `1`

## Summary

Atomically update the repository’s existing Bosatsu dependency mechanism to release 0.0.68: pin the repo-local wrapper to Bosatsu 0.0.68 and update the `core_alpha` public dependency to the matching 9.0.0 artifact, then confirm the project still fetches, checks, and tests successfully.

Plan trajectory: initial steps 1; review revisions 0; review-origin steps 0.

## Current State

At initial planning on `main`, `.bosatsu_version` pins the repo-local wrapper to Bosatsu `0.0.67`. `src/zafu_conf.json` declares `public_deps.core_alpha` version `8.0.2`, fetched from the Bosatsu v0.0.67 release with Blake3 hash `67f348d5e319236d9d6fab5f34ed21b694f4fd3da883b9bfd9d5979054d11527`. These are the only repository-owned Bosatsu release and `core_alpha` pins; the wrapper, dependency fetch, checks, tests, benchmarks, and publishing workflow already consume them. The [Bosatsu v0.0.68 release](https://github.com/johnynek/bosatsu/releases/tag/v0.0.68) publishes `core_alpha-v9.0.0.bosatsu_lib`, whose published Blake3 checksum is `a8abc327ee53c5aa057c94be53cb357ff120563b196f2d65461400cd5c3f1f3d`. The issue-tree manifest contains no conflicting ancestor or dependency requirements.

## Problem

Issue #214 requires Zafu to update to Bosatsu 0.0.68 and explicitly requires the corresponding core alpha library bump. The current 0.0.67 wrapper pin and 8.0.2 core dependency continue to select the previous release, so the repository cannot build and validate against the requested compiler/runtime and `core_alpha` artifact.

## Steps

1. [ ] `update-bosatsu-and-core-alpha-pins` Update the Bosatsu 0.0.68 toolchain and core_alpha dependency

Update the established two-part dependency configuration as one coherent slice. Change `.bosatsu_version` from `0.0.67` to `0.0.68`. In `src/zafu_conf.json`, keep the existing `public_deps.core_alpha` declaration but change its `version` to `9.0.0`, replace its sole hash with `blake3:a8abc327ee53c5aa057c94be53cb357ff120563b196f2d65461400cd5c3f1f3d`, and replace its sole URI with `https://github.com/johnynek/bosatsu/releases/download/v0.0.68/core_alpha-v9.0.0.bosatsu_lib`. Do not introduce a second version setting, modify exported-package or package-discovery configuration, refresh checked-in benchmark results, or update unrelated dependencies or documentation. Use `./bosatsu --fetch` and `./bosatsu fetch` to exercise the updated compiler and dependency metadata, then run the focused repository feedback commands `./bosatsu check --warn` and `./bosatsu test --warn`. If the new compiler or library exposes a concrete compatibility failure, make only the smallest directly required source correction in the affected package, preserve its existing public API and behavior, and add focused regression coverage appropriate to that correction; otherwise keep the change metadata-only and add no artificial tests. The slice is complete when the exact pins are present and all four focused commands succeed. The supervised `scripts/test.sh` required-test gate is run separately by MergeXO and is not a plan step.

#### Invariants

- `.bosatsu_version` remains the single source of truth used by the existing wrapper and selects Bosatsu release `0.0.68`.
- The `core_alpha` version, release URI, and Blake3 hash consistently identify the single `core_alpha-v9.0.0.bosatsu_lib` artifact published with Bosatsu 0.0.68.
- The existing `public_deps.core_alpha` declaration is extended in place; no parallel dependency or version-selection mechanism is introduced.
- Zafu’s exported packages, package discovery, public behavior, and unrelated dependency metadata remain unchanged unless a focused command demonstrates that a minimal compatibility correction is required.

#### Property Tests

- None recorded.

#### Assertion Tests

- Verify `.bosatsu_version` contains exactly `0.0.68` and `src/zafu_conf.json` contains the exact `core_alpha` 9.0.0 version, v0.0.68 URI, and published Blake3 hash.
- Run `./bosatsu --fetch` followed by `./bosatsu fetch`; both must succeed, including download and hash validation of the new `core_alpha` artifact.
- Run `./bosatsu check --warn` and `./bosatsu test --warn` with the updated toolchain and dependency; both must succeed. If a compatibility correction is necessary, add a focused assertion or property in the affected package that fails without that correction.
