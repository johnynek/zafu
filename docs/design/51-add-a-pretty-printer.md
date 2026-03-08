---
issue: 51
priority: 2
touch_paths:
  - docs/design/51-add-a-pretty-printer.md
  - src/Zafu/Text/Pretty.bosatsu
depends_on: []
estimated_size: L
generated_at: 2026-03-08T21:10:00Z
---

# Design: Add a pretty printer (`Zafu/Text/Pretty`)

_Issue: #51 (https://github.com/johnynek/zafu/issues/51)_

## Summary

Add a new `Zafu/Text/Pretty` module that ports the core Paiges `Doc` model and bounded-layout renderer to Bosatsu, plus a `struct Document[a]` typeclass-pattern API with `to_Doc` and `by` combinators. The design keeps O(1) concatenation, bounded lookahead rendering, and stack-safe traversal for large documents.

## Status

Proposed

## Context

`Zafu` currently has no pretty-printer abstraction. Issue #51 asks for:

1. A `Doc` API based on `typelevel/paiges`.
2. A `Document[a]` typeclass-pattern representation.
3. `to_Doc(docu, item)` and `by` (contramap) in the same style as `Eq`/`Hash` combinators.
4. A full list of public exports.
5. An implementation plan that preserves strong runtime/memory efficiency.

Paiges already demonstrates the target algorithmic properties (optimal/bounded layout choice with lazy structure), so this design adopts the same internal invariants while adapting API naming to Bosatsu.

## Goals

1. Add `src/Zafu/Text/Pretty.bosatsu` with an efficient, immutable `Doc` type.
2. Provide near-parity with Paiges combinators and rendering behavior.
3. Add `struct Document[a]` with `to_Doc` and `by`.
4. Provide explicit numeric formatting entry points (`int`, `float`) instead of a generic `toString` bridge.
5. Keep append/composition operations O(1) where Paiges is O(1).
6. Keep render and analysis operations stack-safe for deep documents.
7. Publish an explicit and complete export list.

## Non-goals

1. Full terminal style DSL parity with Paiges `Style` module in this issue.
2. Runtime auto-benchmark tooling in this issue.
3. Prelude/global re-export changes.
4. Rewriting existing Zafu modules to consume `Doc` in this same PR.

## Decision summary

1. Implement one module: `package Zafu/Text/Pretty`.
2. Keep public `Doc` opaque via an internal node enum (`VDoc`) wrapped in `struct Doc(...)`.
3. Port Paiges core nodes (`Concat`, `Nest`, `Align`, `FlatAlt`, `Union`, `LazyDoc`, etc.) and key invariants.
4. Represent deferred docs as `LazyDoc(thunk: Lazy[Doc])` using `Bosatsu/Lazy`.
5. Use a chunk-stream renderer with bounded `fits` lookahead (Paiges `Chunk.best` strategy).
6. Provide named Bosatsu functions for combinators that are symbolic/overloaded in Scala.
7. Add `struct Document[a](to_doc_fn: a -> Doc)` with `to_Doc`, `document_from_fn`, and `by`.
8. Include focused predef `Document` instances (`String`, `Char`, `Unit`, `Bool`, `Int`, `Float64`, `List`, `Option`) with explicit rendering semantics.

## Public exports

The module will export the following API:

1. `Doc`
2. `Document`
3. `empty`
4. `space`
5. `comma`
6. `line`
7. `line_break`
8. `hard_line`
9. `line_or`
10. `line_or_space`
11. `line_or_empty`
12. `char`
13. `text`
14. `text_with_line`
15. `int`
16. `float`
17. `spaces`
18. `defer`
19. `zero_width`
20. `ansi_control`
21. `append`
22. `prepend_text`
23. `append_text`
24. `repeat`
25. `append_line`
26. `append_line_text`
27. `append_space`
28. `append_space_text`
29. `append_line_or_space`
30. `append_line_or_space_text`
31. `hang`
32. `indent`
33. `nested`
34. `aligned`
35. `bracket_by`
36. `tight_bracket_by`
37. `grouped`
38. `flatten`
39. `flatten_option`
40. `unzero`
41. `is_empty`
42. `non_empty`
43. `max_width`
44. `representation`
45. `render`
46. `render_trim`
47. `render_stream`
48. `render_stream_trim`
49. `render_wide_stream`
50. `split`
51. `paragraph`
52. `fill`
53. `fold_docs`
54. `intercalate`
55. `cat`
56. `spread`
57. `stack`
58. `tabulate`
59. `tabulate_with`
60. `document_from_fn`
61. `to_Doc`
62. `by`
63. `document_String`
64. `document_Char`
65. `document_Unit`
66. `document_Bool`
67. `document_Int`
68. `document_Float64`
69. `document_List`
70. `document_Option`

