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
depends_on: []
estimated_size: M
generated_at: 2026-04-09T22:48:40Z
---

# Design: migrate Hash typeclass to use Int64 not Int

_Issue: #207 (https://github.com/johnynek/zafu/issues/207)_

## Summary

Migrate `Hash` to `Int64` while keeping canonical 61-bit hashes, moving `HashMap` and `HashSet` hot-path hashing and bitmap math onto `Int64`, and validating the change with stronger invariant- and property-driven coverage.

## Status
Planned. Merging this doc is the planned milestone for issue #207; implementation can continue on the same child issue afterward.

## Context
`Zafu/Abstract/Hash` currently models `Hash[a]` as an `a -> Int` dictionary, and the exported helpers in `Hash`, `Predef`, `HashMap`, and `HashSet` all assume `Int`-typed hash values.
`HashMap` and `HashSet` already use `Int64` for array indexing, but their cached entry hashes, node bitmaps, and collection-hash accumulators are still `Int`. That keeps the hottest hash-table paths on unbounded integers even though Bosatsu exposes a dedicated `Int64` API.
Issue #207 asks for a repo-wide migration of the Hash typeclass to `Int64`, plus an audit of `HashMap` and `HashSet` so their internal hashing work uses `Int64` wherever it is actually on the hot path.

## Goals
1. Make `Hash[a]` produce `Int64` rather than `Int`.
2. Preserve Eq/Hash coherence and deterministic non-cryptographic hashing semantics.
3. Keep a canonical non-negative 61-bit hash domain so HAMT fragmenting stays stable and sign handling remains simple.
4. Move `HashMap` and `HashSet` cached hashes, bitmap math, and collection-hash accumulators to `Int64`.
5. Update in-repo hash producers and consumers with explicit `Int` hash annotations so the repo compiles cleanly after the type change.
6. Strengthen invariant-driven tests so the migration is validated by behavior, not just by type-checking.

## Non-goals
1. Changing public collection sizes or user-facing count APIs from `Int` to `Int64`.
2. Preserving exact numeric hash outputs across the migration. Behavioral properties matter; specific hash codes do not.
3. Introducing cryptographic hashing or stronger collision-resistance guarantees.
4. Reworking unrelated collection algorithms outside of hash-related hot paths.
5. Carrying a compatibility mode where both `Hash[a] -> Int` and `Hash[a] -> Int64` coexist.

## Architecture

### Hash Core
1. Change `Zafu/Abstract/Hash.bosatsu` so the stored hash function and `hash(inst, value)` both use `Int64`.
2. Keep the public canonical hash range as `[0, 2^61 - 1)`. This preserves the current invariant that exported hashes are non-negative and leave the sign bit clear.
3. Keep `hash_specialized` as the fast constructor for already-canonical `Int64` hash functions.
4. Keep an adapter constructor for simple `Int` projections so instances like `hash_Int` and `hash_Char` do not need repetitive conversion boilerplate. That adapter should normalize in `Int`, then narrow only after the value is known to fit in the canonical 61-bit domain.
5. Migrate `normalize_61`, `mix_61`, and `finish_61` to Int64-backed helpers. Their hot path should use Bosatsu `Int64` operations only; any wider `Int` arithmetic should be limited to compatibility adapters or reference tests.
6. Keep domain separation via seeds and tags, but store those constants as `Int64` so downstream hash builders never widen just to mix constructor or collection tags.
7. `finish_61` should continue accepting collection sizes and tuple arities from public `Int` APIs, but it should reduce those counts into the 61-bit domain before narrowing to `Int64`. That avoids silent truncation while keeping public size APIs unchanged.

