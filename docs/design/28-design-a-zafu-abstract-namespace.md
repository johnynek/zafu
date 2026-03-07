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
  - src/Zafu/Abstract/Instances/Primitive.bosatsu
  - src/Zafu/Abstract/Instances/Vector.bosatsu
  - src/Zafu/Abstract/Instances/Chain.bosatsu
  - src/Zafu/Abstract/Instances/LazyList.bosatsu
  - src/Zafu/Abstract/Instances/Deque.bosatsu
  - src/Zafu/Abstract/Laws.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-07T21:36:05Z
---

# Design: Zafu/Abstract Namespace (Issue #28)

_Issue: #28 (https://github.com/johnynek/zafu/issues/28)_

## Summary

Defines an opaque, evolvable typeclass-dictionary architecture for Zafu under `Zafu/Abstract`, with phased implementation for first-order and higher-kinded abstractions, canonical instances, laws, risks, and rollout guidance.

# Design: `Zafu/Abstract` Namespace (Issue #28)

## Status
Proposed

## Context
Zafu currently exposes concrete collection APIs (`Vector`, `Chain`, `Deque`, `LazyList`) with explicit per-type helpers (`eq`, `cmp`, `foldl`, `map`, etc.). We do not yet have a common abstraction namespace for typeclass-style programming.

Issue #28 asks for a design that:
- Represents typeclasses as values (dictionary style, e.g., `Ord[a]` holds behavior for `a`).
- Supports both default derivation from minimal primitives and future specialization for performance.
- Preserves API evolution flexibility by keeping internals hidden (export `Ord`, not `Ord()`).
- Works for common abstractions: `Eq`, `Ord`, `Hash`, `Show`, `Semigroup`, `Monoid`, `Foldable`, `Traverse`, `Applicative`, `Alternative`, `Monad`.
- Enables generic loops/traversals without exposing collection internals.

## Goals
1. Define a stable `Zafu/Abstract/*` architecture for first-class typeclass dictionaries.
2. Keep representation opaque so internals can evolve without downstream breaks.
3. Provide minimal constructors plus derived operations for ergonomics.
4. Make higher-kinded abstractions (`Foldable`, `Traverse`, `Applicative`, `Alternative`, `Monad`) practical for existing Zafu collections.
5. Keep adoption incremental and non-breaking for current collection APIs.

## Non-goals
1. Rewriting all existing collection APIs in one PR.
2. Introducing implicit/global instance resolution.
3. Solving all syntax ergonomics (import naming collisions, prelude design) in the first iteration.

## Decision Summary
Adopt **opaque dictionary structs per abstraction**, with:
- **Minimal constructor(s)** from law-defining primitive operations.
- **Optional specialized constructor(s)** for optimized overrides.
- **Module-level accessor functions** (callers do not read fields directly).
- **Projection helpers** for hierarchy edges (e.g., `ord_to_eq`, `monoid_to_semigroup`, `monad_to_applicative`).

This combines the flexibility of “store full function set” with long-term compatibility from hidden internals.

## Namespace Layout
Proposed modules:

- `src/Zafu/Abstract/Eq.bosatsu`
- `src/Zafu/Abstract/Ord.bosatsu`
- `src/Zafu/Abstract/Hash.bosatsu`
- `src/Zafu/Abstract/Show.bosatsu`
- `src/Zafu/Abstract/Semigroup.bosatsu`
- `src/Zafu/Abstract/Monoid.bosatsu`
- `src/Zafu/Abstract/Foldable.bosatsu`
- `src/Zafu/Abstract/Traverse.bosatsu`
- `src/Zafu/Abstract/Applicative.bosatsu`
- `src/Zafu/Abstract/Alternative.bosatsu`
- `src/Zafu/Abstract/Monad.bosatsu`
- `src/Zafu/Abstract/Instances/*` (canonical instances)
- `src/Zafu/Abstract/Laws.bosatsu` (property-law helpers)

