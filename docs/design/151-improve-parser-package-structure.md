---
issue: 151
priority: 3
touch_paths:
  - src/zafu_conf.json
  - src/Zafu/Text/Parse/Types.bosatsu
  - src/Zafu/Text/Parse.bosatsu
  - src/Zafu/Text/Parse/Rfc5234.bosatsu
  - src/Zafu/Cli/Args.bosatsu
  - src/Zafu/Cli/Args/Internal/Core.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-28T18:36:47Z
---

# Design parser type facade and public package cleanup

_Issue: #151 (https://github.com/johnynek/zafu/issues/151)_

## Summary

Introduce `Zafu/Text/Parse/Types` as the stable public home for parser carrier types, retarget public parser APIs away from `Internal/*`, and reduce the exported parser package surface without changing parser behavior.

## Context

1. `Zafu/Text/Parse.bosatsu` currently exposes `Zafu/Text/Parse/Internal/Core` because its public combinator signatures mention `Parser0[a]` and `Parser[a]`.
2. `Zafu/Text/Parse/Rfc5234.bosatsu` has the same problem: it exports parser values, so it also exposes an `Internal` package.
3. `Zafu/Cli/Args.bosatsu` depends on parser types for `value_from_parse`, which extends the same leak into a second public API surface.
4. `src/zafu_conf.json` therefore publishes `Zafu/Text/Parse/Internal/Core` and `Zafu/Text/Parse/Internal/Engine` as exported library packages. That is the opposite of the intended package boundary, and it makes generated docs show internal implementation modules as public API.
5. The repository already uses a cleaner pattern in `Zafu/Cli/Args`: public-facing types live in `Zafu/Cli/Args/Types`, while `Internal/*` packages remain implementation details.
6. `Zafu/Text/Parse.bosatsu` also carries a TODO from issue #52 about re-exporting parser types later. Issue #151 is the follow-up cleanup.

## Goals

1. Remove `Zafu/Text/Parse/Internal/*` from the published parser package surface.
2. Introduce a stable public namespace for parser carrier types used in signatures.
3. Keep parser behavior, combinator names, and error semantics unchanged.
4. Minimize implementation churn by avoiding a parser-engine rewrite.
5. Make generated docs and exported package lists reflect the intended public API.

## Non-goals

1. Redesigning parser internals, fuel accounting, or combinator semantics.
2. Changing the public behavior of `parse`, `parse_prefix`, `parse_offset`, or RFC5234 helpers.
3. Renaming `Zafu/Text/Parse/Error` or otherwise reshaping the error model.
4. Solving the separate question of directly re-exporting parser types from `Zafu/Text/Parse` itself. That can remain follow-up work.

## Proposed Design

### Public package boundary

Add a new public package, `Zafu/Text/Parse/Types`, and make it the only public package whose purpose is to carry parser type names across package boundaries.

The intended public parser package set after this change is:

1. `Zafu/Text/Parse`
2. `Zafu/Text/Parse/Types`
3. `Zafu/Text/Parse/Error`
4. `Zafu/Text/Parse/Rfc5234`

`Zafu/Text/Parse/Internal/Core` and `Zafu/Text/Parse/Internal/Engine` should remain implementation modules in the source tree, but they should stop being exported library packages.

### `Zafu/Text/Parse/Types`

`Zafu/Text/Parse/Types` should be intentionally small. Its job is to provide the parser carrier types that appear in public signatures:

1. `Parser0`
2. `Parser`

No new combinators should live in this package. `Zafu/Text/Parse` remains the canonical behavior module for construction, composition, and running parsers.

The preferred implementation is a thin public facade over the existing parser types so the parser runtime stays where it is today. That keeps issue #151 focused on package structure rather than representation changes.

### Public `exposes` cleanup

Update public modules so they expose `Zafu/Text/Parse/Types` instead of `Zafu/Text/Parse/Internal/Core`.

That applies to:

1. `src/Zafu/Text/Parse.bosatsu`
2. `src/Zafu/Text/Parse/Rfc5234.bosatsu`
3. `src/Zafu/Cli/Args.bosatsu`

This keeps the visible type dependencies accurate while removing `Internal` names from the API surface.

### Exported package cleanup

Update `src/zafu_conf.json` so that:

1. `Zafu/Text/Parse/Types` is added to `exported_packages`.
2. `Zafu/Text/Parse/Internal/Core` is removed from `exported_packages`.
3. `Zafu/Text/Parse/Internal/Engine` is removed from `exported_packages`.

`Internal/Engine` is not referenced by any public signature today, so it should stop being published immediately.

