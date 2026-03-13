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
generated_at: 2026-03-12T07:15:00Z
---

# Design: Add Zafu/Abstract/Traverse

_Issue: #114 (https://github.com/johnynek/zafu/issues/114)_

## Summary

Add `Zafu/Abstract/Traverse` inspired by Cats `Traverse`, with dictionary-style construction and explicit `Foldable` projection. After merging `origin/main`, this design now incorporates `Bosatsu/Eval` (core alpha 4.4.0) for stack-safe internal derivations where needed. The public Traverse surface still stays minimal, while specialization hooks preserve near hand-written performance.

## Status

Proposed

## Context

1. Zafu already uses dictionary-style abstractions (`Eq`, `Ord`, `Hash`, `Semigroup`, `Monoid`, `Foldable`, `Applicative`) with minimal and specialized constructors.
2. Issue #114 requests Cats-inspired Traverse, extension of Foldable, easy minimal implementation, and specialization for performance.
3. `origin/main` now includes a Bosatsu core alpha with `Bosatsu/Eval`, which changes stack-safety options from the original draft.
4. Zafu still has no public `State` abstraction, so Cats methods that directly depend on State remain a separate decision.
5. Existing collection modules already provide deterministic-order folds and constructors suitable for lawful Traverse instances.

## Goals

1. Add `Traverse[f]` with explicit projection to `Foldable[f]`.
2. Keep minimal implementation easy (`traverse` + `Foldable`).
3. Allow specialization for `map` and effect-only traversal performance.
4. Use `Bosatsu/Eval` where it materially improves stack safety for derived internals.
5. Keep effect order deterministic and coherent with projected Foldable order.

## Non-goals

1. Full Cats Traverse API parity in this issue (`flatTraverse`, indexed traverse variants, compose helpers).
2. Introducing a public `State` typeclass/module as a prerequisite.
3. Adding every Eval-related method from Cats immediately.
4. Defining Traverse for containers with unsettled traversal lawfulness in current design (`Heap`, `HashSet`, `HashMap`).

## Decision Summary

1. `Traverse[f]` stores `foldable_inst: Foldable[f]` and exposes `traverse_to_foldable`.
2. Minimal constructor: `traverse_from_traverse(traverse_fn, foldable_inst)`.
3. Specialized constructor: `traverse_specialized(traverse_fn, map_fn, traverse_void_fn, foldable_inst)`.
4. `sequence` and `sequence_void` remain derived wrappers.
5. Default `traverse_void` uses `Foldable.foldl` and applicative combinators to avoid constructing `f[b]`.
6. `Bosatsu/Eval` is used for internal stack-safe derivation paths where strict recursion would otherwise risk overflow.
7. Public API does not require public `State`; State-like helpers stay deferred.

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
2. `traverse_fn`: effectful traversal function (`f[a] -> (a -> g[b]) -> Applicative[g] -> g[f[b]]` shape).
3. `map_fn`: specialized map implementation (default derived from `traverse`).
4. `traverse_void_fn`: specialized effect-only traversal implementation.
5. `foldable_inst`: projected Foldable dictionary.

Core behavior:

1. `traverse(inst, fa, fn, app)` delegates to `traverse_fn`.
2. `sequence(inst, fga, app)` is `traverse(inst, fga, ga -> ga, app)`.
3. `map(inst, fa, fn)` delegates to `map_fn`.
4. `traverse_void(inst, fa, fn, app)` delegates to `traverse_void_fn`.
5. `sequence_void(inst, fga, app)` is `traverse_void(inst, fga, ga -> ga, app)`.
6. `traverse_to_foldable(inst)` returns `foldable_inst`.

Constructor behavior:

1. `traverse_specialized` stores all fields directly.
2. `traverse_from_traverse` derives:
   - `map_fn` via a private identity-applicative wrapper.
   - `traverse_void_fn` via projected `Foldable.foldl` + applicative combinators.
3. When derivation requires deferred recursion, internal implementation may use `Bosatsu/Eval` trampolining.

## Eval Scope Decision

### What changes after `Bosatsu/Eval` became available

1. The stack-safety section now explicitly allows Eval-backed internals for derived combinators.
2. Deep traversal defaults are no longer constrained to strict-only strategies.
3. We can avoid introducing ad hoc recursion/fuel workarounds in places where Eval is a better fit.

### Should we add Eval-related functions from Cats now

Decision for this issue:

1. Do not add a broad new public Eval-heavy Traverse surface yet.
2. Do use Eval internally where it strengthens stack safety.
3. Defer Cats-style additions that are State-centric (`mapAccumulate`, indexed traverse helpers) to a follow-up once State direction is settled.
4. Track Foldable-side Eval APIs (for example right-associated folds) as a separate follow-up because they belong primarily in Foldable, not Traverse.

## Stack-Safety Strategy

1. Prefer iterative traversal in concrete instances (left folds in deterministic order).
2. Keep `traverse_void` iterative by default and allocation-light.
3. Use `Bosatsu/Eval` for internal deferred recursion where required for stack safety.
4. Document that full stack safety still depends on the stack behavior of the provided applicative.

