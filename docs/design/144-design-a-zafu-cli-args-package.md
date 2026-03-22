---
issue: 144
priority: 3
touch_paths:
  - docs/design/144-design-a-zafu-cli-args-package.md
  - src/Zafu/Cli/Args.bosatsu
  - src/Zafu/Cli/Args/Internal/Core.bosatsu
  - src/Zafu/Cli/Args/Internal/Lex.bosatsu
  - src/Zafu/Cli/Args/Internal/Decode.bosatsu
  - src/Zafu/Cli/Args/Internal/Help.bosatsu
  - src/Zafu/Cli/ArgsTests.bosatsu
  - src/Zafu/Tool/JsonFormat.bosatsu
depends_on: []
estimated_size: M
generated_at: 2026-03-22T19:15:37Z
---

# Design: `Zafu/Cli/Args`

_Issue: #144 (https://github.com/johnynek/zafu/issues/144)_

## Summary

Introduce an applicative CLI argument package with schema-driven argv decoding, help rendering via `Zafu/Text/Pretty`, value parsing via `Zafu/Text/Parse`, explicit style descriptors, subcommands, and a phased implementation plan.

## Context

1. `Zafu` now has `Zafu/Text/Parse` for string-level parsing and `Zafu/Text/Pretty` for structured layout, but it has no reusable CLI argument package.
2. `src/Zafu/Tool/JsonFormat.bosatsu` currently hand-parses flags. That works for one small tool, but it does not scale to subcommands, alternate spellings, automatic help, or reuse across commands.
3. Issue #144 asks for a design in the style of `decline` or `optparse-applicative`: applicative composition, help derived from the same description as parsing, explicit support for subcommands, and enough spelling flexibility to clone existing CLIs.
4. The existing `Zafu/Text/Parse` API is string-oriented rather than argv-oriented. That means `Zafu/Cli/Args` should use `Zafu/Text/Parse` to decode individual values, but it should own argv tokenization, matching, and command dispatch itself.

## Goals

1. Add a new `Zafu/Cli/Args` package that exposes an applicative API for command-line schemas.
2. Generate usage/help and parse behavior from the same schema so they cannot drift.
3. Use `Zafu/Text/Parse` for typed value readers such as ints, floats, enums, and custom formats.
4. Use `Zafu/Text/Pretty` for wrapped help, usage, and error rendering.
5. Support named options, flags, positional arguments, repeated arguments, trailing args after `--`, and nested subcommands.
6. Support common spelling styles such as `--long`, `--long=value`, `-s`, grouped short flags like `-xzvf`, attached short values like `-Iinclude`, and custom prefixes such as `/help` when configured.
7. Make parsing rules explicit enough that gaps and ambiguities are visible in the API design rather than buried in ad hoc matching logic.

## Non-goals

1. Shell completion generation in the first implementation.
2. Environment-variable or config-file fallback in the first implementation.
3. A fully monadic command parser; v1 is intentionally applicative-first.
4. Automatic generic derivation from records or structs.
5. Supporting every ambiguous legacy CLI edge case by default. V1 should instead provide low-level escape hatches that make those styles expressible.

## Proposed Design

### High-level model

1. `ValueParser[a]` decodes one raw `String` into `a`. It is the bridge to `Zafu/Text/Parse`.
2. `Args[a]` is an opaque applicative description of the arguments for one command scope.
3. `Command[a]` adds command metadata such as name, summary, description, footer, aliases, and the `Args[a]` schema for that command.
4. `ParseResult[a]` is a structured parse outcome rather than just `Result[String, a]`, because the library must distinguish successful parse, help rendering, version rendering, and validation failures.
5. Internally, `Args[a]` is modeled as a normalized schema plus a typed decoder over a shared match state. The schema is used for lexing, help generation, and ambiguity checks. The decoder is used for actual value construction.
6. This is applicative in the public API, but not a plain sequential parser internally. Named options are order-insensitive, so the implementation should not try to model argv as a single left-to-right parser in the same style as `Zafu/Text/Parse`.

### Public module layout

1. `src/Zafu/Cli/Args.bosatsu`
   Public API surface, exported types, value-parser helpers, high-level combinators, and top-level parse/help entrypoints.
