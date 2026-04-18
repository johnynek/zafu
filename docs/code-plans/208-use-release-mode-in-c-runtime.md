# Code Plan #208

> Generated from code plan JSON.
> Edit the `.json` file, not this `.md` file.

## Metadata

- Flow: `small_job`
- Issue: `#208` Use release mode in C runtime
- Pending steps: `0`
- Completed steps: `2`
- Total steps: `2`

## Summary

Make the repo-owned native bootstrap treat release-mode C runtime installs as an explicit contract and keep that contract covered by the required `scripts/test.sh` gate.

## Current State

The repo-local `bosatsu` launcher now makes its implicit native bootstrap explicit by delegating bare `./bosatsu --fetch` to `c-runtime install --profile release`, and `scripts/test.sh` now starts with a dedicated `scripts/test_bosatsu_launcher.sh` regression. That regression creates a throwaway git repo, installs a stub native artifact through `--artifact`, and asserts the release-mode bootstrap argv, repo-root install location, and explicit `--fetch <subcommand>` passthrough behavior without downloading the real CLI or building the real C runtime. `scripts/test.sh` passed locally after wiring in the new regression.

## Problem

Before this round, the required gate relied on upstream defaults and had no dedicated launcher regression. That left room for future edits to silently drop `--profile release`, alter the implicit bootstrap argv, or break explicit passthrough behavior while unrelated checks still passed.

## Steps

1. [x] `pin-release-bootstrap` Make the implicit native bootstrap explicitly select release mode

Update the repo-local `bosatsu` launcher so the no-args `./bosatsu --fetch` convenience path delegates to `c-runtime install --profile release` instead of relying on the upstream default. Keep the existing fetch behavior, `--artifact` override flow, repo-root detection, and passthrough semantics for explicit trailing subcommands unchanged. Add a short comment near the auto-install branch explaining that zafu intentionally validates the optimized C runtime profile.

#### Invariants

- `./bosatsu --fetch` with no trailing subcommand still bootstraps both the CLI artifact and the C runtime from the repo root.
- The implicit C runtime install path always includes `--profile release`.
- If the user supplies explicit trailing args after `--fetch`, the launcher passes only those args through and does not append the auto-install subcommand.

#### Property Tests

- None recorded.

#### Assertion Tests

- Launcher regression case: with a stub installed artifact and `--fetch` only, the wrapped executable receives `c-runtime install --profile release`.
- Passthrough regression case: with a stub installed artifact and an explicit subcommand such as `--fetch version`, the wrapped executable receives only the explicit user args.

#### Completion Notes

Updated the repo-local `bosatsu` launcher so the implicit `./bosatsu --fetch` bootstrap now runs `c-runtime install --profile release`, and added an inline comment explaining that zafu intentionally validates the optimized native runtime profile. The auto-install branch still triggers only for `--fetch` with no trailing subcommand, so explicit passthrough commands such as `./bosatsu --fetch version` keep their prior behavior. Verified both contracts with a temporary git repo and a stub native artifact installed through `--artifact`.

2. [x] `gate-bootstrap-contract` Cover the launcher contract in the required test gate

Add a fast repo-local regression script under `scripts/` that creates a temporary throwaway repo, uses `--artifact` to avoid network and real compiler downloads, and asserts the launcher's implicit bootstrap command line stays pinned to release mode while explicit `--fetch <subcommand>` calls still pass through unchanged. Wire that script into `scripts/test.sh` so the configured `required_tests` gate fails if the launcher stops selecting the release-mode C runtime.

#### Invariants

- `scripts/test.sh` remains the single required pre-PR gate and now covers the native bootstrap profile contract.
- The new regression runs without downloading the real Bosatsu CLI or building the real C runtime.
- The regression exercises the launcher from a nested directory and verifies that the stub artifact is installed under the throwaway repo root.
- Explicit trailing args after `--fetch` still pass through unchanged and do not pick up the auto-install subcommand.

#### Property Tests

- None recorded.

#### Assertion Tests

- Launcher regression case: in a throwaway git repo with a stub native artifact installed through `--artifact`, bare `./bosatsu --fetch` records `c-runtime install --profile release`.
- Repo-root regression case: the same throwaway-repo launch writes the stub artifact under `.bosatsuc/cli/<version>/...` at the repo root even when invoked from a nested working directory.
- Passthrough regression case: `./bosatsu --fetch version` records only `version`.
- `scripts/test.sh` invokes the new launcher regression before the existing bootstrap, check/test, tool, benchmark, and publish-dry-run validations.

#### Completion Notes

Added `scripts/test_bosatsu_launcher.sh`, which creates a throwaway git repo, copies the launcher plus Bosatsu version/platform files, installs a stub native artifact through `--artifact`, and asserts both the implicit release-mode bootstrap argv and explicit-subcommand passthrough from a nested working directory. Wired that regression into `scripts/test.sh` ahead of the heavier bootstrap work so the required gate now fails immediately on launcher contract drift. Verified `scripts/test_bosatsu_launcher.sh` and a full `scripts/test.sh` run locally.
