---
issue: 80
priority: 3
touch_paths:
  - docs/design/80-design-an-eval-class.md
  - src/Zafu/Control/Eval.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-09T06:51:22Z
---

# Design: Zafu/Control/Eval

_Issue: #80 (https://github.com/johnynek/zafu/issues/80)_

## Summary

Design doc for issue #80 proposing an opaque covariant Eval with Lazy-backed constructors and a stack-safe, total trampoline evaluator with explicit fuel.

---
issue: 80
priority: 2
touch_paths:
  - docs/design/80-design-an-eval-class.md
  - src/Zafu/Control/Eval.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-09T07:20:00Z
---

# Design: Zafu/Control/Eval

_Issue: #80 (https://github.com/johnynek/zafu/issues/80)_

## Summary

Add a minimal, opaque, covariant `Eval[a: +*]` to support stack-safe composition of non-tail-recursive pure programs in Bosatsu. The v1 API intentionally stays small: `now`, `later`, `defer`, `flat_map`, and `value`. `value` is implemented as a trampoline with explicit fuel and returns `Option[a]`, which preserves Bosatsu totality and avoids hidden non-termination.

## Status

Proposed

## Context

1. Issue #80 asks for a Cats-inspired `Eval` focused on stack safety, not an effect system.
2. `cats.Eval` demonstrates the target operational shape: lazy/eager constructors plus stack-safe `flatMap` evaluation.
3. Bosatsu requires recursion forms with provable termination; deep interpreter-style recursion generally uses a decreasing fuel argument.
4. Existing Zafu modules (`Vector`, `Heap`, `Chain`) already use the same explicit-fuel pattern for total, stack-safe traversals.
5. We also need `Eval[a: +*]` covariance to support recursive data/program construction.

## Goals

1. Add `src/Zafu/Control/Eval.bosatsu`.
2. Expose an opaque, covariant `Eval[a: +*]`.
3. Implement `now`, `later`, `defer`, `flat_map`, `value`.
4. Guarantee stack-safe evaluation for deep `flat_map`/`defer` chains.
5. Use `Bosatsu/Lazy` to model Scala `lazy val` behavior for deferred memoized values.
6. Keep semantics total: no partial APIs, no unchecked non-termination surface.

## Non-goals

1. Implementing a general effect monad runtime (`recover`, `raise`, async, resource handling).
2. Full Cats parity (`always`, `memoize`, typeclass instances, etc.).
3. Rewriting existing collection APIs to use `Eval` in this same issue.
4. Guaranteeing unbounded evaluation without any fuel argument in v1.

## Decision Summary

1. `Eval` will be opaque and covariant (`Eval[a: +*]`), with constructors hidden from callers.
2. `later` and `defer` will be backed by `Bosatsu/Lazy` so delayed computations are memoized.
3. `flat_map` will build a computation graph; evaluation will use an explicit continuation stack (trampoline) instead of recursive calls.
4. `value` will take explicit fuel and return `Option[a]`:
   - `Some(a)` on successful completion.
   - `None` on budget exhaustion.
5. This makes termination explicit and total, while still giving stack-safe composition for practical deep recursion when fuel is chosen from input size.

## Public API Design

### Module: `Zafu/Control/Eval`

Proposed exports:

1. `Eval`
2. `now`
3. `later`
4. `defer`
5. `flat_map`
6. `value`

Proposed signatures:

1. `def now(value: a) -> Eval[a]`
2. `def later(thunk: () -> a) -> Eval[a]`
3. `def defer(thunk: () -> Eval[a]) -> Eval[a]`
4. `def flat_map(eval: Eval[a], fn: a -> Eval[b]) -> Eval[b]`
5. `def value(eval: Eval[a], fuel: Int) -> Option[a]`

Semantic notes:

1. `now` is eager.
2. `later` delays and memoizes a pure value (`lazy val` semantics).
3. `defer` delays production of the next `Eval`, enabling stack-safe recursive composition.
4. `flat_map` is lazy in the continuation and does not force intermediate values.
5. `value` is total and explicit about termination budget.

## Representation and Opacity

Public `Eval` stays opaque by exporting only the type name (not constructors).
Internally, represent computations with a hidden node type.

Proposed internal shape:

1. `Now(value: a)`
2. `Later(thunk: Lazy[a])`
3. `Defer(thunk: Lazy[Eval[a]])`
4. `FlatMap[b](source: Eval[b], fn: b -> Eval[a])`

`Eval[a: +*]` remains covariant because `a` appears only in positive result positions.

## Evaluation Architecture (Trampoline)

Use an explicit state machine and continuation stack, not recursive `value` calls.

Internal machine states:

1. `RunEval(current: Eval[a], stack: Stack[a, b])`
2. `RunStack(value: a, stack: Stack[a, b])`