2. `src/Zafu/Cli/Args/Internal/Core.bosatsu`
   Internal schema types, primitive descriptors, normalization rules, and `Applicative[Args]` support.
3. `src/Zafu/Cli/Args/Internal/Lex.bosatsu`
   Schema-aware argv lexer that turns `List[String]` into occurrences, short-flag clusters, attached values, and positionals.
4. `src/Zafu/Cli/Args/Internal/Decode.bosatsu`
   Command-path resolution, occurrence consumption, validation accumulation, and leftover-argument checks.
5. `src/Zafu/Cli/Args/Internal/Help.bosatsu`
   Usage/help/error document rendering with `Zafu/Text/Pretty`.
6. `src/Zafu/Cli/ArgsTests.bosatsu`
   End-to-end tests, golden help fixtures, and style-compatibility cases.

## Core Types

### `ValueParser[a]`

1. Sketch: `struct ValueParser[a](parse_fn: String -> Result[Doc, a], metavar: Doc, choices: Option[List[(String, Doc)]])`.
2. `parse_fn` returns `Doc` errors so parse failures can be rendered directly in CLI errors without losing structure.
3. `metavar` is used by help rendering and usage lines.
4. `choices` is optional metadata for enumerated values and richer help output.
5. Main constructors are `value_from_parse`, `value_from_fn`, `string_value`, `int_value`, `float_value`, `bool_value`, `enum_value`, `map_value`, and `and_then_value`.

### `ArgInfo`

1. Sketch: `struct ArgInfo(help: Option[Doc], metavar_override: Option[Doc], group: Option[Doc], hidden: Bool, default_doc: Option[Doc], examples: List[Doc])`.
2. `ArgInfo` holds help-facing metadata only. It does not affect low-level matching except where `metavar_override` changes rendered usage.
3. Metadata combinators such as `with_help`, `with_group`, `hidden`, and `with_default_doc` are record updates over `ArgInfo`.

### `Args[a]`

1. Publicly opaque.
2. Internally equivalent to `struct Args[a](schema: Schema, decode_fn: MatchState -> Result[NonEmptyChain[CliError], a])`.
3. `schema` is a normalized inventory of primitives, command metadata references, spelling indexes, positional ordering, and visibility info.
4. `decode_fn` reads from a shared immutable match state so independently-declared options can be decoded in any argv order.
5. `Args` must expose an `Applicative[Args]` instance through `Zafu/Abstract/Applicative`.
6. Error accumulation should use `Zafu/Control/Result.applicative_combine_Err` with `Zafu/Collection/NonEmptyChain[CliError]`.

### `Command[a]`

1. Sketch: `struct Command[a](name: String, summary: Option[Doc], description: Option[Doc], footer: Option[Doc], aliases: List[String], args: Args[a])`.
2. A command is one node in a tree. Subcommand choice is represented inside `Args[a]`, but help rendering always happens in the context of a `Command[a]`.
3. Each command has its own help section and may inject built-in flags such as `--help` or `--version`.

### `ParseConfig` and `HelpConfig`

1. `ParseConfig` controls lexer behavior: prefixes, `--` terminator handling, short-flag clustering, attached-value rules, case sensitivity, and built-in help/version spellings.
2. `HelpConfig` controls width, hidden-item visibility, section ordering, and whether defaults/examples are rendered.
3. Defaults should target GNU-style CLIs, but the config must allow custom prefixes and attachment rules so other APIs are still representable.

### `ParseResult[a]`

1. `Parsed(value: a)`
2. `RequestedHelp(command_path: List[String], doc: Doc)`
3. `RequestedVersion(doc: Doc)`
4. `Failed(errors: NonEmptyChain[CliError], doc: Doc)`
5. Help and version requests must short-circuit required-argument validation for the selected command path.

### `CliError`

1. Planned variants: `UnknownOption`, `UnknownCommand`, `MissingValue`, `MissingArgument`, `DuplicateOccurrence`, `UnexpectedArgument`, `ValueParseError`, `ValidationError`, and `AmbiguousSpecification`.
2. Errors should carry enough context to render the command path, offending raw token, and the relevant option or positional name.
3. `AmbiguousSpecification` is important because some invalid combinations should fail when the schema is built, not only at parse time.

