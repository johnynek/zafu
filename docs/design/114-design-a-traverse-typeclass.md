---
issue: 114
priority: 3
touch_paths:
  - docs/design/114-design-a-traverse-typeclass.md
  - src/Zafu/Abstract/Traverse.bosatsu
  - src/Zafu/Collection/List.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Control/Result.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/NonEmptyList.bosatsu
  - src/Zafu/Collection/NonEmptyChain.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-11T21:22:39Z
---

# Design: Add Zafu/Abstract/Traverse (#114)

_Issue: #114 (https://github.com/johnynek/zafu/issues/114)_

## Summary

Full design doc content for issue #114 covering Traverse architecture, constructor strategy, Foldable projection, implementation phases, acceptance criteria, risks, and rollout notes.

---
issue: 114
priority: 2
touch_paths:
  - docs/design/114-design-a-traverse-typeclass.md
  - src/Zafu/Abstract/Traverse.bosatsu
  - src/Zafu/Collection/List.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Control/Result.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/NonEmptyList.bosatsu
  - src/Zafu/Collection/NonEmptyChain.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
depends_on:
  - 90
estimated_size: L
generated_at: 2026-03-11T21:30:00Z
---

# Design: Add Zafu/Abstract/Traverse

_Issue: #114 (https://github.com/johnynek/zafu/issues/114)_

## Summary

Add `Zafu/Abstract/Traverse` inspired by Cats `Traverse`, with dictionary-style design matching current Zafu abstractions. `Traverse` will explicitly carry a `Foldable` instance so callers can extract fold behavior directly, provide a minimal constructor (`traverse` + `Foldable`), and expose specialization hooks for `map` and effect-only traversal to recover near hand-written performance. The design avoids public dependency on `State` and avoids Eval-based APIs while remaining stack-safe for Zafu-provided instances.

## Status

Proposed

## Context

1. Zafu already has dictionary-style abstractions (`Eq`, `Hash`, `Ord`, `Semigroup`, `Monoid`, `Foldable`, `Applicative`) with minimal and specialized constructors.
2. Issue #114 requests Cats-inspired `Traverse` semantics and explicit extension of `Foldable` so `Foldable` can be projected from `Traverse`.
3. Zafu does not currently expose an `Eval` abstraction, so right-associated lazy folds are not available as a stack-safety mechanism.
4. Zafu currently has no public `State` abstraction; Cats-style `mapAccumulate` via `State` should not become a hard dependency for this issue.
5. Existing collection modules already provide stack-safe iterative folds and constructors that can back lawful traversal instances.

## Goals

1. Add `Traverse[f]` with an explicit foldable projection (`traverse_to_foldable`).
2. Provide an easy minimal implementation path requiring only `traverse` and `Foldable`.
3. Provide specialization points so performance-sensitive types can avoid default overhead.
4. Keep effect order deterministic and aligned with `Foldable` iteration order.
5. Make stack-safety guarantees explicit in API docs and tests, without requiring Eval.

## Non-goals

1. Full API parity with Cats `Traverse` in this issue (`mapAccumulate`, index methods, composition helpers).
2. Introducing a public `State` typeclass/module as a prerequisite for `Traverse`.
3. Introducing Eval-like lazy fold APIs.
4. Defining `Traverse` for structures where traversal semantics are not clearly lawful or deterministic in current design (`Heap`, `HashSet`, `HashMap`).

## Decision Summary

1. `Traverse[f]` will store a `Foldable[f]` dictionary directly, following the extension/projection pattern used by existing abstractions.
2. `Traverse` minimal constructor is `traverse_from_traverse(traverse_fn, foldable_inst)`.
3. `Traverse` specialized constructor is `traverse_specialized(traverse_fn, map_fn, traverse_void_fn, foldable_inst)`.
4. `sequence` and `sequence_void` are derived wrappers and are not stored as separate fields.
5. Default `traverse_void` is derived via `Foldable.foldl` and `Applicative.product_right` to avoid building `f[b]` when callers only need effects.
6. No public `State` dependency is introduced in v1.
7. Stack safety is achieved by requiring iterative instance implementations and by avoiding recursive default combinators in core paths.

## API Design

### Module: `src/Zafu/Abstract/Traverse.bosatsu`

Proposed exports:

1. `Traverse`
2. `traverse_from_traverse`
3. `traverse_specialized`
4. `traverse`
5. `sequence`
6. `map`
7. `traverse_void`
8. `sequence_void`
9. `traverse_to_foldable`
10. `laws_Traverse`

Proposed dictionary shape:

1. `struct Traverse[f: * -> *](traverse_fn, map_fn, traverse_void_fn, foldable_inst)`
2. `traverse_fn`: higher-kinded traversal function equivalent to Cats `traverse`.
3. `map_fn`: specialized mapping path (defaults to `traverse` with an internal identity applicative wrapper).
4. `traverse_void_fn`: specialized effect-only traversal path.
5. `foldable_inst`: projected by `traverse_to_foldable`.

Function behavior:

1. `traverse(inst, fa, fn, app)` delegates to `traverse_fn`.
2. `sequence(inst, fga, app)` is `traverse(inst, fga, ga -> ga, app)`.
3. `map(inst, fa, fn)` delegates to `map_fn`.
4. `traverse_void(inst, fa, fn, app)` delegates to `traverse_void_fn`.
5. `sequence_void(inst, fga, app)` is `traverse_void(inst, fga, ga -> ga, app)`.
6. `traverse_to_foldable(inst)` returns stored `foldable_inst`.

Constructor behavior:

1. `traverse_specialized` stores all fields directly.
2. `traverse_from_traverse` derives:
   - `map_fn` via a private identity-wrapper applicative used only inside `Traverse`.
   - `traverse_void_fn` via `Foldable.foldl` + `Applicative.product_right` + `Applicative.void`.
3. Derived defaults are lawful but may allocate more than specialized implementations; specialized constructor exists for optimization.

## Stack-Safety Strategy

1. No `Eval`-based APIs are introduced.
2. No recursive default implementation of `traverse` is provided; each instance must supply traversal logic.
3. For list-like structures, recommended implementation is iterative left fold over source order, accumulating effectful reversed results and reversing once at the end.
4. `traverse_void` default is iterative and avoids constructing `f[b]`.
5. Stack safety guarantees are documented as:
   - Zafu-provided traverse instances must be stack-safe for large finite inputs when used with stack-safe applicatives.
   - Non-stack-safe applicatives remain a caller responsibility.

## State Dependency Decision

1. `Traverse` v1 does not depend on a public `State` abstraction.
2. Cats-inspired stateful helpers (`mapAccumulate`, `zipWithIndex`, indexed traverse) are deferred.
3. If needed later, stateful helpers can be added with private internal wrappers in `Traverse` without exposing a new public dependency.

## Law and Test Design

`laws_Traverse` should focus on invariants that are expressible with current Zafu abstractions and test style.

Proposed checks:

1. `map` identity: `map(inst, fa, x -> x) == fa`.
2. `map` composition: `map(map(fa, f), g) == map(fa, x -> g(f(x)))`.
3. `sequence`/`traverse` coherence: `sequence(inst, map(inst, fa, f), app) == traverse(inst, fa, f, app)`.
4. `traverse_void` coherence: `traverse_void(inst, fa, f, app) == Applicative.void(app, traverse(inst, fa, f, app))`.
5. Foldable projection coherence: traversal order observed via a `Const[List[a], *]` applicative matches `to_List(traverse_to_foldable(inst), fa)`.

Testing guidance:

1. Add module-level `Traverse` tests using a local list instance.
2. Add regression tests for deep inputs (for example, 100k elements) for `traverse` and `traverse_void` using `Option` and `Result` applicatives.
3. Add cross-check tests that projected `Foldable` behavior matches dedicated foldable instance behavior.

## Instance Plan

### In-scope for this issue

1. `List`: add `traverse_List` in `src/Zafu/Collection/List.bosatsu`.
2. `Option`: add `traverse_Option` in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
3. `Array`: add `traverse_Array` in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
4. `Result[e]`: add `traverse_Result` in `src/Zafu/Control/Result.bosatsu`.

### Likely follow-up in same implementation stream (if scope allows)

