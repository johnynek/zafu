---
issue: 42
priority: 3
touch_paths:
  - docs/design/42-design-zafu-control-result.md
  - src/Zafu/Control/Result.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-08T17:17:09Z
---

# Design Zafu/Control/Result

_Issue: #42 (https://github.com/johnynek/zafu/issues/42)_

## Summary

Adds a full design doc for issue #42 introducing a Rust-inspired `Result[e, a]` in `Zafu/Control`, including API shape, typeclass integration, phased implementation plan, acceptance criteria, risks, and rollout notes.

---
issue: 42
priority: 2
touch_paths:
  - docs/design/42-design-zafu-control-result.md
  - src/Zafu/Control/Result.bosatsu
depends_on:
  - 28
  - 34
estimated_size: S
generated_at: 2026-03-08T17:30:00Z
---

# Design: Zafu/Control/Result

_Issue: #42 (https://github.com/johnynek/zafu/issues/42)_

## Summary

Add `Zafu/Control/Result` with a Rust-inspired shape:

`enum Result[e, a]: Err(err: e), Ok(ok: a)`

The type is right-biased on `Ok`, supports typed error propagation, and includes focused combinators plus `Eq`/`Ord`/`Hash` adapters aligned with current `Zafu/Abstract` patterns.

## Status

Proposed

## Context

`Zafu` currently has `Option` and collection-specific return values, but no standard two-track success/error carrier. Issue #42 requests a `Result` inspired by Rust with explicit `Err` and `Ok` constructors.

A first-party `Result` provides a consistent primitive for recoverable error handling without introducing exceptions or side effects.

## Goals

1. Add `src/Zafu/Control/Result.bosatsu`.
2. Implement `Result[e, a]` with constructors `Err(err: e)` and `Ok(ok: a)`.
3. Provide right-biased core combinators (`map`, `and_then`) and error combinators (`map_err`, `or_else`).
4. Provide elimination/conversion helpers (`fold`, `unwrap_or`, `unwrap_or_else`, `from_Option`, `to_Option`).
5. Provide `Eq`, `Ord`, and `Hash` adapters coherent with existing abstractions.
6. Keep API small, explicit, and chain-friendly (result-first style).

## Non-goals

1. Panic/exception helpers (no `unwrap` that can crash).
2. Validation-style error accumulation.
3. Broad prelude changes.
4. Refactoring existing modules to adopt `Result` in this same issue.

## Decision summary

1. `Result` is a public enum with public constructors.
2. `Ok` is the success branch for `map`/`and_then`; `Err` short-circuits.
3. `fold` is the canonical eliminator; extraction helpers are convenience wrappers.
4. `Ord` follows Rust-style constructor ordering: `Err(_) < Ok(_)`.
5. `Hash` is constructor-tagged to keep `Err(x)` and `Ok(x)` distinct.
6. Keep initial scope focused on the core API in `Zafu/Control/Result`.

## Proposed API (`Zafu/Control/Result`)

Core type:

1. `Result`
2. Constructors: `Err(err: e)`, `Ok(ok: a)`

Predicates and views:

1. `is_err(result: Result[e, a]) -> Bool`
2. `is_ok(result: Result[e, a]) -> Bool`
3. `err(result: Result[e, a]) -> Option[e]`
4. `ok(result: Result[e, a]) -> Option[a]`
5. `to_Option(result: Result[e, a]) -> Option[a]`

Combinators:

1. `map(result: Result[e, a], fn: a -> b) -> Result[e, b]`
2. `map_err(result: Result[e, a], fn: e -> f) -> Result[f, a]`
3. `and_then(result: Result[e, a], fn: a -> Result[e, b]) -> Result[e, b]`
4. `flat_map(result: Result[e, a], fn: a -> Result[e, b]) -> Result[e, b]` (alias of `and_then`)
5. `or_else(result: Result[e, a], fn: e -> Result[f, a]) -> Result[f, a]`
6. `fold(result: Result[e, a], on_err: e -> b, on_ok: a -> b) -> b`

Extraction/conversion helpers:

1. `unwrap_or(result: Result[e, a], fallback: a) -> a`
2. `unwrap_or_else(result: Result[e, a], on_err: e -> a) -> a`
3. `from_Option(value: Option[a], on_none: () -> e) -> Result[e, a]`

