---
issue: 122
priority: 3
touch_paths:
  - docs/design/122-design-a-monad-typeclass.md
  - src/Zafu/Abstract/Monad.bosatsu
  - src/Zafu/Control/IterState.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Control/Result.bosatsu
  - src/Zafu/Control/PartialResult.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-13T19:23:38Z
---

# Design a Monad typeclass

_Issue: #122 (https://github.com/johnynek/zafu/issues/122)_

## Summary

Add `Zafu/Abstract/Monad` as `Applicative + flat_map + tailrec_steps` (no unbounded `tailrec`), standardize `IterState` type parameter order to `IterState[cont, done]`, keep Monad access to Applicative features via projection (no duplicated accessors), and include baseline instances for `Option`, `Prog`, `Result`, and `PartialResult` (the latter parameterized by `Semigroup[e]`).

## Status
Proposed

## Context
1. `Applicative`, `Foldable`, and `Traverse` are already implemented as explicit dictionaries with minimal and specialized constructors.
2. `typeclass_design.md` sets the Monad call-shape rule as subject-first sequencing: `ma.flat_map(monad, fn)`.
3. Issue #122 raises concern that requiring full unbounded `tailrec` is not implementable for all monads in Bosatsu's total setting.
4. We still need bounded, explicit stepping to support stack-safe monadic loops where possible.
5. We also need a consistent policy for inherited typeclass APIs (`Monad` vs `Applicative`, `Traverse` vs `Foldable`).

## Goals
1. Add `Zafu/Abstract/Monad` with constructor layering consistent with current abstract modules.
2. Keep API shape aligned with `typeclass_design.md`.
3. Use `tailrec_steps` (bounded stepping) as the recursion primitive for Monad.
4. Make parent access consistent: no duplicated inherited APIs; use projection functions.
5. Include practical baseline instances for immediate usage.

## Non-goals
1. Full Cats parity (`MonadError`, `MonadState`, transformers, Kleisli helpers) in this issue.
2. Defining monad instances for every collection module.
3. Adding an unbounded `tailrec` operation to `Monad`.
4. Solving termination for arbitrary user step functions.

## Decision Summary
1. Introduce `Monad[f]` as `Applicative[f] + flat_map + tailrec_steps`.
2. Store `applicative_inst: Applicative[f]` directly in `Monad` and expose `monad_to_applicative`.
3. Do not include `tailrec` in the Monad API; use only bounded `tailrec_steps`.
4. Standardize `IterState` parameter order to `IterState[cont, done]`.
5. Do not duplicate Applicative accessors (`pure`, `map`, `map2`) on Monad. Access those via `monad_to_applicative`.
6. Include `monad_PartialResult(semi)` in scope.
7. For `Result`, support two applicative flavors:
- existing left-biased applicative (monad-compatible),
- new `applicative_combine_Err(sg)` that combines errors with a semigroup.

## API Design

### IterState Parameter Order

Update `IterState` to use continuation-first type parameters:

```bosatsu
enum IterState[cont: +*, done: +*]:
  Continue(cont: cont)
  Done(done: done)
```

Monad step signatures then use `IterState[a, b]` where `a` is the next seed and `b` is the completed result.

### Module: `src/Zafu/Abstract/Monad.bosatsu`

Proposed exports:
1. `Monad`
2. `monad_specialized`
3. `monad_from_applicative_flat_map_tailrec_steps`
4. `monad_to_applicative`
5. `flat_map`
6. `flatten`
7. `tailrec_steps`
8. `laws_Monad`

Proposed dictionary shape:

```bosatsu
struct Monad[f: * -> *](
  applicative_inst: Applicative[f],
  flat_map_fn: forall a, b. (f[a], a -> f[b]) -> f[b],
  tailrec_steps_fn: forall a, b. (Int, a, a -> f[IterState[a, b]]) -> f[IterState[a, b]],
)
```

Notes:
1. `flat_map` remains subject-first.
2. `tailrec_steps` is dictionary-first capability selection.
3. Users call `monad_to_applicative(monad)` when they need `pure`, `map`, `map2`, etc.

### `tailrec_steps` Semantics
1. `tailrec_steps(inst, max_steps, init, step)` executes at most `max_steps` transitions.
2. If it reaches `Done(result)` within fuel, return `Done(result)`.
3. If fuel is exhausted first, return `Continue(next_seed)`.
4. For `max_steps <= 0`, return `Continue(init)` in `f`.

