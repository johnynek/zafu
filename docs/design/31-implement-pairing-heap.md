---
issue: 31
priority: 3
touch_paths:
  - docs/design/31-implement-pairing-heap.md
  - src/Zafu/Collection/Heap.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-07T23:31:17Z
---

# Design doc for issue #31: implement pairing heap

_Issue: #31 (https://github.com/johnynek/zafu/issues/31)_

## Summary

Proposed architecture and implementation plan for `Zafu/Collection/Heap` using a pairing heap with O(1) size, explicit `Ord`-driven operations, abstraction support mapping, acceptance criteria, risks, and rollout notes.

---
issue: 31
priority: 2
touch_paths:
  - docs/design/31-implement-pairing-heap.md
  - src/Zafu/Collection/Heap.bosatsu
depends_on:
  - 28
estimated_size: M
generated_at: 2026-03-07T23:50:00Z
---

# Design: Zafu/Collection/Heap (pairing heap)

_Issue: #31 (https://github.com/johnynek/zafu/issues/31)_

## Summary

Add a persistent pairing heap at `Zafu/Collection/Heap` with explicit `Ord`-driven operations, O(1) size lookup, and APIs aligned with existing `Zafu/Collection` naming. The module will provide core heap operations, sorted extraction, structural folds, and adapters for the `Zafu/Abstract` typeclass dictionaries that are lawful for this data type.

## Status

Proposed

## Context

Zafu currently has sequence-like collections (`Vector`, `Chain`, `LazyList`, `Deque`) but no priority queue. Issue #31 asks for a pairing heap design that:

1. Uses `Ord` from the `Zafu/Abstract` direction in issue #28.
2. Uses a pairing heap strategy.
3. Guarantees O(1) `size` to support recursion-by-size patterns in Bosatsu.
4. Lists which `Zafu/Abstract` abstractions the heap can support.

Pairing heap is selected because it keeps `meld` simple and fast while providing strong amortized performance for immutable priority-queue use.

## Goals

1. Add `src/Zafu/Collection/Heap.bosatsu` with an opaque `Heap[a]`.
2. Keep `size_Heap` O(1) by storing cached size in each non-empty node.
3. Provide efficient `combine` (meld), `insert`, `peek/min`, and `pop_min`.
4. Keep API naming consistent with `Vector`/`Chain` style (`*_Heap` plus `size` alias).
5. Add property tests in-module following existing `Collection` module practice.
6. Document support and non-support for `Zafu/Abstract` abstractions.

## Non-goals

1. Mutable or in-place heap operations.
2. `decrease_key`/handle-based APIs.
3. Stability guarantees among equal-priority values.
4. Indexed access or arbitrary delete.
5. Forcing a `Traverse`/`Monad` API that cannot be made lawful without extra constraints.

## Decision summary

1. Represent heap as a tree of roots with child subheaps.
2. Cache total subtree size on every `Node` for O(1) size.
3. Implement `combine_Heap` with root linking based on `Ord`.
4. Implement `pop_min_Heap` with classic two-pass pairwise child merging.
5. Implement `to_List_Heap` in ascending order by repeatedly popping minimum.
6. Implement `foldl_Heap` and `foldr_Heap` as structural folds (not priority-order folds).
7. Provide abstraction adapters where lawful (`Semigroup`, `Monoid`, `Foldable`, plus canonical comparison helpers).

## Proposed module API

Proposed exports:

1. `Heap`
2. `empty_Heap`
3. `singleton_Heap`
4. `size`
5. `size_Heap`
6. `is_empty_Heap`
7. `min_Heap`
8. `combine_Heap`
9. `insert_Heap`
10. `pop_min_Heap`
11. `from_List_Heap`
12. `to_List_Heap`
13. `foldl_Heap`
14. `foldr_Heap`
15. `eq_Heap`
16. `cmp_Heap`
17. `semigroup_Heap`
18. `monoid_Heap`
19. `foldable_Heap`
20. `hash_Heap` (only if `Zafu/Abstract/Hash` API from issue #28 is available when implementation lands)

Operational contracts:

1. `size_Heap(heap)` is O(1).
2. `min_Heap(heap)` is O(1).
3. `combine_Heap(ord, left, right)` is O(1) worst-case.
4. `insert_Heap(ord, item, heap)` is O(1) amortized.
5. `pop_min_Heap(ord, heap)` is O(log n) amortized, O(n) worst-case.
6. `from_List_Heap(ord, items)` targets O(n) amortized by pairwise build.
7. `to_List_Heap(ord, heap)` is O(n log n), returning ascending order.

## Data model and invariants

Internal representation:

`enum Heap[a: +*]:`
`  Empty`
`  Node(size: Int, min: a, children: List[Heap[a]])`

Invariants:

1. `Empty` represents size `0`.
2. `Node(size, _, _)` always has `size > 0`.
3. `size` equals `1 + sum(size(child))`.
4. Children never contain `Empty`.
5. Heap order: for each child root `c`, `min <= c` under provided `Ord[a]`.
6. All exported constructors/operations preserve these invariants.

## Core algorithms

1. Link/combine:
- Compare two roots with `Ord`.
- Smaller root becomes new root.
- Larger heap is prepended to winner's child list.
- New size is sum of both cached sizes.

2. Pop minimum:
- Remove root.
- Merge children with two-pass strategy:
  - Pass 1: pair adjacent children and meld each pair.
  - Pass 2: meld pair-results from right to left.
- Return popped element and merged remainder.

3. Build from list:
- Turn each item into singleton heap.
- Reuse pairwise merging rounds until one heap remains.
- Avoid long one-sided insertion chains.

4. Sorted extraction:
- Repeatedly call `pop_min_Heap`.
- Accumulate popped values to list.

5. Structural folds:
- `foldl_Heap` and `foldr_Heap` traverse internal tree shape with explicit loop/fuel from cached size for stack safety.
- Priority-order fold is intentionally expressed via `to_List_Heap` + list fold when needed.

## Abstraction support from `Zafu/Abstract`

| Abstraction | Support | Notes |
| --- | --- | --- |
| `Eq` | Yes | Canonical multiset equality via sorted pop stream (`cmp_Heap == EQ`). |
| `Ord` | Yes | Lexicographic compare of ascending pop streams. |
| `Hash` | Yes | Hash canonical sorted stream so equal heaps hash equally. |
| `Show` | Yes | Render from canonical sorted list. |
| `Semigroup` | Yes | `combine_Heap(ord)` is associative under fixed `Ord`. |
| `Monoid` | Yes | `empty_Heap` + `combine_Heap(ord)`. |
| `Foldable` | Yes | Structural fold over heap nodes. |
| `Traverse` | No | Would require `Ord[b]` after mapping, which `Traverse` cannot require. |
| `Applicative` | No | No lawful instance matching heap semantics. |
| `Alternative` | No | Depends on `Applicative` lawfulness. |
| `Monad` | No | Depends on lawful `Applicative`/`flat_map` semantics with heap-order constraints. |
| `Compose` helpers | Not applicable | No `Traverse`/`Applicative` instance to compose. |

Initial implementation scope for issue #31: core heap API plus `Semigroup`/`Monoid`/`Foldable` adapters and explicit `eq_Heap`/`cmp_Heap` helpers. `hash_Heap` and `show` adapters can land in the same PR if issue #28 APIs exist on `main`; otherwise they are follow-up additions.

## Implementation plan

### Phase 1: module skeleton and invariants

1. Add `src/Zafu/Collection/Heap.bosatsu`.
2. Define `Heap` representation and O(1) `size_Heap`.
3. Add `empty_Heap`, `singleton_Heap`, `is_empty_Heap`, `min_Heap`.

### Phase 2: core pairing heap operations

1. Implement internal `link` and exported `combine_Heap`.
2. Implement `insert_Heap`.
3. Implement two-pass `pop_min_Heap` and helper pair-merge functions.
4. Add internal invariant checker for tests.

### Phase 3: conversions and folds

1. Implement `from_List_Heap` using pairwise build rounds.
2. Implement `to_List_Heap` via repeated `pop_min_Heap`.
3. Implement stack-safe `foldl_Heap` and `foldr_Heap`.

### Phase 4: abstraction adapters

1. Add `semigroup_Heap(ord)` and `monoid_Heap(ord)`.
2. Add `foldable_Heap`.
3. Add `eq_Heap` and `cmp_Heap` canonical comparisons.
4. Add `hash_Heap` if `Zafu/Abstract/Hash` is available on `main`.

### Phase 5: validation

1. Add unit sanity assertions and property tests in the module.
2. Validate with:
- `./bosatsu lib check`
- `./bosatsu lib test`
- `scripts/test.sh`

## Acceptance criteria

1. `docs/design/31-implement-pairing-heap.md` is added with this plan.
2. `src/Zafu/Collection/Heap.bosatsu` exists and exports the agreed API.
3. `size_Heap` is O(1) and reads cached size directly.
4. `combine_Heap` maintains heap-order and cached-size invariants.
5. `pop_min_Heap` uses two-pass child pairing/merging.
6. `from_List_Heap` and `to_List_Heap` are implemented and documented.
7. `to_List_Heap` returns ascending order under supplied `Ord`.
8. `foldl_Heap` and `foldr_Heap` are stack-safe for deep heaps.
9. Abstraction support list is reflected in exported adapters/helpers (`Semigroup`, `Monoid`, `Foldable`, comparison helpers; `Hash` when available).
10. Property tests cover ordering, size law, invariant preservation, and deep-stack behavior.
11. `./bosatsu lib check` passes.
12. `./bosatsu lib test` passes.
13. `scripts/test.sh` passes before merge.

## Risks and mitigations

1. Risk: incorrect two-pass merge breaks amortized behavior or invariants.
Mitigation: property tests that compare against list-model behavior and invariant checks after random operation sequences.

2. Risk: recursive traversal can overflow on pathological heaps.
Mitigation: implement iterative/loop-based traversal with fuel derived from cached size.

3. Risk: mismatch between `Eq` and `Hash` semantics if one is structural and the other canonical.
Mitigation: define both over the same canonical sorted stream.

4. Risk: dependency on issue #28 APIs may block typeclass adapter code.
Mitigation: keep core heap operations independent; gate adapters behind available `Zafu/Abstract` modules or split into immediate follow-up PR.

## Rollout notes

1. Land as additive API on `main`; no existing collection API changes required.
2. Start by exposing core heap operations; keep adapter exports small and explicit.
3. Document that structural folds are not priority-order folds.
4. If `Hash`/`Show` adapters are deferred due issue #28 timing, track in follow-up issue and keep core heap ship-ready.
5. Prefer one PR for module + tests, then optional follow-up PR for additional adapters if dependencies lag.

## Out of scope

1. Mutable heap optimizations.
2. Fibonacci/binomial heap alternatives.
3. Decrease-key or indexed-priority-queue APIs.
4. Global/prelude-level re-export policy for new heap functions.