## Core API Shape
Pattern used by every abstraction module:
1. Opaque type export only (no constructor export).
2. One minimal constructor from primitives.
3. Optional specialized constructor for overrides.
4. Accessor/derived operations as plain functions.

Illustrative shape for `Ord`:

```bosatsu
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

# constructor remains private because Ord() is not exported
struct Ord[a](
  cmp_fn: (a, a) -> Comparison,
  lt_fn: (a, a) -> Bool,
  lteq_fn: (a, a) -> Bool,
  gt_fn: (a, a) -> Bool,
  gteq_fn: (a, a) -> Bool,
  min_fn: (a, a) -> a,
  max_fn: (a, a) -> a,
)
```

`ord_from_cmp` derives defaults for all secondary ops. `ord_specialized` allows opt-in replacement of selected ops while preserving a single opaque public type.

## Abstraction-by-Abstraction Design
Minimal primitives and key derived operations:

1. `Eq[a]`
- Primitive: `eq: (a, a) -> Bool`
- Derived: `neq`
- Constructor: `eq_from_fn`

2. `Ord[a]`
- Primitive: `cmp: (a, a) -> Comparison`
- Derived: `eq`, `lt`, `lteq`, `gt`, `gteq`, `min`, `max`
- Constructors: `ord_from_cmp`, `ord_specialized`
- Projection: `ord_to_eq`

3. `Hash[a]`
- Primitive: `hash: a -> Int`
- Required companion: `Eq[a]` for hash/eq coherence
- Constructor: `hash_from_fn(eq_inst, hash_fn)`

4. `Show[a]`
- Primitive: `show: a -> String`
- Constructor: `show_from_fn`

5. `Semigroup[a]`
- Primitive: `combine: (a, a) -> a`
- Constructor: `semigroup_from_combine`

6. `Monoid[a]`
- Primitive: `empty: a` plus semigroup combine
- Constructor: `monoid_from_parts(empty, combine)`
- Projection: `monoid_to_semigroup`

7. `Foldable[f]`
- Primitive: `foldl` and `foldr` (or one + derived counterpart)
- Derived: `to_list`, `size`, `all`, `any`, `fold_map`

8. `Applicative[f]`
- Primitive: `pure`, `ap`
- Derived: `map`, `map2`, `product_l`, `product_r`

9. `Monad[f]`
- Primitive: `pure`, `flat_map`
- Derived: `map`, `ap`
- Projection: `monad_to_applicative`

10. `Alternative[f]`
- Primitive: `applicative`, `empty`, `or_else`
- Derived: `some`, `many`
- Projection: `alternative_to_applicative`

11. `Traverse[t]`
- Primitive: `traverse`
- Derived: `sequence`, `map` via identity applicative
- Dependency: consumes `Applicative[g]` argument for effect `g`

## How This Supports Hidden Collection Internals
`Foldable`/`Traverse` instances for `Vector`, `Chain`, and `LazyList` can be built from already exported operations (`foldl_*`, `foldr_*`, `map_*`, constructors like `empty_*`, `prepend_*`, `append_*`) without exposing internal enum constructors.

Result: generic algorithms can operate on abstract capabilities instead of concrete internals, while each collection preserves private representation.

## Instance Strategy
Use dedicated instance modules under `src/Zafu/Abstract/Instances/` to avoid polluting collection modules and to centralize canonical dictionaries.

Initial canonical instances:
1. `Primitive.bosatsu`: `Int`, `Bool`, `String`, `Comparison` for `Eq`/`Ord`/`Show`/`Hash` as available.
2. `Vector.bosatsu`: `Eq`, `Ord`, `Show`, `Foldable`, `Traverse`, `Applicative`, `Monad` (where lawful and practical).
3. `Chain.bosatsu`: same profile as `Vector`.
4. `LazyList.bosatsu`: `Eq`, `Show`, `Foldable`, and `Traverse`/`Monad` if law checks pass with bounded semantics.
5. `Deque.bosatsu`: `Eq`, `Ord`, `Show`, `Foldable` first; add `Traverse`/`Monad` only after `map`/`flat_map` API exists and laws pass.

