---
issue: 107
priority: 3
touch_paths:
  - docs/design/107-design-a-partialresult-class.md
  - src/Zafu/Control/PartialResult.bosatsu
  - src/Zafu/Control/Result.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-11T20:24:08Z
---

# Design: PartialResult (#107)

_Issue: #107 (https://github.com/johnynek/zafu/issues/107)_

## Summary

Full design doc content for issue #107 proposing Zafu/Control/PartialResult, semigroup-aware sequential and product composition, law/test plan, acceptance criteria, risks, and rollout notes.

---
issue: 107
priority: 2
touch_paths:
  - docs/design/107-design-a-partialresult-class.md
  - src/Zafu/Control/PartialResult.bosatsu
  - src/Zafu/Control/Result.bosatsu
depends_on:
  - 42
  - 59
estimated_size: M
generated_at: 2026-03-11T20:00:00Z
---

# Design: Add Zafu/Control/PartialResult

_Issue: #107 (https://github.com/johnynek/zafu/issues/107)_

## Summary

Add `PartialResult[e, a]` with three states:

1. `TotalErr(err: e)`
2. `PartialErr(err: e, partial: a)`
3. `TotalOk(ok: a)`

The module keeps `Result`-style ergonomics while adding semigroup-aware composition that accumulates error information without stopping when a usable partial value exists.

## Status

Proposed

## Context

1. `Zafu/Control/Result` is binary (`Err`/`Ok`) and fail-fast.
2. Some workflows can keep computing after a failure and should return both error context and best-effort output.
3. Issue #107 asks for a tri-state type plus `combine_product` and `combine_map2` to accumulate as much error information as possible.
4. The issue explicitly requires lawful sequential composition for `and_then`/`flat_map`.

## Goals

1. Add `src/Zafu/Control/PartialResult.bosatsu` with the requested enum shape.
2. Define a full API inventory aligned with `Result` naming and style.
3. Make sequential composition (`and_then`/`flat_map`) lawful under a fixed `Semigroup[e]`.
4. Provide semigroup-aware product composition (`combine_product`, `combine_map2`) that preserves all available errors.
5. Keep the change additive and backward compatible with existing `Result` users.

## Non-goals

1. Replacing or changing `Result` semantics.
2. Adding implicit or global typeclass resolution.
3. Refactoring all callers to use `PartialResult` in this issue.
4. Designing a full validation/traversal framework beyond the requested composition primitives.

## Data Model and Invariants

Type:

1. `enum PartialResult[e, a]:`
2. `TotalErr(err: e)`
3. `PartialErr(err: e, partial: a)`
4. `TotalOk(ok: a)`

Invariants:

1. `TotalErr` carries error only.
2. `TotalOk` carries value only.
3. `PartialErr` carries both error and value.
4. Error information must never be dropped when composition can continue with a value.

Conceptual model:

1. Equivalent to `(Option[e], Option[a])` with the invalid `(None, None)` state excluded.
2. This model makes combination rules explicit and easy to test.

## API Design

### Module: `Zafu/Control/PartialResult`

Proposed exports:

1. `PartialResult`
2. `is_total_err`
3. `is_partial_err`
4. `is_total_ok`
5. `has_err`
6. `has_ok`
7. `err`
8. `ok`
9. `to_Option`
10. `map`
11. `map_err`
12. `and_then`
13. `flat_map`
14. `or_else`
15. `fold`
16. `unwrap_or`
17. `unwrap_or_else`
18. `from_Option`
19. `from_Result`
20. `to_Result_fail_fast`
21. `combine_product`
22. `combine_map2`
23. `combine_product_l`
24. `combine_product_r`
25. `eq`
26. `ord`
27. `hash`

### Function Semantics

Predicates/views:

1. `has_err` is true for `TotalErr` and `PartialErr`.
2. `has_ok` is true for `TotalOk` and `PartialErr`.
3. `err` returns `Some(e)` for error-carrying states, else `None`.
4. `ok`/`to_Option` return `Some(a)` for value-carrying states, else `None`.

