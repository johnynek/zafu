---
issue: 40
priority: 2
touch_paths:
  - docs/design/40-zafu-collection-hashmap.md
  - src/Zafu/Collection/HashMap.bosatsu
depends_on:
  - 34
estimated_size: L
generated_at: 2026-03-08T03:45:00Z
---

# Design: Zafu/Collection/HashMap (HAMT)

_Issue: #40 (https://github.com/johnynek/zafu/issues/40)_

## Summary

Add `Zafu/Collection/HashMap` as a persistent bitmap-indexed HAMT keyed by `Zafu/Abstract/Hash`. The API uses short names consistent with newer collection modules, keeps `size` O(1), provides expected O(1) / O(log32 n) key operations, and includes `transform(HashMap[k, v], (k, v) -> w) -> HashMap[k, w]` implemented as a shape-preserving value rewrite with no key rehashing.

## Status

Proposed

## Context

`Zafu/Collection` currently includes sequence and heap structures but no hash map. Issue #40 requests a high-performance HAMT implementation with a clean collection-style API and internal algorithms (not list-conversion wrappers). Since #34 introduced `Zafu/Abstract/Hash`, this module can own a `Hash[k]` dictionary and use it for coherent hashing/equality behavior across all key operations.

## Goals

1. Add `src/Zafu/Collection/HashMap.bosatsu` with a persistent HAMT representation.
2. Make lookup/insert/update/remove expected O(1) and structural O(log32 n), with O(1) `size`.
3. Expose a complete, efficient map API with short names and map-first argument order.
4. Implement `transform(map, fn)` by traversing existing nodes and rewriting only values, reusing key hashes and node shape.
5. Keep operations node-native (`filter`, `partition`, `union`, etc.) without list-conversion roundtrips.
6. Include property tests and invariants aligned with existing module testing style.

## Non-goals

1. Mutable/in-place hash map operations.
2. Ordered-map semantics (`Ord`-sorted iteration).
3. Key remapping APIs that require rehash/rebucket (`map_keys`) in initial scope.
4. Deterministic views/folds in this PR scope (`items`, `keys`, `values`, `to_List`, `foldl`, `foldr`).
5. Global prelude/re-export policy changes.

## Decision summary

1. `HashMap[k, v]` stores `Hash[k]` internally (same pattern as `Heap` storing `Ord`), so callers do not pass hashing on every operation.
2. Internal nodes use a bitmap-indexed HAMT (CHAMP-style split bitmaps for entries vs children) plus explicit collision nodes.
3. Each stored entry caches normalized key hash (`Int` in 61-bit domain from `Hash`), so deep operations and `transform` never recompute key hashes.
4. Structural updates are path-copy persistent updates with branch compression on delete.
5. Bulk operations use trie-native traversal rather than list-based intermediate conversions.
6. Cross-map operations are always correct; optimized structural merge is used when hash semantics are assumed shared, with a safe fallback otherwise.

## Proposed API (`Zafu/Collection/HashMap`)

Core type and constructors:

1. `HashMap`
2. `empty(hash_key: Hash[k]) -> HashMap[k, v]`
3. `singleton(hash_key: Hash[k], key: k, value: v) -> HashMap[k, v]`
4. `from_List(hash_key: Hash[k], items: List[(k, v)]) -> HashMap[k, v]`

Queries:

1. `size(map: HashMap[k, v]) -> Int`
2. `is_empty(map: HashMap[k, v]) -> Bool`
3. `contains_key(map: HashMap[k, v], key: k) -> Bool`
4. `get(map: HashMap[k, v], key: k) -> Option[v]`
5. `get_or(map: HashMap[k, v], key: k, on_missing: () -> v) -> v`

Persistent updates:

1. `updated(map: HashMap[k, v], key: k, value: v) -> HashMap[k, v]`
2. `alter(map: HashMap[k, v], key: k, fn: Option[v] -> Option[v]) -> HashMap[k, v]`
3. `remove(map: HashMap[k, v], key: k) -> HashMap[k, v]`

Node-native transforms:

1. `transform(map: HashMap[k, v], fn: (k, v) -> w) -> HashMap[k, w]`
2. `map_values(map: HashMap[k, v], fn: v -> w) -> HashMap[k, w]` (derived from `transform`)
3. `filter(map: HashMap[k, v], pred: (k, v) -> Bool) -> HashMap[k, v]`
4. `partition(map: HashMap[k, v], pred: (k, v) -> Bool) -> (HashMap[k, v], HashMap[k, v])`

Bulk map operations:

1. `union_with(left: HashMap[k, v], right: HashMap[k, v], resolve: (k, v, v) -> v) -> HashMap[k, v]`
2. `intersection_with(left: HashMap[k, v], right: HashMap[k, w], combine: (k, v, w) -> x) -> HashMap[k, x]`
3. `difference(left: HashMap[k, v], right: HashMap[k, w]) -> HashMap[k, v]`
4. `union_with_assume_same_hash(...)` (explicit fast path; caller opt-in)

Typeclass adapters:

1. `eq(eq_value: Eq[v]) -> Eq[HashMap[k, v]]`
2. `hash(hash_value: Hash[v]) -> Hash[HashMap[k, v]]`

## Internal representation and invariants

Proposed internal shapes:

1. `struct Entry(hash: Int, key: k, value: v)`
2. `enum Node`
- `Indexed(data_bitmap: Int, entries: Array[Entry[k, v]], node_bitmap: Int, children: Array[Node[k, v]])`
- `Collision(hash: Int, entries: Array[Entry[k, v]])`
3. `enum HashMap`
- `Empty(hash_key: Hash[k])`
- `Root(hash_key: Hash[k], size: Int, root: Node[k, v])`

Key invariants:

1. `size` is exact and O(1) to read.
2. Every `Entry.hash` equals `hash(hash_key, entry.key)` normalized to the 61-bit domain.
3. `Indexed` node bitmaps and arrays are aligned: `entries.size == popcount(data_bitmap)` and `children.size == popcount(node_bitmap)`.
4. `Collision(hash, entries)` has `entries.size >= 2` and all entries share that hash.
5. No empty internal nodes; deletes collapse degenerate nodes where possible.
6. Map hash/equality semantics are fixed by stored `Hash[k]`.

## Core algorithms

Hash navigation helpers:

1. `fragment(entry_hash, shift)` returns the 5-bit branch fragment at depth `shift` (`shift` steps by 5).
2. `bitpos(fragment)` returns the branch bit for bitmap indexing.
3. `bitmap_index(bitmap, bit)` returns packed-array index via popcount of lower bits.

Lookup (`get` / `contains_key`):

1. Compute `h = hash(hash_key, key)` once.
2. Descend by fragment/bitmap tests.
3. Compare keys only at candidate entries (`Eq` from `hash_to_Eq(hash_key)`).
4. Collision nodes do linear scan on usually-small same-hash bucket.

Insert/update (`updated` / `alter`):

1. Compute key hash once; path-copy along traversal.
2. Entry match (`same hash + eq key`) replaces value in place (persistent array copy only on touched node).
3. Entry clash with different key promotes to child branch or collision node as required.
4. Returns `(new_node, size_delta)` to keep root size exact without a second traversal.

Remove:

1. Path-copy descent to target.
2. On deletion, collapse nodes:
- remove empty child references
- compress single-entry/single-child indexed nodes when safe
- collapse collision node of size 1 back to entry form
3. Return unchanged map when key not present.

`transform` (required operation):

1. Traverse node tree and rebuild with identical shape metadata.
2. For each entry: keep `hash` and `key`, replace `value` with `fn(key, value)`.
3. Do not call `hash(hash_key, key)` during traversal.
4. Complexity: O(n) time, O(log32 n) stack/recursion depth, shape-preserving output.

Filter/partition:

1. Explicit stack traversal over node arrays.
2. `filter`/`partition` reuse remove/collapse helpers to maintain invariants.

Bulk operations:

1. `union_with_assume_same_hash`: node-wise bitmap merge; expected O(n + m).
2. `union_with` default: safe fallback by folding right into left using left semantics (correct for mismatched hash dictionaries).
3. `intersection_with` and `difference`: trie-native when possible, fallback otherwise.

