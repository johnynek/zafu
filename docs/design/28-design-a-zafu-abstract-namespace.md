---
issue: 28
priority: 3
touch_paths:
  - docs/design/28-design-a-zafu-abstract-namespace.md
  - src/Zafu/Abstract/Eq.bosatsu
  - src/Zafu/Abstract/Ord.bosatsu
  - src/Zafu/Abstract/Hash.bosatsu
  - src/Zafu/Abstract/Show.bosatsu
  - src/Zafu/Abstract/Semigroup.bosatsu
  - src/Zafu/Abstract/Monoid.bosatsu
  - src/Zafu/Abstract/Foldable.bosatsu
  - src/Zafu/Abstract/Traverse.bosatsu
  - src/Zafu/Abstract/Applicative.bosatsu
  - src/Zafu/Abstract/Alternative.bosatsu
  - src/Zafu/Abstract/Monad.bosatsu
  - src/Zafu/Abstract/Laws.bosatsu
  - src/Zafu/Abstract/Instances/Primitive.bosatsu
  - src/Zafu/Abstract/Instances/Vector.bosatsu
  - src/Zafu/Abstract/Instances/Chain.bosatsu
  - src/Zafu/Abstract/Instances/LazyList.bosatsu
  - src/Zafu/Abstract/Instances/Deque.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-07T21:54:19Z
---

# Design: Zafu/Abstract namespace

_Issue: #28 (https://github.com/johnynek/zafu/issues/28)_

## Summary

Proposes an opaque, evolvable dictionary-based abstraction layer under Zafu/Abstract, with per-typeclass contracts, phased implementation, acceptance criteria, risks, and rollout strategy for issue #28.

---
issue: 28
title: design a Zafu/Abstract/ namespace
status: proposed
base_branch: main
---

# Design: Zafu/Abstract namespace

Issue: #28

## Context

Zafu currently ships concrete collection APIs under `Zafu/Collection/*` (`Vector`, `Chain`, `LazyList`, `Deque`) with explicit per-module functions. We do not yet have a unified abstraction namespace for typeclass-style programming.

Issue #28 asks for a representation that:

1. Models typeclasses as values.
2. Allows default derivation from minimal primitives.
3. Allows specialization for hot paths.
4. Keeps internal representation hidden for long-term compatibility.
5. Covers common abstractions: `Eq`, `Ord`, `Hash`, `Show`, `Semigroup`, `Monoid`, `Foldable`, `Traverse`, `Applicative`, `Alternative`, `Monad`.
6. Supports generic loops/traversals without exposing collection internals.

## Goals

1. Add a stable `Zafu/Abstract/*` architecture for explicit dictionary passing.
2. Keep abstraction representations opaque so internals can evolve without downstream source breaks.
3. Support both minimal and specialized constructors.
4. Enable higher-kinded programming patterns needed for folds, traversals, and effect composition.
5. Keep adoption incremental and additive to current `Zafu/Collection/*` APIs.

## Non-goals

1. No implicit/global instance search in this change.
2. No forced migration of existing collection call sites.
3. No prelude redesign in this issue.

## Decision

Adopt an opaque dictionary design for each abstraction module.

1. Each abstraction exports an opaque type plus constructor/accessor functions.
2. Constructors are not exported directly (`Ord` is exported, `Ord()` is not).
3. Every abstraction has a minimal constructor from law-defining primitives.
4. Abstractions with meaningful performance deltas also get a specialized constructor.
5. Callers interact via module functions, not record field access.

This picks the "do both" direction from the issue: minimal primitives remain simple, and specialization remains possible without exposing internals.

## Architecture

### 1. Namespace layout

New modules:

1. `src/Zafu/Abstract/Eq.bosatsu`
2. `src/Zafu/Abstract/Ord.bosatsu`
3. `src/Zafu/Abstract/Hash.bosatsu`
4. `src/Zafu/Abstract/Show.bosatsu`
5. `src/Zafu/Abstract/Semigroup.bosatsu`
6. `src/Zafu/Abstract/Monoid.bosatsu`
7. `src/Zafu/Abstract/Foldable.bosatsu`
8. `src/Zafu/Abstract/Traverse.bosatsu`
9. `src/Zafu/Abstract/Applicative.bosatsu`
10. `src/Zafu/Abstract/Alternative.bosatsu`
11. `src/Zafu/Abstract/Monad.bosatsu`
12. `src/Zafu/Abstract/Laws.bosatsu`
13. `src/Zafu/Abstract/Instances/Primitive.bosatsu`
14. `src/Zafu/Abstract/Instances/Vector.bosatsu`
15. `src/Zafu/Abstract/Instances/Chain.bosatsu`
16. `src/Zafu/Abstract/Instances/LazyList.bosatsu`
17. `src/Zafu/Abstract/Instances/Deque.bosatsu`

### 2. Opaque dictionary pattern

Pattern used by every module:

1. Opaque dictionary type.
2. Minimal constructor from primitives.
3. Optional specialized constructor for overrides.
4. Accessor and derived helper functions.
5. Projection helpers for hierarchy edges.

Illustrative API shape for `Ord`:

    package Zafu/Abstract/Ord

    export (
      Ord,
      ord_from_cmp,
      ord_specialized,
      cmp,
      lt,
      lteq,
      gt,
      gteq,
      min,
      max,
      reverse,
      ord_to_eq,
    )

    # constructor is private because Ord() is not exported
    struct Ord[a](
      cmp_fn: (a, a) -> Comparison,
      lt_fn: (a, a) -> Bool,
      lteq_fn: (a, a) -> Bool,
      gt_fn: (a, a) -> Bool,
      gteq_fn: (a, a) -> Bool,
      min_fn: (a, a) -> a,
      max_fn: (a, a) -> a,
    )

`ord_from_cmp` derives all secondary operations from `cmp`. `ord_specialized` permits overriding hot-path functions.

### 3. Abstraction contracts

1. `Eq[a]`
- Minimal: `eq`
- Derived: `neq`
- Constructor: `eq_from_fn`

2. `Ord[a]`
- Minimal: `cmp`
- Derived: `lt`, `lteq`, `gt`, `gteq`, `min`, `max`, plus `Eq`
- Constructors: `ord_from_cmp`, `ord_specialized`
- Projection: `ord_to_eq`

3. `Hash[a]`
- Minimal: `hash` plus coherent `Eq[a]`
- Constructor: `hash_from_fn(eq_inst, hash_fn)`
- Accessors: `hash`, `hash_eq`

4. `Show[a]`
- Minimal: `show`
- Constructor: `show_from_fn`

5. `Semigroup[a]`
- Minimal: `combine`
- Constructor: `semigroup_from_combine`

6. `Monoid[a]`
- Minimal: `empty` and `combine`
- Constructor: `monoid_from_parts`
- Projection: `monoid_to_semigroup`

7. `Foldable[f]`
- Minimal: `foldl` and `foldr`
- Derived: `size`, `to_list`, `all`, `any`, `fold_map`

8. `Applicative[f]`
- Minimal: `pure`, `ap`
- Derived: `map`, `map2`, `product_l`, `product_r`

9. `Alternative[f]`
- Minimal: `applicative`, `empty`, `or_else`
- Derived: `some`, `many`
- Projection: `alternative_to_applicative`

10. `Monad[f]`
- Minimal: `pure`, `flat_map`
- Derived: `map`, `ap`, `flatten`
- Projection: `monad_to_applicative`

11. `Traverse[t]`
- Minimal: `traverse`
- Derived: `sequence`, `map`
- Dependency: consumes `Applicative[g]` to traverse into effect `g`

### 4. Hidden internals and generic loops

The design keeps collection internals private while enabling generic algorithms.

1. `Foldable` and `Traverse` instances are implemented in `Zafu/Abstract/Instances/*` using only exported collection operations.
2. Generic code can run loops and traversals via dictionaries instead of pattern matching on internal enums.
3. Existing collection modules remain free to change representation without breaking generic code.

### 5. Instance strategy

Canonical instances live in `Zafu/Abstract/Instances/*`.

