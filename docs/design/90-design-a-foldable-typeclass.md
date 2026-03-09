---
issue: 90
priority: 3
touch_paths:
  - docs/design/90-design-a-foldable-typeclass.md
  - src/Zafu/Abstract/Foldable.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Collection/List.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/Heap.bosatsu
  - src/Zafu/Collection/HashSet.bosatsu
  - src/Zafu/Collection/HashMap.bosatsu
  - src/Zafu/Collection/NonEmptyList.bosatsu
  - src/Zafu/Collection/NonEmptyChain.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-09T20:36:26Z
---

# Design: Add Zafu/Abstract/Foldable

_Issue: #90 (https://github.com/johnynek/zafu/issues/90)_

## Summary

Full design doc content for issue #90 proposing a Cats-inspired (non-Eval) Foldable typeclass, complete exported API signatures, per-module instance placement (all collection modules plus Array in Predef), phased implementation plan, acceptance criteria, risks, and rollout notes.

---
issue: 90
priority: 2
touch_paths:
  - docs/design/90-design-a-foldable-typeclass.md
  - src/Zafu/Abstract/Foldable.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Collection/List.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
  - src/Zafu/Collection/Deque.bosatsu
  - src/Zafu/Collection/LazyList.bosatsu
  - src/Zafu/Collection/Heap.bosatsu
  - src/Zafu/Collection/HashSet.bosatsu
  - src/Zafu/Collection/HashMap.bosatsu
  - src/Zafu/Collection/NonEmptyList.bosatsu
  - src/Zafu/Collection/NonEmptyChain.bosatsu
depends_on:
  - 28
  - 73
estimated_size: L
generated_at: 2026-03-09T22:00:00Z
---

# Design: Add Zafu/Abstract/Foldable

_Issue: #90 (https://github.com/johnynek/zafu/issues/90)_

## Summary

Add `Zafu/Abstract/Foldable` in the same dictionary style as existing `Eq`/`Ord`/`Hash`/`Semigroup`/`Monoid`, inspired by Cats `Foldable` but intentionally excluding Eval-based APIs. Define a complete non-Eval Foldable function set with full type signatures, add `foldable_Array` in `Predef`, and colocate collection instances in each collection module.

Reference inspiration: https://github.com/typelevel/cats/blob/main/core/src/main/scala/cats/Foldable.scala

## Status

Proposed

## Context

1. Zafu currently has first-order abstract typeclasses (`Eq`, `Ord`, `Hash`, `Semigroup`, `Monoid`) with explicit dictionaries and law helpers.
2. `Foldable` is planned in the abstract namespace but is not implemented yet.
3. Issue #90 asks for Cats-inspired Foldable, with an explicit exclusion: no Eval-related methods.
4. Collection modules already expose concrete fold operations (`foldl`, and in many modules `foldr`) that can back per-module Foldable instances.
5. `Array` is not defined in `src/Zafu/Collection`, so its canonical Foldable instance should live in `src/Zafu/Abstract/Instances/Predef.bosatsu`.

## Goals

1. Add `src/Zafu/Abstract/Foldable.bosatsu` with a complete, documented non-Eval API.
2. Keep naming and constructor style consistent with existing abstract modules.
3. Provide a complete list of Foldable functions with full type signatures.
4. Define concrete instance placement for all collection modules and `Array`.
5. Include law checking and implementation guidance that keeps behavior predictable and stack-safe.

## Non-goals

1. Adding Eval or lazy-right-fold APIs (`foldRight` in Eval style, `foldRightDefer`, etc.).
2. Adding effectful Foldable helpers that depend on not-yet-implemented abstractions (`Applicative`, `Monad`, `Alternative`, `Traverse`) in this issue.
3. Introducing `UnorderedFoldable` in this issue.
4. Refactoring existing collection APIs away from their current direct `foldl`/`foldr` exports.

## Decision Summary

1. `Foldable` will be strict/non-Eval and expose both `foldl` and `foldr` in direct style.
2. The module will provide constructor tiers similar to `Semigroup`:
   1. A minimal constructor from `foldl`.
   2. A constructor from both folds.
   3. A specialized constructor that also accepts optimized `is_empty`, `size`, and `to_List`.
