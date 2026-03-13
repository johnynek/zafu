---
issue: 122
priority: 3
touch_paths:
  - docs/design/122-design-a-monad-typeclass.md
  - src/Zafu/Abstract/Monad.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
  - src/Zafu/Control/Result.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-13T19:23:38Z
---

# Design a Monad typeclass

_Issue: #122 (https://github.com/johnynek/zafu/issues/122)_

## Summary

Add `Zafu/Abstract/Monad` as `Applicative + flat_map + IterState-based tail recursion`, with constructors supporting either `tailrec` or `tailrec_steps`, curated Applicative convenience accessors, baseline instances (`Option`, `Prog`, `Result`), and explicit law/stack-safety validation.

## Status
Proposed

## Context
1. `Applicative`, `Foldable`, and `Traverse` are already implemented as explicit dictionaries with minimal and specialized constructors.
2. `typeclass_design.md` sets the Monad call-shape rule: subject-first sequencing (`ma.flat_map(monad, fn)`) and dictionary-first capability accessors.
3. `IterState` already exists as `IterState[done, cont]`, with `Done`/`Continue` used for explicit iterative control.
4. Issue #122 requests a Monad design that composes with `Applicative`, supports tail-recursive monadic loops, and resolves whether Monad should expose Applicative conveniences.
5. Existing modules already have monad-like operations (`Result.flat_map`, `Option` pattern matching, `Prog.await` sequencing), but there is no shared `Monad` dictionary.

## Goals
1. Add `Zafu/Abstract/Monad` with constructor layering consistent with current abstract modules.
2. Keep API shape aligned with `typeclass_design.md`.
3. Support both unbounded `tailrec` and bounded `tailrec_steps` based on `IterState`.
4. Improve ergonomics when users already have a Monad instance, without duplicating large parent APIs.
5. Ship baseline lawful instances that unblock generic usage.

## Non-goals
1. Full Cats parity (`MonadError`, `MonadState`, transformers, Kleisli helpers) in this issue.
2. Defining monad instances for every collection module.
3. Expanding `Traverse`/`Foldable` surfaces in this PR.
4. Proving termination of user-provided step functions.

## Decision Summary
1. Introduce `Monad[f]` as `Applicative[f] + flat_map + tail recursion support`.
2. Store `applicative_inst: Applicative[f]` directly in `Monad` and expose `monad_to_applicative`.
3. Keep both recursion forms available on the dictionary:
- `tailrec`: unbounded monadic tail recursion.
- `tailrec_steps`: bounded stepping that yields `Continue(seed)` when fuel is exhausted.
4. Provide two non-specialized constructors so implementers can supply whichever recursion primitive is easier:
- from `flat_map + tailrec`,
- from `flat_map + tailrec_steps`.
5. Derive the missing primitive in each constructor:
- derive `tailrec_steps` from `tailrec` by threading `(remaining_steps, seed)`,
- derive `tailrec` from `tailrec_steps` by chunked re-entry with increasing fuel.
6. Expose curated Applicative conveniences on Monad: `pure`, `map`, `map2` (plus `ap`/`void` only if needed for derivations).
7. Keep consistency policy: small curated parent conveniences are allowed; full parent APIs stay behind projection functions.

## API Design

### Module: `src/Zafu/Abstract/Monad.bosatsu`

Proposed exports:
1. `Monad`
2. `monad_specialized`
3. `monad_from_applicative_flat_map_tailrec`
4. `monad_from_applicative_flat_map_tailrec_steps`
5. `monad_to_applicative`
6. `pure`
7. `map`
8. `map2`
9. `flat_map`
10. `flatten`
11. `tailrec`
12. `tailrec_steps`
13. `laws_Monad`

Proposed dictionary shape:
```bosatsu
struct Monad[f: * -> *](
  applicative_inst: Applicative[f],
  flat_map_fn: forall a, b. (f[a], a -> f[b]) -> f[b],
  tailrec_fn: forall a, b. (a, a -> f[IterState[b, a]]) -> f[b],
  tailrec_steps_fn: forall a, b. (Int, a, a -> f[IterState[b, a]]) -> f[IterState[b, a]],
)
```

Notes:
1. `IterState` order is `IterState[done, cont]`, so Monad recursion uses `IterState[result, next_seed]` = `IterState[b, a]`.
2. `flat_map` is subject-first.
3. `tailrec` and `tailrec_steps` are dictionary-first capability calls.