### HashMap and HashSet
1. In `src/Zafu/Collection/HashMap.bosatsu` and `src/Zafu/Collection/HashSet.bosatsu`, change cached `Entry.hash` and `Collision.hash` fields from `Int` to `Int64`.
2. Change HAMT bitmaps from `Int` to `Int64` as well. Only the low 32 bits are semantically used, but moving them to `Int64` keeps bitwise hot paths off boxed `Int`.
3. Keep fragment shift counts and public `size` as `Int`, since those are already natural `Int` APIs and are not the hot-path hash payload. The intended split is: hash payloads and bitmaps are `Int64`; loop fuel and public counts stay `Int`.
4. Rework helpers such as `fragment`, `bitpos`, `has_bit`, and `bitmap_index` around `Int64` bitwise operations and `popcount_Int64`.
5. Move collection-hash adapters for maps and sets to `Int64` accumulators. Their behavior should stay the same at the semantic level: equal collections hash equally, and map or set hash aggregation remains order-independent with respect to traversal or insertion order.
6. Expand the inline invariant helpers so they check more than cached size. They should validate cached-hash correctness, collision-node consistency, bitmap and array alignment, and canonical hash range.

### Wider Call-Site Sweep
1. `src/Zafu/Abstract/Instances/Predef.bosatsu` must be updated so all primitive and composite hash builders return `Int64`, including tuple arities, list and string accumulation, and `Dict` hashing.
2. `src/Zafu/Collection/Vector.bosatsu` has explicit `Int` hash accumulators and should be migrated to `Int64`.
3. `src/Zafu/Control/Result.bosatsu`, `src/Zafu/Control/PartialResult.bosatsu`, and `src/Zafu/Text/Parse/Error.bosatsu` each define local hash builders with explicit `Int` types and will need direct edits.
4. Generic `hash_by` users that do not spell out raw hash types should mostly recompile once the core API changes, but they still need coverage in the validation sweep.

## Behavioral Properties and Invariants
1. Eq/Hash coherence remains mandatory: whenever `eq(x, y)` holds, `hash(x) == hash(y)` must also hold.
2. Exported hashes stay in the canonical 61-bit non-negative domain `[0, 2^61 - 1)`.
3. Hash results remain deterministic across supported backends because the implementation uses Bosatsu-defined `Int64` operations rather than host-sized `Int` behavior.
4. `HashMap` and `HashSet` public semantics do not change: lookup, membership, update, alter, delete, transform, union, intersection, and difference must keep the same logical behavior as before.
5. Every cached HAMT entry hash equals a fresh recomputation from the stored `Hash[k]` dictionary and key.
6. Collision nodes contain only entries with the same cached hash, and bitmap nodes keep array sizes aligned with the popcount of their respective bitmaps.
7. Equal sets and maps must hash equally regardless of insertion order or traversal order. Sequence-like structures such as lists, vectors, tuples, and constructor-tagged sum types must remain order-sensitive or constructor-sensitive where they are today.
8. Exact numeric hash values are not a post-change invariant. Tests should pin laws and semantics, not old raw hash literals.

## Implementation Plan
1. Update `src/Zafu/Abstract/Hash.bosatsu` first. Change the core type, change exported helper signatures, and add an internal or test-only reference implementation so Int64 helper behavior can be checked against a simpler oracle.
2. Sweep `src/Zafu/Abstract/Instances/Predef.bosatsu` next. This is the widest call-site surface because it owns primitive hashes, list and string hashing, tuple hashing, and `Dict` hashing.
3. Migrate `src/Zafu/Collection/HashMap.bosatsu` and `src/Zafu/Collection/HashSet.bosatsu` together. They share the same HAMT representation pattern, so the cached-hash and bitmap conversion should stay structurally parallel.
4. Update the remaining direct hash producers and consumers in `src/Zafu/Collection/Vector.bosatsu`, `src/Zafu/Control/Result.bosatsu`, `src/Zafu/Control/PartialResult.bosatsu`, and `src/Zafu/Text/Parse/Error.bosatsu`.
5. Run a repo-wide compile and test sweep with `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` only after the full type migration is in place. Partial rollout is not useful because the repo will be in a mixed, non-compiling state in the middle of the change.

## Test Plan

### Property-Check Coverage
1. Add randomized property checks for the new Int64 hash helpers in `src/Zafu/Abstract/Hash.bosatsu`. The key property is that canonicalization and mixing satisfy the range invariant and remain coherent with a simple reference implementation over many random inputs.
2. Keep or expand hash law coverage for predef instances so randomized tests continue to assert Eq/Hash coherence and range invariants for primitives and common composites.
3. Keep the model-based randomized operation tests in `HashMap` and `HashSet`, but run them against the strengthened HAMT invariants after every step. Those properties are the right place to validate that changing cached-hash types and bitmap types did not change table semantics.
4. Add permutation-style properties for map and set hash adapters so equal collections built from different insertion orders still hash equally.
5. Keep randomized collection-hash parity properties such as vector-versus-list hashing where they already exist, because they protect against accidental semantic drift while accumulator types change.

