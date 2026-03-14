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
  - src/Zafu/Abstract/Compose.bosatsu
  - src/Zafu/Abstract/Instances/Primitive.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-07T22:20:00Z
---

# Design: Zafu/Abstract namespace

_Issue: #28 (https://github.com/johnynek/zafu/issues/28)_

## Summary

Define an opaque, evolvable typeclass-dictionary architecture under `Zafu/Abstract`, with canonical instances colocated with data types when possible, law helpers colocated with each typeclass, and composition support (`Compose`) for `Foldable`, `Traverse`, and `Applicative`.

## Status

Proposed

## Context

Zafu currently exposes concrete collection modules (`Vector`, `Chain`, `LazyList`, `Deque`) with explicit per-module APIs. We want a shared abstraction layer for typeclass-style programming that keeps representation details hidden while still allowing optimized implementations.

Issue #28 asks for a design that:

1. Represents typeclasses as values.
2. Supports default derivation from minimal primitives.
3. Allows future specialization without breaking callers.
4. Covers `Eq`, `Ord`, `Hash`, `Show`, `Semigroup`, `Monoid`, `Foldable`, `Traverse`, `Applicative`, `Alternative`, `Monad`.
5. Enables generic loops/traversals without forcing exposure of private data constructors.

## Goals

1. Add `Zafu/Abstract/*` with opaque dictionary types and stable function-based APIs.
2. Keep constructors private so internals can evolve compatibly.
3. Keep API naming small and idiomatic.
4. Support composition patterns needed in real code (`Compose` and hierarchy projections).
5. Keep rollout additive and source-compatible with existing collection APIs.

## Non-goals

1. Implicit/global instance search.
2. A full prelude redesign.
3. Immediate migration of all existing call sites.

## Decision summary

1. Use opaque dictionary structs for each abstraction module.
2. Export minimal constructors and derived accessors as functions.
3. Keep canonical instances with the type definition package when possible.
4. Keep law helpers in each typeclass module (not one shared public `Laws` package).
5. Add `Compose` support so `Foldable`, `Traverse`, and `Applicative` compose explicitly.
6. Keep short names (`map`, `foldl`, `empty`, etc.) and rely on import aliasing (`as`) on collisions.

## Namespace layout

Core abstraction modules:

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
12. `src/Zafu/Abstract/Compose.bosatsu`

Instance location:

1. Canonical collection instances are exported from collection packages (`Zafu/Collection/Vector`, `Chain`, `LazyList`, `Deque`).
2. Primitive/base-type instances live in `src/Zafu/Abstract/Instances/Primitive.bosatsu` (since those types are not defined in this repo).
3. Optional orphan/compat instances may be added in dedicated modules only when colocating is impossible.

## Core API pattern

Each abstraction module follows this shape:

1. Export opaque type (e.g., `Ord`) without exporting constructor syntax (`Ord()`).
2. Export minimal constructor from law primitives.
3. Optionally export specialized constructor for hot paths.
4. Export all operations as module functions.
5. Export law-check helper functions for that abstraction.

Illustrative `Ord` shape:

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
      laws_Ord,
    )

    struct Ord[a](
      cmp_fn: (a, a) -> Comparison,
      lt_fn: (a, a) -> Bool,
      lteq_fn: (a, a) -> Bool,
      gt_fn: (a, a) -> Bool,
      gteq_fn: (a, a) -> Bool,
      min_fn: (a, a) -> a,
      max_fn: (a, a) -> a,
    )

## Abstraction contracts

1. `Eq[a]`
- Minimal: `eq`
- Derived: `neq`
- Laws export: `laws_Eq`

2. `Ord[a]`
- Minimal: `cmp`
- Derived: `eq`, `lt`, `lteq`, `gt`, `gteq`, `min`, `max`
- Projection: `ord_to_eq`
- Constructors: `ord_from_cmp`, `ord_specialized`
- Laws export: `laws_Ord`

3. `Hash[a]`
- Minimal: `hash` with coherent `Eq[a]`
- Accessors: `hash`, `hash_eq`
- Laws export: `laws_Hash`

4. `Show[a]`
- Minimal: `show`
- Laws export: lightweight round-trip/readability checks where applicable

5. `Semigroup[a]`
- Minimal: `combine`
- Laws export: `laws_Semigroup`

6. `Monoid[a]`
- Minimal: `empty`, `combine`
- Projection: `monoid_to_semigroup`
- Laws export: `laws_Monoid`

7. `Applicative[f]`
- Minimal: `pure`, `ap`
- Derived: `map`, `map2`, `product_l`, `product_r`
- Laws export: `laws_Applicative`

8. `Monad[f]`
- Minimal: `pure`, `flat_map`
- Derived: `map`, `ap`, `flatten`
- Projection: `monad_to_applicative`
- Laws export: `laws_Monad`

9. `Alternative[f]`
- Minimal: `applicative`, `empty`, `or_else`
- Derived: `some`, `many`
- Projection: `alternative_to_applicative`
- Laws export: `laws_Alternative`