### In-repo import cleanup

Any in-repo module that imports parser types by name for signatures or annotations should prefer `Zafu/Text/Parse/Types` after this change, especially where that import is part of a public API surface.

In practice, the main consumer that matters is `Zafu/Cli/Args.bosatsu`. Internal-only modules can be migrated for consistency, but that is secondary to the public package cleanup.

### Documentation intent

Generated docs should present `Zafu/Text/Parse/Types` as the stable place to look up parser type definitions, while `Zafu/Text/Parse` remains the entrypoint for the combinator API. The docs should no longer advertise parser `Internal/*` packages as part of the library.

## Implementation Plan

1. Add `src/Zafu/Text/Parse/Types.bosatsu` with a minimal public surface for `Parser0` and `Parser`.
2. Update `src/Zafu/Text/Parse.bosatsu` to expose `Zafu/Text/Parse/Types` instead of `Zafu/Text/Parse/Internal/Core`.
3. Update `src/Zafu/Text/Parse/Rfc5234.bosatsu` to expose `Zafu/Text/Parse/Types`.
4. Update `src/Zafu/Cli/Args.bosatsu` to import and expose parser types through `Zafu/Text/Parse/Types`.
5. Optionally sweep internal in-repo imports that only need parser type names so they also use `Zafu/Text/Parse/Types` for consistency.
6. Update `src/zafu_conf.json` so the exported parser package list matches the new boundary.
7. Run `./bosatsu lib check`, `./bosatsu lib test`, `scripts/test.sh`, and a docs generation pass such as `./bosatsu doc --outdir ...` to confirm the package list and generated docs no longer publish parser `Internal/*` packages.

## Acceptance Criteria

1. `src/Zafu/Text/Parse/Types.bosatsu` exists and is the public package used for parser carrier types.
2. `src/zafu_conf.json` exports `Zafu/Text/Parse/Types` and no longer exports `Zafu/Text/Parse/Internal/Core` or `Zafu/Text/Parse/Internal/Engine`.
3. `src/Zafu/Text/Parse.bosatsu` exposes `Zafu/Text/Parse/Types` rather than any parser `Internal/*` package.
4. `src/Zafu/Text/Parse/Rfc5234.bosatsu` exposes `Zafu/Text/Parse/Types` rather than `Zafu/Text/Parse/Internal/Core`.
5. `src/Zafu/Cli/Args.bosatsu` exposes parser types through `Zafu/Text/Parse/Types` rather than `Zafu/Text/Parse/Internal/Core`.
6. No public package in the exported parser surface requires consumers to import an `Internal` parser module to type-check public signatures.
7. Parser behavior is unchanged: this issue is package-surface cleanup, not a semantic parser rewrite.
8. Generated API docs show `Zafu/Text/Parse/Types` as public and do not publish `Zafu/Text/Parse/Internal/*` as part of the supported library surface.
9. In-repo parser consumers that name `Parser` or `Parser0` still compile after the namespace cleanup.
10. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: a thin facade may not be sufficient if Bosatsu export rules still force the underlying defining package to remain public.
Mitigation: validate the facade with `lib check` first. If needed, widen the refactor just enough to make `Zafu/Text/Parse/Types` the true public source of `Parser0` and `Parser`, while still keeping parser state, failure, and engine helpers internal.

2. Risk: downstream users may already import `Zafu/Text/Parse/Internal/Core` directly.
Mitigation: update all in-repo users in the same PR and call out the package cleanup in release notes. If compatibility pressure appears, a short alias window can be considered separately, but it should not block the boundary fix.

3. Risk: generated docs may still contain links or package entries for old internal names.
Mitigation: include doc generation in verification, not just `lib check` and tests.

4. Risk: `Zafu/Text/Parse/Types` could accidentally become a second catch-all API module.
Mitigation: keep it restricted to the small set of types that actually appear in public signatures. Leave `ParseState`, `Step`, `ParseFailure`, engine helpers, and fuel logic in `Internal/*`.

## Rollout Notes

1. This should land as a single PR because it is a structural cleanup with limited in-repo touch points.
2. Update public-facing examples and docs to import parser types from `Zafu/Text/Parse/Types` whenever explicit type imports are needed.
3. After merge, treat `Zafu/Text/Parse/Internal/*` as unsupported library surface even though the source files remain in the repository.
4. If the project later wants an even smaller public import story, direct re-export of `Parser0` and `Parser` from `Zafu/Text/Parse` can be a separate follow-up. It is not required to satisfy this issue.
