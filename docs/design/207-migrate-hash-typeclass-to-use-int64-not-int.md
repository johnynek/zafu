---
issue: 207
priority: 3
touch_paths:
  - docs/design/207-migrate-hash-typeclass-to-use-int64-not-int.md
  - src/Zafu/Abstract/Hash.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Collection/HashMap.bosatsu
  - src/Zafu/Collection/HashSet.bosatsu
  - src/Zafu/Collection/Vector.bosatsu
  - src/Zafu/Control/Result.bosatsu
  - src/Zafu/Control/PartialResult.bosatsu
  - src/Zafu/Text/Parse/Error.bosatsu
  - src/Zafu/Collection/NonEmptyList.bosatsu
  - src/Zafu/Collection/NonEmptyChain.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-04-18T18:22:35Z
---

# Design: migrate Hash typeclass to use Int64 not Int

_Issue: #207 (https://github.com/johnynek/zafu/issues/207)_

## Summary

Plan the Hash Int64 migration, move HashMap and HashSet hot-path internals onto Int64, and validate the change with stronger invariant-driven tests.

## Context
`Zafu/Abstract/Hash` currently stores `hash_fn: a -> Int`, and the public helpers in `Hash`, `Predef`, `HashMap`, `HashSet`, and downstream adapters assume `Int`-typed hashes.
`HashMap` and `HashSet` already use `Int64` for array indexing, but their cached entry hashes, collision hashes, HAMT bitmaps, and unordered collection-hash accumulators still use `Int`.
Issue #207 asks for two related changes: move the `Hash` typeclass itself to `Int64`, and audit `HashMap` and `HashSet` so the hot path uses `Int64` wherever the Bosatsu `Int64` API makes that practical.
The Bosatsu `Int64` docs provide the operations needed for this sweep: arithmetic and bitwise operators, `mod_Int64`, `popcount_Int64`, `shift_right_unsigned_Int64`, and explicit conversions such as `int_to_Int64` and `int_low_bits_to_Int64`.
Merging this design doc is the planned milestone for this lane. Implementation may continue afterward on the same child issue.

## Problem
The current design pays repeated `Int` and `Int64` conversion costs in the most hash-heavy code paths.
That split also hides important invariants. `HashMap` and `HashSet` currently validate cached size in tests, but they do not check cached-hash correctness, bitmap shape, collision-node consistency, or canonical hash range.
A type-only migration would not be enough. If `Hash[a]` changes to `Int64` while HAMT internals and collection hash adapters keep widening back to `Int`, the repo absorbs the churn without getting the intended simplification or performance benefit.

## Goals
1. Change `Hash[a]` so the stored hash function and `hash(inst, value)` return `Int64`.
2. Preserve Eq/Hash coherence and deterministic hashing semantics across supported backends.
3. Keep the canonical hash domain as `[0, 2^61 - 1)`.
4. Move `HashMap` and `HashSet` cached hashes, HAMT bitmaps, and unordered collection-hash accumulators to `Int64`.
5. Update in-repo hash producers and consumers that still assume `Int` hashes.
6. Strengthen invariant-driven tests so the migration is validated by properties, not only by compilation.

## Non-goals
1. Changing public collection sizes or other user-facing count APIs from `Int` to `Int64`.
2. Keeping a long-term dual public hash result API where both `Int` and `Int64` are primary results.
3. Redesigning unrelated collection algorithms outside hash-related hot paths.
4. Promising that every concrete numeric hash output is part of the public contract beyond the existing coherence and domain guarantees.
5. Introducing cryptographic hashing or stronger collision-resistance guarantees.

## Proposed Design

### Hash Core API
1. Change `src/Zafu/Abstract/Hash.bosatsu` to `struct Hash[a](hash_fn: a -> Int64, eq_inst: Eq[a])` and make `hash(inst, value) -> Int64`.
2. Make `hash_specialized` the Int64-native constructor for already-canonical hash functions.
3. Retain a compatibility constructor for simple `Int`-producing code paths. The intended shape is to keep `hash_from_fn` as the adapter that normalizes an `a -> Int` into the canonical `Int64` domain, so existing simple instances do not gain repetitive conversion boilerplate.
4. Keep `mix_61` and `finish_61` as the main exported composition helpers, but move their working representation to `Int64`.
5. Keep tuple arity and collection size inputs as `Int` at the public boundary. `finish_61` should convert those counts only after an explicit fit check or reduction into the canonical domain so the migration never relies on silent truncation.
6. Keep `hash_to_Eq`, `hash_by`, and `laws_Hash`, updating their comparisons and range checks to `Int64`.

### 61-bit Int64 Arithmetic
1. Keep the existing modulus `M = 2^61 - 1` and the existing seed and tag domain-separation strategy. Move those constants to `Int64` so downstream hash builders stay in one representation.
2. Preserve the canonical exported invariant that every public hash lies in `[0, M)`.
3. Implement an internal `reduce_61_i64` helper using the Mersenne identity `2^61 ≡ 1 (mod M)`. For bounded non-negative intermediates, fold high bits back into the low 61 bits and subtract `M` when needed.
4. Implement a dedicated multiply-reduce helper for `mix_61` that stays Int64-first. It should use `Int64` limb decomposition and reduction rather than widening the hot path back to arbitrary-precision `Int`.
5. Keep `normalize_61` as the compatibility adapter for arbitrary `Int` inputs, but Hash internals and collection internals should prefer Int64-native reduction helpers once data is in the canonical domain.
6. Validate the Int64 arithmetic against a clearer `Int`-based oracle in tests so the subtle math stays explainable and checkable.