1. `Primitive`: `Int`, `Bool`, `String`, `Comparison` dictionaries for first-order abstractions.
2. `Vector`: first complete higher-kinded implementation target (`Foldable`, `Traverse`, `Applicative`, `Monad`) plus first-order dictionaries.
3. `Chain`: same model as `Vector` once signatures are validated.
4. `LazyList`: start with `Eq`, `Show`, `Foldable`; add `Traverse` and `Monad` only with law coverage over bounded semantics.
5. `Deque`: start with `Eq`, `Ord`, `Show`, `Foldable`; add higher-kinded instances after law and performance review.

## Implementation plan

### Phase 0: Representation spike

1. Implement `Applicative` and `Traverse` shells plus one concrete `Vector` instance.
2. Confirm Bosatsu type signatures and inference are practical for dictionary fields.
3. Lock naming and constructor conventions only after this compiles.

### Phase 1: First-order abstractions

1. Add `Eq`, `Ord`, `Hash`, `Show`, `Semigroup`, `Monoid` modules.
2. Implement minimal and specialized constructors where relevant (`Ord` initially).
3. Add primitive instances in `Instances/Primitive`.
4. Add first-order law checks in `Laws`.

### Phase 2: Higher-kinded abstractions

1. Add `Foldable`, `Applicative`, `Alternative`, `Monad`, `Traverse` modules.
2. Add derived helper functions only after minimal constructors compile.
3. Implement `Vector` instances first.

### Phase 3: Expand instances

1. Add `Chain` instances matching `Vector` coverage.
2. Add `LazyList` and `Deque` instances incrementally with law checks.
3. Add specialization hooks only for measured hotspots.

### Phase 4: Adoption and examples

1. Add generic utilities that consume abstraction dictionaries.
2. Keep existing concrete helpers intact for source compatibility.
3. Add docs/examples showing explicit dictionary passing patterns.

## Acceptance criteria

1. `docs/design/28-design-a-zafu-abstract-namespace.md` documents this architecture and plan.
2. Modules exist for all requested abstractions under `src/Zafu/Abstract/*`.
3. Constructors for abstraction dictionary internals are not exported.
4. `Ord` supports creation from only `cmp` and exposes `lt/lteq/gt/gteq/min/max` through exported functions.
5. Hierarchy projections exist: `ord_to_eq`, `monoid_to_semigroup`, `monad_to_applicative`, `alternative_to_applicative`.
6. Primitive instances compile and satisfy core first-order laws.
7. At least one collection (`Vector`) has working `Foldable`, `Traverse`, `Applicative`, and `Monad` instances with law checks.
8. `Chain` has at least `Foldable` and `Traverse` instances.
9. Existing `Zafu/Collection/*` public APIs remain source-compatible.
10. `./bosatsu lib check` passes.
11. `./bosatsu lib test` passes.
12. `scripts/test.sh` passes before merge.

## Risks and mitigations

1. Risk: higher-kinded dictionary signatures are harder than first-order dictionaries.
- Mitigation: Phase 0 compile spike before broad rollout.

2. Risk: dictionary indirection can add runtime overhead.
- Mitigation: keep minimal kernels small, precompute derived ops in constructors, add specialized constructors only where benchmarked.

3. Risk: multiple competing instances can cause incoherent behavior.
- Mitigation: provide canonical instances under `Zafu/Abstract/Instances/*` and document naming/import conventions.

4. Risk: law regressions, especially around `Hash` coherence and lazy traversal semantics.
- Mitigation: centralize law checks in `Zafu/Abstract/Laws` and require property coverage in CI.

5. Risk: API name collisions (`map`, `empty`, `foldl`) across modules.
- Mitigation: recommend qualified or aliased imports in examples and docs.

## Rollout notes

1. Land as additive modules on `main`; do not remove current collection helpers.
2. Land in small PRs by phase to isolate type-system and law failures.
3. Keep first merge focused on module scaffolding plus `Vector` proof of viability.
4. Delay broad deprecations until the abstraction API is exercised and benchmarked.
5. Treat `LazyList` and `Deque` higher-kinded instances as opt-in follow-ups after correctness and perf validation.

## Follow-ups out of scope for this issue

1. Implicit instance resolution.
2. Prelude/re-export surface design.
3. Cross-repo ecosystem alignment beyond this repository.