### Narrow Case Coverage
1. Keep explicit Float64 regression tests for NaN canonicalization and signed zero, since those are small, sharp cases where a single example is more valuable than a broad generator.
2. Add boundary tests around raw negative inputs, `0`, `-1`, `2^61 - 2`, `2^61 - 1`, and fragment boundaries near shifts `0`, `5`, and `60`. These are the places most likely to expose sign, mask, or reduction mistakes.
3. Keep direct collision-node insert, remove, and compression tests in `HashMap` and `HashSet`. Randomized model tests are good at finding semantic drift, but specific collapse cases are still best captured as named regressions.
4. Keep explicit cross-hash bulk-operation tests where left and right collections use different hash dictionaries. Those examples pin the intended fallback behavior more clearly than a generator alone.
5. Keep small constructor-tagging tests in modules like `Result`, `PartialResult`, and `Text/Parse/Error` so refactors do not accidentally merge distinct hash domains.

## Acceptance Criteria
1. `docs/design/207-migrate-hash-typeclass-to-use-int64-not-int.md` lands with this migration plan and marks the planned milestone for issue #207.
2. `Hash[a]` and `hash(inst, value)` are Int64-backed, and the repo has a supported constructor path for both already-Int64 hash builders and simple Int projections.
3. Exported hash helpers enforce the canonical `[0, 2^61 - 1)` range after the migration.
4. `Predef` hash instances and the tuple, list, string, and dict builders compile and emit `Int64` hashes.
5. `HashMap` and `HashSet` store cached hashes as `Int64`, use `Int64` bitmaps in their HAMT internals, and keep public behavior unchanged.
6. Strengthened HAMT invariant helpers validate cached-hash correctness, collision-node consistency, bitmap and popcount alignment, and exact cached size.
7. Model-based property tests for `HashMap` and `HashSet` continue to pass for default, collision-heavy, and differing-hash-dictionary scenarios.
8. Case-based tests cover Float64 special cases, boundary normalization cases, and named collision or compression regressions.
9. Tests stop asserting legacy raw `Int` hash literals unless the value is still intentionally guaranteed after the migration.
10. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass on the full migration branch.

## Risks and Mitigations
1. Risk: the new Int64 helper math accidentally changes canonicalization or mixing invariants. Mitigation: add a simple reference oracle in tests and compare the Int64 helpers against it across randomized inputs.
2. Risk: mixed `Int` and `Int64` conversions in HAMT code introduce fragment or bitmap bugs. Mitigation: keep the type split explicit, strengthen invariants, and add boundary tests around fragment extraction and node compression.
3. Risk: a repo-wide type migration misses smaller modules with local `Int`-typed hash helpers. Mitigation: do a deliberate search over `hash_from_fn`, `hash_specialized`, `hash_Hash`, `mix_61`, `finish_61`, and local `def hash_* -> Int` helpers before validation.
4. Risk: performance gains are diluted if hot paths still bounce between `Int` and `Int64`. Mitigation: make cached hashes, bitmaps, and collection-hash accumulators Int64-first, and treat `Int` as an API boundary type rather than a storage type.
5. Risk: downstream callers experience source breakage because raw hash types change. Mitigation: land the migration atomically, keep the convenience constructor for Int projections, and update tests and docs to talk about laws rather than concrete old hash numbers.

## Rollout Notes
1. This design doc merge is the planned milestone for the issue; implementation can continue afterward without reopening design.
2. The code change should be landed as one compile-green migration PR off `main`. A half-converted repo is not a useful intermediate state.
3. No feature flag or dual-type rollout is planned. The type system itself is the migration boundary.
4. If the migration changes concrete hash outputs, that is acceptable so long as the invariants above continue to hold and collection behavior is unchanged.