10. `Traverse[t]`
- Minimal: `traverse`
- Derived: `sequence`, `map`
- Projection: `traverse_to_foldable`
- Laws export: `laws_Traverse`

11. `Foldable[f]`
- Primary export: `foldl`, `foldr`, `fold_map`, `size`, `to_list`, `all`, `any`
- Constructor strategy: direct constructor for performance-sensitive types and derived constructor `foldable_from_traverse` via `Traverse`
- Laws export: `laws_Foldable`

## Composition support

Add `Compose` in `src/Zafu/Abstract/Compose.bosatsu`:

    struct Compose[f: * -> *, g: * -> *, a](fga: f[g[a]])

Provide composition builders:

1. `compose_foldable(fold_f, fold_g) -> Foldable[Compose[f, g, *]]`
2. `compose_traverse(traverse_f, traverse_g) -> Traverse[Compose[f, g, *]]`
3. `compose_applicative(app_f, app_g) -> Applicative[Compose[f, g, *]]`

This gives reusable composition for the abstractions where laws support it.

## Instance placement and performance

Canonical instance exports should live with each data type package to preserve ergonomics and allow optimized implementations over private structures.

1. `Vector` instance values exported from `src/Zafu/Collection/Vector.bosatsu`.
2. `Chain` instance values exported from `src/Zafu/Collection/Chain.bosatsu`.
3. `LazyList` instance values exported from `src/Zafu/Collection/LazyList.bosatsu`.
4. `Deque` instance values exported from `src/Zafu/Collection/Deque.bosatsu`.

This enables efficient `Traverse`/`Foldable` implementations that can use private internals when needed, while still exposing only abstraction dictionaries to callers.

## Naming and imports

Use minimal function names inside abstraction modules (`map`, `foldl`, `empty`, `combine`, etc.). Resolve collisions with explicit import aliasing:

1. `from Zafu/Abstract/Foldable import (foldl as foldl_Foldable)`
2. `from Zafu/Collection/Deque import (foldl as foldl_Deque)`

Do not force globally unique long names at definition sites.

## Implementation plan

### Phase 1: first-order core

1. Add `Eq`, `Ord`, `Hash`, `Show`, `Semigroup`, `Monoid` modules.
2. Add per-module law helper exports (`laws_Eq`, `laws_Ord`, etc.).
3. Add primitive instances in `Instances/Primitive`.

### Phase 2: higher-kinded core + composition

1. Add `Applicative`, `Monad`, `Alternative`, `Traverse`, `Foldable`.
2. Add `foldable_from_traverse` / `traverse_to_foldable` helpers.
3. Add `Compose` module and composition builders for `Foldable`, `Traverse`, `Applicative`.

### Phase 3: colocated instances

1. Export canonical abstraction dictionaries directly from each collection module.
2. Start with `Vector` and `Chain` for full higher-kinded coverage.
3. Add `LazyList` and `Deque` incrementally with law/property checks and performance review.

### Phase 4: adoption and validation

1. Add examples using explicit dictionary passing.
2. Keep existing collection APIs source-compatible.
3. Validate with `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh`.

## Acceptance criteria

1. Design doc is updated with this architecture.
2. All requested abstraction modules exist under `src/Zafu/Abstract/*`.
3. Abstraction constructors remain opaque (constructor syntax not exported).
4. `Ord` can be built from `cmp` and exposes derived operations via exported functions.
5. `Traverse` exposes `traverse_to_foldable` (or equivalent) to derive `Foldable`.
6. `Compose` type exists and has composition builders for `Foldable`, `Traverse`, and `Applicative`.
7. Law helper exports exist in each typeclass module (not only in a single central public laws package).
8. Canonical instances for collection types are exported from their collection modules.
9. Primitive/base instances exist for common primitive types.
10. Naming guidance uses short names plus aliasing on collisions.
11. Existing collection APIs remain source-compatible.
12. `./bosatsu lib check` passes.
13. `./bosatsu lib test` passes.
14. `scripts/test.sh` passes before merge.

## Risks and mitigations

1. Risk: higher-kinded signatures in Bosatsu may require iteration.
- Mitigation: validate with an early compile spike in `Vector`.

2. Risk: dictionary dispatch overhead in hot paths.
- Mitigation: support specialized constructors and colocated optimized instances.

3. Risk: law regressions for lazy structures and hashing coherence.
- Mitigation: per-module law helpers plus property tests with supplied `Rand` generators.

4. Risk: name collisions across modules.
- Mitigation: standardize on short names and explicit `as` aliases at import sites.

## Rollout notes

1. Ship as additive API on `main`.
2. Use small phased PRs so type-system and law failures are isolated.
3. Land collection-local instance exports before broad generic refactors.
4. Defer deprecations until usage and performance are validated.

## Out of scope

1. Implicit instance search.
2. Prelude/re-export strategy.
3. Cross-repo ecosystem policy.
