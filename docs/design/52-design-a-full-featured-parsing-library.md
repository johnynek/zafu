---
issue: 52
priority: 3
touch_paths:
  - docs/design/52-design-a-full-featured-parsing-library.md
  - src/Zafu/Text/Parse.bosatsu
  - src/Zafu/Text/Parse/Internal/Core.bosatsu
  - src/Zafu/Text/Parse/Internal/Engine.bosatsu
  - src/Zafu/Text/Parse/Internal/Error.bosatsu
  - src/Zafu/Text/Parse/Rfc5234.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-08T20:34:19Z
---

# Design: Zafu/Text/Parse

_Issue: #52 (https://github.com/johnynek/zafu/issues/52)_

## Summary

Architecture and phased implementation plan for issue #52: a cats-parse-inspired parsing library with Parser0/Parser split, totality fuel model, full combinator inventory, acceptance criteria, risks, and rollout guidance.

---
issue: 52
priority: 2
touch_paths:
  - docs/design/52-design-a-full-featured-parsing-library.md
  - src/Zafu/Text/Parse.bosatsu
  - src/Zafu/Text/Parse/Internal/Core.bosatsu
  - src/Zafu/Text/Parse/Internal/Engine.bosatsu
  - src/Zafu/Text/Parse/Internal/Error.bosatsu
  - src/Zafu/Text/Parse/Rfc5234.bosatsu
depends_on:
  - 42
estimated_size: L
generated_at: 2026-03-08T21:00:00Z
---

# Design: Zafu/Text/Parse

_Issue: #52 (https://github.com/johnynek/zafu/issues/52)_

## Summary

Add a full-featured parser combinator library under `Zafu/Text/Parse`, inspired by `cats-parse`, with explicit `Parser0` vs `Parser` separation, strong stack-safety/totality guarantees, high-performance execution, rich combinator coverage, and precise parse errors.

Core entrypoint:

`def parse[a](parser: Parser[a], text: String) -> Result[Error, a]`

## Status

Proposed

## Context

`zafu` currently has no text parsing module. Issue #52 requests a complete parsing library design modeled after `cats-parse`, including:

1. `Parser0` (may consume zero input) separated from `Parser` (must consume at least one token on success).
2. Unbounded repetition only on `Parser`.
3. High performance and stack-safety.
4. Concrete combinator inventory.
5. A totality strategy that avoids non-termination, especially from `Parser0` paths.

## Goals

1. Add a new first-party parsing namespace rooted at `Zafu/Text/Parse`.
2. Expose `parse(parser, text)` returning `Result[Error, a]`.
3. Preserve the `Parser0`/`Parser` safety split and enforce it in combinator APIs.
4. Make all runtime parsing loops stack-safe using explicit loop-based interpreter paths.
5. Guarantee total evaluation by using bounded fuel derived from the input length and parser shape.
6. Ship an ergonomic API with both named combinators and operator aliases.
7. Provide precise, farthest-failure errors with expectation merging and context stack support.

## Non-goals

1. Left-recursive grammar support in v1.
2. Packrat/memoizing parsers in v1.
3. Incremental streaming parser state in v1.
4. Binary parsing (bytes) in this issue.
5. Full parity with every cats-parse micro-optimization in the first implementation.

## Architecture Overview

### Module layout

1. `src/Zafu/Text/Parse.bosatsu`
   Public API surface, exported types, combinators, and top-level parse functions.
2. `src/Zafu/Text/Parse/Internal/Core.bosatsu`
   Internal parser node representation and parser metadata (consumption and budget traits).
3. `src/Zafu/Text/Parse/Internal/Engine.bosatsu`
   Loop-based evaluation engine, state transitions, fuel accounting, and backtracking machinery.
4. `src/Zafu/Text/Parse/Internal/Error.bosatsu`
   Error/expectation model and rendering helpers.
5. `src/Zafu/Text/Parse/Rfc5234.bosatsu`
   Common character-class parsers (`digit`, `alpha`, `sp`, etc.) built on top of core primitives.

### Public types

1. `Parser0[a]`
   Parser that may succeed without consuming input.
2. `Parser[a]`
   Parser that must consume at least one token on success.
3. `Error`
   Final parse error exposed from `parse`/`parse_prefix`.
4. `Expectation`
   Structured expected-token/error context entries.
5. `Caret`
   `(offset, line, column)` location helper for diagnostics.

### Input model

We model input as `n + 1` logical tokens for a string of length `n`:

1. `Char` tokens for offsets `[0, n - 1]`.
2. A single virtual `End` token at offset `n`.

This lets `end` be a consuming `Parser[Unit]` rather than a non-consuming `Parser0[Unit]`, which helps keep repetition safety invariants simple.

### Internal representation and execution

`Parser0`/`Parser` are opaque wrappers around an internal node graph plus metadata:

1. `root: Node[a]`
2. `consumes_on_success: Bool`
3. `node_cost: Int`
4. `allows_epsilon_success: Bool`

`Node` variants (internal, not exported) cover primitives and combinators:

1. `Pure`, `Fail`, `FailWith`
2. `AnyChar`, `Char`, `CharIn`, `CharWhere`, `String`, `String0`, `End`
3. `Map`, `As`, `Void`, `WithString`
4. `Product`, `KeepLeft`, `KeepRight`, `OneOf`, `EitherOr`
5. `Backtrack`, `SoftProduct`, `Peek`, `Not`, `Optional`
6. `FlatMap`, `Defer`
7. `Rep`, `RepSep`, `RepUntil`, `ChainLeft1`, `ChainRight1`
8. `WithContext`, `Label`

The engine evaluates nodes with an explicit frame stack (continuation frames for mapping, sequencing, alternatives, and backtracking marks) using `loop`/`int_loop` rather than recursive interpretation. This keeps stack use bounded even for deep repetition or nested combinator trees.

### Performance strategy

1. Fast-path node tags for `char`, `char_in`, `string`, and `end` avoid generic dispatch overhead in hot loops.
2. `void` and `matched` use capture flags to skip unnecessary value allocations.
3. `one_of` constructors normalize and merge branches where possible (especially string and char alternatives).
4. Choice evaluation keeps farthest-failure bookkeeping in mutable-like state tuples to avoid rebuilding error collections at each branch.
5. Repetition uses tight loop forms with parser-local accumulators.

### Invariants

1. `Parser[a]` success always advances offset by at least one logical token.
2. `Parser0[a]` may succeed at same offset.
3. Repetition combinators with unbounded upper bounds accept only `Parser[a]` items.
4. Every parse run terminates: engine consumes fuel on every evaluation step.
5. Choice (`or_else` / `|`) only falls through on epsilon failure.
6. Backtracking is opt-in (`backtrack` / `soft_product`) to keep errors precise by default.

## Failure Model

### Internal failure classes

1. `EpsilonFailure`
   Failure with no consumed input in this branch.
2. `ArrestingFailure`
   Failure after consumption; branch is committed unless explicitly backtracked.

### Public error

`Error` captures:

1. `input: String`
2. `failed_at: Int`
3. `expected: List[Expectation]` (deduplicated/merged at farthest offset)
4. `contexts: List[String]` (innermost-first or outermost-first by chosen renderer, fixed consistently)

Expectation variants:

1. `ExpectedChar(ch: Char)`
2. `ExpectedString(value: String)`
3. `InRange(lower: Char, upper: Char)`
4. `ExpectedEnd`
5. `ExpectedPredicate(label: String)`
6. `FailWith(message: String)`
7. `InContext(label: String)`

## Totality and Stack-Safety Plan

Issue #52 explicitly calls out totality concerns around `Parser0`. The plan combines type-level restrictions plus runtime budgets:

### 1. Static metadata per parser

Each internal parser node carries precomputed metadata:

1. `consumes_on_success: Bool`
2. `node_cost: Int` (rough per-step complexity estimate)
3. `allows_epsilon_success: Bool`

For `Parser`, `consumes_on_success` is always `True`.

### 2. Runtime fuel derived from input

At parse entry, compute:

1. `token_budget = text_length + 1` (includes virtual `End` token).
2. `step_budget_per_token = max(32, parser.node_cost * 4)`.
3. `fuel = token_budget * step_budget_per_token`.

Engine rule: every interpreter dispatch decrements `fuel` by 1. If `fuel` reaches 0, parsing stops with deterministic failure (`FuelExhausted` internal error mapped to user-facing `Error` with context indicating likely non-productive parser shape).

This guarantees termination, including pathological `Parser0` combinations.

### 3. Minimize public `Parser0` surface

`Parser0` is kept for cases that are semantically non-consuming:

1. `pure0`
2. `optional`
3. `peek`
4. `not` (internal/public low-level)
5. `index`/`caret`/`start`

Preferred user-facing negation is consuming composition:

`def not_then[a, b](pa: Parser[a], pb: Parser[b]) -> Parser[b]`