## Matching Model

### Names, spellings, scope, and cardinality

1. Introduce a low-level `Spelling` description that captures prefix, visible name, and how values may attach.
2. Sketch: `struct Spelling(prefix: String, name: String, style: ValueStyle, clusterable: Bool)`.
3. `ValueStyle` variants should include `NoValue`, `SeparateOnly`, `AttachedOnly`, `SeparateOrAttached`, and `AttachedOptional`.
4. `AttachedOptional` covers forms such as `--color=always` while keeping `--color foo` unambiguous by default.
5. Named arguments should also carry a `Scope` value: `Local` or `Inherited`.
6. `Inherited` named args are visible to descendant subcommands so both `tool --verbose sub` and `tool sub --verbose` can work when desired.
7. Primitive occurrences should also carry a `Cardinality` value such as `ExactlyOne`, `ZeroOrOne`, `ZeroOrMore`, `OneOrMore`, and `CountOccurrences`.
8. High-level helpers such as `long`, `short`, and `custom_name` should build `Spelling` values.

### Primitive kinds

1. Named flag with no payload.
2. Named option with a payload decoded by `ValueParser[a]`.
3. Positional argument.
4. Optional positional argument.
5. Rest argument that captures all remaining positionals after normal positional parsing.
6. Subcommand choice over a non-empty list of child commands.
7. All high-level constructors should compile down to a single primitive inventory in `Schema`.

### Schema normalization rules

1. Every primitive receives a stable internal id.
2. Duplicate visible spellings within the same command visibility scope are rejected up front.
3. At most one rest positional is allowed, and it must be last.
4. Required positional arguments cannot follow an optional positional or a rest positional.
5. Two subcommands at the same node cannot share the same name or alias.
6. A short-flag cluster spelling is only legal for single-character names.
7. An option that consumes an attached short value inside a cluster must be the final entry in that cluster.
8. These rules should be enforced during schema construction so the runtime parser never has to guess.

## Parse Pipeline

1. Normalize the `Command[a]` tree into command-local `Schema` values and visible spelling indexes.
2. Use the visible schema to lex raw `argv: List[String]` into occurrences. The lexer must be schema-aware so `-1` can remain positional when no visible `-1` spelling exists.
3. Resolve the command path by walking positional tokens against the current node's subcommand table until no child matches.
4. Build a `MatchState` for the selected path. It should retain named occurrences, remaining positionals, tokens after `--`, and a consumed/unconsumed marker per occurrence.
5. Check for built-in help or version flags for the selected command path before running required-argument validation.
6. Run each command scope's `decode_fn` with validation accumulation. Parent scopes only see their own local primitives plus inherited ones.
7. After decode, fail if any occurrence or positional token remains unclaimed.
8. Render failures through `Internal/Help` so the user sees both the specific error and the relevant usage/help block.

### Why `Zafu/Text/Parse` is not the whole engine

1. `Zafu/Text/Parse` is still central, but it should parse values, not own the entire argv grammar.
2. CLI parsing differs from text parsing because named options are order-insensitive and subcommand boundaries are semantic rather than purely lexical.
3. The design therefore uses `Zafu/Text/Parse` at the leaves and a dedicated argv matcher at the top level.
4. This keeps the dependency real without forcing awkward sequential-parser semantics onto option matching.

## Public API Sketch

### Entry points

1. `command(name, args) -> Command[a]`
2. `parse(config, command, argv) -> ParseResult[a]`
3. `help_doc(config, command, command_path) -> Doc`
4. `failure_doc(config, command, errors) -> Doc`
5. `with_help_flag(command) -> Command[a]`
6. `with_version_flag(command, version_doc) -> Command[a]`

### Value-parser combinators

1. `value_from_parse`
2. `value_from_fn`
3. `string_value`
4. `int_value`
5. `float_value`
6. `bool_value`
7. `enum_value`
8. `map_value`
9. `and_then_value`

### Low-level spelling and primitive builders

1. `long(name) -> Spelling`
2. `short(ch) -> Spelling`
3. `custom_name(prefix, name) -> Spelling`
4. `allow_separate(spelling) -> Spelling`
5. `allow_attached(spelling) -> Spelling`
6. `allow_equals(spelling) -> Spelling`
7. `clusterable(spelling) -> Spelling`
8. `primitive(spellings, value_parser, cardinality, info) -> Args[a]`

