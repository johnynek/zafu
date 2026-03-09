---
issue: 68
priority: 2
touch_paths:
  - docs/design/68-implement-nonemptychain.md
  - src/Zafu/Collection/NonEmptyChain.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
depends_on:
  - 57
  - 59
estimated_size: M
generated_at: 2026-03-08T23:42:08Z
---

# Design: Implement NonEmptyChain

_Issue: #68 (https://github.com/johnynek/zafu/issues/68)_

## Summary

Add `Zafu/Collection/NonEmptyChain` as requested:

`enum NonEmptyChain[a: +*]:`
`  Prepend(head: a, tail: Chain[a])`
`  Append(init: Chain[a], last: a)`

The module mirrors `NonEmptyList` ergonomics (non-empty-safe signatures, conversion helpers, functional transforms) while reusing `Chain` for structural operations and O(1) concat-style composition.

## Status

Proposed

## Context

1. `Zafu/Collection/Chain` provides stack-safe folds, O(1) concat, and efficient prepend and append construction, but it is nullable.
2. `Zafu/Collection/NonEmptyList` already defines the expected non-empty collection API style in this repo.
3. Issue #68 asks for a non-empty chain type with the exact two-constructor shape above and API parity with existing collection modules.
4. Recent API direction in Zafu is receiver-first ordering where the package-defined type is the first argument for most functions.

## Goals

1. Add `src/Zafu/Collection/NonEmptyChain.bosatsu`.
2. Define the exact enum constructors from the issue body.
3. Preserve a non-empty invariant at the type level for total operations.
4. Provide API parity with `NonEmptyList` where semantics make sense, backed by `Chain`.
5. Reuse existing `Chain` behavior for traversal and indexing to avoid semantic drift.
6. Keep function signatures receiver-first where practical, including `sort(items, order)`.

## Non-goals

1. Reworking `Chain` internals.
2. Replacing `NonEmptyList`.
3. Introducing new abstract typeclass modules beyond using existing `Semigroup`.
4. Micro-optimizing beyond clear correctness and parity in this issue.

## Data Model and Invariants

Type:

1. `enum NonEmptyChain[a: +*]:`
2. `Prepend(head: a, tail: Chain[a])`
3. `Append(init: Chain[a], last: a)`

Invariants:

1. Every value contains at least one element.
2. `to_Chain` preserves iteration order for both constructors.
3. Any API that can remove all elements returns `Option[NonEmptyChain[a]]`.
4. Reconstruction helpers never fabricate an invalid empty `NonEmptyChain`.

## Proposed API Inventory

Type and constructors:

1. `NonEmptyChain()`
2. `singleton(item: a) -> NonEmptyChain[a]`
3. `from_prepend(head: a, tail: Chain[a]) -> NonEmptyChain[a]`
4. `from_append(init: Chain[a], last: a) -> NonEmptyChain[a]`
5. `from_Chain(items: Chain[a]) -> Option[NonEmptyChain[a]]`
6. `from_List(items: List[a]) -> Option[NonEmptyChain[a]]`
7. `to_Chain(items: NonEmptyChain[a]) -> Chain[a]`
8. `to_List(items: NonEmptyChain[a]) -> List[a]`
9. `to_NonEmptyList(items: NonEmptyChain[a]) -> NonEmptyList[a]`

Queries and decomposition:

1. `head(items: NonEmptyChain[a]) -> a`
2. `tail(items: NonEmptyChain[a]) -> Chain[a]`
3. `uncons(items: NonEmptyChain[a]) -> (a, Chain[a])`
4. `last(items: NonEmptyChain[a]) -> a`
5. `init(items: NonEmptyChain[a]) -> Chain[a]`
6. `uncons_right(items: NonEmptyChain[a]) -> (Chain[a], a)`
7. `size(items: NonEmptyChain[a]) -> Int`
8. `get(items: NonEmptyChain[a], idx: Int) -> Option[a]`
9. `get_or(items: NonEmptyChain[a], idx: Int, on_missing: () -> a) -> a`