3. Derived helpers (search/reduce/monoidal/list-conversion/order helpers) are defined in the Foldable module, not re-implemented in each instance module.
4. Collection instances are colocated with each collection module; `Array` instance is in `Predef`.
5. `HashMap` Foldable will fold values (`v`) for `HashMap[k, v]`, consistent with Cats `Map` Foldable behavior.

## API Design

### Module: `Zafu/Abstract/Foldable`

Proposed dictionary shape:

1. `struct Foldable[f: * -> *](foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b, foldr_fn: forall a, b. (f[a], b, (a, b) -> b) -> b, is_empty_fn: forall a. f[a] -> Bool, size_fn: forall a. f[a] -> Int, to_List_fn: forall a. f[a] -> List[a])`

Complete proposed function list (full signatures):

1. `Foldable`
2. `foldable_from_foldl(foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b) -> Foldable[f]`
3. `foldable_from_folds(foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b, foldr_fn: forall a, b. (f[a], b, (a, b) -> b) -> b) -> Foldable[f]`
4. `foldable_specialized(foldl_fn: forall a, b. (f[a], b, (b, a) -> b) -> b, foldr_fn: forall a, b. (f[a], b, (a, b) -> b) -> b, is_empty_fn: forall a. f[a] -> Bool, size_fn: forall a. f[a] -> Int, to_List_fn: forall a. f[a] -> List[a]) -> Foldable[f]`
5. `foldl(inst: Foldable[f], fa: f[a], init: b, fn: (b, a) -> b) -> b`
6. `foldr(inst: Foldable[f], fa: f[a], init: b, fn: (a, b) -> b) -> b`
7. `is_empty(inst: Foldable[f], fa: f[a]) -> Bool`
8. `non_empty(inst: Foldable[f], fa: f[a]) -> Bool`
9. `size(inst: Foldable[f], fa: f[a]) -> Int`
10. `to_List(inst: Foldable[f], fa: f[a]) -> List[a]`
11. `fold(inst: Foldable[f], fa: f[a], monoid: Monoid[a]) -> a`
12. `combine_all(inst: Foldable[f], fa: f[a], monoid: Monoid[a]) -> a`
13. `combine_all_option(inst: Foldable[f], fa: f[a], semigroup: Semigroup[a]) -> Option[a]`
14. `fold_map(inst: Foldable[f], fa: f[a], fn: a -> b, monoid: Monoid[b]) -> b`
15. `fold_map_option(inst: Foldable[f], fa: f[a], fn: a -> b, semigroup: Semigroup[b]) -> Option[b]`
16. `reduce_left_to_option(inst: Foldable[f], fa: f[a], first: a -> b, combine: (b, a) -> b) -> Option[b]`
17. `reduce_right_to_option(inst: Foldable[f], fa: f[a], first: a -> b, combine: (a, b) -> b) -> Option[b]`
18. `reduce_left_option(inst: Foldable[f], fa: f[a], combine: (a, a) -> a) -> Option[a]`
19. `reduce_right_option(inst: Foldable[f], fa: f[a], combine: (a, a) -> a) -> Option[a]`
20. `find(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Option[a]`
21. `exists(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Bool`
22. `for_all(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Bool`
23. `any(inst: Foldable[f], fa: f[Bool]) -> Bool`
24. `all(inst: Foldable[f], fa: f[Bool]) -> Bool`
25. `contains(inst: Foldable[f], eq_inst: Eq[a], fa: f[a], target: a) -> Bool`
26. `count(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> Int`
27. `get(inst: Foldable[f], fa: f[a], idx: Int) -> Option[a]`
28. `collect_first_some(inst: Foldable[f], fa: f[a], fn: a -> Option[b]) -> Option[b]`
29. `collect_fold_some(inst: Foldable[f], fa: f[a], fn: a -> Option[b], monoid: Monoid[b]) -> b`
30. `minimum_option(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> Option[a]`
31. `maximum_option(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> Option[a]`
32. `minimum_by_option(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> Option[a]`
33. `maximum_by_option(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> Option[a]`
34. `minimum_list(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> List[a]`
35. `maximum_list(inst: Foldable[f], ord_inst: Ord[a], fa: f[a]) -> List[a]`
36. `minimum_by_list(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> List[a]`
37. `maximum_by_list(inst: Foldable[f], ord_b: Ord[b], fa: f[a], fn: a -> b) -> List[a]`
38. `intercalate(inst: Foldable[f], fa: f[a], middle: a, monoid: Monoid[a]) -> a`
39. `filter_to_List(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> List[a]`
40. `take_while_to_List(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> List[a]`
41. `drop_while_to_List(inst: Foldable[f], fa: f[a], pred: a -> Bool) -> List[a]`
42. `laws_Foldable(inst: Foldable[f], eq_item: Eq[a], fa: f[a]) -> Test`

