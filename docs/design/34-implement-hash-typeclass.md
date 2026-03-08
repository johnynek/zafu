---
issue: 34
priority: 3
touch_paths:
  - docs/design/34-implement-hash-typeclass.md
  - src/Zafu/Abstract/Hash.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-08T01:04:10Z
---

# Design: implement Hash typeclass (#34)

_Issue: #34 (https://github.com/johnynek/zafu/issues/34)_

## Summary

Adds a full design doc for introducing `Zafu/Abstract/Hash` plus coherent `Predef` hash instances for all existing predef types, with a 61-bit positive hash domain, ordered composition strategy, acceptance criteria, risks, and rollout notes.

---
issue: 34
priority: 2
touch_paths:
  - docs/design/34-implement-hash-typeclass.md
  - src/Zafu/Abstract/Hash.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
depends_on:
  - 28
estimated_size: M
generated_at: 2026-03-08T02:15:00Z
---

# Design: implement Hash typeclass

_Issue: #34 (https://github.com/johnynek/zafu/issues/34)_

## Summary

Add `Zafu/Abstract/Hash` and `Predef` Hash instances for every type that already has `Eq`/`Ord`, using deterministic 61-bit non-negative hash values and an order-sensitive composition strategy for tuples and lists.

## Status

Proposed

## Context

`Eq` and `Ord` already exist with opaque dictionary structs, constructor helpers, accessors, and law-check helpers. `Predef` currently provides `eq_*`/`ord_*` instances for:

1. `Unit`, `Bool`, `Char`, `Comparison`, `Int`, `Float64`, `String`
2. `Option[a]`, `List[a]`, `Dict[k, v]`
3. `Tuple1` through `Tuple32`

Issue #34 asks for a matching `Hash` abstraction and instances for all of the above, with a concrete plan for 61-bit-safe hash arithmetic and composition.

## Goals

1. Add `src/Zafu/Abstract/Hash.bosatsu` in the same style as `Eq`/`Ord`.
2. Keep all public hash outputs in `[0, 2^61 - 2]`.
3. Guarantee Eq/Hash coherence: if `eq(x, y)` then `hash(x) == hash(y)`.
4. Add `Predef` hash instances for all currently supported predef types, including `Tuple1..Tuple32`.
5. Use an ordered composition strategy for tuples/lists/dicts that is deterministic across backends.

## Non-goals

1. Cryptographic hashing.
2. Collision resistance guarantees beyond standard non-crypto hashing quality.
3. New hash-based collection APIs in this issue.
4. Prelude/re-export policy changes outside `Hash` and `Predef` additions.

## Decision summary

1. `Hash[a]` is an opaque dictionary holding `(a -> Int)` plus coherent `Eq[a]`.
2. Hash values are normalized into a 61-bit positive domain using modulus `M = 2^61 - 1`.
3. Composition uses ordered polynomial-style mixing in that modulus.
4. Composition is domain-separated by type/constructor tags and finalized with length/arity.
5. `Float64` hashing explicitly canonicalizes all NaN payloads to a single hash representative to stay coherent with `cmp_Float64`-derived equality.
6. `Dict` hashing follows existing `eq_Dict` semantics by hashing `items(dict)` in order.

## API shape (`Zafu/Abstract/Hash`)

Proposed exports:

1. `Hash`
2. `hash_from_fn`
3. `hash_specialized`
4. `hash`
5. `hash_eq`
6. `normalize_61`
7. `mix_61`
8. `finish_61`
9. `laws_Hash`

Proposed structure:

1. `struct Hash[a](hash_fn: a -> Int, eq_inst: Eq[a])`
2. `hash_from_fn(eq_inst, hash_fn)` wraps `hash_fn` with `normalize_61`.
3. `hash_specialized(hash_fn, eq_inst)` allows already-normalized/high-performance paths.
4. `hash(inst, value)` reads `hash_fn`.
5. `hash_eq(inst)` projects the coherent `Eq[a]`.

Law helper intent:

1. Reuse `Eq` law checks via `hash_eq(inst)`.
2. Check coherence for samples: if `eq(x, y)` then `hash(x) == hash(y)`.
3. Check range invariant for sample inputs.

## Hash arithmetic domain

Constants:

1. `M = 2305843009213693951` (`2^61 - 1`, a Mersenne prime)
2. `MASK = M`
3. `MIX_PRIME = 1099511628211`
4. `MIX_ADD = 1469598103934665603`

Operations:

1. `normalize_61(raw)`:
- `r = mod_Int(raw, M)`
- if `r < 0`, add `M`
- result is in `[0, M - 1]`

2. `reduce_61(x)` (fast Mersenne reduction for positive `x`):
- fold high bits with `and_Int` and `shift_right_Int(61)`
- do two folds, then subtract `M` once if needed
- keeps arithmetic in the 61-bit domain efficiently

3. `mix_61(acc, next)`:
- `reduce_61(acc * MIX_PRIME + next + MIX_ADD)`

4. `finish_61(acc, size_or_arity, tag)`:
- `mix_61(mix_61(acc, size_or_arity), tag)`

Rationale:

1. `M = 2^61 - 1` gives field arithmetic properties.
2. Ordered multiply-add composition preserves sequence order information.
3. Fixed constants and deterministic arithmetic keep cross-backend behavior stable.

## Composition strategy for predef types

### Primitive types