## Complexity targets

1. `size`, `is_empty`: O(1)
2. `get`, `contains_key`, `updated`, `alter`, `remove`: expected O(1), structural O(log32 n), worst-case O(n) under extreme collisions
3. `transform`, `filter`, `partition`: O(n)
4. `from_List`: O(n) expected (amortized inserts)
5. `union_with_assume_same_hash`: O(n + m) expected
6. `union_with` safe fallback: O(m log32(n + 1))

## Implementation plan

Phase 1: module skeleton and node math

1. Add `src/Zafu/Collection/HashMap.bosatsu` exports and opaque type.
2. Implement bitmap helpers, entry helpers, and invariants.
3. Implement `empty`, `singleton`, `size`, `is_empty`.

Phase 2: core key operations

1. Implement `get`, `contains_key`, `get_or`.
2. Implement `updated`, `alter`, `remove` with path-copy + compression.
3. Add deterministic sanity tests for replace/delete/collision behavior.

Phase 3: traversal and transform

1. Implement `transform` and `map_values` as node-native traversals.
2. Implement `filter` and `partition` without list roundtrip.

Phase 4: bulk ops and adapters

1. Implement `union_with`, `intersection_with`, `difference`.
2. Add opt-in `union_with_assume_same_hash` fast path.
3. Implement `eq` and `hash` adapters coherent with map semantics.

Phase 5: validation

1. Add property tests (random operation sequences vs simple model).
2. Validate with:
- `./bosatsu lib check`
- `./bosatsu lib test`
- `scripts/test.sh`

## Acceptance criteria

1. `docs/design/40-zafu-collection-hashmap.md` exists with this architecture and rollout plan.
2. `src/Zafu/Collection/HashMap.bosatsu` exists and exports the proposed API (or a documented strict subset implemented in phase order).
3. `size` is cached and O(1).
4. `get`/`contains_key`/`updated`/`remove` are implemented by HAMT traversal, not via `to_List` conversion.
5. `alter` supports insert/update/delete in one operation.
6. `transform(HashMap[k, v], (k, v) -> w) -> HashMap[k, w]` preserves trie shape and reuses cached entry hashes.
7. `transform` implementation does not invoke key hashing during traversal.
8. `from_List` uses last-write-wins semantics for duplicate keys.
9. Collision nodes are handled correctly (same-hash distinct keys remain addressable).
10. Delete path compression preserves invariants and exact size.
11. Bulk operations are correct for both same-hash fast path and safe fallback path.
12. `eq`/`hash` adapters are coherent with key/value equality semantics.
13. Property tests cover random insert/update/remove/get sequences and collision-heavy cases.
14. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and mitigations

1. Risk: bitmap index/popcount bugs can silently misplace entries.
Mitigation: heavy property tests plus invariant checks after random operation sequences.

2. Risk: pathological hash collisions degrade to linear behavior.
Mitigation: dedicated collision node representation, targeted tests, and documented worst-case complexity.

3. Risk: cross-map operations with different `Hash[k]` dictionaries can be incorrect if merged structurally.
Mitigation: safe fallback path as default; make structural fast path explicit (`*_assume_same_hash`).

4. Risk: implementation drift reintroduces list-based intermediate conversions.
Mitigation: keep transform/filter implementations node-native and add regression tests guarding direct traversal behavior.

5. Risk: module size/complexity becomes hard to maintain.
Mitigation: keep clear internal helper boundaries (bitmap math, node edits, traversal, bulk ops) and document invariants near helpers.

## Rollout notes

1. Land as additive module on `main`; no breaking changes to existing collections.
2. Ship in phases: core map first, then traversal/transform, then bulk ops fast paths.
3. Keep internal node constructors unexported so representation can evolve without API breakage.
4. Defer deterministic views/folds to follow-up issues.
5. After merge, profile large-map workloads and refine constants/helpers where benchmarks show hot spots.

## Out of scope (initial release)

1. Mutable/transient builders.
2. Ordered-map APIs.
3. Key remapping APIs (`map_keys`) that require full rehash and repartition.