This encodes "forbid prefix, then consume" without exposing unsafe repetition over non-consuming parsers.

### 4. Repetition restriction

Unbounded repetition APIs (`rep`, `rep0`, `rep_sep0`, `rep_until0`) are defined from a consuming item parser (`Parser[a]`) only. This preserves progress at every loop iteration.

### 5. Loop-based interpreter

No recursive descent over input in hot paths. Repetition, alternation traversal, and error merging use `loop`/`int_loop` style constructs to stay stack-safe.

## API and Combinator Inventory

This is the planned full combinator surface for `Zafu/Text/Parse` v1.

### Parse entrypoints

1. `def parse[a](parser: Parser[a], text: String) -> Result[Error, a]`
   Requires complete parse (`parser <* end`).
2. `def parse_prefix[a](parser: Parser0[a], text: String) -> Result[Error, (String, a)]`
   Parses a prefix and returns unconsumed suffix.
3. `def parse_offset[a](parser: Parser0[a], text: String) -> Result[Error, (Int, a)]`
   Prefix parse returning remaining offset.

### Primitive constructors

1. `def pure0[a](value: a) -> Parser0[a]`
2. `def fail[a] -> Parser[a]`
3. `def fail_with[a](message: String) -> Parser[a]`
4. `def any_char -> Parser[Char]`
5. `def char(ch: Char) -> Parser[Unit]`
6. `def char_in(chars: List[Char]) -> Parser[Char]`
7. `def char_where(pred: Char -> Bool, label: String) -> Parser[Char]`
8. `def string(value: String) -> Parser[Unit]` (non-empty required)
9. `def string0(value: String) -> Parser0[Unit]` (allows empty)
10. `def ignore_case_char(ch: Char) -> Parser[Unit]`
11. `def ignore_case_string(value: String) -> Parser[Unit]`
12. `def index -> Parser0[Int]`
13. `def caret -> Parser0[Caret]`
14. `def start -> Parser0[Unit]`
15. `def end -> Parser[Unit]` (consumes virtual End token)
16. `def defer0[a](mk: () -> Parser0[a]) -> Parser0[a]`
17. `def defer[a](mk: () -> Parser[a]) -> Parser[a]`

### Value combinators

1. `def map[a, b](pa: Parser0[a], fn: a -> b) -> Parser0[b]`
2. `def as[a, b](pa: Parser0[a], value: b) -> Parser0[b]`
3. `def void(pa: Parser0[a]) -> Parser0[Unit]`
4. `def with_string[a](pa: Parser0[a]) -> Parser0[(a, String)]`
5. `def matched(pa: Parser0[a]) -> Parser0[String]`
6. `def map_filter[a, b](pa: Parser0[a], fn: a -> Option[b]) -> Parser0[b]`
7. `def collect[a, b](pa: Parser0[a], fn: a -> Option[b], label: String) -> Parser0[b]`
8. `def filter[a](pa: Parser0[a], pred: a -> Bool, label: String) -> Parser0[a]`
9. `def flat_map0[a, b](pa: Parser0[a], fn: a -> Parser0[b]) -> Parser0[b]`
10. `def flat_map[a, b](pa: Parser[a], fn: a -> Parser[b]) -> Parser[b]`

### Choice and sequencing

1. `def or_else[a](left: Parser0[a], right: Parser0[a]) -> Parser0[a]`
2. `def either_or[a, b](left: Parser0[a], right: Parser0[b]) -> Parser0[Either[b, a]]`
3. `def one_of0[a](choices: List[Parser0[a]]) -> Parser0[a]`
4. `def one_of[a](choices: List[Parser[a]]) -> Parser[a]`
5. `def product0[a, b](left: Parser0[a], right: Parser0[b]) -> Parser0[(a, b)]`
6. `def product10[a, b](left: Parser[a], right: Parser0[b]) -> Parser[(a, b)]`
7. `def product01[a, b](left: Parser0[a], right: Parser[b]) -> Parser[(a, b)]`
8. `def product[a, b](left: Parser[a], right: Parser[b]) -> Parser[(a, b)]`
9. `def keep_left0[a, b](left: Parser0[a], right: Parser0[b]) -> Parser0[a]`
10. `def keep_right0[a, b](left: Parser0[a], right: Parser0[b]) -> Parser0[b]`
11. `def keep_left[a, b](left: Parser[a], right: Parser0[b]) -> Parser[a]`
12. `def keep_right[a, b](left: Parser0[a], right: Parser[b]) -> Parser[b]`
13. `def between0[a](open: Parser0[Any], inner: Parser0[a], close: Parser0[Any]) -> Parser0[a]`
14. `def between[a](open: Parser0[Any], inner: Parser[a], close: Parser0[Any]) -> Parser[a]`
15. `def surrounded_by0[a](inner: Parser0[a], border: Parser0[Any]) -> Parser0[a]`
16. `def surrounded_by[a](inner: Parser[a], border: Parser0[Any]) -> Parser[a]`