Typeclass adapters:

1. `eq(eq_err: Eq[e], eq_ok: Eq[a]) -> Eq[Result[e, a]]`
2. `ord(ord_err: Ord[e], ord_ok: Ord[a]) -> Ord[Result[e, a]]`
3. `hash(hash_err: Hash[e], hash_ok: Hash[a]) -> Hash[Result[e, a]]`

## Semantics and invariants

1. `map(Err(e), fn) == Err(e)`.
2. `map(Ok(a), fn) == Ok(fn(a))`.
3. `map_err(Ok(a), fn) == Ok(a)`.
4. `map_err(Err(e), fn) == Err(fn(e))`.
5. `and_then(Err(e), fn) == Err(e)`.
6. `or_else(Ok(a), fn) == Ok(a)`.
7. `unwrap_or` is eager; `unwrap_or_else` is lazy.
8. `eq`/`ord`/`hash` are constructor-sensitive.
9. `ord` enforces `Err < Ok` globally.
10. `hash` uses branch tags and 61-bit normalization via existing hash helpers.

## Implementation sketch

Data model:

1. Add enum in `src/Zafu/Control/Result.bosatsu`:
   - `Err(err: e)`
   - `Ok(ok: a)`

Implementation style:

1. Use direct `match` in each function for clarity and inlining.
2. Implement `flat_map` as alias forwarding to `and_then`.
3. Keep result-first argument order for chain ergonomics.

Typeclass adapter style:

1. `eq`: compare payloads only when constructors match.
2. `ord`: compare constructor rank first (`Err=0`, `Ok=1`), then payload.
3. `hash`: mix constructor tag plus payload hash using `mix_61`/`finish_61`.

Testing strategy:

1. Unit tests for every exported function on both branches.
2. Sanity tests for map identity/composition and short-circuit behavior.
3. Eq/Ord/Hash coherence checks on representative values.

## Implementation plan

Phase 1: module skeleton and core shape

1. Create `src/Zafu/Control/Result.bosatsu`.
2. Add enum and exports.
3. Implement `is_err`, `is_ok`, `err`, `ok`, `to_Option`, `fold`.

Phase 2: combinators and conversions

1. Implement `map`, `map_err`, `and_then`, `flat_map`, `or_else`.
2. Implement `unwrap_or`, `unwrap_or_else`, `from_Option`.
3. Add branch-complete tests.

Phase 3: abstraction adapters

1. Implement `eq`, `ord`, `hash` in `Zafu/Control/Result`.
2. Add adapter coherence tests.

Phase 4: validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance criteria

1. `docs/design/42-design-zafu-control-result.md` exists with this plan.
2. `src/Zafu/Control/Result.bosatsu` exists.
3. `Result[e, a]` has exactly two constructors: `Err(err: e)` and `Ok(ok: a)`.
4. Public API supports direct pattern matching and exported helper functions.
5. `map`, `map_err`, `and_then`, and `or_else` obey documented branch behavior.
6. `flat_map` is functionally equivalent to `and_then`.
7. `from_Option` and `to_Option` handle success/failure conversions correctly.
8. `eq`, `ord`, and `hash` adapters exist and are constructor-sensitive.
9. `ord` guarantees `Err(_) < Ok(_)`.
10. `hash` uses distinct constructor tags and 61-bit domain-safe mixing.
11. Tests cover both constructor paths for all exported helpers and adapters.
12. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and mitigations

1. Risk: confusion between `and_then` and `flat_map` naming.
Mitigation: export both and document alias relationship.

2. Risk: unexpected eager fallback cost with `unwrap_or`.
Mitigation: provide and test `unwrap_or_else` as lazy alternative.

3. Risk: Eq/Hash mismatch bugs.
Mitigation: add coherence tests and constructor-tagged hash strategy.

4. Risk: scope creep into a larger error framework.
Mitigation: keep this issue constrained to core `Result` data type and combinators.

## Rollout notes

1. Land as additive change on `main`; no breaking changes.
2. Keep migration incremental; existing `Option` code remains valid.
3. Keep canonical typeclass adapters in `Zafu/Control/Result`.
4. Follow-up issues can add integrations in collections/control-flow modules once core `Result` usage patterns are established.