## Formatting specification

### `int`

1. `int(value: Int) -> Doc` renders the canonical base-10 integer form with optional leading `-`.
2. No extra whitespace or grouping separators are inserted.

### `float`

1. `float(value: Float64) -> Doc` renders a deterministic, parseable format.
2. `NaN` renders as `NaN`.
3. Positive and negative infinity render as `Infinity` and `-Infinity`.
4. Finite values render in a shortest round-trippable decimal representation.
5. `-0.0` is preserved as `-0.0`.

## Paiges parity mapping

API compatibility is semantic, with Bosatsu naming adjustments:

1. Paiges `d + e` -> `append(d, e)`.
2. Paiges `d / e` -> `append_line(d, e)`.
3. Paiges `d & e` -> `append_space(d, e)`.
4. Paiges `d.lineOrSpace(e)` -> `append_line_or_space(d, e)`.
5. Paiges `d.grouped` -> `grouped(d)`.
6. Paiges `d.nested(i)` -> `nested(d, i)`.
7. Paiges `d.aligned` -> `aligned(d)`.
8. Paiges `d.bracketBy(l, r, i)` -> `bracket_by(d, l, r, i)`.
9. Paiges `Doc.fill(...)`, `Doc.intercalate(...)`, etc. -> same names in snake_case.
10. Paiges `Document[A].contramap` -> `by(docu, project)`.

Deliberate differences:

1. No Scala operator overload entry points in the export surface.
2. No `PrintWriter` APIs (`writeTo`, `writeToTrim`) in this pure Bosatsu module.

## Architecture

### Core representation

`Doc` will be a wrapper over an internal node tree:

1. `Empty`
2. `Text(str)`
3. `ZeroWidth(str)`
4. `Line`
5. `FlatAlt(default, when_flat)`
6. `Concat(left, right)`
7. `Nest(indent, doc)`
8. `Align(doc)`
9. `Union(flattened, fallback)`
10. `LazyDoc(thunk: Lazy[Doc])`

Why this shape:

1. Matches Paiges invariants directly.
2. Keeps append O(1) by building `Concat` nodes.
3. Supports bounded-width branch choice via `Union` + `fits`.
4. Supports delayed construction for recursive combinators (`defer`, `fill`) via `Bosatsu/Lazy`.

### Invariants

1. `Text` nodes are non-empty and contain no literal newline.
2. `Union(flattened, fallback)` obeys: `flatten(flattened) == flatten(fallback)` and left branch is the optimistic branch.
3. Flattening preserves or improves right-association of concatenation chains.
4. `FlatAlt` is only used where flattening changes behavior.
5. Public constructors normalize inputs to avoid redundant nodes (`append(empty, x) == x`, etc.).

### Rendering engine

Renderer follows Paiges `Chunk.best` logic:

1. Maintain a work stack of `(indent, VDoc)` states.
2. Emit chunks incrementally (`Text`, newline+indent, zero-width chunks).
3. For `Union`, run `fits` over optimistic branch using bounded lookahead at configured width.
4. Choose optimistic branch if it fits, fallback otherwise.
5. Provide `render_trim` variants that drop trailing spaces per line.

This gives:

1. Bounded layout decisions (lookahead is width-bounded, not document-bounded).
2. Stable performance for deep docs when implemented with explicit loops.
3. Stream-friendly rendering without building all intermediate alternatives.

### Document typeclass-pattern API

`Document` mirrors `Eq`/`Hash` style:

1. `struct Document[a](to_doc_fn: a -> Doc)`
2. `document_from_fn(fn)` constructor
3. `to_Doc(docu, item)` accessor
4. `by(docu_b, project_a_to_b)` contramap/projection combinator

Built-in instance semantics:

1. `document_List(item_doc)` renders list items by mapping each element with `to_Doc(item_doc, item)`, combining with `fill(comma + line, ...)`, and wrapping with list brackets via `tight_bracket_by`.
2. `document_Option(item_doc)` renders `None` as `text("None")` and `Some(x)` as `text("Some(") + to_Doc(item_doc, x) + text(")")`, grouped for width-sensitive layout.

## Complexity and performance targets

1. `append`, `append_line`, `append_space`, `nested`, `aligned`: O(1)
2. `repeat(doc, n)`: O(log n)
3. `flatten`, `grouped`, `unzero`: O(n)
4. `max_width`: O(n)
5. `render(width)`: O(output + branch_checks * width) in practice, with bounded branch checks
6. `render_wide_stream`: O(output), no `fits` checks
7. No operation should recurse linearly on document depth without an explicit loop/trampoline strategy

