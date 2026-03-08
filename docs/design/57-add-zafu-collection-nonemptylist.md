---
issue: 57
priority: 3
touch_paths:
  - docs/design/57-add-zafu-collection-nonemptylist.md
  - src/Zafu/Collection/NonEmptyList.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-08T20:46:36Z
---

# Design: Add Zafu/Collection/NonEmptyList (Issue #57)

_Issue: #57 (https://github.com/johnynek/zafu/issues/57)_

## Summary

Design doc content for issue #57 proposing a new Zafu/Collection/NonEmptyList module with constructor export, complete function inventory, implementation phases, acceptance criteria, risks, and rollout guidance.

---
issue: 57
priority: 2
touch_paths:
  - docs/design/57-add-zafu-collection-nonemptylist.md
  - src/Zafu/Collection/NonEmptyList.bosatsu
depends_on:
  - 48
estimated_size: M
generated_at: 2026-03-08T20:41:40Z
---

# Design: Add Zafu/Collection/NonEmptyList

_Issue: #57 (https://github.com/johnynek/zafu/issues/57)_

## Summary

Add `Zafu/Collection/NonEmptyList` as a first-class non-empty sequence:

`struct NonEmptyList[a: +*](head: a, tail: List[a])`

The module exports the constructor, adds `from_append(lst, last)`, and provides a List-parity API (`map`, `sort`, folds, indexing, etc.) while preserving non-empty guarantees in function signatures wherever possible.

## Status

Proposed

## Context

`Zafu/Collection/List` now provides a consistent list utility API, but callers still must handle emptiness even when business logic guarantees at least one element. Issue #57 requests a dedicated non-empty type with constructor export and List-like operations.

The key design challenge is API parity with `Zafu/Collection/List` without losing type-level non-empty guarantees.

## Goals

1. Add `src/Zafu/Collection/NonEmptyList.bosatsu`.
2. Define `struct NonEmptyList[a: +*](head: a, tail: List[a])` exactly as requested.
3. Export the constructor and support direct pattern matching.
4. Add `from_append(lst: List[a], last: a) -> NonEmptyList[a]`.
5. Provide List-like API including `sort` and `map`.
6. Preserve non-empty invariants in return types wherever feasible.
7. Add tests covering constructor, conversions, parity functions, and invariant-preserving behavior.

## Non-goals

1. Replacing built-in `List`.
2. Refactoring existing modules to adopt `NonEmptyList` in this PR.
3. Adding typeclass adapters (`Ord`, `Hash`) beyond what issue #57 needs.
4. Introducing partial/throwing APIs that can violate non-empty safety.

## Data Model and Invariants

Type:

1. `struct NonEmptyList[a: +*](head: a, tail: List[a])`

Core invariants:

1. Every `NonEmptyList` has at least one element.
2. `to_List(NonEmptyList(head, tail)) == [head, *tail]`.
3. Functions that can become empty return `Option[NonEmptyList[a]]` (or `List[a]` where explicitly chosen), never an invalid `NonEmptyList`.
4. Constructor-based operations (`singleton`, `prepend`, `append`, `concat`, `map`, `sort`, `zip`) always return a valid non-empty value.

## API Inventory (All Functions to Add)

Exported type/constructor:

1. `NonEmptyList()` (constructor export for `NonEmptyList(head, tail)` pattern matching)

Constructors and conversions:

1. `singleton(item: a) -> NonEmptyList[a]`
2. `from_prepend(head: a, tail: List[a]) -> NonEmptyList[a]`
3. `from_append(lst: List[a], last: a) -> NonEmptyList[a]`
4. `from_List(lst: List[a]) -> Option[NonEmptyList[a]]`
5. `to_List(items: NonEmptyList[a]) -> List[a]`

Shape and query helpers:

1. `head(items: NonEmptyList[a]) -> a`
2. `tail(items: NonEmptyList[a]) -> List[a]`
3. `uncons(items: NonEmptyList[a]) -> (a, List[a])`
4. `last(items: NonEmptyList[a]) -> a`
5. `size(items: NonEmptyList[a]) -> Int`
6. `is_empty(items: NonEmptyList[a]) -> Bool` (always `False`, for API parity)
7. `any(items: NonEmptyList[Bool]) -> Bool`
8. `exists(items: NonEmptyList[a], pred: a -> Bool) -> Bool`
9. `for_all(items: NonEmptyList[a], pred: a -> Bool) -> Bool`
10. `get_List(items: NonEmptyList[a], idx: Int) -> Option[a]`
11. `get_or(items: NonEmptyList[a], idx: Int, on_missing: () -> a) -> a`
12. `set_List(items: NonEmptyList[a], idx: Int, value: a) -> Option[NonEmptyList[a]]`

Transforms and folds:

1. `foldl(items: NonEmptyList[a], init: b, fn: (b, a) -> b) -> b`
2. `foldr(items: NonEmptyList[a], init: b, fn: (a, b) -> b) -> b`
3. `sum(items: NonEmptyList[Int]) -> Int`
4. `sumf(items: NonEmptyList[Float64]) -> Float64`
5. `map(items: NonEmptyList[a], fn: a -> b) -> NonEmptyList[b]`
6. `flat_map(items: NonEmptyList[a], fn: a -> NonEmptyList[b]) -> NonEmptyList[b]`
7. `sort(order: Order[a], items: NonEmptyList[a]) -> NonEmptyList[a]`
8. `zip(left: NonEmptyList[a], right: NonEmptyList[b]) -> NonEmptyList[(a, b)]`
9. `filter(items: NonEmptyList[a], pred: a -> Bool) -> Option[NonEmptyList[a]]`

