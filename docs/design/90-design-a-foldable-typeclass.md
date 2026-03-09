---
issue: 90
priority: 2
touch_paths:
  - docs/design/90-design-a-foldable-typeclass.md
  - src/Zafu/Control/IterState.bosatsu
  - src/Zafu/Abstract/Foldable.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Collection/List.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/Heap.bosatsu
  - src/Zafu/Collection/NonEmptyList.bosatsu
  - src/Zafu/Collection/NonEmptyChain.bosatsu
depends_on:
  - 28
  - 73
estimated_size: L
generated_at: 2026-03-09T22:25:00Z
---

# Design: Add Zafu/Abstract/Foldable

_Issue: #90 (https://github.com/johnynek/zafu/issues/90)_

## Summary

Add `Zafu/Abstract/Foldable` in the same dictionary style as existing abstract modules, inspired by Cats `Foldable` but without Eval-based APIs. Add explicit short-circuiting support through a new `IterState` control type and `fold_iter`, place deterministic-order instances in collection modules, and add `foldable_Array` in `Predef`.

Reference inspiration: https://github.com/typelevel/cats/blob/main/core/src/main/scala/cats/Foldable.scala

## Status

Proposed

## Context

1. Zafu has dictionary-style abstractions (`Eq`, `Ord`, `Hash`, `Semigroup`, `Monoid`) and matching `laws_*` helpers.
2. Issue #90 asks for a Foldable design inspired by Cats and explicitly says no Eval-related methods.
3. Existing collection modules already expose concrete folds that can back Foldable instances.
4. Short-circuiting currently requires ad hoc loops; a reusable control type gives a total and explicit alternative to Eval.
5. `Array` is not defined in `src/Zafu/Collection`, so its instance belongs in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
6. `HashSet` and `HashMap` traversal order is not deterministic enough for this Foldable scope.

## Goals

1. Add a complete non-Eval Foldable API with full function signatures.
2. Add explicit short-circuit fold support via `fold_iter`.
3. Keep style and naming consistent with current `Zafu/Abstract` modules.
4. Place instances in each deterministic-order collection module plus `Array` in `Predef`.
5. Define acceptance criteria, rollout plan, and risks clearly enough to implement directly.

## Non-goals

1. Eval-based right folds and derived Eval APIs.
2. Effectful Foldable APIs requiring not-yet-implemented abstractions (`Applicative`, `Monad`, `Traverse`, `Alternative`).
3. Foldable instances for nondeterministic-order collections (`HashSet`, `HashMap`) in this issue.
4. Refactoring existing concrete fold APIs out of collection modules.

## Decision Summary

1. Introduce `Zafu/Control/IterState` for explicit early termination and reuse in future abstractions.
2. Add `fold_iter` to `Foldable`; use it to implement short-circuiting helpers (`exists`, `for_all`, `find`, `collect_first_some`, etc.).
3. Keep `foldl` and strict `foldr` in Foldable for compatibility with existing fold usage and Cats-inspired shape.
4. Offer constructor tiers (minimal and specialized) like current abstract modules.
5. Implement deterministic-order collection instances only: `List`, `Vector`, `Chain`, `Deque`, `LazyList`, `Heap`, `NonEmptyList`, `NonEmptyChain`, plus `Array` in `Predef`.

## API Design

### Module: `Zafu/Control/IterState`

Proposed shape:

1. `enum IterState[done: +*, cont: +*]: Done(done: done), Continue(cont: cont)`

Proposed helpers:

1. `done(value: d) -> IterState[d, c]`
2. `continue(value: c) -> IterState[d, c]`
3. `map_continue(state: IterState[d, c], fn: c -> e) -> IterState[d, e]`
4. `map_done(state: IterState[d, c], fn: d -> e) -> IterState[e, c]`

### Module: `Zafu/Abstract/Foldable`

Proposed dictionary shape:

1. `struct Foldable[f: * -> *](foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b, foldr_fn: forall a, b. (f[a], b, (a, b) -> b) -> b, fold_iter_fn: forall a, b. (f[a], b, (b, a) -> IterState[b, b]) -> b, is_empty_fn: forall a. f[a] -> Bool, size_fn: forall a. f[a] -> Int, to_List_fn: forall a. f[a] -> List[a])`

Complete proposed function list (full signatures):

