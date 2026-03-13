---
issue: 127
priority: 3
touch_paths:
  - docs/design/127-improve-semigroup-design.md
  - src/Zafu/Abstract/Semigroup.bosatsu
  - src/Zafu/Abstract/Monoid.bosatsu
  - src/Zafu/Abstract/Foldable.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Collection/Chain.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-13T23:42:54Z
---

# Design: Improve Semigroup Mapped Bulk Combination

_Issue: #127 (https://github.com/johnynek/zafu/issues/127)_

## Summary

Add mapped bulk-combine APIs to `Semigroup` and `Monoid`, preserve specialization hooks, and switch list-backed `Foldable` paths to call the new APIs so `fold_map` can avoid intermediate mapped-list allocation.

## Status

Proposed

## Context

1. `Semigroup` currently supports `combine`, `combine_n`, and `combine_all_option`, with specialization hooks for `combine_n` and list-wide combination.
2. `Monoid.combine_all` currently calls `Semigroup.combine_all_option` and unwraps `Option`, which adds an avoidable wrapper/unwrapper path for the non-empty case.
3. Some `fold_map` implementations currently do `items.map_List(fn)` followed by `combine_all`, which allocates an intermediate mapped list.
4. Issue #127 asks for mapped bulk-combine operations so we can combine while mapping in one pass, and then route Foldable list paths through that API.

## Problem

1. The API has no Semigroup-level operation for “map while combining” over non-empty or optional lists.
2. `Monoid` lacks a direct mapped combine API, so callers either allocate mapped lists or pay `Option` round-trips.
3. `Foldable` list-backed implementations cannot currently express “combine mapped values directly” through `Monoid` and therefore do extra allocation work.
4. We need to add this without breaking existing Semigroup/Monoid construction patterns or regressing current specialized behavior.

## Goals

1. Add Semigroup mapped bulk operations that support both non-empty and possibly-empty list inputs.
2. Add Monoid mapped bulk combination that returns `a` directly and uses `empty` for empty input.
3. Preserve backward compatibility for existing Semigroup and Monoid call sites.
4. Preserve or improve specialization opportunities for performance-sensitive instances (especially list concatenation).
5. Update list-backed Foldable paths to use the new API and avoid intermediate mapped list allocation.

## Non-goals

1. Redesigning algebraic laws beyond current Semigroup/Monoid laws.
2. Refactoring every collection fold implementation in this issue.
3. Adding new higher-kinded abstractions or changing typeclass receiver style.
4. Removing existing APIs such as `combine_all_option`, `combine_all`, or `fold_map`.

## Proposed Design

### Semigroup API

1. Add `combine_map_all(inst: Semigroup[a], head: b, tail: List[b], fn: b -> a) -> a` for non-empty mapped combination.
2. Add `combine_map_all_option(inst: Semigroup[a], items: List[b], fn: b -> a) -> Option[a]` as the empty-aware wrapper.
3. Extend Semigroup internals with a mapped non-empty specialization hook so instances can optimize mapped aggregation directly.
4. Keep `semigroup_specialized` source-compatible by deriving the mapped hook with a safe default.
5. Add a new specialized constructor (for example `semigroup_specialized_map_all`) that accepts the mapped hook explicitly for performance-critical instances.
6. Keep `combine_all_option` API and semantics unchanged; enforce coherence through tests that compare it to mapped identity usage.

### Monoid API

1. Add `combine_map_all(inst: Monoid[a], items: List[b], fn: b -> a) -> a`.
2. Implement it as:
3. If `items` is empty, return `empty(inst)`.
4. If non-empty, call `Semigroup.combine_map_all` through `monoid_to_semigroup`.
5. Re-express `combine_all(inst, items)` via `combine_map_all(inst, items, item -> item)`.
6. This removes unnecessary `Option` construction/teardown in the non-empty path while preserving existing external behavior.

### Foldable Integration