## Implementation Plan

### Phase 1: First-order abstractions
1. Add `Eq`, `Ord`, `Hash`, `Show`, `Semigroup`, `Monoid` modules.
2. Keep constructors opaque and provide constructor/accessor/projection functions.
3. Add basic primitive instances in `Instances/Primitive.bosatsu`.

### Phase 2: Higher-kinded abstractions
1. Add `Foldable`, `Applicative`, `Monad`, `Alternative`, `Traverse` modules.
2. Start with one “compile spike” instance (`Vector`) to validate type signatures and inference.
3. Add derived helper operations only after minimal constructors compile cleanly.

### Phase 3: Collection instances
1. Implement instance modules for `Vector`, `Chain`, `LazyList`, `Deque`.
2. Reuse existing exported collection operations; do not expose internal constructors.
3. Where collection API lacks needed primitive ops, add minimal helpers in collection module (e.g., `map` for `Deque`) behind normal API review.

### Phase 4: Laws and integration
1. Add `Zafu/Abstract/Laws.bosatsu` with reusable law test functions.
2. Validate core laws for each canonical instance (Eq reflexive/symmetric/transitive; Ord consistency; Monoid identity; Monad laws; Traverse naturality/composition/identity).
3. Add one or two generic examples that use only abstraction dictionaries (no concrete collection assumptions).

## Acceptance Criteria
1. `docs/design/28-design-a-zafu-abstract-namespace.md` is added with this architecture and plan.
2. New modules exist for all requested abstractions under `src/Zafu/Abstract/`.
3. All abstraction types are opaque to callers (constructors not exported).
4. `Ord` can be created from only `cmp` and supports `lt/lteq/gt/gteq/min/max` through exported functions.
5. Hierarchy projection helpers exist where applicable (`ord_to_eq`, `monoid_to_semigroup`, `monad_to_applicative`, `alternative_to_applicative`).
6. Canonical primitive instances compile and pass core laws.
7. Collection instances exist at least for `Vector` and `Chain` for `Foldable` + `Traverse`, and for `Vector` or `Chain` for `Applicative` + `Monad`.
8. Existing collection APIs remain source-compatible (no required call-site migration).
9. `./bosatsu lib check` and `./bosatsu lib test` pass after integration.

## Risks and Mitigations
1. Higher-kinded signature limitations in Bosatsu.
- Mitigation: run an early compile spike in `Applicative`/`Traverse` with `Vector`; adjust representation before broad rollout.

2. Dictionary overhead (extra closures / indirect calls).
- Mitigation: keep minimal primitive fields, precompute hot derived functions in constructors, and allow specialized constructors.

3. Instance incoherence (multiple conflicting dictionaries for same type).
- Mitigation: define canonical instances in `Zafu/Abstract/Instances/*`; document naming and import conventions.

4. Law regressions (especially `Hash` coherence and `Traverse` laws for lazy structures).
- Mitigation: centralized law test helpers and CI-enforced property tests.

5. API naming collisions in explicit imports.
- Mitigation: maintain module-scoped naming conventions and optionally provide suffixed aliases where collisions are common.

## Rollout Notes
1. Roll out as additive API on `main`; keep existing concrete helper functions intact.
2. Migrate selected internal/generic utilities to dictionary-based abstractions incrementally.
3. Defer any deprecations of old helpers until abstraction APIs are exercised by real users and performance-tested.
4. Prefer small PRs by phase to reduce review risk and isolate type-system issues.

## Out of Scope / Follow-ups
1. Implicit instance search or global coherence enforcement.
2. Full prelude design and wildcard re-export strategy.
3. Cross-package ecosystem alignment beyond this repository.