Mapping:

1. `map` transforms value in `TotalOk` and `PartialErr`; leaves `TotalErr` unchanged.
2. `map_err` transforms error in `TotalErr` and `PartialErr`; leaves `TotalOk` unchanged.

Sequential composition (`and_then` / `flat_map`):

1. Signature: `and_then[e, a, b](semi: Semigroup[e], result: PartialResult[e, a], fn: a -> PartialResult[e, b]) -> PartialResult[e, b]`
2. `flat_map` is an alias of `and_then`.
3. Behavior:
   - `TotalErr(e)` short-circuits as `TotalErr(e)`.
   - `TotalOk(a)` evaluates `fn(a)`.
   - `PartialErr(e, a)` evaluates `fn(a)` and accumulates any new error with `combine(semi, e, e2)`.
4. Explicit cases for `PartialErr(e, a)`:
   - `fn(a) == TotalOk(b)` => `PartialErr(e, b)`
   - `fn(a) == PartialErr(e2, b)` => `PartialErr(combine(semi, e, e2), b)`
   - `fn(a) == TotalErr(e2)` => `TotalErr(combine(semi, e, e2))`

Error recovery:

1. `or_else(result, fn)` recovers only when there is no usable value:
   - `TotalErr(e)` => `fn(e)`
   - `PartialErr(e, a)` => unchanged (`PartialErr(e, a)`)
   - `TotalOk(a)` => unchanged (`TotalOk(a)`)
2. This keeps `or_else` aligned with "recover missing value" behavior and avoids discarding partial data.

Elimination/conversion:

1. `fold(result, on_total_err, on_partial_err, on_total_ok)` is the canonical eliminator.
2. `unwrap_or` / `unwrap_or_else` return the carried value for `TotalOk` and `PartialErr`, fallback only for `TotalErr`.
3. `from_Option(value, on_none)` maps `None` to `TotalErr(on_none())`, `Some(x)` to `TotalOk(x)`.
4. `from_Result` maps `Err` -> `TotalErr`, `Ok` -> `TotalOk`.
5. `to_Result_fail_fast` maps `PartialErr(e, _)` to `Err(e)` to preserve error visibility at fail-fast boundaries.

Parallel/product composition:

1. `combine_product[e, a, b](semi: Semigroup[e], left: PartialResult[e, a], right: PartialResult[e, b]) -> PartialResult[e, (a, b)]`
2. `combine_map2[e, a, b, c](semi: Semigroup[e], left: PartialResult[e, a], right: PartialResult[e, b], fn: (a, b) -> c) -> PartialResult[e, c]`
3. Derived helpers:
   - `combine_product_l(semi, left, right)`
   - `combine_product_r(semi, left, right)`

`combine_product` decision table (`<>` means `combine(semi, _, _)`):

| left \\ right | `TotalErr(e2)` | `PartialErr(e2, b)` | `TotalOk(b)` |
|---|---|---|---|
| `TotalErr(e1)` | `TotalErr(e1 <> e2)` | `TotalErr(e1 <> e2)` | `TotalErr(e1)` |
| `PartialErr(e1, a)` | `TotalErr(e1 <> e2)` | `PartialErr(e1 <> e2, (a, b))` | `PartialErr(e1, (a, b))` |
| `TotalOk(a)` | `TotalErr(e2)` | `PartialErr(e2, (a, b))` | `TotalOk((a, b))` |

`combine_map2` is defined as:

1. `combine_map2(semi, left, right, fn) = map(combine_product(semi, left, right), pair -> fn(pair.0, pair.1))`

Typeclass adapters:

1. `eq(eq_err, eq_ok)` compares constructor first, payloads within matching constructor.
2. `ord(ord_err, ord_ok)` uses constructor rank: `TotalErr < PartialErr < TotalOk`; payload compare inside each branch.
3. `hash(hash_err, hash_ok)` uses constructor tags so equal payloads across different constructors never collide by construction domain.