1. `Foldable`
2. `foldable_from_fold_iter(fold_iter_fn: forall a, b. (f[a], b, (b, a) -> IterState[b, b]) -> b) -> Foldable[f]`
3. `foldable_from_foldl(foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b) -> Foldable[f]`
4. `foldable_from_folds(foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b, foldr_fn: forall a, b. (f[a], b, (a, b) -> b) -> b) -> Foldable[f]`
5. `foldable_specialized(foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b, foldr_fn: forall a, b. (f[a], b, (a, b) -> b) -> b, fold_iter_fn: forall a, b. (f[a], b, (b, a) -> IterState[b, b]) -> b, is_empty_fn: forall a. f[a] -> Bool, size_fn: forall a. f[a] -> Int, to_List_fn: forall a. f[a] -> List[a]) -> Foldable[f]`
6. `foldl(inst: Foldable[f], fa: f[a], init: b, fn: (b, a) -> b) -> b`
7. `foldr(inst: Foldable[f], fa: f[a], init: b, fn: (a, b) -> b) -> b`
8. `fold_iter(inst: Foldable[f], fa: f[a], init: b, fn: (b, a) -> IterState[b, b]) -> b`
9. `is_empty(inst: Foldable[f], fa: f[a]) -> Bool`
10. `non_empty(inst: Foldable[f], fa: f[a]) -> Bool`
11. `size(inst: Foldable[f], fa: f[a]) -> Int`
12. `to_List(inst: Foldable[f], fa: f[a]) -> List[a]`
13. `fold(inst: Foldable[f], fa: f[a], monoid: Monoid[a]) -> a`
14. `combine_all(inst: Foldable[f], fa: f[a], monoid: Monoid[a]) -> a`
15. `combine_all_option(inst: Foldable[f], fa: f[a], semigroup: Semigroup[a]) -> Option[a]`
16. `fold_map(inst: Foldable[f], fa: f[a], fn: a -> b, monoid: Monoid[b]) -> b`
17. `fold_map_option(inst: Foldable[f], fa: f[a], fn: a -> b, semigroup: Semigroup[b]) -> Option[b]`
18. `reduce_left_to_option(inst: Foldable[f], fa: f[a], first: a -> b, combine: (b, a) -> b) -> Option[b]`
19. `reduce_right_to_option(inst: Foldable[f], fa: f[a], first: a -> b, combine: (a, b) -> b) -> Option[b]`
20. `reduce_left_option(inst: Foldable[f], fa: f[a], combine: (a, a) -> a) -> Option[a]`
21. `reduce_right_option(inst: Foldable[f], fa: f[a], combine: (a, a) -> a) -> Option[a]`
22. `find(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Option[a]`
23. `exists(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Bool`
24. `for_all(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Bool`
25. `any(inst: Foldable[f], fa: f[Bool]) -> Bool`
26. `all(inst: Foldable[f], fa: f[Bool]) -> Bool`
27. `contains(inst: Foldable[f], eq_inst: Eq[a], fa: f[a], target: a) -> Bool`
28. `count(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Int`
29. `get(inst: Foldable[f], fa: f[a], idx: Int) -> Option[a]`
30. `collect_first_some(inst: Foldable[f], fa: f[a], fn: a -> Option[b]) -> Option[b]`
31. `collect_fold_some(inst: Foldable[f], fa: f[a], fn: a -> Option[b], monoid: Monoid[b]) -> b`
32. `minimum_option(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> Option[a]`
33. `maximum_option(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> Option[a]`
34. `minimum_by_option(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> Option[a]`
35. `maximum_by_option(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> Option[a]`
36. `minimum_list(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> List[a]`
37. `maximum_list(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> List[a]`
38. `minimum_by_list(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> List[a]`
39. `maximum_by_list(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> List[a]`
40. `intercalate(inst: Foldable[f], fa: f[a], middle: a, monoid: Monoid[a]) -> a`
41. `filter_to_List(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> List[a]`
42. `take_while_to_List(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> List[a]`
43. `drop_while_to_List(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> List[a]`
44. `laws_Foldable(inst: Foldable[f], eq_item: Eq[a], fa: f[a]) -> Test`

Constructor behavior:

1. `foldable_from_fold_iter` derives `foldl`, `foldr`, `to_List`, `is_empty`, and `size`.
2. `foldable_from_foldl` derives `fold_iter` as a never-short-circuit fold (`Continue(...)`) and derives the rest from `foldl`.
3. `foldable_from_folds` derives `fold_iter` from `foldl` and derives structural helpers.
4. `foldable_specialized` allows efficient native short-circuit loops and O(1) metadata access.

Method notes:

1. `exists`, `for_all`, `find`, `collect_first_some`, and `get` should be implemented via `fold_iter` to short-circuit.
2. `foldr` remains strict (non-Eval) and does not promise lazy right-associative short-circuit semantics.
3. Eval-based and effectful Foldable methods remain deferred.

## Law Design

`laws_Foldable` checks these invariants for sample `fa`:

1. `size(inst, fa)` equals length of `to_List(inst, fa)`.
2. `is_empty(inst, fa)` is equivalent to `size(inst, fa).eq_Int(0)`.
3. `non_empty(inst, fa)` is equivalent to logical negation of `is_empty(inst, fa)`.
4. `foldl(inst, fa, [], (acc, a) -> [a, *acc]).reverse()` equals `to_List(inst, fa)`.
5. `foldr(inst, fa, [], (a, acc) -> [a, *acc])` equals `to_List(inst, fa)`.
6. `fold_iter(inst, fa, 0, (count, _) -> Done(count.add(1)) if count.eq_Int(0) else Continue(count.add(1)))` stops after first element.
7. `reduce_left_option` and `reduce_right_option` agree with list-model reductions on `to_List(inst, fa)`.