### Parent Accessor Policy (Consistency Decision)
1. No inherited API duplication in child typeclasses.
2. `Monad` exposes projection (`monad_to_applicative`) rather than re-exporting `pure`/`map`/`map2`.
3. This matches the existing `Traverse -> Foldable` projection model.

## Instance Plan

### In-scope baseline instances
1. `src/Zafu/Abstract/Instances/Predef.bosatsu`
- `monad_Option: Monad[Option]`
- `monad_Prog: forall e. Monad[Prog[e]]`
2. `src/Zafu/Control/Result.bosatsu`
- `monad_Result: forall e. Monad[Result[e]]` (left-biased error behavior)
- `applicative_combine_Err: forall e. Semigroup[e] -> Applicative[Result[e]]`
3. `src/Zafu/Control/PartialResult.bosatsu`
- `monad_PartialResult: forall e. Semigroup[e] -> Monad[PartialResult[e]]`

### Explicitly out of scope
1. Collection monads (`List`, `Vector`, `Chain`, etc.) until their applicative pairing is intentionally chosen.

## Law and Test Plan
1. `laws_Monad` checks left identity, right identity, and associativity.
2. Add coherence checks between `flat_map` and projected applicative usage where expressible.
3. Add `tailrec_steps` behavior tests:
- `max_steps <= 0` returns `Continue(init)`,
- bounded stepping returns `Done` for small terminating loops,
- bounded stepping preserves remainder seed when fuel is exhausted.
4. Add `Result` tests that differentiate:
- left-biased monad-compatible applicative,
- semigroup-combining applicative.
5. Add `PartialResult` tests for monad laws under a fixed lawful semigroup.

## Implementation Plan

### Phase 1: IterState order + Monad core
1. Update `src/Zafu/Control/IterState.bosatsu` type parameter order to `IterState[cont, done]`.
2. Add `src/Zafu/Abstract/Monad.bosatsu` with dictionary, constructors, projection, operations, and `laws_Monad`.

### Phase 2: Baseline instances
1. Update `src/Zafu/Abstract/Instances/Predef.bosatsu` with `monad_Option` and `monad_Prog`.
2. Update `src/Zafu/Control/Result.bosatsu` with `monad_Result` and `applicative_combine_Err`.
3. Update `src/Zafu/Control/PartialResult.bosatsu` with `monad_PartialResult(semi)`.

### Phase 3: Validation
1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria
1. `docs/design/122-design-a-monad-typeclass.md` is updated with this design.
2. `src/Zafu/Abstract/Monad.bosatsu` exists and exports the API listed above.
3. `Monad` stores and projects `Applicative` via `monad_to_applicative`.
4. `flat_map` is subject-first and follows `typeclass_design.md`.
5. Monad includes `tailrec_steps` and does not include unbounded `tailrec`.
6. `IterState` parameter order is `IterState[cont, done]`.
7. Monad does not duplicate Applicative accessors; parent access is via projection.
8. Baseline instance exports exist for `monad_Option`, `monad_Prog`, `monad_Result`, and `monad_PartialResult(semi)`.
9. `Result` exposes `applicative_combine_Err(sg)` in addition to the monad-compatible applicative.
10. Monad laws and `tailrec_steps` behavior tests pass for baseline instances.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations
1. Risk: changing IterState type parameter order breaks existing type annotations.
Mitigation: update signatures mechanically and validate with full check + test runs.

2. Risk: users may confuse the two `Result` applicative variants.
Mitigation: explicit naming, docs, and tests showing behavior differences.

3. Risk: `PartialResult` monad/applicative semantics can be conflated with validation-style combinators.
Mitigation: keep monad construction explicitly semigroup-parameterized and document that it is sequencing-oriented.

4. Risk: bounded stepping may be misunderstood as guaranteeing completion.
Mitigation: document `tailrec_steps` as fuel-bounded and continuation-returning by design.

## Rollout Notes
1. Ship as additive API on `main`.
2. Land in order: IterState parameter-order update, Monad core, then baseline instances.
3. Keep canonical naming (`monad_Option`, `monad_Prog`, `monad_Result`, `monad_PartialResult`).
4. Defer collection monads and additional applicative/monad pairings to follow-up issues.