Internal continuation stack:

1. `Done(fn: a -> b)`
2. `More[c](fn: a -> Eval[c], rest: Stack[c, b])`

Evaluation loop behavior:

1. If `RunEval(Now(v), stack)`: move to `RunStack(v, stack)`.
2. If `RunEval(Later(t), stack)`: force `get_Lazy(t)`, then `RunStack(v, stack)`.
3. If `RunEval(Defer(t), stack)`: force `get_Lazy(t)`, then `RunEval(next, stack)`.
4. If `RunEval(FlatMap(src, fn), stack)`: push `fn` to stack, continue with `src`.
5. If `RunStack(v, Done(k))`: return `Some(k(v))` (for `value`, `k` is identity).
6. If `RunStack(v, More(fn, rest))`: compute `fn(v)` and continue with `RunEval(next, rest)`.
7. Each transition decrements `fuel`; when `fuel <= 0`, return `None`.

This keeps call stack bounded and makes deep bind chains safe.

## Totality Strategy

### Why explicit fuel in `value`

Bosatsu recursion must have a provably decreasing argument. For a general `Eval` interpreter, explicit fuel is the most direct and reliable proof vehicle. It also makes runaway computations observable via `None`.

### Why not parameterless `value` in v1

Issue #80 explicitly calls out uncertainty about fuel-free running. Without either:

1. a strong, computable global bound for each `Eval`, or
2. a richer domain-predicate witness carried in the type,

a fuel-free total API is not straightforward. v1 therefore chooses correctness and explicitness over hidden heuristics.

## Expected Complexity

1. `now`, `later`, `defer`, `flat_map`: O(1) construction.
2. `value(eval, fuel)`: O(steps executed) time, O(pending flat_map depth) heap, O(1) call stack.
3. No recursive stack growth from left- or right-associated `flat_map` chains.

## Implementation Plan

### Phase 1: New module and core representation

1. Add `src/Zafu/Control/Eval.bosatsu`.
2. Define opaque `Eval[a: +*]` and hidden internal node constructors.
3. Implement `now`, `later`, `defer`, `flat_map`.

### Phase 2: Trampoline evaluator

1. Add hidden stack and machine-state types.
2. Implement `value(eval, fuel)` as a fuel-decreasing loop/recur state machine.
3. Ensure all recursive calls are accepted under Bosatsu termination checks.

### Phase 3: Tests

Add module tests covering:

1. `now`/`later`/`defer` basic correctness.
2. `flat_map` composition behavior.
3. Deep bind chain stack-safety (for example 100k steps with sufficient fuel).
4. Fuel exhaustion returns `None` deterministically.
5. Covariance compile witness (widening `Eval[Sub]` to `Eval[Super]`).

### Phase 4: Validation

1. `./bosatsu lib check`
2. `./bosatsu lib test`
3. `scripts/test.sh`

## Acceptance Criteria

1. `docs/design/80-design-an-eval-class.md` exists with this architecture and rollout plan.
2. `src/Zafu/Control/Eval.bosatsu` exists and exports `Eval`, `now`, `later`, `defer`, `flat_map`, `value`.
3. `Eval` is declared covariant (`Eval[a: +*]`).
4. `Eval` constructors are opaque to external modules.
5. `later` and `defer` use `Bosatsu/Lazy` internally for delayed computation.
6. `value(eval, fuel)` is implemented via an explicit trampoline/state machine.
7. `value` is stack-safe for very deep `flat_map` chains when fuel is sufficient.
8. Exhausted fuel yields `None` (no crashes, no partial pattern-match failures).
9. Tests cover core semantics, stack-safety regression, and fuel exhaustion behavior.
10. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: fuel ergonomics are inconvenient for callers.
Mitigation: document recommended fuel derivation from input size in API docs and examples; keep possible wrapper APIs as follow-up.

2. Risk: under-fueling may look like logical failure.
Mitigation: make `None` semantics explicit in docs/tests and keep behavior deterministic.

3. Risk: retention of large closures through deferred/lazy thunks.
Mitigation: prefer small closure capture in examples; force and release intermediate nodes during evaluation path.

4. Risk: variance/type-checking complexity around existential `FlatMap` internals.
Mitigation: if direct constructor typing is rejected, fall back to the known Church-encoded stack/frame style already used in Bosatsu test workspace `Eval`.

## Rollout Notes

1. Land as an additive module on `main`; no migration required.
2. Start with internal/module-local adoption in new recursive utilities before broad refactors.
3. Use explicit fuel at call sites derived from known problem size (for example recursion depth or input length).
4. Track real-world fuel patterns; if usage stabilizes, follow up with a convenience API for common budgets.
5. Revisit a fuel-free API only after we have a defensible totality story (domain witness or proven bound strategy).