Notes on constructor behavior:

1. `foldable_from_foldl` derives `to_List`, `foldr`, `is_empty`, and `size` from `foldl`.
2. `foldable_from_folds` derives `to_List`, `is_empty`, and `size` from the two folds.
3. `foldable_specialized` is for performance-sensitive instances with O(1) size checks or native right-folds.

Notes on strictness:

1. All folds are strict (non-Eval).
2. Right-fold behavior is deterministic but does not provide Cats-style lazy short-circuit semantics.

Methods intentionally deferred from Cats-inspired surface:

1. Eval-based methods and aliases (for example lazy `foldRight`, `foldRightDefer`, Eval-based right reductions).
2. Effectful methods requiring missing abstractions (`foldM`, `foldMapM`, `foldMapA`, `traverseVoid`, `sequenceVoid`, `findM`, `existsM`, `forallM`, `partitionEither`, `partitionEitherM`, `partitionBifold`, `partitionBifoldM`, `compose`).
3. Partial-function methods that do not map directly to Bosatsu (`collectFirst`, `collectFold` in partial-function form).

## Law Design

`laws_Foldable` checks these invariants for a sample `fa`:

1. `size(inst, fa)` equals length of `to_List(inst, fa)`.
2. `is_empty(inst, fa)` is equivalent to `size(inst, fa).eq_Int(0)`.
3. `non_empty(inst, fa)` is equivalent to logical negation of `is_empty(inst, fa)`.
4. `foldl(inst, fa, [], (acc, a) -> [a, *acc]).reverse()` equals `to_List(inst, fa)`.
5. `foldr(inst, fa, [], (a, acc) -> [a, *acc])` equals `to_List(inst, fa)`.
6. `reduce_left_option` and `reduce_right_option` agree with list-model reductions on `to_List(inst, fa)`.

## Instance Placement Plan

Collection-local instance placement (as requested):

1. `src/Zafu/Collection/List.bosatsu`: `foldable_List: Foldable[List]`.
2. `src/Zafu/Collection/Vector.bosatsu`: `foldable_Vector: Foldable[Vector]`.
3. `src/Zafu/Collection/Chain.bosatsu`: `foldable_Chain: Foldable[Chain]`.
4. `src/Zafu/Collection/Deque.bosatsu`: `foldable_Queue: Foldable[Queue]`.
5. `src/Zafu/Collection/LazyList.bosatsu`: `foldable_LazyList: Foldable[LazyList]`.
6. `src/Zafu/Collection/Heap.bosatsu`: `foldable_Heap: Foldable[Heap]`.
7. `src/Zafu/Collection/HashSet.bosatsu`: `foldable_HashSet: Foldable[HashSet]`.
8. `src/Zafu/Collection/HashMap.bosatsu`: `foldable_HashMap_values: forall k. Foldable[HashMap[k, *]]`.
9. `src/Zafu/Collection/NonEmptyList.bosatsu`: `foldable_NonEmptyList: Foldable[NonEmptyList]`.
10. `src/Zafu/Collection/NonEmptyChain.bosatsu`: `foldable_NonEmptyChain: Foldable[NonEmptyChain]`.
11. `src/Zafu/Abstract/Instances/Predef.bosatsu`: `foldable_Array: Foldable[Array]`.

Instance-specific notes:

1. `HashMap` Foldable folds values (`v`) only, not keys.
2. `HashSet` and `HashMap` traversal order is implementation-defined; behavior is deterministic for a fixed runtime/hash semantics but not a stable insertion-order guarantee.
3. Where modules already have efficient `foldl`/`foldr`, prefer `foldable_specialized`.
4. Where only `foldl` exists, use `foldable_from_foldl` and document derived `foldr` cost.

