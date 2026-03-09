---
issue: 73
priority: 3
touch_paths:
  - docs/design/73-zafu-monoid.md
  - src/Zafu/Abstract/Monoid.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-09T03:34:18Z
---

# Design: Add Zafu/Abstract/Monoid

_Issue: #73 (https://github.com/johnynek/zafu/issues/73)_

## Summary

Design doc content for issue #73 proposing a Monoid abstraction layered on Semigroup with specialization-preserving projection, law definitions, predef instance coverage, and delivery criteria.

---
issue: 73
priority: 2
touch_paths:
  - docs/design/73-zafu-monoid.md
  - src/Zafu/Abstract/Monoid.bosatsu
  - src/Zafu/Abstract/Instances/Predef.bosatsu
depends_on:
  - 59
estimated_size: M
generated_at: 2026-03-09T04:40:00Z
---

# Design: Add Zafu/Abstract/Monoid

_Issue: #73 (https://github.com/johnynek/zafu/issues/73)_

## Summary

Add `Zafu/Abstract/Monoid` as `Semigroup + empty`, define monoid laws, preserve semigroup specialization through `monoid_to_semigroup`, and add `Predef` monoid instances consistent with existing semigroup naming and behavior.

## Status

Proposed

## Context

1. `Zafu/Abstract/Semigroup` already exists with specialization hooks (`combine_n_positive_fn`, `combine_all_option_fn`) and broad `Predef` coverage.
2. Issue #73 asks for a Cats-inspired `Monoid`: semigroup operation plus identity element, law helper, and safe projection to semigroup without losing specialization.
3. Existing abstract modules (`Eq`, `Ord`, `Hash`, `Semigroup`) use dictionary structs, constructor helpers, projection helpers, and `laws_*` test helpers.
4. `src/Zafu/Abstract/Instances/Predef.bosatsu` is the canonical location for baseline instances.

## Goals

1. Add `src/Zafu/Abstract/Monoid.bosatsu` with a stable dictionary-based API.
2. Define `laws_Monoid` for associativity and identity.
3. Ensure `monoid_to_semigroup` preserves all specialization embedded in the original semigroup dictionary.
4. Keep API and naming consistent with current `Semigroup` module style.
5. Add practical `Predef` monoid instances for existing primitive and structural types.
6. Document recommended `Semigroup` additions requested in the issue body.

## Non-goals

1. Adding algebraic hierarchy types beyond `Monoid` (for example `CommutativeMonoid`, `Group`, `Semilattice`) in this issue.
2. Global or implicit instance resolution.
3. Refactoring existing collections to require `Monoid`.
4. Choosing unsuffixed default monoids for ambiguous scalar semantics (`Bool`, `Int`, `Float64`).

## Decision Summary

1. Represent `Monoid[a]` as a pair of `empty` value and concrete `Semigroup[a]` dictionary.
2. Make `monoid_from_semigroup` a first-class constructor so specialization is retained.
3. Implement `monoid_to_semigroup` as a direct field projection, not reconstruction from `combine`.
4. Derive `combine_n` and `combine_all` from semigroup operations plus identity fallback (`n <= 0` and empty input).
5. Keep ambiguous primitive names explicitly suffixed in `Predef` (`*_add`, `*_mul`, `*_and`, `*_or`).

## API Design

### Module: `Zafu/Abstract/Monoid`

Proposed exports:

1. `Monoid`
2. `monoid_from_semigroup`
3. `monoid_from_combine`
4. `monoid_specialized`
5. `empty`
6. `combine`
7. `combine_n`
8. `combine_all`
9. `is_empty`
10. `reverse`
11. `monoid_to_semigroup`
12. `laws_Monoid`

Proposed struct shape:

1. `empty_value: a`
2. `semigroup_inst: Semigroup[a]`

Constructor behavior:

1. `monoid_from_semigroup(empty_value, semigroup_inst)` is the preferred constructor when a semigroup already exists.
2. `monoid_from_combine(empty_value, combine_fn)` delegates to `semigroup_from_combine(combine_fn)`.
3. `monoid_specialized(empty_value, combine_fn, combine_n_positive_fn, combine_all_option_fn)` wraps `semigroup_specialized(...)` then calls `monoid_from_semigroup`.

Operation behavior:

1. `empty(inst)` returns the identity value.
2. `combine(inst, left, right)` delegates to `combine_Semigroup(monoid_to_semigroup(inst), left, right)`.
3. `combine_n(inst, value, n)` returns `empty(inst)` when `n <= 0`; otherwise delegates to semigroup `combine_n` and unwraps `Some`.
4. `combine_all(inst, items)` returns `empty(inst)` on empty input; otherwise delegates to semigroup `combine_all_option` and unwraps `Some`.
5. `is_empty(inst, eq_inst, value)` compares `value` with `empty(inst)`.
6. `reverse(inst)` keeps the same identity and uses `reverse_Semigroup(monoid_to_semigroup(inst))`.
7. `monoid_to_semigroup(inst)` returns stored `semigroup_inst` directly.

Dependency boundary:

1. Core monoid behavior depends only on Bosatsu predef and `Semigroup`.
2. `Eq` is used for `is_empty` and `laws_Monoid`, matching existing law-helper style.

## Law Design

`laws_Monoid(inst, eq_inst, x, y, z) -> Test` checks:

1. Associativity through `laws_Semigroup(monoid_to_semigroup(inst), eq_inst, x, y, z)`.
2. Left identity: `combine(inst, empty(inst), x) == x`.
3. Right identity: `combine(inst, x, empty(inst)) == x`.