1. Keep Foldable public API unchanged.
2. Update list-backed `fold_map` implementations that currently do `items.map_List(fn)` followed by monoid combine.
3. Route those paths through `Monoid.combine_map_all` to fuse mapping and accumulation.
4. Initial call-site targets:
5. `src/Zafu/Abstract/Foldable.bosatsu` (`foldable_List`)
6. `src/Zafu/Abstract/Instances/Predef.bosatsu` (`foldable_List`)
7. `src/Zafu/Collection/Chain.bosatsu` (the `WrapList` branch inside `fold_map`)

### Predef Specialization

1. `semigroup_List` should provide a mapped specialization to preserve linear-time concatenation behavior when combining mapped list chunks.
2. The specialization should avoid left-associated repeated concat and avoid allocating a full mapped `List[List[a]]` where possible.
3. Existing instance names and exports remain unchanged.

### Coherence Invariants

1. For any Semigroup instance and mapping `fn`, `combine_map_all_option(items, fn)` should match the result of mapped-then-`combine_all_option`.
2. For non-empty input, `combine_map_all(head, tail, fn)` should match unwrapping `combine_map_all_option([head, *tail], fn)`.
3. `Monoid.combine_all(items)` should remain equivalent to `Monoid.combine_map_all(items, item -> item)`.

## Implementation Plan

1. Phase 1: Semigroup core.
2. Add new mapped APIs and internal hook plumbing in `src/Zafu/Abstract/Semigroup.bosatsu`.
3. Add default derivation path and specialized constructor path.
4. Add tests for empty/non-empty behavior, coherence, and specialization dispatch.
5. Phase 2: Monoid adoption.
6. Add `combine_map_all` to `src/Zafu/Abstract/Monoid.bosatsu`.
7. Re-implement `combine_all` via mapped identity.
8. Add tests for empty/non-empty behavior and projection through specialized semigroup.
9. Phase 3: Foldable call-site updates.
10. Replace mapped-list allocation call sites with `Monoid.combine_map_all` in:
11. `src/Zafu/Abstract/Foldable.bosatsu`
12. `src/Zafu/Abstract/Instances/Predef.bosatsu`
13. `src/Zafu/Collection/Chain.bosatsu`
14. Phase 4: Predef specialization and validation.
15. Update `semigroup_List` in `src/Zafu/Abstract/Instances/Predef.bosatsu` to provide mapped specialization.
16. Run `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/127-improve-semigroup-design.md` documents this architecture, plan, and rollout.
2. `Semigroup` exports mapped bulk APIs for non-empty and optional list inputs.
3. Existing Semigroup constructor usage remains source-compatible (no mandatory signature churn at existing call sites).
4. A specialization path exists for mapped bulk combine and is usable by `semigroup_List`.
5. `Monoid` exports `combine_map_all` and `combine_all` delegates to identity-mapped usage.
6. `Foldable` public API remains unchanged.
7. The three list-backed `fold_map` call sites listed above no longer allocate an intermediate `items.map_List(fn)` just to combine.
8. `semigroup_List` retains linear-time behavior for large concatenation workloads.
9. Coherence tests pass for Semigroup and Monoid mapped/non-mapped equivalents.
10. Existing tests continue passing, and no existing exported names are removed.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass before merge.

## Risks and Mitigations

1. Risk: semantic drift between old and new combine paths.
Mitigation: add explicit coherence tests comparing mapped and non-mapped results.
2. Risk: accidental performance regression for list concatenation if mapped specialization is not implemented.
Mitigation: implement and test `semigroup_List` mapped specialization in `Predef`.
3. Risk: larger blast radius from Semigroup internal shape changes.
Mitigation: keep existing constructor API stable and add a new opt-in specialized constructor.
4. Risk: behavior differences in derived combinators (`reverse`, `intercalate`) after adding mapped hooks.
Mitigation: preserve existing behavior with targeted regression tests for those combinators.

## Rollout Notes

1. Land as an additive API change on `main`.
2. Merge in order: Semigroup core, Monoid, Foldable call-site usage, then instance specialization cleanup.
3. Keep old APIs (`combine_all_option`, `combine_all`, `fold_map`) intact so downstream code does not require migration.
4. Note in PR description that new mapped APIs are the preferred path for list-backed fold-map implementations.
5. Follow-up (optional): extend mapped call-site adoption to other modules where mapped lists are still allocated before monoid combination.