1. `Vector`: `traverse_Vector` in `src/Zafu/Collection/Vector.bosatsu`.
2. `Chain`: `traverse_Chain` in `src/Zafu/Collection/Chain.bosatsu`.
3. `LazyList`: `traverse_LazyList` in `src/Zafu/Collection/LazyList.bosatsu`.
4. `NonEmptyList`: `traverse_NonEmptyList` in `src/Zafu/Collection/NonEmptyList.bosatsu`.
5. `NonEmptyChain`: `traverse_NonEmptyChain` in `src/Zafu/Collection/NonEmptyChain.bosatsu`.
6. `Deque`: `traverse_Queue` in `src/Zafu/Collection/Deque.bosatsu`.

### Explicitly excluded in this issue

1. `Heap`: no lawful/general `Traverse` given ordering constraints and lack of value-level `map` semantics.
2. `HashSet` and `HashMap`: traversal order is not deterministic enough for this issue's law expectations.

## Implementation Plan

### Phase 1: Core typeclass module

1. Add `src/Zafu/Abstract/Traverse.bosatsu` with struct, constructors, accessors, and derived helpers.
2. Implement private identity-wrapper helper for default `map` derivation.
3. Implement default `traverse_void` from projected `Foldable` + `Applicative` combinators.
4. Add `laws_Traverse` and baseline tests.

### Phase 2: Baseline instances and exports

1. Add `traverse_List` to `src/Zafu/Collection/List.bosatsu`.
2. Add `traverse_Option` and `traverse_Array` to `src/Zafu/Abstract/Instances/Predef.bosatsu`.
3. Add `traverse_Result` to `src/Zafu/Control/Result.bosatsu`.
4. Export new instance values from the corresponding modules.

### Phase 3: Extended deterministic collections

1. Add traverse instances for `Vector`, `Chain`, `LazyList`, `NonEmptyList`, `NonEmptyChain`, and `Deque`.
2. Prefer specialized constructor where module internals can avoid avoidable intermediate conversions.
3. Validate traversal order and stack safety per module with existing property-test style.

### Phase 4: Validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/114-design-a-traverse-typeclass.md` is added with this architecture.
2. `src/Zafu/Abstract/Traverse.bosatsu` exists and exports the API listed in this doc.
3. `Traverse` carries a `Foldable` dictionary and `traverse_to_foldable` projects it.
4. A minimal constructor (`traverse_from_traverse`) and specialized constructor (`traverse_specialized`) both exist.
5. `sequence`, `map`, `traverse_void`, and `sequence_void` are available from `Traverse`.
6. Core implementation introduces no public `State` dependency and no Eval-based API.
7. `laws_Traverse` checks map coherence, sequence/traverse coherence, traverse_void coherence, and foldable projection coherence.
8. Baseline instances exist for `List`, `Option`, `Array`, and `Result[e]`.
9. Deep-input stack-safety tests for baseline instances are present and pass.
10. `Heap`, `HashSet`, and `HashMap` do not receive `Traverse` instances in this issue.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: projected `Foldable` and `traverse` can disagree on element order.
Mitigation: explicit coherence law and per-instance tests comparing traversal log order with `Foldable.to_List`.

2. Risk: stack overflow from recursive instance implementations.
Mitigation: require iterative implementation patterns and deep-input tests for each baseline instance.

3. Risk: default derivations are correct but slower than hand-tuned implementations.
Mitigation: keep specialization hooks (`map_fn`, `traverse_void_fn`) and use them in performance-sensitive modules.

4. Risk: scope grows if all collection instances are attempted in one pass.
Mitigation: ship core + baseline instances first, then add extended deterministic collections incrementally.

5. Risk: users expect Cats-complete Traverse API immediately.
Mitigation: document deferred APIs (`mapAccumulate`/indexed traversals/composition helpers) and keep follow-up issues explicit.

## Rollout Notes

1. Land as additive API on `main`; no migration required for existing `Foldable`/`Applicative` users.
2. Encourage new code to require `Traverse` only when effectful traversal is needed; otherwise keep `Foldable` constraints.
3. Introduce extended collection instances only after baseline performance and stack-safety checks are green.
4. Track deferred indexed/stateful helpers in a follow-up issue once Traverse core stabilizes.

## References

1. Cats Traverse source (primary inspiration): https://github.com/typelevel/cats/blob/main/core/src/main/scala/cats/Traverse.scala
2. Issue #114: https://github.com/johnynek/zafu/issues/114
3. Iterator pattern paper referenced by Cats docs: https://www.cs.ox.ac.uk/jeremy.gibbons/publications/iterator.pdf