## Instance Placement Plan

Collection-local instance placement:

1. `src/Zafu/Collection/List.bosatsu`: `foldable_List: Foldable[List]`.
2. `src/Zafu/Collection/Vector.bosatsu`: `foldable_Vector: Foldable[Vector]`.
3. `src/Zafu/Collection/Chain.bosatsu`: `foldable_Chain: Foldable[Chain]`.
4. `src/Zafu/Collection/Deque.bosatsu`: `foldable_Queue: Foldable[Queue]`.
5. `src/Zafu/Collection/LazyList.bosatsu`: `foldable_LazyList: Foldable[LazyList]`.
6. `src/Zafu/Collection/Heap.bosatsu`: `foldable_Heap: Foldable[Heap]`.
7. `src/Zafu/Collection/NonEmptyList.bosatsu`: `foldable_NonEmptyList: Foldable[NonEmptyList]`.
8. `src/Zafu/Collection/NonEmptyChain.bosatsu`: `foldable_NonEmptyChain: Foldable[NonEmptyChain]`.
9. `src/Zafu/Abstract/Instances/Predef.bosatsu`: `foldable_Array: Foldable[Array]`.

Placement decisions:

1. `HashSet` and `HashMap` are intentionally excluded from Foldable in this issue because traversal order is not deterministic.
2. Prefer `foldable_specialized` where modules already have native folds and cached size.
3. Use constructor-derived helpers where only one fold direction exists.

## Implementation Plan

### Phase 1: Add IterState and Foldable core

1. Add `src/Zafu/Control/IterState.bosatsu`.
2. Add `src/Zafu/Abstract/Foldable.bosatsu`.
3. Implement dictionary shape, constructors, and all exported functions listed above.
4. Implement short-circuiting helpers in terms of `fold_iter`.
5. Add `laws_Foldable` and unit tests.

### Phase 2: Add Predef Array instance

1. Update `src/Zafu/Abstract/Instances/Predef.bosatsu` imports for `Array` folding helpers.
2. Add and export `foldable_Array`.
3. Add instance tests that cover `foldl`, `fold_iter` short-circuit, `to_List`, and `size`.

### Phase 3: Add collection instances

1. Add Foldable imports and `foldable_*` exports in each deterministic-order collection module listed in touch paths.
2. Use native loops when available so `fold_iter` can short-circuit efficiently.
3. Keep existing concrete APIs unchanged (`foldl`, `foldr`, etc.).

### Phase 4: Validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/90-design-a-foldable-typeclass.md` reflects this design and complete signature list.
2. `src/Zafu/Control/IterState.bosatsu` exists with `IterState` and helper constructors.
3. `src/Zafu/Abstract/Foldable.bosatsu` exists and exports every function in the “Complete proposed function list”.
4. No Eval-based methods are included in this Foldable issue.
5. `fold_iter` exists and is used for short-circuiting helpers.
6. `laws_Foldable` validates ordering, structural helpers, and short-circuit behavior.
7. `foldable_Array` exists in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
8. `foldable_List` exists in `src/Zafu/Collection/List.bosatsu`.
9. `foldable_Vector` exists in `src/Zafu/Collection/Vector.bosatsu`.
10. `foldable_Chain` exists in `src/Zafu/Collection/Chain.bosatsu`.
11. `foldable_Queue` exists in `src/Zafu/Collection/Deque.bosatsu`.
12. `foldable_LazyList` exists in `src/Zafu/Collection/LazyList.bosatsu`.
13. `foldable_Heap` exists in `src/Zafu/Collection/Heap.bosatsu`.
14. `foldable_NonEmptyList` exists in `src/Zafu/Collection/NonEmptyList.bosatsu`.
15. `foldable_NonEmptyChain` exists in `src/Zafu/Collection/NonEmptyChain.bosatsu`.
16. This issue does not add Foldable instances for `HashSet` or `HashMap`.
17. `./bosatsu lib check` passes.
18. `./bosatsu lib test` passes.
19. `scripts/test.sh` passes before merge.

## Risks and Mitigations

1. Risk: adding `IterState` expands scope beyond Foldable.
   Mitigation: keep `IterState` minimal and focused on explicit control flow.

2. Risk: derived strict `foldr` can allocate intermediate structures and regress performance.
   Mitigation: prefer `foldable_specialized` in performance-sensitive modules.

3. Risk: short-circuit semantics could diverge across instances.
   Mitigation: enforce via `laws_Foldable` tests that exercise early termination.

4. Risk: naming collisions (`foldl`, `foldr`) with collection modules.
   Mitigation: keep alias import style (`foldl as foldl_Foldable`) in examples and usage.

## Rollout Notes

1. This is additive and does not remove existing concrete fold APIs.
2. Land `IterState` and Foldable core first, then `Array`, then collection instances.
3. Keep instance symbols explicit (`foldable_*`) and colocated with each data type module.
4. Defer `HashSet`/`HashMap` Foldable to a future design only if deterministic traversal semantics are introduced.
5. Defer effectful Foldable APIs until higher-kinded abstractions are in place.