Non-empty structural ops:

1. `prepend(item: a, items: NonEmptyList[a]) -> NonEmptyList[a]`
2. `append(items: NonEmptyList[a], item: a) -> NonEmptyList[a]`
3. `concat(left: NonEmptyList[a], right: NonEmptyList[a]) -> NonEmptyList[a]`
4. `concat_all(items: NonEmptyList[NonEmptyList[a]]) -> NonEmptyList[a]`
5. `reverse(items: NonEmptyList[a]) -> NonEmptyList[a]`

Equality helper:

1. `eq_NonEmptyList(eq_item: (a, a) -> Bool, left: NonEmptyList[a], right: NonEmptyList[a]) -> Bool`

## Architecture and Implementation Notes

Module layout:

1. New file: `src/Zafu/Collection/NonEmptyList.bosatsu`.
2. Export list includes `NonEmptyList()` and all functions above.
3. Keep constructor public; no opaque wrapper.

Implementation strategy:

1. Define `to_List` as the canonical bridge to `Zafu/Collection/List` behavior.
2. Implement fast-path direct functions without conversion where trivial (`head`, `tail`, `uncons`, `prepend`, `map`, `size`).
3. For parity behavior (`sort`, `sum`, `sumf`, `exists`, `for_all`, `get_List`, `set_List`, `foldl`, `foldr`), delegate through `Zafu/Collection/List` on `to_List(items)`.
4. Reconstruct `NonEmptyList` via a single private helper from known-non-empty list results (used by `sort`, `zip`, `concat`, `reverse`, etc.).
5. Keep impossible-empty branches explicit and defensive in pattern matches.

Preservation rules:

1. Operations that are total on non-empty inputs return `NonEmptyList[...]`.
2. Operations that may remove all elements return `Option[NonEmptyList[...]]` (`filter`).
3. Index-based mutation keeps `Option` semantics from `List.set_List` but upgrades successful branch to `NonEmptyList`.

Complexity targets:

1. `head`, `tail`, `uncons`, `prepend`: O(1)
2. `append`, `last`, `size`, `map`, `foldl`, `foldr`, `sum`, `sumf`, `reverse`, `filter`: O(n)
3. `get_List`, `set_List`: O(n)
4. `zip`: O(min(n, m))
5. `sort`: O(n log n)

## Implementation Plan

Phase 1: Type and construction

1. Add `NonEmptyList` struct and constructor export.
2. Implement `singleton`, `from_prepend`, `from_append`, `from_List`, `to_List`.
3. Add core shape functions: `head`, `tail`, `uncons`, `size`, `last`.

Phase 2: List-parity API

1. Implement parity queries and indexing: `is_empty`, `any`, `exists`, `for_all`, `get_List`, `get_or`, `set_List`.
2. Implement folds/transforms: `foldl`, `foldr`, `sum`, `sumf`, `map`, `flat_map`, `sort`, `zip`, `filter`.
3. Implement structural ops: `prepend`, `append`, `concat`, `concat_all`, `reverse`, `eq_NonEmptyList`.

Phase 3: Tests and validation

1. Add module tests in `src/Zafu/Collection/NonEmptyList.bosatsu` covering all exports.
2. Add targeted edge tests for: `from_List([]) == None`, `filter` all-false behavior, `set_List` out-of-range and negative index behavior, singleton `zip`, and `sort`/`map` non-empty preservation.
3. Run `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/57-add-zafu-collection-nonemptylist.md` exists with this architecture and plan.
2. `src/Zafu/Collection/NonEmptyList.bosatsu` exists and defines exactly `struct NonEmptyList[a: +*](head: a, tail: List[a])`.
3. Constructor export is present (`NonEmptyList()`), allowing direct construction/pattern matching.
4. `from_append(lst, last)` exists and returns a valid non-empty result for all `lst`.
5. `map` and `sort` are implemented and return `NonEmptyList`.
6. All functions in the API inventory are implemented and exported.
7. Functions that may empty a collection do not fabricate invalid values (`filter` uses `Option[NonEmptyList[a]]`).
8. Index semantics (`get_List`, `set_List`, `get_or`) match `Zafu/Collection/List` behavior for out-of-range and negative indices.
9. Unit tests cover constructor/conversion laws and branch behavior for each partial function.
10. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: accidental invariant break when reconstructing from `List`.
Mitigation: centralize reconstruction in one private helper and test every call site.

2. Risk: API drift from `Zafu/Collection/List` semantics.
Mitigation: delegate parity functions to `Zafu/Collection/List` rather than reimplementing behavior.

3. Risk: confusion around `filter`/`flat_map` signatures.
Mitigation: keep names aligned with `List`, but document non-empty-preserving types explicitly.

4. Risk: performance overhead from repeated `to_List` conversions.
Mitigation: implement common O(1)/single-pass paths directly and limit conversions to parity wrappers.

## Rollout Notes

1. Change is additive and does not break existing `List` users.
2. No migration is required; adoption is opt-in for call sites that want non-empty guarantees.
3. Initial rollout should prioritize correctness/invariants over aggressive optimization.
4. Follow-up issues can add adapters (`Ord`/`Hash`) and integrations in modules that currently use `(head, tail)` pairs manually.