### HashMap and HashSet Internals
1. In `src/Zafu/Collection/HashMap.bosatsu` and `src/Zafu/Collection/HashSet.bosatsu`, change cached `Entry.hash` and `Collision.hash` from `Int` to `Int64`.
2. Change `Indexed.data_bitmap` and `Indexed.node_bitmap` from `Int` to `Int64`. Only the low 32 bits are semantically used, but representing them as `Int64` avoids bouncing between numeric types on the same path.
3. Keep public `size`, loop fuel, and shift counts as `Int`. The intended split is: payload hashes and bitmaps are `Int64`; public counts remain `Int`.
4. Rework helpers such as `fragment`, `bitpos`, `has_bit`, and `bitmap_index` around `Int64` bitwise operations, `popcount_Int64`, and `shift_right_unsigned_Int64` where sign-sensitive right shift would otherwise be fragile.
5. Keep map and set hash adapters order-insensitive. The current `sum_acc` plus `xor_acc` strategy can stay, but the accumulators and XOR path should become `Int64` so equal maps or sets hash equally regardless of insertion order.
6. Strengthen the test-only invariant helpers so they validate more than cached size: cached-hash correctness, collision-node consistency, bitmap disjointness, bitmap and popcount alignment, canonical range, and exact root size.

### Wider Call-Site Sweep
1. `src/Zafu/Abstract/Instances/Predef.bosatsu` is the largest direct migration surface. Primitive hashes, string and list hashing, option hashing, tuple hashing, and dict hashing all need Int64-backed helpers and constants.
2. `src/Zafu/Collection/Vector.bosatsu` has explicit hash accumulators and a parity property against list hashing. It needs a direct migration to Int64-backed composition.
3. `src/Zafu/Control/Result.bosatsu`, `src/Zafu/Control/PartialResult.bosatsu`, and `src/Zafu/Text/Parse/Error.bosatsu` each define local constructor-tagged hash builders and currently assume `Int`-typed helper outputs.
4. Inline tests in `src/Zafu/Collection/NonEmptyList.bosatsu` and `src/Zafu/Collection/NonEmptyChain.bosatsu` compare hash results with `eq_Int`; those checks need to move to the Int64 equivalents.
5. The migration should search explicitly for `hash_from_fn`, `hash_specialized`, `mix_61`, `finish_61`, `.eq_Int` on hash values, and `eq_Int(hash_Hash(...), ...)` so fallout is handled deliberately instead of reactively.

## Behavioral Properties and Invariants
1. Eq/Hash coherence remains mandatory: if `eq(x, y)` holds, then `hash(x) == hash(y)` must also hold.
2. Every exported hash value remains in `[0, 2^61 - 1)`.
3. Hash results remain deterministic across supported backends because the implementation is defined in terms of Bosatsu `Int64` operations and explicit reductions, not host-sized integer behavior.
4. Sequence-like structures remain order-sensitive. That includes lists, vectors, tuples, and constructor-tagged sum types.
5. Unordered collection adapters remain order-insensitive. Equal `HashMap` and `HashSet` values must hash equally regardless of insertion order or traversal order.
6. `HashMap` and `HashSet` public semantics do not change. Lookup, membership, update, alter, remove, transform, union, intersection, and difference keep the same logical behavior as before.
7. Every cached HAMT entry hash equals a fresh recomputation from the stored `Hash[k]` dictionary and the stored key.
8. Collision nodes contain only entries that share the collision hash, and they never persist as empty or single-entry nodes after compression.
9. Indexed-node invariants remain strict: `data_bitmap & node_bitmap == 0`, `entries.size == popcount(data_bitmap)`, and `children.size == popcount(node_bitmap)`.
10. Root size remains exact and equals the number of reachable entries.
11. The migration must not rely on lossy `Int -> Int64` narrowing for sizes, arities, or hash constants. Any such conversion must happen only after the value is known to fit or after explicit reduction into the 61-bit domain.

## Implementation Plan
1. Migrate `src/Zafu/Abstract/Hash.bosatsu` first. Change the core type signatures, add the Int64 reduction and multiply-reduce helpers, and keep a simple reference implementation in tests so the new arithmetic can be checked against a clearer oracle.
2. Sweep `src/Zafu/Abstract/Instances/Predef.bosatsu` next. This updates the broadest surface area and unblocks downstream modules that depend on predef hash instances.
3. Migrate `src/Zafu/Collection/HashMap.bosatsu` and `src/Zafu/Collection/HashSet.bosatsu` together. Their HAMT representations and property suites are intentionally parallel, so cached-hash and bitmap changes should stay structurally aligned.
4. Update the remaining direct hash producers and consumers in `src/Zafu/Collection/Vector.bosatsu`, `src/Zafu/Control/Result.bosatsu`, `src/Zafu/Control/PartialResult.bosatsu`, `src/Zafu/Text/Parse/Error.bosatsu`, `src/Zafu/Collection/NonEmptyList.bosatsu`, and `src/Zafu/Collection/NonEmptyChain.bosatsu`.
5. Run the repo-wide search for Int-specific hash comparisons and conversion leftovers before considering the migration complete.
6. Validate only once the full repo-wide type migration is in place. A half-converted branch is not a useful intermediate state because `Hash[a]` sits at the center of many modules.