Memory targets:

1. Keep doc construction persistent and shareable.
2. Avoid eagerly materializing both union branches during render.
3. Keep chunk stream incremental to avoid large temporary strings.

## Implementation plan

### Phase 1: module skeleton and core nodes

1. Create `src/Zafu/Text/Pretty.bosatsu`.
2. Add `Doc` wrapper + internal node enum.
3. Implement base constructors/constants (`empty`, `text`, `line`, `line_break`, `int`, `float`, `spaces`, `char`, `comma`).

### Phase 2: structural combinators

1. Implement append and line/space variants.
2. Implement nesting/alignment/hang/indent.
3. Implement `flatten`, `flatten_option`, `grouped`, `bracket_by`, `tight_bracket_by`, `unzero`.

### Phase 3: renderer

1. Implement chunk-stream evaluator with bounded `fits`.
2. Implement `render`, `render_trim`, `render_stream`, `render_stream_trim`, `render_wide_stream`.
3. Implement `max_width` and `representation`.

### Phase 4: collection combinators

1. Implement `fold_docs`, `intercalate`, `cat`, `spread`, `stack`.
2. Implement `split`, `paragraph`, `fill`, `tabulate`, `tabulate_with`.
3. Add `zero_width` and `ansi_control`.

### Phase 5: `Document[a]`

1. Add `Document` struct, `document_from_fn`, `to_Doc`, and `by`.
2. Add default instances listed in exports.
3. Implement and test the explicit `document_List` and `document_Option` rendering rules above.

### Phase 6: validation

1. Port representative Paiges examples as tests (paragraph wrapping, bracketed JSON-like docs, fill behavior).
2. Port all core laws from Paiges/the original paper as property checks (group/flatten laws, associativity/identity behavior, and layout equivalence laws used by Paiges tests).
3. Add stack-safety tests for very large docs (`max_width` and `render_wide_stream`).
4. Run `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh`.

## Test strategy

1. Golden tests: expected rendering at multiple widths.
2. Ported law suite from Paiges/original paper as property tests.
3. `fill` regression tests to preserve right-associated union behavior.
4. Trim tests for dangling indentation spaces.
5. `Document.by` projection tests (same pattern as `eq_by`/`hash_by`).
6. `document_List` and `document_Option` behavioral tests for both wide and narrow widths.
7. Numeric-format tests for `int` and `float` edge cases (`NaN`, infinities, `-0.0`).

## Acceptance criteria

1. `docs/design/51-add-a-pretty-printer.md` exists with this architecture and plan.
2. `src/Zafu/Text/Pretty.bosatsu` exists and exports the 70-item public surface listed above.
3. `Doc` is represented via an internal node structure that preserves O(1) append operations.
4. `LazyDoc` uses `Bosatsu/Lazy[Doc]` thunks.
5. `struct Document[a]` exists with `to_Doc(docu, item)`.
6. `by` exists and behaves as a contramap/project combinator.
7. `int` and `float` are exported with the formatting rules described in this design.
8. `document_List` and `document_Option` are implemented with the explicit rendering behavior described in this design.
9. `grouped`, `flatten`, `line_or_space`, and `fill` semantics match Paiges behavior on representative fixtures.
10. `render`, `render_trim`, and stream renderers are implemented and width-sensitive.
11. `render_wide_stream` avoids bounded-fit branching and is stack-safe on large inputs.
12. `max_width` is implemented and stack-safe on large concatenation chains.
13. The full Paiges/paper law suite is ported as property checks and passes.
14. New tests cover correctness and stack-safety regressions.
15. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass before merge.

## Risks and mitigations

1. Risk: subtle `Union`/flatten invariant violations can cause incorrect line-breaking or super-linear behavior.
Mitigation: keep constructors normalized, add invariant-focused regression tests, and port Paiges edge-case fixtures.

2. Risk: deep document shapes may overflow stack in flatten/render helpers.
Mitigation: use explicit loop/state-machine traversals for all hot paths.

3. Risk: trimming behavior can regress around blank/indented lines.
Mitigation: dedicated `render_trim` tests with dangling-space fixtures.

4. Risk: float formatting expectations may drift across runtimes.
Mitigation: lock down deterministic `float` edge-case behavior in golden tests.

## Rollout notes

1. This lands as an additive module; no existing API breaks.
2. Initial adoption should be opt-in (import `Zafu/Text/Pretty` directly in callers).
3. Keep constructor/combinator semantics stable after first release to avoid rendering churn across downstream codegen tools.
4. Follow-up issues can add richer style/color APIs and module integrations once the core `Doc` + `Document` layer is stable.