## Implementation Plan

### Phase 1: Add Foldable abstraction

1. Create `src/Zafu/Abstract/Foldable.bosatsu`.
2. Implement dictionary type, three constructors, and all exported non-Eval functions listed above.
3. Add `laws_Foldable` plus module tests with list-backed models.
4. Keep naming/import style consistent with existing abstract modules.

### Phase 2: Add Predef Array instance

1. Update `src/Zafu/Abstract/Instances/Predef.bosatsu` imports to include array fold helpers from `Bosatsu/Collection/Array`.
2. Add and export `foldable_Array`.
3. Add tests validating `foldl`, `to_List`, and `size` behavior for `foldable_Array`.

### Phase 3: Add collection instances in collection files

1. Add `Foldable` imports in each collection file listed in touch paths.
2. Add and export the instance value in each module (`foldable_*`).
3. Prefer existing module-native folds and cached sizes where available.
4. For modules without native right-fold, derive via list model through constructor helpers.
5. For `HashMap`, add internal value-fold helpers as needed to avoid key/value materialization overhead where possible.

### Phase 4: Verification

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/90-design-a-foldable-typeclass.md` contains this architecture and complete API list.
2. `src/Zafu/Abstract/Foldable.bosatsu` exists and exports every function in the “Complete proposed function list”.
3. No Eval-related methods are added to `Foldable` in this issue.
4. `laws_Foldable` exists and checks order/size/emptiness/reduction consistency.
5. `src/Zafu/Abstract/Instances/Predef.bosatsu` exports `foldable_Array`.
6. `foldable_List` exists in `src/Zafu/Collection/List.bosatsu`.
7. `foldable_Vector` exists in `src/Zafu/Collection/Vector.bosatsu`.
8. `foldable_Chain` exists in `src/Zafu/Collection/Chain.bosatsu`.
9. `foldable_Queue` exists in `src/Zafu/Collection/Deque.bosatsu`.
10. `foldable_LazyList` exists in `src/Zafu/Collection/LazyList.bosatsu`.
11. `foldable_Heap` exists in `src/Zafu/Collection/Heap.bosatsu`.
12. `foldable_HashSet` exists in `src/Zafu/Collection/HashSet.bosatsu`.
13. `foldable_HashMap_values` exists in `src/Zafu/Collection/HashMap.bosatsu` and folds values.
14. `foldable_NonEmptyList` exists in `src/Zafu/Collection/NonEmptyList.bosatsu`.
15. `foldable_NonEmptyChain` exists in `src/Zafu/Collection/NonEmptyChain.bosatsu`.
16. Each instance has at least one law-oriented or model-oriented Foldable test.
17. `./bosatsu lib check` passes.
18. `./bosatsu lib test` passes.
19. `scripts/test.sh` passes before merge.

## Risks and Mitigations

1. Risk: derived strict `foldr` implementations may allocate intermediate lists and regress performance.
   Mitigation: use `foldable_specialized` in modules with native `foldr`.

2. Risk: stack behavior for right folds could degrade if implemented recursively.
   Mitigation: derive strict right-fold via reverse-and-left-fold models, not non-tail recursion.

3. Risk: `HashSet`/`HashMap` traversal order can surprise users expecting insertion ordering.
   Mitigation: document order as implementation-defined and avoid claiming insertion-order semantics.

4. Risk: API scope creep from Cats methods requiring missing abstractions.
   Mitigation: explicitly defer effectful APIs until `Applicative`/`Monad` land.

5. Risk: naming collisions (`foldl`, `foldr`) with collection modules.
   Mitigation: keep current alias import practice (`foldl as foldl_Foldable`) in downstream usage examples.

## Rollout Notes

1. This is additive; existing collection APIs stay source-compatible.
2. Land `Foldable` module and array instance first, then collection instances.
3. Keep instance symbols explicit (`foldable_*`) and colocated with data structures for discoverability.
4. Document the HashMap value-fold convention and hash-collection order caveat in module comments/tests.
5. Follow-up issue can add effectful Foldable APIs once higher-kinded abstractions are in place.