## Test Strategy

### Property-Check Coverage
1. Add randomized properties in `src/Zafu/Abstract/Hash.bosatsu` for the new Int64 arithmetic helpers. The key checks are canonical range preservation, reduction idempotence, and agreement with a simpler `Int`-based oracle for randomly generated canonical inputs.
2. Keep or expand the hash-law checks in `src/Zafu/Abstract/Instances/Predef.bosatsu` so randomized coverage continues to assert Eq/Hash coherence, canonical range, constructor tagging, and sequence order sensitivity for common composite instances.
3. Keep the model-based randomized operation tests in `src/Zafu/Collection/HashMap.bosatsu` and `src/Zafu/Collection/HashSet.bosatsu`, but make every step also assert the strengthened HAMT invariants. Those properties are the right place to catch bugs introduced by cached-hash and bitmap type changes.
4. Add permutation-style properties for map and set hash adapters so collections built from different insertion orders still hash equally.
5. Keep the `Vector` parity property that `hash_Vector` agrees with list hashing, because it guards a meaningful downstream invariant while the shared hash helpers change underneath it.

### Narrow Case Coverage
1. Keep explicit `Float64` regressions for NaN canonicalization and signed zero. Those are small, sharp semantic cases where a named example is more valuable than a broad generator.
2. Add boundary tests for normalization and fragment extraction around `-1`, `0`, `2^61 - 2`, `2^61 - 1`, and the fragment-shift boundaries `0`, `5`, and `60`.
3. Keep direct collision-node insert, remove, and compression tests in `HashMap` and `HashSet`. Randomized model tests are good at finding semantic drift, but node-collapse edge cases are still best pinned as named regressions.
4. Keep explicit cross-dictionary bulk-operation tests where left and right collections use different hash dictionaries. Those examples pin the intended fallback behavior more clearly than a generator alone.
5. Keep constructor-tagging checks in `Result`, `PartialResult`, and `Text/Parse/Error` so refactors do not accidentally collapse distinct variants into the same hash domain.

## Acceptance Criteria
1. `docs/design/207-migrate-hash-typeclass-to-use-int64-not-int.md` lands and serves as the planned milestone for issue #207.
2. `Hash[a]` and `hash(inst, value)` are Int64-backed, and the repo still has a supported constructor path for both Int64-native hash builders and simple Int projections.
3. The 61-bit helper pipeline is Int64-first in the hot path, including an overflow-safe multiply-reduce strategy for `mix_61`.
4. All exported hash helpers continue to enforce the canonical `[0, 2^61 - 1)` range.
5. `Predef` hash instances and composite hash builders compile and emit `Int64` hashes.
6. `HashMap` and `HashSet` store cached hashes and HAMT bitmaps as `Int64`, while preserving existing public behavior.
7. Strengthened HAMT invariants validate cached-hash correctness, collision-node consistency, bitmap alignment, bitmap disjointness, canonical range, and exact cached size.
8. Property tests continue to pass for default, collision-heavy, and differing-hash-dictionary scenarios in `HashMap` and `HashSet`, and the `Vector` hash parity property still holds.
9. Case-based tests cover `Float64` special cases, 61-bit boundary normalization, constructor tagging, and named collision and compression regressions.
10. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass on the full migration branch.

## Risks and Rollout Notes
1. Risk: the Int64 multiply-reduce helper is subtle and easy to get wrong. Mitigation: isolate it in `Hash`, validate it against a simpler `Int`-based oracle, and add targeted boundary tests in addition to randomized coverage.
2. Risk: mixed `Int` and `Int64` conversions in HAMT code reintroduce fragment or bitmap bugs. Mitigation: keep the type split explicit, strengthen invariants, and search specifically for Int-specific hash comparisons and leftover narrowing paths during the sweep.
3. Risk: the migration achieves the public type change but leaves performance on the table if hot loops still widen back to `Int`. Mitigation: keep cached hashes, bitmaps, fragment helpers, and unordered collection-hash accumulators Int64-first, and treat any remaining `Int` arithmetic as a deliberate boundary or compatibility path.
4. Risk: downstream callers or inline tests depend on the old raw hash type. Mitigation: land the code change atomically, preserve a supported Int-adapter constructor path, and update tests to talk about coherence and invariants rather than `Int`-specific helper APIs.
5. The design doc merge is the planned milestone for this lane. Implementation can continue afterward from the same child issue without reopening design.
6. The implementation branch should stay close to `main` while this migration is in flight, because there is no useful long-lived mixed `Int` and `Int64` state for `Hash`.
