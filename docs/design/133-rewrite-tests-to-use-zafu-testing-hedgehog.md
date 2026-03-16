---
issue: 133
priority: 3
touch_paths:
  - docs/design/133-rewrite-tests-to-use-zafu-testing-hedgehog.md
  - src/Zafu/Testing/HedgeHog.bosatsu
  - src/Zafu/Collection/List.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
  - src/Zafu/Collection/HashMap.bosatsu
  - src/Zafu/Collection/HashSet.bosatsu
  - src/Zafu/Collection/Heap.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/LazyTree.bosatsu
  - src/Zafu/Abstract/Applicative.bosatsu
  - src/Zafu/Abstract/Monad.bosatsu
  - src/Zafu/Control/IterState.bosatsu
  - src/Zafu/Collection/LazyListTests.bosatsu
  - src/Zafu/Collection/LazyTreeTests.bosatsu
  - src/Zafu/Abstract/ApplicativeTests.bosatsu
  - src/Zafu/Abstract/MonadTests.bosatsu
  - src/Zafu/Control/IterStateTests.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-15T22:10:36Z
---

# Rewrite Tests to Use `Zafu/Testing/HedgeHog`

_Issue: #133 (https://github.com/johnynek/zafu/issues/133)_

## Summary

Migrate Zafu’s property-test stack from `Bosatsu/Testing/Properties` to `Zafu/Testing/HedgeHog`, split tests for HedgeHog dependency modules into dedicated `*Tests` packages to avoid dependency cycles, and roll out module-by-module with full `lib check`/`lib test` validation.

## Context
1. The repository currently runs tests via `./bosatsu lib test`, with test discovery based on top-level `tests` values in packages under `src`.
2. Several modules still use `Bosatsu/Testing/Properties` and `Bosatsu/Rand` for property checks (notably `List`, `Vector`, `Chain`, `Deque`, `HashMap`, `HashSet`, `Heap`, `LazyList`, `LazyTree`).
3. `Zafu/Testing/HedgeHog` already exists and provides shrinking-capable property testing (`Gen`, `Prop`, `forall_Prop`, `suite_Prop`, `run_Prop`).
4. `Zafu/Testing/HedgeHog` imports `Zafu/Abstract/Applicative`, `Zafu/Abstract/Monad`, `Zafu/Control/IterState`, `Zafu/Collection/LazyList`, and `Zafu/Collection/LazyTree`.
5. Issue #133 asks to remove Bosatsu property checks, rewrite tests to HedgeHog, and create separate `*Tests` packages for modules HedgeHog depends on (examples: `LazyListTests`, `ApplicativeTests`, `MonadTests`).

## Problem
1. Existing Bosatsu property checks do not shrink failing inputs, so debugging counterexamples is slower.
2. Naively importing HedgeHog in modules that HedgeHog itself imports introduces circular dependencies.
3. Property-test code is currently mixed with production modules, which makes dependency-safe migration harder.
4. The project currently has two property-generation models (`Rand` and `Gen`), creating inconsistent failure behavior and maintenance overhead.

## Goals
1. Replace all uses of `Bosatsu/Testing/Properties` with `Zafu/Testing/HedgeHog`.
2. Preserve an acyclic package graph by moving HedgeHog-dependent module tests into dedicated test packages.
3. Keep production runtime APIs and semantics unchanged.
4. Keep CI/local validation commands green (`./bosatsu lib check`, `./bosatsu lib test`, `scripts/test.sh`).
5. Improve debuggability of failures through shrinking.

## Non-goals
1. Redesigning collection or typeclass APIs.
2. Forcing all deterministic unit tests to become generative properties.
3. Exactly preserving old random distributions from `Bosatsu/Rand`.
4. Reworking Bosatsu test-runner internals.

## Proposed Design
### Test framework convergence
1. Migrate property suites to HedgeHog primitives: `Gen`, `forall_Prop`, `suite_Prop`, `run_Prop`.
2. Remove `Bosatsu/Testing/Properties` imports from source modules.
3. Replace test-only `Rand` generators with HedgeHog generators and module-local `show_*` helpers for failure rendering.