### Backtracking and lookahead

1. `def backtrack0[a](pa: Parser0[a]) -> Parser0[a]`
2. `def backtrack[a](pa: Parser[a]) -> Parser[a]`
3. `def soft_product0[a, b](left: Parser0[a], right: Parser0[b]) -> Parser0[(a, b)]`
4. `def soft_product10[a, b](left: Parser[a], right: Parser0[b]) -> Parser[(a, b)]`
5. `def soft_product01[a, b](left: Parser0[a], right: Parser[b]) -> Parser[(a, b)]`
6. `def optional[a](pa: Parser[a]) -> Parser0[Option[a]]`
7. `def peek(pa: Parser0[Any]) -> Parser0[Unit]`
8. `def not(pa: Parser0[Any]) -> Parser0[Unit]`
9. `def not_then[a, b](forbidden: Parser[a], then_parse: Parser[b]) -> Parser[b]`

### Repetition (unbounded only on Parser)

1. `def rep[a](pa: Parser[a]) -> Parser[List[a]]` (guaranteed at least one item by semantics)
2. `def rep_min[a](pa: Parser[a], min: Int) -> Parser[List[a]]`
3. `def rep_min_max[a](pa: Parser[a], min: Int, max: Int) -> Parser[List[a]]`
4. `def rep0[a](pa: Parser[a]) -> Parser0[List[a]]`
5. `def rep0_max[a](pa: Parser[a], max: Int) -> Parser0[List[a]]`
6. `def rep_exactly[a](pa: Parser[a], times: Int) -> Parser[List[a]]`
7. `def rep_sep[a](pa: Parser[a], sep: Parser0[Any]) -> Parser[List[a]]`
8. `def rep_sep0[a](pa: Parser[a], sep: Parser0[Any]) -> Parser0[List[a]]`
9. `def rep_until[a](pa: Parser[a], end: Parser0[Any]) -> Parser[List[a]]`
10. `def rep_until0[a](pa: Parser[a], end: Parser0[Any]) -> Parser0[List[a]]`
11. `def chain_left1[a](term: Parser[a], op: Parser[(a, a) -> a]) -> Parser[a]`
12. `def chain_right1[a](term: Parser[a], op: Parser[(a, a) -> a]) -> Parser[a]`

### Context and diagnostics

1. `def with_context0[a](pa: Parser0[a], ctx: String) -> Parser0[a]`
2. `def with_context[a](pa: Parser[a], ctx: String) -> Parser[a]`
3. `def label0[a](pa: Parser0[a], expected: String) -> Parser0[a]`
4. `def label[a](pa: Parser[a], expected: String) -> Parser[a]`

### Operator aliases

Because Bosatsu does not rely on subclass-based syntax extension, operators are thin top-level aliases exported from `Zafu/Text/Parse` (or `Zafu/Text/Parse/Ops` if split):

1. `|` -> `or_else`
2. `~` -> product variants
3. `*>` -> `keep_right*`
4. `<*` -> `keep_left*`
5. `?` alias function for `optional` (named alias if operator form is awkward)

Named functions remain canonical; operators are convenience only.

## Implementation Plan

### Phase 1: Core data model and engine skeleton

1. Create `Parser0`, `Parser`, `Error`, `Expectation`, `Caret` types.
2. Implement parser metadata (`consumes_on_success`, `node_cost`).
3. Build minimal engine state (input, offset, failure accumulator, fuel).
4. Implement `parse_prefix` for `Parser0` and `parse` for `Parser` + `end`.

### Phase 2: Primitive parsers and sequencing

1. Implement character/string primitives (`any_char`, `char`, `char_in`, `char_where`, `string`, `string0`, `end`).
2. Implement map/as/void/with_string.
3. Implement `product*`, `keep_left*`, `keep_right*`, `between*`, `surrounded_by*`.
4. Add choice (`or_else`, `one_of*`) with epsilon/arresting semantics.

### Phase 3: Backtracking/lookahead and Parser0 minimization hooks