1. `hash_Unit`: fixed constant tag.
2. `hash_Bool`: distinct constants for `False` and `True`.
3. `hash_Char`: `normalize_61(char_to_Int(c))`.
4. `hash_Comparison`: hash rank (`LT=0`, `EQ=1`, `GT=2`) with tag separation.
5. `hash_Int`: `normalize_61(i)`.
6. `hash_Float64`:
- if `is_nan(x)`, return fixed NaN constant
- else hash `normalize_61(float64_bits_to_Int(x))`
- this avoids Eq/Hash violation from distinct NaN payloads that compare equal
7. `hash_String`:
- fold over characters in order using `mix_61`
- use string-specific seed/tag and `finish_61(..., length, tag)`

### Parametric/composite types

1. `hash_Option(hash_item)`:
- `None`: `finish_61(seed_none, 0, tag_none)`
- `Some(v)`: `finish_61(mix_61(seed_some, hash(v)), 1, tag_some)`

2. `hash_List(hash_item)`:
- left-fold in element order
- `acc = mix_61(acc, hash(element))`
- finalize with list length and list tag

3. `hash_TupleN(...)` for `N=1..32`:
- tuple-specific seed/tag (`tag_tuple_base + N`)
- mix fields left-to-right
- finalize with arity `N`

4. `hash_Dict(hash_key, hash_value)`:
- define pair hash via `hash_Tuple2(hash_key, hash_value)`
- hash `items(dict)` as an ordered list of pairs
- matches existing `eq_Dict`/`ord_Dict` sequence-based semantics

## `Predef` exports to add

Add to `src/Zafu/Abstract/Instances/Predef.bosatsu`:

1. `hash_Unit`
2. `hash_Bool`
3. `hash_Char`
4. `hash_Comparison`
5. `hash_Int`
6. `hash_Float64`
7. `hash_String`
8. `hash_Option`
9. `hash_List`
10. `hash_Dict`
11. `hash_Tuple1` through `hash_Tuple32`

This mirrors current `eq_*`/`ord_*` coverage and naming.

## Implementation plan

### Phase 1: Hash module

1. Add `src/Zafu/Abstract/Hash.bosatsu` with opaque `Hash[a]` struct.
2. Implement constructors/accessors (`hash_from_fn`, `hash_specialized`, `hash`, `hash_eq`).
3. Implement 61-bit helpers (`normalize_61`, `mix_61`, `finish_61`) and `laws_Hash`.
4. Add module-local tests for range/coherence sanity.

### Phase 2: Predef primitive instances

1. Wire primitive instances (`Unit`, `Bool`, `Char`, `Comparison`, `Int`, `Float64`, `String`).
2. Import `Bosatsu/Num/Float64` helpers for safe `Float64` canonicalization.
3. Add primitive coherence tests in `Predef` test suite.

### Phase 3: Predef composite instances

1. Add `hash_Option`, `hash_List`, `hash_Dict`.
2. Add `hash_Tuple1..hash_Tuple32` in the same style as `eq_Tuple*`/`ord_Tuple*`.
3. Add order-sensitivity and arity/length-sensitivity tests.

### Phase 4: validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance criteria

1. `docs/design/34-implement-hash-typeclass.md` exists with this design.
2. `src/Zafu/Abstract/Hash.bosatsu` exists and exports constructor/accessor/law APIs consistent with `Eq`/`Ord` style.
3. All public hash outputs satisfy `0 <= hash < 2^61 - 1`.
4. `laws_Hash` checks Eq coherence and hash-domain invariants.
5. `src/Zafu/Abstract/Instances/Predef.bosatsu` exports `hash_*` instances for all currently supported predef types.
6. `hash_Tuple1..hash_Tuple32` are implemented and compiled.
7. `hash_List` and `hash_TupleN` are order-sensitive by construction.
8. `hash_Dict` is coherent with existing `eq_Dict` semantics by hashing `items(dict)`.
9. `hash_Float64` canonicalizes NaN values so equal NaNs hash identically.
10. Existing `Eq` and `Ord` behavior is unchanged.
11. `./bosatsu lib check` passes.
12. `./bosatsu lib test` passes.
13. `scripts/test.sh` passes before merge.

## Risks and mitigations

1. Risk: subtle Eq/Hash mismatch for `Float64` edge cases.
Mitigation: explicit NaN canonicalization, plus tests using multiple NaN payloads and signed-zero cases.

2. Risk: tuple boilerplate errors across `Tuple1..Tuple32`.
Mitigation: keep uniform implementation pattern and add representative high-arity tuple tests.

3. Risk: composition quality/performance tradeoff.
Mitigation: centralize mix/finalize in `Hash` module so constants/implementation can be tuned without touching all instances.

4. Risk: dependence on `items(dict)` ordering semantics.
Mitigation: intentionally match current `eq_Dict` behavior; if dict semantics change later, update Eq/Ord/Hash together in one follow-up.

## Rollout notes

1. Land as additive API on `main` with no call-site breakage.
2. Keep constants and composition rules stable once merged to preserve deterministic hashes across releases/backends.
3. Encourage downstream code to use the shared `Hash` combinators for custom instances rather than ad-hoc mixing.
4. Follow-up abstractions (for collections like `Heap`) can start consuming `Hash` after this lands.

## Out of scope

1. Hash-based map/set container design.
2. Cryptographic digest APIs.
3. Prelude-level automatic instance wiring.