List-parity predicates and folds:

1. `any(items: NonEmptyChain[Bool]) -> Bool`
2. `exists(items: NonEmptyChain[a], pred: a -> Bool) -> Bool`
3. `for_all(items: NonEmptyChain[a], pred: a -> Bool) -> Bool`
4. `set(items: NonEmptyChain[a], idx: Int, value: a) -> Option[NonEmptyChain[a]]`
5. `foldl(items: NonEmptyChain[a], init: b, fn: (b, a) -> b) -> b`
6. `foldr(items: NonEmptyChain[a], init: b, fn: (a, b) -> b) -> b`
7. `sum(items: NonEmptyChain[Int]) -> Int`
8. `sumf(items: NonEmptyChain[Float64]) -> Float64`
9. `combine_all(items: NonEmptyChain[a], semi: Semigroup[a]) -> a`

Transforms and composition:

1. `map(items: NonEmptyChain[a], fn: a -> b) -> NonEmptyChain[b]`
2. `flat_map(items: NonEmptyChain[a], fn: a -> NonEmptyChain[b]) -> NonEmptyChain[b]`
3. `sort(items: NonEmptyChain[a], order: Order[a]) -> NonEmptyChain[a]`
4. `zip(left: NonEmptyChain[a], right: NonEmptyChain[b]) -> NonEmptyChain[(a, b)]`
5. `filter(items: NonEmptyChain[a], pred: a -> Bool) -> Option[NonEmptyChain[a]]`
6. `distinct_by_hash(h: Hash[a], items: NonEmptyChain[a]) -> NonEmptyChain[a]`
7. `prepend(item: a, items: NonEmptyChain[a]) -> NonEmptyChain[a]`
8. `append(items: NonEmptyChain[a], item: a) -> NonEmptyChain[a]`
9. `concat(left: NonEmptyChain[a], right: NonEmptyChain[a]) -> NonEmptyChain[a]`
10. `concat_all(items: NonEmptyChain[NonEmptyChain[a]]) -> NonEmptyChain[a]`
11. `reverse(items: NonEmptyChain[a]) -> NonEmptyChain[a]`

Typeclass adapters matching `NonEmptyList`:

1. `eq_NonEmptyChain(eq_item: Eq[a]) -> Eq[NonEmptyChain[a]]`
2. `ord_NonEmptyChain(ord_item: Ord[a]) -> Ord[NonEmptyChain[a]]`
3. `hash_NonEmptyChain(hash_item: Hash[a]) -> Hash[NonEmptyChain[a]]`

## Architecture and Implementation Notes

1. Add a private helper `from_non_empty_Chain_or(items, on_empty)` that builds `NonEmptyChain` from `Chain` via `uncons_left_Chain`, with a defensive fallback for impossible empty paths.
2. Keep `to_Chain` as the canonical bridge:
`Prepend(head, tail)` maps to `prepend_Chain(head, tail)`.
`Append(init, last)` maps to `append_Chain(init, last)`.
3. Add `to_NonEmptyList` by pattern matching on `to_List(items)` and constructing `NonEmptyList(head, tail)` directly, with an internal impossible fallback for the empty branch.
4. Implement fold and indexing APIs directly on `Chain` delegates (`foldl_Chain`, `foldr_Chain`, `index_Chain`, `get_or_Chain`) to preserve `Chain` semantics.
5. Implement List-parity wrappers (`set`, `sort`, `zip`, `filter`, `distinct_by_hash`) via `to_List` and `Zafu/Collection/List` helpers, then reconstruct with `from_non_empty_Chain_or`.
6. Implement `combine_all(items, semi)` as a non-empty fold: start with `head(items)` and combine over `tail(items)`.
7. Keep receiver-first argument order whenever one argument is the package-defined type. In this module, `sort(items, order)` follows this rule.
8. Keep the module fully additive and self-contained; no required changes to `Chain` representation.

Complexity targets:

1. `singleton`, `from_prepend`, `from_append`, `prepend`, `append`, `concat`: O(1) structural.
2. `head` and `last`: O(1) on matching constructor, otherwise O(n) worst case.
3. `size`, `foldl`, `foldr`, `map`, `flat_map`, `filter`, `reverse`, `distinct_by_hash`, `combine_all`: O(n).
4. `get`, `set`: O(n).
5. `zip`: O(min(n, m)).
6. `sort`: O(n log n).

## Implementation Plan

Phase 1: module skeleton and core conversions

1. Create `src/Zafu/Collection/NonEmptyChain.bosatsu` with enum and exports.
2. Add `singleton`, `from_prepend`, `from_append`, `from_Chain`, `from_List`, `to_Chain`, `to_List`, and `to_NonEmptyList`.
3. Add core decomposition helpers (`head`, `tail`, `uncons`, `last`, `init`, `uncons_right`, `size`).

Phase 2: parity API and composition

1. Add predicates and indexing wrappers (`any`, `exists`, `for_all`, `get`, `get_or`, `set`).
2. Add folds and transforms (`foldl`, `foldr`, `sum`, `sumf`, `combine_all`, `map`, `flat_map`, `sort`, `zip`, `filter`, `distinct_by_hash`).
3. Add structural operations (`prepend`, `append`, `concat`, `concat_all`, `reverse`).

Phase 3: typeclass adapters and tests

1. Add `eq_NonEmptyChain`, `ord_NonEmptyChain`, and `hash_NonEmptyChain` via `to_List`.
2. Add module tests mirroring `NonEmptyList` and `Chain` style: constructor pattern matching, conversion roundtrips, index edge cases, non-empty preservation, `combine_all` sanity, and ordering and hash sanity.
3. Validate with:
`./bosatsu lib check`
`./bosatsu lib test`
`scripts/test.sh`

## Acceptance Criteria

1. `docs/design/68-implement-nonemptychain.md` is added with this plan.
2. `src/Zafu/Collection/NonEmptyChain.bosatsu` exists and defines exactly:
`enum NonEmptyChain[a: +*]:`
`Prepend(head: a, tail: Chain[a])`
`Append(init: Chain[a], last: a)`
3. Constructor export `NonEmptyChain()` supports direct pattern matching.
4. Module includes conversions from and to both `Chain` and `List`, plus `to_NonEmptyList`.
5. `map`, `flat_map`, `sort(items, order)`, and `concat` return `NonEmptyChain` and preserve non-empty guarantees.
6. Potentially-empty operations (`filter`, and `set` invalid index) return `Option` without invalid values.
7. `head`, `tail`, `last`, and `init` produce correct results for both constructors, including empty `tail` or `init` edges.
8. `combine_all(items, semi)` exists and combines all elements without requiring an explicit seed.
9. `eq_NonEmptyChain`, `ord_NonEmptyChain`, and `hash_NonEmptyChain` are implemented and tested.
10. Tests cover negative and out-of-range indices and conversion roundtrips.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: invariant bugs when reconstructing from `Chain` or `List`.
Mitigation: centralize reconstruction in one helper and test all fallback paths.

2. Risk: endpoint operation performance varies by constructor orientation.
Mitigation: document complexity explicitly and keep prepend, append, and concat O(1) so callers can choose optimal construction style.

3. Risk: semantic drift from existing `List`, `NonEmptyList`, and `Chain` behavior.
Mitigation: delegate parity functions to existing modules rather than reimplementing indexing and sort semantics.

4. Risk: hidden extra allocations from repeated `to_List` conversion.
Mitigation: use Chain-native folds and indexing where possible and reserve list conversion for APIs not present on `Chain`.

## Rollout Notes

1. Change is additive and backward compatible.
2. No migration is required for existing `Chain` callers.
3. Early adopters should use `from_Chain` at boundaries where non-empty can be proven.
4. Follow-up issues should align existing collection `sort` function signatures to receiver-first order for consistency across Zafu.
5. Follow-up optimization work can add stricter constructor normalization or cached endpoints if benchmarks show hotspots.