### Tailrec Semantics
1. `tailrec(inst, init, step)` repeatedly runs `step` until `Done(result)`.
2. `tailrec_steps(inst, max_steps, init, step)` executes at most `max_steps` transitions:
- `Done(result)` if completed within budget,
- `Continue(next_seed)` if fuel is exhausted.
3. For `max_steps <= 0`, `tailrec_steps` must return `inst.pure(Continue(init))`.
4. For terminating programs, `tailrec` derived from `tailrec_steps` must match repeated stepping semantics.

### Reader/State Feasibility
1. Reader (`r -> a`) can implement `tailrec_steps` by local looping while reusing `r`.
2. State (`s -> (s, a)`) can implement `tailrec_steps` by local looping while threading `s`.
3. No finite-step proof is required; non-termination remains possible and acceptable.

### Parent Accessor Policy (Consistency Decision)
1. Monad exposes curated Applicative conveniences (`pure`, `map`, `map2`) for common call-site ergonomics.
2. Monad still exposes `monad_to_applicative` for full Applicative functionality.
3. Traverse remains projection-first (`traverse_to_foldable`) and does not mirror Foldable’s full accessor set.
4. This is the consistent policy: curated convenience is allowed, full parent API duplication is not.

## Instance Plan

### In-scope baseline instances
1. `src/Zafu/Abstract/Instances/Predef.bosatsu`
- `monad_Option: Monad[Option]`
- `monad_Prog: forall e. Monad[Prog[e]]`
2. `src/Zafu/Control/Result.bosatsu`
- `monad_Result: forall e. Monad[Result[e]]` (optional `monad` alias, matching existing `applicative` alias style)

### Explicitly out of scope
1. `PartialResult` Monad dictionary in this issue (requires a separate decision about `Semigroup[e]`-parameterized sequencing vs validation-style applicative behavior).
2. Collection monads (`List`, `Vector`, `Chain`, etc.) until Applicative strategy is intentionally chosen.

## Law and Test Plan
1. `laws_Monad` checks left identity, right identity, and associativity.
2. Add Monad/Applicative coherence checks, e.g. `fa.map(monad, f) == fa.flat_map(monad, x -> monad.pure(f(x)))`.
3. Add tail recursion behavior tests:
- `tailrec_steps(0, init, step)` returns `Continue(init)`,
- bounded stepping reaches `Done` when expected,
- deep `tailrec` loops are stack-safe for baseline strict instances.
4. Keep tests module-local in the same style as existing abstract modules.

## Implementation Plan

### Phase 1: Core Monad module
1. Add `src/Zafu/Abstract/Monad.bosatsu`.
2. Implement dictionary, constructors, projection, derived helpers, and `laws_Monad`.
3. Add local law and tailrec tests.

### Phase 2: Baseline instances
1. Update `src/Zafu/Abstract/Instances/Predef.bosatsu` with `monad_Option` and `monad_Prog`.
2. Update `src/Zafu/Control/Result.bosatsu` with `monad_Result` export and tests.

### Phase 3: Validation
1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria
1. `docs/design/122-design-a-monad-typeclass.md` is added with this architecture and rollout plan.
2. `src/Zafu/Abstract/Monad.bosatsu` exists and exports the API listed above.
3. `Monad` stores and projects `Applicative` via `monad_to_applicative`.
4. `flat_map` is subject-first and follows `typeclass_design.md`.
5. `tailrec` and `tailrec_steps` both exist and use `IterState[b, a]`.
6. Constructors exist for both implementation styles (`flat_map + tailrec`, and `flat_map + tailrec_steps`).
7. Monad exposes curated Applicative conveniences (`pure`, `map`, `map2`) without duplicating full Applicative API.
8. `Traverse`/`Foldable` surfaces remain unchanged in this issue.
9. Baseline instance exports exist for `monad_Option`, `monad_Prog`, and `monad_Result`.
10. Monad laws and tailrec behavior tests are present and passing for baseline instances.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations
1. Risk: `IterState` parameter-order confusion causes incorrect recursion implementations.
Mitigation: standardize and test `IterState[b, a]` signatures.

2. Risk: derived `tailrec` from `tailrec_steps` may be slower for long-running loops.
Mitigation: keep `monad_specialized` and direct-`tailrec` constructor for optimized instances.

3. Risk: inherited-accessor API bloat across typeclasses.
Mitigation: enforce curated convenience + projection-only policy.

4. Risk: adding `PartialResult` Monad prematurely introduces law/coherence ambiguity.
Mitigation: keep it explicitly out of scope and handle in follow-up design.

## Rollout Notes
1. Ship as additive API on `main`; no migration required.
2. Land in order: core Monad module, baseline instances, then broader adoption.
3. Keep canonical naming (`monad_Option`, `monad_Result`, `monad_Prog`).
4. Track follow-ups for `PartialResult` monad/applicative alignment and optional Reader/State examples once those abstractions are introduced.
