# Pre-PR Review Guidance

Review `zafu` in this priority order:

1. Correctness and robustness.
2. Performance, stack safety, and shrink/runtime behavior.
3. Idiomatic Bosatsu in the style already used in this repo.

Repo-specific guidance:

- Treat stack safety as a correctness property. Do not approve pseudo-tail-recursive rewrites that still recurse on the host stack, especially through lambdas, `flat_map`, or helper indirection. If the intent is iterative execution, `loop` should be used correctly.
- Keep the public API surface small and intentional. Do not export tests, internal helpers, or implementation details just to make a change easier. Prefer thin public facades or `Types` packages over exposing `Internal/*` modules, and keep `exported_packages` and `exposes` entries minimal and deliberate.
- Preserve repo-owned behavior when refactoring to shared libraries. If a Zafu parser, CLI path, or data-structure implementation is serving as a correctness, performance, or diagnostics test bed, do not delete or bypass it unless the replacement is clearly better and the lost value is explicitly covered.
- Avoid regressions in diagnostics and CLI behavior. Error reporting, `--` passthrough, `BrokenPipe` handling, leftover-argument behavior, and similar edge cases need focused review and targeted tests.
- Push hard against duplication. If the same helper or combinator appears in multiple places in the diff, prefer extracting or reusing a shared helper instead of adding more local copies.
- Prefer existing collection, parser, and typeclass helpers over ad hoc local reimplementations, especially for equality, traversal, bulk operations, and parser scaffolding.
- Prefer Bosatsu-native repo idioms: `<-` pipelines instead of deep nesting, record patterns and record updates, `matches` for total equality checks, pattern lambdas for total destructures, and direct string or pattern matching when it is clearer than lower-level char-list manipulation.
- Use helper constructors when the repo expects them. For example, construct `IterState` values with `done(...)` and `continue(...)`; keep raw constructors mostly for pattern matching.
- In HedgeHog and test code, prefer shared `Gen` combinators, minimize `flat_map_Gen` when `map2_Gen` or another structure-preserving combinator gives better shrinking, and do not blur `Gen` into `Rand` terminology.
- Prefer existing efficient primitives over clever local rewrites when performance is known to matter. Stylistic cleanups are not wins if they regress shrink quality, parser behavior, or hot-path performance.
- Require focused regressions for parser, CLI, generator or shrinking, stack-safety, and public-surface changes. `scripts/test.sh` staying green is necessary, but it is not enough on its own for risky semantic changes.
- Add short comments when a transformation, normalization step, or public-surface choice is subtle enough that a future maintainer could easily misread it.
