---
issue: 59
priority: 3
touch_paths:
  - docs/design/59-add-zafu-abstract-semigroup.md
  - src/Zafu/Abstract/Semigroup.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-08T21:07:02Z
---

# Design Doc Content for Issue #59: Add Zafu/Abstract/Semigroup

_Issue: #59 (https://github.com/johnynek/zafu/issues/59)_

## Summary

Complete design-doc content proposing `Zafu/Abstract/Semigroup`, its law/helpers/combinators, and a concrete `Predef` semigroup instance plan with acceptance criteria, risks, and rollout notes.

---
issue: 59
priority: 2
touch_paths:
  - docs/design/59-add-zafu-abstract-semigroup.md
  - src/Zafu/Abstract/Semigroup.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
depends_on:
  - 28
estimated_size: M
generated_at: 2026-03-08T21:20:00Z
---

# Design: Add Zafu/Abstract/Semigroup

_Issue: #59 (https://github.com/johnynek/zafu/issues/59)_

## Summary

Add `Zafu/Abstract/Semigroup` for associative combining, include a law helper and Cats-inspired convenience/combinator APIs (`reverse`, `intercalate`, etc.), and add a concrete `Predef` instance set with explicit naming where semantics are ambiguous.

## Status

Proposed

## Context

1. Zafu has `Eq`, `Ord`, and `Hash`, but not `Semigroup`.
2. Existing abstract modules use opaque dictionary structs with constructor helpers, derived operations, and `laws_*` checkers in the same module.
3. Issue #59 asks for an implementation inspired by Cats kernel Semigroup, including helper and combinator ergonomics.
4. `src/Zafu/Abstract/Instances/Predef.bosatsu` is the established place for built-in baseline instances.

## Goals

1. Add `src/Zafu/Abstract/Semigroup.bosatsu` with stable, dictionary-based APIs.
2. Define semigroup associativity law checking.
3. Implement convenience helpers and combinators requested by issue #59.
4. Add practical Semigroup instances to `Predef` with clear semantics.
5. Keep the change additive and compatible with existing modules.

## Non-goals

1. Introducing `Monoid` or commutativity/idempotence hierarchies in this issue.
2. Adding implicit/global instance resolution.
3. Forcing one unsuffixed Semigroup choice for every ambiguous primitive type.
4. Refactoring all existing collection modules to consume Semigroup in this PR.

## API Design

### Module: `Zafu/Abstract/Semigroup`

Proposed exports:

1. `Semigroup`
2. `semigroup_from_combine`
3. `semigroup_specialized`
4. `combine`
5. `combine_n`
6. `combine_all_option`
7. `maybe_combine_left`
8. `maybe_combine_right`
9. `reverse`
10. `intercalate`
11. `first`
12. `last`
13. `laws_Semigroup`

Proposed struct shape:

1. `combine_fn: (a, a) -> a`
2. `combine_n_positive_fn: (a, Int) -> a`
3. `combine_all_option_fn: List[a] -> Option[a]`

Constructor behavior:

1. `semigroup_from_combine` takes only `combine_fn` and derives helper fields.
2. `semigroup_specialized` allows optimized helper implementations while preserving `combine` semantics.

Operation behavior:

1. `combine(inst, x, y)` delegates to `combine_fn`.
2. `combine_n(inst, a, n) -> Option[a]` returns `None` when `n <= 0`; otherwise returns `Some(a combined n times)`.
3. `combine_all_option(inst, items)` returns `None` for empty input and `Some(total)` for non-empty input.
4. `maybe_combine_left(inst, left_opt, right)` combines when `left_opt` is `Some`, otherwise returns `right`.
5. `maybe_combine_right(inst, left, right_opt)` combines when `right_opt` is `Some`, otherwise returns `left`.

Combinator behavior:

1. `reverse(inst)` swaps operand order: `reverse.combine(x, y) == combine(inst, y, x)`.
2. `intercalate(inst, middle)` inserts `middle` between operands: `x <> middle <> y`.
3. `first()` always returns the left operand.
4. `last()` always returns the right operand.

Implementation notes:

1. `combine_n_positive_fn` should use exponentiation-by-squaring style repeated doubling for logarithmic combine count.
2. Derived `combine_all_option` should use strict left fold to avoid recursion depth growth on large lists.
3. `reverse` should preserve `combine_n` behavior for repeated identical values.

## Law Design

`laws_Semigroup(inst, eq_inst, x, y, z) -> Test` will assert associativity:

1. `combine(x, combine(y, z)) == combine(combine(x, y), z)` using `Eq` equality checks.

Law scope and intent:

1. Associativity is the only required Semigroup law.
2. Helper behavior checks (`combine_n`, `reverse`, `intercalate`) belong in module tests, not in the law definition itself.
3. The law helper follows existing `laws_Eq`, `laws_Ord`, and `laws_Hash` style: sample-based checks with assertion labels.

## Predef Instance Plan

### Instances to add now

Unambiguous and structural instances:

1. `semigroup_Unit`: always returns `Unit`.
2. `semigroup_String`: left-to-right string concatenation.
3. `semigroup_List`: left-to-right list concatenation.
4. `semigroup_Option(item_sg)`: `Some+Some` combines payloads; otherwise returns the present side; `None+None` is `None`.
5. `semigroup_Tuple1` through `semigroup_Tuple32`: field-wise combination using each field Semigroup.

Ambiguous primitive operations with explicit names:

1. `semigroup_Bool_and`
2. `semigroup_Bool_or`
3. `semigroup_Int_add`
4. `semigroup_Int_mul`
5. `semigroup_Float64_add`
6. `semigroup_Float64_mul`

### Naming policy

1. Keep unsuffixed `semigroup_*` names for structurally unambiguous cases.
2. Require operation suffixes for ambiguous scalar semantics to avoid locking policy accidentally.
3. Do not add unsuffixed `semigroup_Bool`, `semigroup_Int`, or `semigroup_Float64` in this issue.

### Deferred instances

1. `Dict` Semigroup is deferred because key-collision semantics need an explicit policy decision (`last-wins` vs `value-combine`) and would couple to key equality/hash conventions.
2. Collection-specific semigroups for Zafu custom data structures remain colocated with those modules and are not part of `Predef` in this issue.

## Implementation Plan

### Phase 1: Semigroup module

1. Add `src/Zafu/Abstract/Semigroup.bosatsu`.
2. Implement dictionary struct, constructors, core operations, helpers, and combinators.
3. Implement `laws_Semigroup` and module tests for associativity and helper behavior.

### Phase 2: Predef integration

1. Import `Semigroup` module in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
2. Add exports and implementations for the planned instances.
3. Add tuple Semigroup family (`Tuple1..Tuple32`) in the same style as existing Eq/Ord/Hash tuple families.
4. Extend `Predef` tests with representative coverage for structural and suffixed primitive instances.

### Phase 3: Validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/59-add-zafu-abstract-semigroup.md` exists with this architecture and rollout plan.
2. `src/Zafu/Abstract/Semigroup.bosatsu` exists and exports the API listed in this doc.
3. `laws_Semigroup` checks associativity via `Eq`.
4. `reverse` and `intercalate` are implemented and covered by tests.
5. `combine_n` is implemented with `Option` return semantics and large-`n` behavior is stack-safe.
6. `combine_all_option` is implemented and returns `None` on empty input.
7. `first` and `last` combinator constructors are implemented.
8. `src/Zafu/Abstract/Instances/Predef.bosatsu` exports all instances listed in the `Instances to add now` section.
9. Tuple Semigroup instances are available for `Tuple1..Tuple32`.
10. No existing `Eq`, `Ord`, or `Hash` behavior changes.
11. `./bosatsu lib check` passes.
12. `./bosatsu lib test` passes.
13. `scripts/test.sh` passes before merge.

## Risks and Mitigations

1. Risk: ambiguous primitive semantics cause user confusion.
Mitigation: explicit suffixed names for ambiguous primitive Semigroups and no unsuffixed aliases in this issue.

2. Risk: tuple boilerplate mistakes across `Tuple1..Tuple32`.
Mitigation: follow existing tuple instance pattern and add representative tuple tests at low and high arities.

3. Risk: helper semantics drift from `combine` lawfulness.
Mitigation: derive helpers from `combine` by default and keep specialization behind `semigroup_specialized`.

4. Risk: performance regressions for large `combine_n`.
Mitigation: use logarithmic repeated-combine algorithm and include stress tests.

## Rollout Notes

1. Ship as additive API on `main`; no migrations required.
2. Keep helper semantics stable after merge so downstream code can rely on predictable behavior.
3. Encourage downstream modules to import explicit suffixed primitive Semigroups when policy matters.
4. Follow-up issue can introduce `Monoid` and optional unsuffixed primitive aliases if consensus forms.
