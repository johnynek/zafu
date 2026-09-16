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

Update the repository’s existing Bosatsu version-pin mechanism to Bosatsu 0.0.68 and the matching `core_alpha` 9.0.0 release artifact, while preserving Zafu’s source behavior, public package surface, and unrelated configuration.

Plan trajectory: initial steps 1; review revisions 0; review-origin steps 0.

## Current State

On `main`, `.bosatsu_version` pins the repo-local wrapper to Bosatsu 0.0.67. The sole active `core_alpha` dependency declaration is `public_deps.core_alpha` in `src/zafu_conf.json`, which pins version 8.0.2 to the artifact published with Bosatsu 0.0.67. The generic launcher and benchmark tooling already read `.bosatsu_version`, so they do not contain a second active compiler version pin. Historical benchmark results and earlier code plans contain older version metadata but are not dependency configuration.

## Problem

Issue #214 requests the update to Bosatsu 0.0.68 and explicitly requires bumping the core alpha library. The Bosatsu 0.0.68 release publishes `core_alpha` 9.0.0, but the repository still selects the 0.0.67 compiler/runtime and `core_alpha` 8.0.2 artifact. The two active pins must move together so dependency fetching, checking, testing, and publishing use a consistent release.

## Steps

1. [ ] `bump-bosatsu-and-core-alpha` Update the Bosatsu and core_alpha release pins

Change `.bosatsu_version` from `0.0.67` to `0.0.68`. In `src/zafu_conf.json`, update only `public_deps.core_alpha`: set `version` to `9.0.0`, set its sole hash to `blake3:a8abc327ee53c5aa057c94be53cb357ff120563b196f2d65461400cd5c3f1f3d`, and set its sole URI to `https://github.com/johnynek/bosatsu/releases/download/v0.0.68/core_alpha-v9.0.0.bosatsu_lib`. Leave `exported_packages`, `all_packages`, repository metadata, `bosatsu_libs.json`, historical benchmark results, generated planning artifacts, and generic launcher/benchmark code unchanged. Use `./bosatsu --fetch` and `./bosatsu fetch` to exercise the new release and dependency metadata, then run `./bosatsu check --warn` and `./bosatsu test --warn` as focused compatibility checks. Do not make speculative source changes; if the new compiler or library exposes a concrete incompatibility, apply only the smallest source/test correction needed to preserve existing behavior and public APIs, with focused regression coverage for any behavior change.

#### Invariants

- The repo-local wrapper resolves Bosatsu release 0.0.68 through the existing `.bosatsu_version` mechanism.
- The `core_alpha` version, Blake3 hash, and download URI identify the same `core_alpha` 9.0.0 artifact published with Bosatsu 0.0.68.
- The bounded active-pin inventory remains `.bosatsu_version` and `src/zafu_conf.json`; historical version records and consumers that already resolve `.bosatsu_version` are not rewritten.
- Zafu’s exported packages, package discovery settings, repository metadata, and existing behavior remain unchanged unless a concrete 0.0.68 compatibility failure requires a minimal correction.

#### Property Tests

- None recorded.

#### Assertion Tests

- Verify the trimmed contents of `.bosatsu_version` equal `0.0.68`.
- Verify `src/zafu_conf.json` declares `public_deps.core_alpha` with version `9.0.0`, hash `blake3:a8abc327ee53c5aa057c94be53cb357ff120563b196f2d65461400cd5c3f1f3d`, and URI `https://github.com/johnynek/bosatsu/releases/download/v0.0.68/core_alpha-v9.0.0.bosatsu_lib`.
- Verify `./bosatsu --fetch` and `./bosatsu fetch` succeed using the updated release metadata.
- Verify `./bosatsu check --warn` and `./bosatsu test --warn` succeed with Bosatsu 0.0.68 and `core_alpha` 9.0.0; add no artificial tests when the change remains metadata-only.
