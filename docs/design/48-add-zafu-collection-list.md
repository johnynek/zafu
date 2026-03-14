---
issue: 48
priority: 3
touch_paths:
  - docs/design/48-add-zafu-collection-list.md
  - src/Zafu/Collection/List.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-08T19:43:49Z
---

# Design: Add Zafu/Collection/List (Issue #48)

_Issue: #48 (https://github.com/johnynek/zafu/issues/48)_

## Summary

Proposes a new `Zafu/Collection/List` utility module (no new list type), defines required and supplemental API, outlines phased implementation, acceptance criteria, risks, and rollout guidance.

---
issue: 48
priority: 2
touch_paths:
  - docs/design/48-add-zafu-collection-list.md
  - src/Zafu/Collection/List.bosatsu
depends_on: []
estimated_size: S
generated_at: 2026-03-08T19:38:36Z
---

# Design: Zafu/Collection/List

_Issue: #48 (https://github.com/johnynek/zafu/issues/48)_

## Summary

Add `Zafu/Collection/List` as a function-only utility module over the built-in `List` type (no new list data type). The module will re-export key `Bosatsu/List` capabilities (`any`, `exists`, `get_List`, `head`, `for_all`, `set_List`, `size`, `sum`, `sort`, `uncons`, `zip`) and add missing collection helpers used across Zafu (`sumf`, `is_empty`, `get_or`, `last`, `foldl`, `foldr`, `map`, `flat_map`, `filter`, `concat_all`, `eq_List`).

## Status

Proposed

## Context

- Zafu has multiple collection modules but no `Zafu/Collection/List` wrapper package.
- Many functions already exist in `Bosatsu/List`, but access is split between direct imports and `List` methods.
- Issue #48 requests a dedicated module with useful list operations and explicitly says not to add a new list type.

## Goals

1. Add `src/Zafu/Collection/List.bosatsu`.
2. Keep list representation as `Bosatsu/Predef::List[a]` only.
3. Provide the issue-requested function set with matching semantics to `Bosatsu/List`.
4. Add `sumf` for `List[Float64]`.
5. Provide a small parity layer with other Zafu collections (`is_empty`, fold/map/filter-style helpers).

## Non-goals

1. Defining a custom `List` enum/struct.
2. Replacing `Bosatsu/List` internals or changing core semantics.
3. Adding advanced numeric accumulation algorithms (e.g., compensated summation) in this issue.
4. Refactoring all existing modules to use `Zafu/Collection/List` in the same PR.

## Decision Summary

1. `Zafu/Collection/List` will be a thin, explicit utility layer with zero custom data structures.
2. Required issue functions are direct delegates to `Bosatsu/List` where available.
3. `sumf` will be implemented via strict left fold using `Bosatsu/Num/Float64.addf` with `0.0`.
4. Index mutation semantics follow `set_List` from `Bosatsu/List`: out-of-range and negative indices return `None`.
5. Extra helpers will be additive and conservative, focused on operations already idiomatic in existing collection modules.

## Proposed API (`Zafu/Collection/List`)

Core pass-throughs (required by issue):

1. `any(items: List[Bool]) -> Bool`
2. `exists(items: List[a], pred: a -> Bool) -> Bool`
3. `for_all(items: List[a], pred: a -> Bool) -> Bool`
4. `size(items: List[a]) -> Int`
5. `head(items: List[a]) -> Option[a]`
6. `uncons(items: List[a]) -> Option[(a, List[a])]`
7. `get_List(items: List[a], idx: Int) -> Option[a]`
8. `set_List(items: List[a], idx: Int, value: a) -> Option[List[a]]`
9. `zip(left: List[a], right: List[b]) -> List[(a, b)]`
10. `sort(order: Order[a], items: List[a]) -> List[a]`
11. `sum(items: List[Int]) -> Int`
12. `sumf(items: List[Float64]) -> Float64`

Collection-style helper layer:

1. `eq_List(eq_item: (a, b) -> Bool, left: List[a], right: List[b]) -> Bool`
2. `is_empty(items: List[a]) -> Bool`
3. `get_or(items: List[a], idx: Int, on_missing: () -> a) -> a`
4. `last(items: List[a]) -> Option[a]`
5. `foldl(items: List[a], init: b, fn: (b, a) -> b) -> b`
6. `foldr(items: List[a], init: b, fn: (a, b) -> b) -> b`
7. `map(items: List[a], fn: a -> b) -> List[b]`
8. `flat_map(items: List[a], fn: a -> List[b]) -> List[b]`
9. `filter(items: List[a], pred: a -> Bool) -> List[a]`
10. `concat_all(items: List[List[a]]) -> List[a]`

## Architecture and Implementation Notes

Module shape:

1. Single file package: `package Zafu/Collection/List`.
2. `export (...)` includes the curated API only.
3. No `enum List` / `struct List` declarations.

Implementation approach:

1. Delegate existing operations to `Bosatsu/List` to preserve behavior and reduce bug surface.
2. Implement helper-only functions in terms of `foldl_List`, `map_List`, `flat_map_List`, and pattern matching.
3. Implement `sumf` as `items.foldl_List(0.0, addf)`.
4. Implement `foldr` in stack-safe style using reverse + left fold.
5. Implement `filter` via foldr-style rebuild to preserve order without intermediate Array conversion.
6. Keep all operations purely persistent; no mutation or array-backed state.

Complexity targets:

1. `head`, `uncons`, `is_empty`: O(1)
2. `size`, `sum`, `sumf`, `last`, `foldl`, `foldr`, `map`, `flat_map`, `filter`, `concat_all`: O(n)
3. `get_List`, `set_List`: O(n)
4. `zip`: O(min(n, m))
5. `sort`: O(n log n)

## Implementation Plan

Phase 1: Module skeleton + required delegates

1. Add `src/Zafu/Collection/List.bosatsu`.
2. Wire and export required issue functions.
3. Add basic tests for required functions (including negative/out-of-range index behavior for `get_List`/`set_List`).

Phase 2: Helper layer and `sumf`

1. Add `sumf` using `Bosatsu/Num/Float64`.
2. Add collection-style helpers (`is_empty`, `get_or`, `last`, `foldl`, `foldr`, `map`, `flat_map`, `filter`, `concat_all`, `eq_List`).
3. Add parity tests against equivalent list-method behavior.

Phase 3: Validation and polish

1. Ensure function docs/comments are concise and clear about semantics.
2. Run `./bosatsu lib check`.
3. Run `./bosatsu lib test`.
4. Run `scripts/test.sh`.

## Acceptance Criteria

1. `src/Zafu/Collection/List.bosatsu` exists and defines no new list data type.
2. Package exports include all issue-requested functions: `any`, `exists`, `get_List`, `head`, `for_all`, `set_List`, `size`, `sum`, `sumf`, `sort`, `uncons`, `zip`.
3. `get_List` and `set_List` semantics match `Bosatsu/List` (including negative/out-of-range handling).
4. `sumf` is implemented for `List[Float64]` and validated with deterministic tests.
5. Added helper functions (`is_empty`, `get_or`, `last`, `foldl`, `foldr`, `map`, `flat_map`, `filter`, `concat_all`, `eq_List`) compile and pass tests.
6. No existing public module behavior regresses.
7. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass on the branch.
8. `docs/design/48-add-zafu-collection-list.md` is present with this architecture, plan, acceptance criteria, risks, and rollout notes.

## Risks and Mitigations

1. Risk: API overlap/confusion with `Bosatsu/List`.
Mitigation: keep behavior identical for delegated functions and document module intent as convenience/consistency layer.

2. Risk: `sumf` floating-point precision surprises.
Mitigation: document strict left-fold accumulation semantics; avoid claiming algebraic associativity.

3. Risk: scope creep from adding too many helpers.
Mitigation: phase the work; treat issue-requested function set as the hard minimum and keep extras conservative.

4. Risk: subtle semantic drift in wrapper functions.
Mitigation: use direct delegation whenever possible and test wrappers against known `Bosatsu/List` behavior.

## Rollout Notes

1. Change is fully additive; no migration is required for existing users.
2. Existing imports from `Bosatsu/List` remain valid.
3. Follow-up PRs can optionally migrate internal Zafu modules to import this package for consistency.
4. If API surface needs trimming/expansion after adoption feedback, do it in separate additive issues to avoid breaking first release behavior.