1. Implement `backtrack*`, `soft_product*`, `peek`, `not`, `optional`, `not_then`.
2. Ensure `not_then` is documented as the preferred negation combinator in user grammars.
3. Add context and labeling combinators.

### Phase 4: Repetition and expression combinators

1. Implement `rep*`, `rep_sep*`, `rep_until*`, `rep_exactly`.
2. Enforce at type boundary that repeated element parser is `Parser`.
3. Implement `chain_left1` and `chain_right1` for expression parsing.

### Phase 5: RFC helper module and error polish

1. Add `Zafu/Text/Parse/Rfc5234` helpers (`alpha`, `digit`, `hexdig`, `sp`, `wsp`, etc.).
2. Finalize expectation dedup/merge and pretty error rendering.
3. Add targeted performance cleanups (`void` fast path, merged one-of, string-map dispatch).

### Phase 6: Verification and performance validation

1. Add unit and property tests in parser modules.
2. Include regression tests for totality/fuel exhaustion and backtracking behavior.
3. Run `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh`.
4. Run microbenchmarks for representative grammars (numbers, JSON subset, CSV-like rows).

## Testing Strategy

1. Primitive parser correctness tests for all success/failure edges.
2. Combinator laws:
   - map identity/composition
   - sequencing associativity for equivalent forms
   - optional/rep semantics
3. Error precision tests (farthest failure and merged expectations).
4. Backtracking tests to ensure fallback only after explicit backtrack/soft forms.
5. Progress safety tests:
   - repetition over `Parser` always terminates
   - contrived `Parser0` cycles fail deterministically via fuel exhaustion
6. Property-based equivalence tests for parser algebra rewrites (e.g., `between` vs explicit product form).

## Acceptance Criteria

1. `docs/design/52-design-a-full-featured-parsing-library.md` exists and documents architecture, implementation phases, acceptance criteria, risks, and rollout.
2. `src/Zafu/Text/Parse.bosatsu` exists and exports `Parser0`, `Parser`, `Error`, `parse`, and the listed core combinators.
3. `parse(parser, text)` returns `Result[Error, a]` and requires full input consumption.
4. `Parser` and `Parser0` are separate public types with enforced consuming-success invariant for `Parser`.
5. Unbounded repetition APIs accept `Parser` items only.
6. `end` is implemented as a consuming parser over a virtual end token.
7. Engine uses explicit loop/fuel accounting and cannot diverge on malformed/non-productive parser graphs.
8. Error reporting returns farthest-failure offsets and merged expectations.
9. `not_then` is implemented and documented as the preferred consuming negative-lookahead combinator.
10. The combinator inventory in this doc is implemented or explicitly marked as follow-up in code comments with TODO references.
11. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: Fuel heuristic too small can reject valid parses.
   Mitigation: parser metadata-driven budget, conservative defaults, and dedicated tests that stress deep but valid grammars.

2. Risk: Fuel heuristic too large can hide performance regressions.
   Mitigation: benchmark-based calibration and parser-level instrumentation for step counts in tests.

3. Risk: Backtracking misuse degrades error quality and runtime.
   Mitigation: keep backtracking opt-in and document default committed-failure behavior.

4. Risk: API sprawl from full-featured combinator set.
   Mitigation: keep canonical named functions stable; operators remain aliases; stage advanced combinators by phase.

5. Risk: Unicode edge cases for char indexing and caret mapping.
   Mitigation: define offsets in terms of Bosatsu `String` indexing semantics and test with multi-byte UTF-8 cases.

6. Risk: User grammars accidentally encode left recursion.
   Mitigation: document unsupported left recursion in v1; detect obvious self-recursive `defer` cycles when possible; fail with explicit error context.

## Rollout Notes

1. Land as an additive module family under `Zafu/Text`; no breaking changes to existing APIs.
2. Merge in phases, but keep `parse` + core primitives available in the first deliverable.
3. Keep internals (`Internal/*`) unexported so optimization changes do not break user code.
4. Publish `Rfc5234` helpers after core stabilizes to avoid locking premature names.
5. After merge, use real grammar examples (JSON subset, URL query parser, simple expression parser) to validate ergonomics before declaring API stable.

## Open Questions

1. Should `rep` return `List[a]` or a dedicated non-empty list type when one is introduced in Zafu?
2. Should parser profiling counters (step count, backtrack count) be exposed publicly or only in test/debug builds?
3. Do we want a separate `Zafu/Text/Parse/Expr` helper module for precedence climbing beyond `chain_left1`/`chain_right1`?