### Dependency-safe split for HedgeHog upstream modules
1. Keep tests in-place for modules not imported by HedgeHog.
2. Move tests out of HedgeHog upstream modules into separate packages:
3. `Zafu/Collection/LazyListTests`
4. `Zafu/Collection/LazyTreeTests`
5. `Zafu/Abstract/ApplicativeTests`
6. `Zafu/Abstract/MonadTests`
7. `Zafu/Control/IterStateTests`
8. Production modules in that set remain HedgeHog-free; new `*Tests` modules depend on both the target module and HedgeHog.

### Generator and law migration strategy
1. Map existing test combinators to HedgeHog equivalents (tuple/list generation, size scaling, fixed-size runs).
2. For higher-order law inputs (function values), generate finite function tags and interpret tags into deterministic lambdas.
3. Keep existing seed/count defaults initially to reduce migration noise; tune only after baseline pass.
4. Reuse existing `laws_*` helpers where available; shift property sampling/wrapping into HedgeHog-based tests.

### Test discovery contract
1. Each new `*Tests` package defines a top-level `tests` value.
2. Original modules that are split out remove their HedgeHog-based `tests` block to avoid duplicates and import cycles.
3. Naming convention: `src/Zafu/.../<Name>Tests.bosatsu` with package `Zafu/.../<Name>Tests`.

## Implementation Plan
1. Phase 1: Create dependency-safe test packages.
2. Add `LazyListTests`, `LazyTreeTests`, `ApplicativeTests`, `MonadTests`, and `IterStateTests` files.
3. Move existing tests/property helpers from corresponding production files into these packages.
4. Remove HedgeHog test imports/blocks from the upstream production modules.
5. Phase 2: Convert non-upstream property suites.
6. Rewrite property suites in `List`, `Vector`, `Chain`, `Deque`, `HashMap`, `HashSet`, and `Heap` to HedgeHog.
7. Delete `Bosatsu/Testing/Properties` and test-only `Bosatsu/Rand` usage from those modules.
8. Phase 3: Shared helper consolidation (if needed).
9. If migration duplicates generator/show boilerplate, add shared helpers in `Zafu/Testing/HedgeHog` (or a sibling helper module) and refactor call sites.
10. Phase 4: Validation.
11. Run `./bosatsu lib check`.
12. Run `./bosatsu lib test`.
13. Run `scripts/test.sh`.
14. Confirm no `Bosatsu/Testing/Properties` imports remain.

## Acceptance Criteria
1. `docs/design/133-rewrite-tests-to-use-zafu-testing-hedgehog.md` captures the approved architecture and plan.
2. `rg -l "Bosatsu/Testing/Properties" src` returns no matches.
3. The following packages exist and expose top-level `tests`: `Zafu/Collection/LazyListTests`, `Zafu/Collection/LazyTreeTests`, `Zafu/Abstract/ApplicativeTests`, `Zafu/Abstract/MonadTests`, `Zafu/Control/IterStateTests`.
4. `src/Zafu/Collection/LazyList.bosatsu`, `src/Zafu/Collection/LazyTree.bosatsu`, `src/Zafu/Abstract/Applicative.bosatsu`, `src/Zafu/Abstract/Monad.bosatsu`, and `src/Zafu/Control/IterState.bosatsu` do not import `Zafu/Testing/HedgeHog`.
5. Migrated property suites use HedgeHog `Prop`/`forall_Prop` and run through `run_Prop`.
6. `./bosatsu lib check` passes.
7. `./bosatsu lib test` passes.
8. `scripts/test.sh` passes.

## Risks and Mitigations
1. Risk: accidental circular imports during migration.
Mitigation: create split `*Tests` packages first, then migrate properties.
2. Risk: behavior drift from generator changes.
Mitigation: preserve seeds/counts initially and compare module-by-module outcomes.
3. Risk: increased runtime from shrinking on large recursive structures.
Mitigation: bound generator sizes/depth and keep heavier suites at lower counts where necessary.
4. Risk: duplicate test execution if old and new suites coexist.
Mitigation: remove or relocate old top-level `tests` bindings in split modules as part of the same change.
5. Risk: weak failure rendering for complex values.
Mitigation: add focused `show_*` helpers (for example, size + small preview) per module.

## Rollout Notes
1. Roll out in dependency-safe order on `main`: split upstream-module tests first, then migrate non-upstream property suites.
2. Keep each migration step small enough to isolate regressions by module.
3. Expect failure text and minimal counterexamples to change because HedgeHog shrinking is now active.
4. Keep scope limited to test-framework migration; defer unrelated API/refactor work to follow-up issues.