## Law Design

For a fixed lawful `Semigroup[e]`:

1. `and_then(semi, TotalOk(x), f) == f(x)` (left identity).
2. `and_then(semi, m, x -> TotalOk(x)) == m` (right identity).
3. `and_then(semi, and_then(semi, m, f), g) == and_then(semi, m, x -> and_then(semi, f(x), g))` (associativity).
4. `flat_map` shares all `and_then` laws by aliasing.

Additional laws/consistency checks:

1. `map` obeys identity and composition.
2. `map_err` obeys identity and composition.
3. `combine_map2` is consistent with `combine_product` + `map`.
4. If both inputs carry errors, `combine_product` output error equals exactly one semigroup combine of both errors.

## Implementation Plan

### Phase 1: module skeleton and Result-parity APIs

1. Create `src/Zafu/Control/PartialResult.bosatsu`.
2. Add enum, exports, predicates/views, `map`, `map_err`, `fold`, unwrap helpers, and option/result conversions.
3. Add baseline branch coverage tests for each exported function.

### Phase 2: semigroup-aware composition

1. Implement `and_then` and `flat_map` with explicit `Semigroup[e]` parameter.
2. Implement `combine_product`, `combine_map2`, `combine_product_l`, `combine_product_r`.
3. Add 9-case table-driven tests for `combine_product`.
4. Add monad associativity tests for `and_then` with at least one non-trivial semigroup (`semigroup_List` or `semigroup_String`).

### Phase 3: adapters and integration boundary

1. Implement `eq`, `ord`, `hash` adapters mirroring `Result` style.
2. Add `to_Result_fail_fast` and tests that `PartialErr` does not silently become success.
3. Add optional symmetric conversion helper in `src/Zafu/Control/Result.bosatsu` if needed for discoverability (`from_PartialResult_fail_fast`).

### Phase 4: validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/107-design-a-partialresult-class.md` is added with this architecture and rollout plan.
2. `src/Zafu/Control/PartialResult.bosatsu` exists and defines:
   - `TotalErr(err: e)`
   - `PartialErr(err: e, partial: a)`
   - `TotalOk(ok: a)`
3. The API inventory in this document is exported (or explicitly marked deferred).
4. `and_then` and `flat_map` accept `Semigroup[e]` and preserve/accumulate errors as defined.
5. Monad associativity for `and_then` passes tests under a fixed lawful semigroup.
6. `combine_product` and `combine_map2` are implemented with the exact decision-table behavior.
7. `combine_product` tests cover all 9 constructor pairings.
8. `map`, `map_err`, `fold`, `unwrap_or`, and `unwrap_or_else` have tests across all three constructors.
9. `eq`, `ord`, and `hash` adapters exist and are constructor-sensitive.
10. `to_Result_fail_fast(PartialErr(e, a))` yields `Err(e)`.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: monad laws may appear to fail if callers use a non-lawful semigroup.
Mitigation: document that laws assume semigroup associativity and include tests with known-lawful `Predef` semigroups.

2. Risk: confusion between sequential (`and_then`) and parallel (`combine_map2`) composition behavior.
Mitigation: document both semantics explicitly and add matrix tests for product composition.

3. Risk: accidental error loss in conversion to `Result`.
Mitigation: only provide `to_Result_fail_fast` in the core API and make lossy behavior explicit if ever added later.

4. Risk: performance overhead from repeated error combines in long chains.
Mitigation: keep operations single-pass and avoid extra allocations in constructor transitions.

## Rollout Notes

1. Change is additive; existing `Result` code remains valid.
2. Prefer `PartialResult` where best-effort output plus diagnostics is required.
3. Keep fail-fast boundaries explicit via `to_Result_fail_fast`.
4. Initial rollout should target modules that already build aggregate diagnostics (parsers, validators, data import paths), then expand incrementally.
5. Follow-up issues can add traversal helpers (`sequence`/`traverse`) once core semantics are established in production usage.