## Law and Test Design

`laws_Traverse` focuses on laws expressible with current abstractions.

Proposed checks:

1. `map` identity: `map(inst, fa, x -> x) == fa`.
2. `map` composition: `map(map(fa, f), g) == map(fa, x -> g(f(x)))`.
3. `sequence`/`traverse` coherence: `sequence(inst, map(inst, fa, f), app) == traverse(inst, fa, f, app)`.
4. `traverse_void` coherence: `traverse_void(inst, fa, f, app) == Applicative.void(app, traverse(inst, fa, f, app))`.
5. Foldable projection coherence: traversal log order (`Const[List[a], *]`) matches `to_List(traverse_to_foldable(inst), fa)`.

Testing guidance:

1. Add module-level Traverse tests with a local list instance.
2. Add deep-input traversal tests (for example, 100k elements) for baseline instances.
3. Add at least one deep-input test that exercises Eval-backed derivation path to prove stack safety improvement.

## Instance Plan

### In-scope for this issue

1. `List`: `traverse_List` in `src/Zafu/Collection/List.bosatsu`.
2. `Option`: `traverse_Option` in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
3. `Array`: `traverse_Array` in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
4. `Result[e]`: `traverse_Result` in `src/Zafu/Control/Result.bosatsu`.

### Likely follow-up in same implementation stream (if scope allows)

1. `Vector`: `traverse_Vector` in `src/Zafu/Collection/Vector.bosatsu`.
2. `Chain`: `traverse_Chain` in `src/Zafu/Collection/Chain.bosatsu`.
3. `LazyList`: `traverse_LazyList` in `src/Zafu/Collection/LazyList.bosatsu`.
4. `NonEmptyList`: `traverse_NonEmptyList` in `src/Zafu/Collection/NonEmptyList.bosatsu`.
5. `NonEmptyChain`: `traverse_NonEmptyChain` in `src/Zafu/Collection/NonEmptyChain.bosatsu`.
6. `Deque`: `traverse_Queue` in `src/Zafu/Collection/Deque.bosatsu`.

### Explicitly excluded in this issue

1. `Heap`.
2. `HashSet`.
3. `HashMap`.

## Implementation Plan

### Phase 1: Core typeclass module

1. Add `src/Zafu/Abstract/Traverse.bosatsu` with dictionary, constructors, and core helpers.
2. Implement derived defaults for `map` and `traverse_void`.
3. Add Eval-backed internal helper path for stack-safe deferred recursion.
4. Add `laws_Traverse` and baseline tests.

### Phase 2: Baseline instances and exports

1. Add `traverse_List`, `traverse_Option`, `traverse_Array`, and `traverse_Result`.
2. Export instance values from owning modules.
3. Add tests for order, law coherence, and deep-input stack safety.

### Phase 3: Extended deterministic collections

1. Add traverse instances for `Vector`, `Chain`, `LazyList`, `NonEmptyList`, `NonEmptyChain`, and `Deque`.
2. Prefer specialized constructors where internals can avoid avoidable conversions.

### Phase 4: Validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/114-design-a-traverse-typeclass.md` reflects this Eval-aware design.
2. `src/Zafu/Abstract/Traverse.bosatsu` exists with the API listed above.
3. `Traverse` projects to `Foldable` via `traverse_to_foldable`.
4. Minimal and specialized constructors both exist.
5. `sequence`, `map`, `traverse_void`, and `sequence_void` are available.
6. Design and implementation do not require a public State abstraction in this issue.
7. Eval usage is documented as internal stack-safety support, not broad public API expansion.
8. Baseline instances exist for `List`, `Option`, `Array`, and `Result[e]`.
9. Deep-input stack-safety tests pass, including at least one Eval-backed derivation path test.
10. `Heap`, `HashSet`, and `HashMap` are not given Traverse instances in this issue.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: Foldable projection order and traverse effect order diverge.
Mitigation: explicit coherence law plus per-instance order tests.

2. Risk: stack overflows in recursive default paths.
Mitigation: Eval-backed deferred recursion helpers and deep-input tests.

3. Risk: performance regressions from generic defaults.
Mitigation: specialization hooks and targeted optimized instances.

4. Risk: scope growth from adding too many Cats-inspired helpers at once.
Mitigation: keep public API tight in this issue and track deferred helpers separately.

## Rollout Notes

1. Land as additive API on top of merged `origin/main`.
2. Keep public Traverse surface minimal for first merge.
3. Use Eval internally now; decide public Eval/State-oriented helper surface in follow-up issues.
4. Expand deterministic collection coverage incrementally after baseline stabilizes.

## References

1. Cats Traverse source: https://github.com/typelevel/cats/blob/main/core/src/main/scala/cats/Traverse.scala
2. PR feedback comment introducing Eval context: https://github.com/johnynek/zafu/pull/117#issuecomment-4051219618
3. Issue #114: https://github.com/johnynek/zafu/issues/114