### High-level argument constructors

1. `flag(spellings, info) -> Args[Bool]`
2. `flag_value(spellings, value, info) -> Args[a]`
3. `count(spellings, info) -> Args[Int]`
4. `option(value_parser, spellings, info) -> Args[a]`
5. `option_optional_value(value_parser, spellings, info) -> Args[Option[a]]`
6. `positional(value_parser, info) -> Args[a]`
7. `positional_optional(value_parser, info) -> Args[Option[a]]`
8. `rest(value_parser, info) -> Args[List[a]]`
9. `subcommands(commands, info) -> Args[a]`

### Applicative and validation combinators

1. `pure`
2. `map`
3. `ap`
4. `product`
5. `product_left`
6. `product_right`
7. `validate(args, fn: a -> Result[Doc, a]) -> Args[a]`

### Cardinality and defaulting combinators

1. `optional(arg) -> Args[Option[a]]`
2. `many(arg) -> Args[List[a]]`
3. `some(arg) -> Args[NonEmptyList[a]]`
4. `with_default(arg, value, rendered_default) -> Args[a]`
5. `many`, `some`, `optional`, and `with_default` should be limited to primitive or subcommand nodes. Applying them to an arbitrary composite `Args[a]` should be rejected during schema normalization.

### Help and metadata combinators

1. `with_help(arg, doc) -> Args[a]`
2. `with_metavar(arg, doc) -> Args[a]`
3. `with_default_doc(arg, doc) -> Args[a]`
4. `with_group(arg, doc) -> Args[a]`
5. `hidden(arg) -> Args[a]`
6. `with_aliases(command, aliases) -> Command[a]`
7. `with_scope(arg, scope) -> Args[a]`
8. `example(command, doc) -> Command[a]`

### Explicit non-feature in v1

1. Do not expose a general `Alternative` or `or_else` instance for `Args[a]` in v1.
2. General choice makes help text and ownership semantics ambiguous for order-insensitive named options.
3. Targeted choice is still supported through `subcommands`, `enum_value`, aliases, and low-level primitive spellings.
4. If general choice is needed later, it should be designed as a separate layer with explicit ambiguity rules.

## Help Rendering

1. Help rendering should consume only normalized `Schema` plus `Command` metadata.
2. The same schema used for parsing must drive usage lines, option tables, positional sections, subcommand listings, default text, and examples.
3. Rendering should be built from `Zafu/Text/Pretty.Doc` so wrapping is width-sensitive and section layout stays deterministic.
4. Required rendered sections are `Usage`, command description, positional arguments, named options grouped by section, subcommands, examples, and footer text.
5. Hidden items are omitted by default but may be shown through `HelpConfig`.
6. Failure docs should include the error block before usage, not instead of usage.
7. `RequestedHelp` for a subcommand should render that subcommand's section, not the root command's section.

## Implementation Plan

1. Phase 1: create `src/Zafu/Cli/Args/Internal/Core.bosatsu` and `src/Zafu/Cli/Args.bosatsu` with `ValueParser`, `ArgInfo`, `Args`, `Command`, `CliError`, `ParseResult`, schema normalization, and an `Applicative[Args]` instance.
2. Phase 2: implement `src/Zafu/Cli/Args/Internal/Lex.bosatsu` for schema-aware argv tokenization, short-cluster expansion, `--` handling, attached values, and unknown-option detection.
3. Phase 3: implement `src/Zafu/Cli/Args/Internal/Decode.bosatsu` for command-path selection, occurrence consumption, inherited-scope handling, validation accumulation, and leftover detection.
4. Phase 4: implement `src/Zafu/Cli/Args/Internal/Help.bosatsu` for usage/help/failure rendering using `Zafu/Text/Pretty`.
5. Phase 5: add built-in value parsers backed by `Zafu/Text/Parse`, plus convenience constructors such as `flag`, `option`, `positional`, `rest`, and `subcommands`.
6. Phase 6: add `src/Zafu/Cli/ArgsTests.bosatsu` with golden help tests, parser edge cases, and end-to-end command-tree cases.
7. Phase 7: migrate `src/Zafu/Tool/JsonFormat.bosatsu` from hand-written `parse_args` to `Zafu/Cli/Args` as a small real-world integration and smoke test.
8. Phase 8: run `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` before merge.