Law notes:

1. `combine_n` and `combine_all` behavior for empty/non-positive inputs are API semantics derived from identity, not separate algebraic laws.
2. The helper follows the same sample-based `TestSuite` style used by other abstract modules.

## Predef Instance Plan

### Monoid instances to add now

1. `monoid_Unit`: identity `()` with `semigroup_Unit`.
2. `monoid_Bool_and`: identity `True` with `semigroup_Bool_and`.
3. `monoid_Bool_or`: identity `False` with `semigroup_Bool_or`.
4. `monoid_Int_add`: identity `0` with `semigroup_Int_add`.
5. `monoid_Int_mul`: identity `1` with `semigroup_Int_mul`.
6. `monoid_Float64_add`: identity `0.0` with `semigroup_Float64_add`.
7. `monoid_Float64_mul`: identity `1.0` with `semigroup_Float64_mul`.
8. `monoid_String`: identity `""` with `semigroup_String`.
9. `monoid_Option(semigroup_item)`: identity `None`, built from `semigroup_Option(semigroup_item)`.
10. `monoid_List`: identity `[]` with `semigroup_List`.
11. `monoid_Tuple1` through `monoid_Tuple32`: field-wise monoids built from field monoids; identity is tuple of field identities; combine uses existing tuple semigroup constructors fed by `monoid_to_semigroup` per field.

Naming policy:

1. Keep unsuffixed names for structurally unambiguous instances only.
2. Keep suffixes for ambiguous scalar policies.
3. Do not add unsuffixed aliases (`monoid_Int`, `monoid_Bool`, `monoid_Float64`) in this issue.

### Semigroup suggestions requested by issue #73

The issue also asks which semigroups should be added to `Predef`. Recommended candidates:

1. `semigroup_Comparison_then`: left-biased non-`EQ` composition (`EQ` behaves as identity), matching lexicographic comparator chaining.
2. `semigroup_Dict_merge(semigroup_value)`: key-wise union that combines colliding values with provided semigroup.
3. Explicit bias variants if a default map policy is undesirable:
`semigroup_Dict_first` (left-biased)
`semigroup_Dict_last` (right-biased)

These semigroup additions are recommendations; they are not required to ship `Monoid` core.

## Implementation Plan

### Phase 1: Monoid module

1. Add `src/Zafu/Abstract/Monoid.bosatsu`.
2. Implement dictionary type, constructors, projection, operations, `reverse`, and `laws_Monoid`.
3. Add module tests for:
- identity behavior,
- `combine_n` on non-positive `n`,
- `combine_all` on empty list,
- `reverse` behavior,
- law helper sanity.

### Phase 2: Predef integration

1. Import `Monoid` in `src/Zafu/Abstract/Instances/Predef.bosatsu`.
2. Add exports and definitions for all monoid instances listed above.
3. Add tuple monoid family `Tuple1..Tuple32` in style parallel to existing tuple semigroup family.
4. Extend `Predef` tests with representative primitive, option/list, and high-arity tuple checks.

### Phase 3: Specialization-preservation validation

1. Add targeted tests proving `monoid_to_semigroup` preserves specialized semigroup paths.
2. Use a custom semigroup in tests with intentionally distinct `combine_n_positive_fn` and `combine_all_option_fn` results to ensure projection does not regress to derived defaults.

### Phase 4: Validation

1. Run `./bosatsu lib check`.
2. Run `./bosatsu lib test`.
3. Run `scripts/test.sh`.

## Acceptance Criteria

1. `docs/design/73-zafu-monoid.md` is added with this architecture and rollout plan.
2. `src/Zafu/Abstract/Monoid.bosatsu` exists and exports the API listed in this document.
3. `Monoid` construction from an existing semigroup is supported (`monoid_from_semigroup`).
4. `monoid_to_semigroup` is implemented as direct projection and preserves specialized semigroup behavior.
5. `laws_Monoid` checks associativity and left and right identity.
6. `combine_n(inst, value, n)` returns `empty(inst)` for `n <= 0`.
7. `combine_all(inst, [])` returns `empty(inst)`.
8. `src/Zafu/Abstract/Instances/Predef.bosatsu` exports monoid instances listed in `Monoid instances to add now`.
9. Tuple monoid constructors are available for `Tuple1..Tuple32`.
10. Existing `Eq`, `Ord`, `Hash`, and `Semigroup` behavior remains unchanged.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: semigroup specialization is accidentally dropped when converting from monoid.
Mitigation: project stored semigroup dictionary directly and add explicit regression tests for specialized `combine_n` and `combine_all_option` behavior.

2. Risk: tuple boilerplate introduces copy/paste mistakes.
Mitigation: follow established tuple-generation pattern and include representative low/high arity tests (`Tuple2`, `Tuple32`).

3. Risk: ambiguity of scalar operation choices causes confusion.
Mitigation: keep explicit suffixed names and avoid unsuffixed defaults for ambiguous primitives.

4. Risk: scope expansion from map/dict semigroup policy decisions delays monoid delivery.
Mitigation: keep dict semigroup recommendations out of required scope for this issue.

## Rollout Notes

1. Ship as additive API on `main`; no migration required.
2. Existing semigroup-based code continues to work unchanged.
3. Encourage downstream modules to prefer `monoid_from_semigroup` so optimized semigroup implementations are reused.
4. Include short PR notes with examples of replacing manual empty+fold code with `combine_all`.
5. Track semigroup recommendation follow-ups (`Comparison_then`, `Dict_*`) as separate issues if not included in this implementation PR.
