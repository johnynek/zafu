---
issue: 31
priority: 2
touch_paths:
  - docs/design/31-implement-pairing-heap.md
  - src/Zafu/Collection/Heap.bosatsu
depends_on:
  - 28
estimated_size: M
generated_at: 2026-03-08T00:35:00Z
---

# Design: Zafu/Collection/Heap (pairing heap)

_Issue: #31 (https://github.com/johnynek/zafu/issues/31)_

## Summary

Add a persistent pairing heap at `Zafu/Collection/Heap` with O(1) size lookup, min-ordered folds, short API names, and an implementation strategy that keeps heap structure opaque.

## Status

Proposed

## Context

Zafu has sequence collections (`Vector`, `Chain`, `LazyList`, `Deque`) but no priority queue. Issue #31 asks for a pairing heap design that:

1. Uses `Ord` from `Zafu/Abstract`.
2. Is implemented as a pairing heap.
3. Guarantees O(1) `size` to support recursion-on-size in Bosatsu.
4. Lists which `Zafu/Abstract` abstractions Heap can support.

## Goals

1. Add `src/Zafu/Collection/Heap.bosatsu` with opaque `Heap[a]`.
2. Keep `size` O(1) with cached subtree size.
3. Keep heap operations ordered by a single comparator for each non-empty heap.
4. Use short names (`empty`, `size`, `insert`, ...) and rely on `as` import aliasing.
5. Keep chaining ergonomics by taking `heap` as the first argument for primary operations.
6. Provide ordered folds from min to max without materializing a full intermediate list.

## Non-goals

1. Mutable heap operations.
2. `decrease_key` or handle-based updates.
3. Stability guarantees among equal-priority values.
4. Exposing internal tree constructors.
5. Forcing unlawful `Traverse`/`Monad`/`Applicative` instances.

## Decision summary

1. Heap internals are opaque; only functions are exported.
2. Every non-empty heap carries an `Ord[a]` chosen at creation time.
3. `size` is cached in heap nodes and read in O(1).
4. Core operations use pairing-heap link and two-pass child merge.
5. `foldl` and `foldr` iterate in min-to-max logical order (the same order as repeated `pop_min`), implemented as a streaming loop to avoid building a full list.
6. Public functions use short names and heap-first argument order where practical.

## API shape

Proposed exports:

1. `Heap`
2. `empty`
3. `singleton`
4. `is_empty`
5. `size`
6. `min`
7. `insert`
8. `combine`
9. `pop_min`
10. `from_List`
11. `to_List`
12. `foldl`
13. `foldr`
14. `eq`
15. `cmp`
16. `semigroup`
17. `monoid`
18. `foldable`
19. `hash` (if `Zafu/Abstract/Hash` from issue #28 is available at implementation time)

Representative signatures (heap-first style):

1. `insert(heap: Heap[a], item: a) -> Heap[a]`
2. `combine(heap: Heap[a], other: Heap[a]) -> Heap[a]`
3. `pop_min(heap: Heap[a]) -> Option[(a, Heap[a])]`
4. `foldl(heap: Heap[a], init: b, fn: (b, a) -> b) -> b`
5. `foldr(heap: Heap[a], init: b, fn: (a, b) -> b) -> b`

Creation signatures:

1. `empty(ord: Ord[a]) -> Heap[a]`
2. `singleton(ord: Ord[a], item: a) -> Heap[a]`
3. `from_List(ord: Ord[a], items: List[a]) -> Heap[a]`

## Ordering ownership: pros/cons and choice

Pairing heaps are only valid relative to one ordering. Re-supplying arbitrary `Ord` per operation is unsafe because existing structure was built under a prior comparator.

### Option A: caller passes `Ord` on every operation

Pros:

1. Keeps `Heap[a]` easier to make covariant.
2. No comparator stored in heap nodes.

Cons:

1. Easy to call one operation with a different `Ord` and silently corrupt semantics.
2. Every compare-based operation repeats comparator threading.

### Option B: non-empty heap keeps its own `Ord` (chosen)

Pros:

1. Comparator consistency is preserved by construction after first non-empty creation.
2. Simpler call sites for chained operations (`heap.insert(x).insert(y).pop_min()`).
3. Fewer API surfaces that require passing comparator repeatedly.

Cons:

1. Covariance is harder (or impossible) for the concrete heap representation because `Ord[a]` consumes `a`.
2. Merging heaps created with different orderings needs defined behavior.

Chosen behavior for `combine`:

1. `empty(ord).combine(other)` and `heap.combine(empty(ord))` are fast-paths.
2. For two non-empty heaps, when orderings are not known identical, implementation must preserve correctness by rebuilding the right heap under the left heap's ordering (stream right via `pop_min` and `insert`).
3. This keeps semantics correct even if it sacrifices the ideal O(1) meld in cross-ordering cases.

## Covariance note

Covariance is valuable in Bosatsu for nested recursion patterns such as `struct Foo(a: Int, foos: Heap[Foo])`.

This design prioritizes ordering safety first (heap-owned `Ord`) and documents the covariance tradeoff explicitly. If recursive covariant use-cases become important, we can add a follow-up design for a split representation (covariant tree payload + separate ordering witness wrapper) while preserving the same external operations.

## Data model and invariants (opaque)

Internal representation is intentionally private. Invariants that must hold:

1. Size is cached and exact for every non-empty subtree.
2. `size(empty(ord)) == 0` and `size(non_empty) > 0`.
3. Heap-order property is maintained under the heap's stored `Ord`.
4. No exported API leaks node/child constructors.
5. All public mutators preserve invariants.

## Core algorithms

1. Link/meld:
- Compare roots with stored ordering.
- Smaller root becomes parent; larger root becomes first child.
- Size cache is updated by addition.

2. `pop_min`:
- Remove root.
- Merge children using two-pass pairing:
  - Pair adjacent children left-to-right and meld each pair.
  - Meld resulting heaps right-to-left.

3. `from_List`:
- Build singleton heaps and merge in rounds.
- Avoid pathological one-sided insertion chains.

4. Ordered folds:
- `foldl`/`foldr` consume heap in ascending order using repeated `pop_min` on a local working heap state.
- Implementation streams directly into accumulator to avoid allocating `to_List`.

5. `to_List`:
- Defined via the same ordered pop stream, producing ascending output.

## Abstraction support from `Zafu/Abstract`

| Abstraction | Support | Notes |
| --- | --- | --- |
| `Eq` | Yes | Canonical equality via ascending pop stream. |
| `Ord` | Yes | Lexicographic compare of ascending pop streams. |
| `Hash` | Yes | Hash ascending pop stream so `Eq`/`Hash` stay coherent. |
| `Show` | Yes | Render from ascending iteration. |
| `Semigroup` | Yes | `semigroup(ord)` uses `combine` under fixed ordering semantics. |
| `Monoid` | Yes | `monoid(ord)` provides `empty(ord)` + `combine`. |
| `Foldable` | Yes | `foldl`/`foldr` are min-to-max ordered folds. |
| `Traverse` | No | Would require `Ord[b]` after mapping. |
| `Applicative` | No | No lawful instance consistent with heap semantics. |
| `Alternative` | No | Depends on lawful `Applicative`. |
| `Monad` | No | Depends on lawful `Applicative`/`flat_map` under ordering constraints. |
| `Compose` helpers | Not applicable | No `Traverse`/`Applicative` instance. |

## Implementation plan

### Phase 1: module skeleton

1. Add `src/Zafu/Collection/Heap.bosatsu`.
2. Implement opaque heap type and O(1) cached `size`.
3. Add `empty`, `singleton`, `is_empty`, `min`.

### Phase 2: pairing-heap core

1. Implement internal link and two-pass merge helpers.
2. Implement `insert`, `combine`, `pop_min`.
3. Add correctness path for combining heaps that may carry different orderings.

### Phase 3: ordered iteration and folds

1. Implement `from_List`.
2. Implement streaming `foldl` and `foldr` over ascending pop stream.
3. Implement `to_List` on top of the same stream.

### Phase 4: abstraction adapters

1. Add `eq`, `cmp`, `semigroup`, `monoid`, `foldable`.
2. Add `hash` if `Zafu/Abstract/Hash` is available on `main`.

### Phase 5: validation

1. Add module property tests and sanity tests.
2. Validate with:
- `./bosatsu lib check`
- `./bosatsu lib test`
- `scripts/test.sh`

## Acceptance criteria

1. `docs/design/31-implement-pairing-heap.md` reflects this design.
2. `src/Zafu/Collection/Heap.bosatsu` exists with short-name exports.
3. `size` is O(1) and reads cached size.
4. `foldl` and `foldr` are min-to-max ordered folds.
5. Ordered folds do not require building full `to_List` first.
6. `combine`, `insert`, and `pop_min` preserve heap invariants.
7. `pop_min` uses two-pass child pairing/merge.
8. `to_List` returns ascending order.
9. API supports heap-first chaining for primary operations.
10. Abstraction support table is reflected in implemented adapters.
11. Property tests cover ordering laws, size laws, invariant preservation, and deep-stack behavior.
12. `./bosatsu lib check` passes.
13. `./bosatsu lib test` passes.
14. `scripts/test.sh` passes before merge.

## Risks and mitigations

1. Risk: cross-ordering `combine` semantics may be expensive.
Mitigation: document behavior, fast-path empties and same-ordering internal cases, and test correctness first.

2. Risk: two-pass merge bugs can violate invariants.
Mitigation: randomized operation-sequence properties with invariant checks after each step.

3. Risk: ordered folds could accidentally regress to list-materialization.
Mitigation: implement folds directly over pop stream and keep allocation-focused regression tests.

4. Risk: heap-owned ordering may limit covariance in some recursive type designs.
Mitigation: track recursive-use demand and add a follow-up split-representation design if needed.

## Rollout notes

1. Ship as additive API on `main`.
2. Land module + tests first; add optional adapters only when upstream abstractions are available.
3. Keep representation opaque in docs and code.
4. Call out short-name import style and recommend `as` aliasing at use sites.

## Out of scope

1. Mutable priority queues.
2. Decrease-key APIs.
3. Indexed delete/update.
4. Prelude/re-export policy changes.