## Testing Strategy

1. Golden tests for help output at multiple widths.
2. End-to-end parse tests for named flags, named options, repeated options, positionals, rest args, and `--` terminator handling.
3. Style-compatibility tests for `--long=value`, `-s`, `-abc`, attached short values, and custom prefixes.
4. Negative-number tests to ensure `-1` remains positional unless a visible spelling requires otherwise.
5. Subcommand tests for nested help, aliases, inherited global flags, and unknown-command failures.
6. Validation tests to ensure applicative error accumulation reports multiple independent missing or invalid arguments together.
7. Schema-construction tests for rejected ambiguous specs such as duplicate spellings or positional-after-rest.
8. A real integration test or migration of `Zafu/Tool/JsonFormat.bosatsu` to confirm the API works for an existing command.

## Acceptance Criteria

1. `docs/design/144-design-a-zafu-cli-args-package.md` exists and documents the architecture, combinator inventory, implementation phases, acceptance criteria, risks, and rollout notes.
2. `src/Zafu/Cli/Args.bosatsu` exists and exports `ValueParser`, `ArgInfo`, `Args`, `Command`, `ParseConfig`, `HelpConfig`, `ParseResult`, and the combinator families described in this design.
3. `Args` exposes an applicative API and drives both parsing and help from the same normalized schema.
4. `ValueParser` integrates with `Zafu/Text/Parse` rather than inventing a second string-parser abstraction.
5. Help and failure rendering are built on `Zafu/Text/Pretty.Doc`.
6. The implementation supports `--long`, `--long=value`, `-s`, grouped short flags, attached short values, `--`, positionals, optional positionals, rest args, and custom prefixes when configured.
7. Subcommands are supported, including command-local help and aliases.
8. Inherited named arguments can be declared explicitly and parsed on descendant command paths.
9. Ambiguous schema shapes are rejected during schema construction rather than resolved implicitly at runtime.
10. Tests cover help rendering, style compatibility, subcommands, inherited scope, negative-number positionals, duplicate detection, and validation accumulation.
11. `src/Zafu/Tool/JsonFormat.bosatsu` is migrated to the new package or an equivalent end-to-end fixture proves the same flag style.
12. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: trying to support every CLI spelling directly in high-level combinators will bloat the API.
Mitigation: keep a small set of high-level builders layered on top of one explicit low-level `primitive` plus `Spelling` model.

2. Risk: optional-valued options can become ambiguous with following positionals.
Mitigation: default optional values to attached-only forms such as `--color=always`, and reject or require explicit opt-in for ambiguous separate-token variants.

3. Risk: parent and child command scopes can fight over the same occurrence.
Mitigation: make scope explicit with `Local` and `Inherited`, normalize scope ownership up front, and add path-scoped tests.

4. Risk: help rendering and parse behavior can drift if they are built from separate representations.
Mitigation: both features must consume the same normalized `Schema`.

5. Risk: schema-aware lexing may become expensive on large command trees.
Mitigation: precompute visible spelling indexes per command path and keep lexing to a single pass over argv.

## Rollout Notes

1. Land this as an additive module family under `Zafu/Cli`; no existing public API should break.
2. Keep the default configuration GNU-like so common CLIs are easy to express, but ship the low-level `Spelling` escape hatch in the first version so unusual APIs do not require parser forks.
3. Use `Zafu/Tool/JsonFormat.bosatsu` as the first in-repo adopter after the core package lands.
4. Defer shell completion, env/config fallbacks, and any general `Alternative` layer until real command migrations show which gaps matter.
5. Once the core schema is stable, follow-up work can add completion or manpage generation on top of the same `Schema` without changing parse semantics.

## Open Questions

1. Should inherited global options be opt-in through `with_scope(Inherited)` only, or should root-command named options be inherited by default?
2. Do we want any general choice combinator beyond `subcommands`, or is an applicative-only public surface enough for v1?
3. Should optional-value options ever be allowed to consume the next argv element, or should v1 keep them attached-only to avoid ambiguity?
