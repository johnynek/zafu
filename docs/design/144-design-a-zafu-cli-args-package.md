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
5. Internally, `Args[a]` should be modeled as a hybrid of a walkable first-order node tree plus a typed decoder over a shared match state.
6. The walkable tree is what help generation, schema normalization, and subcommand-path discovery consume.
7. The typed decoder is what constructs the final `a` and accumulates validation errors.
8. This is applicative in the public API, but not a plain sequential parser internally. Named options are order-insensitive, so the implementation should not try to model argv as a single left-to-right parser in the same style as `Zafu/Text/Parse`.

### Representation choice: hybrid walkable node vs typed `Args` enum

1. One option is a fully typed `enum Args[a]` with variants such as `Pure`, `Map`, `Ap`, `Validate`, `Primitive`, and `Subcommands`, and then separate interpreters for parsing and help.
2. The main benefit of that approach is conceptual clarity: one tree is the source of truth, and walking the tree for help or parsing is straightforward in principle.
3. The main drawback is Bosatsu encoding pressure. `Map`, `Ap`, and `Validate` naturally introduce hidden intermediate types, so a direct typed `enum Args[a]` needs existential-style storage to be ergonomic. That is exactly the part Bosatsu is a poor fit for.
4. Another option is a direct `schema + decode_fn` representation only.
5. The benefit of `schema + decode_fn` is that it maps cleanly to Bosatsu and makes the runtime decoder explicit.
6. The drawback is that if the schema is only an opaque normalized blob, the design becomes harder to explain, help generation becomes less obviously connected to user combinators, and subcommand structure is less explicit.
7. The proposed design is a hybrid: `Args[a]` stores a walkable untyped `ArgsNode` plus a typed `decode_fn`.
8. `ArgsNode` preserves the shape needed for help generation and subcommand discovery, while `decode_fn` avoids trying to encode all applicative intermediate types in a first-order Bosatsu ADT.
9. This is the best fit for Bosatsu: we keep an explicit internal ADT for traversal, but we do not force the entire typed applicative API into a single existential-heavy enum.

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
2. Internally equivalent to `struct Args[a](node: ArgsNode, decode_fn: MatchState -> Result[NonEmptyChain[CliError], a])`.
3. `node` is a walkable tree used for help generation, schema normalization, and subcommand-path discovery.
4. `decode_fn` reads from a shared immutable match state so independently-declared options can be decoded in any argv order.
5. `Args` must expose an `Applicative[Args]` instance through `Zafu/Abstract/Applicative`.
6. Error accumulation should use `Zafu/Control/Result.applicative_combine_Err` with `Zafu/Collection/NonEmptyChain[CliError]`.

### `ArgsNode`, `PrimitiveSpec[a]`, and `SubcommandNode`

1. `ArgsNode` is the internal first-order ADT that mirrors the user-visible combinator structure closely enough to walk.
2. Sketch: `enum ArgsNode: Empty | Product(left: ArgsNode, right: ArgsNode) | Primitive(prim: PrimitiveShape) | Validated(node: ArgsNode, label: Doc) | Subcommands(commands: NonEmptyList[SubcommandNode])`.
3. `PrimitiveSpec[a]` is the typed input to the low-level constructor: `struct PrimitiveSpec[a](kind: PrimitiveKind[a], cardinality: Cardinality, scope: Scope)`.
4. `PrimitiveKind[a]` should have variants like `FlagValue(spellings: NonEmptyList[Spelling], when_present: a)`, `NamedValue(spellings: NonEmptyList[Spelling], value_parser: ValueParser[a])`, `Positional(value_parser: ValueParser[a])`, and `Rest(value_parser: ValueParser[a])`.
5. `PrimitiveShape` is the erased, walkable form stored in `ArgsNode`; it keeps only the metadata needed for help, normalization, and token ownership.
6. `SubcommandNode` is a walkable command child: `struct SubcommandNode(name: String, aliases: List[String], summary: Option[Doc], description: Option[Doc], footer: Option[Doc], body: ArgsNode)`.
7. The important Bosatsu point is that `ArgsNode` stores `SubcommandNode`, not `Command[a]`. That avoids a module-level `Command` to `Args` to `Command` dependency story while still giving us a recursive tree we can walk.

### `Command[a]`

1. Sketch: `struct Command[a](name: String, summary: Option[Doc], description: Option[Doc], footer: Option[Doc], aliases: List[String], args: Args[a])`.
2. A command is the public root wrapper. It is not stored recursively inside `ArgsNode`.
3. `subcommands` should accept child `Command[a]` values at the public API boundary, but internally lower them through `subcommand_from_command[a](command: Command[a]) -> SubcommandNode`.
4. That decomposition is what avoids the problematic `Args` depends on `Command`, `Command` depends on `Args` story in Bosatsu. `Command[a]` depends on `Args[a]`, while recursive walking happens only through `ArgsNode` and `SubcommandNode`.
5. Each command has its own help section and may inject built-in flags such as `--help` or `--version`.

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
2. Sketch: `struct Spelling(prefix: String, name: String, value_kind: ValueKind, value_forms: List[ValueForm], clusterable: Bool)`.
3. `ValueKind` should be `Flag`, `RequiredValue`, or `OptionalValue`.
4. `ValueForm` should be `SeparateToken`, `AttachedToken`, or `EqualsToken`.
5. `EqualsToken` is only meaningful for long-form spellings such as `--foo=bar`.
6. `OptionalValue` plus only `EqualsToken` is how we encode GNU-like forms such as `--color` and `--color=always` without also stealing the next positional token by default.
7. Named arguments should also carry a `Scope` value: `Local` or `Inherited`.
8. `Inherited` named args are visible to descendant subcommands so both `tool --verbose sub` and `tool sub --verbose` can work when desired.
9. Primitive occurrences should also carry a `Cardinality` value such as `ExactlyOne`, `ZeroOrOne`, `ZeroOrMore`, `OneOrMore`, and `CountOccurrences`.
10. High-level helpers such as `long`, `short`, and `custom_name` should build `Spelling` values.

### GNU-compatible long and short option forms

1. `flag([short('f'), long('foo')], info)` should accept `-f` and `--foo`.
2. A long spelling marked with `SeparateToken` and `EqualsToken` should accept both `--foo bar` and `--foo=bar`.
3. A short spelling marked with `SeparateToken`, paired with a long spelling marked with `SeparateToken` and `EqualsToken`, should accept `-f bar`, `--foo bar`, and `--foo=bar`.
4. `option_optional_value` with a long spelling marked only with `EqualsToken` should accept `--foo` and `--foo=bar`.
5. `option_optional_value` with `SeparateToken` and `EqualsToken` may additionally accept `--foo bar`, but that should be explicit opt-in because it is more ambiguous around following positionals.
6. `=` is not universal. A spelling accepts `=` only if `EqualsToken` is present in its `value_forms`.
7. Help rendering should reflect the accepted syntax exactly: `--foo`, `--foo BAR`, `--foo=BAR`, or `--foo[=BAR]` depending on `ValueKind`, `ValueForm`, and `ArgInfo.metavar_override`.

### Primitive kinds

1. Named flag with no payload is modeled as `PrimitiveSpec[Bool]` or `PrimitiveSpec[a]` with a `FlagValue` payload chosen by the constructor.
2. Named option with a payload decoded by `ValueParser[a]` is modeled as `PrimitiveSpec[a]` with `NamedValue`.
3. Positional argument is modeled as `PrimitiveSpec[a]` with `Positional`.
4. Optional positional argument is the same positional shape plus `ZeroOrOne` cardinality.
5. Rest argument is modeled as `PrimitiveSpec[List[a]]` with `Rest`.
6. Subcommand choice is not a `PrimitiveSpec[a]`; it is an `ArgsNode.Subcommands` branch plus a decoder that dispatches into the chosen child `Command[a]`.
7. All high-level constructors should lower either to `PrimitiveSpec[a]` plus `primitive`, or to `SubcommandNode` plus `subcommands`.

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
2. The first normalization pass walks `ArgsNode` and lowers each `Command[a]` child via `subcommand_from_command`.
3. Use the visible schema to lex raw `argv: List[String]` into occurrences. The lexer must be schema-aware so `-1` can remain positional when no visible `-1` spelling exists.
4. Resolve the command path by walking positional tokens against the current node's subcommand table until no child matches.
5. Build a `MatchState` for the selected path. It should retain named occurrences, remaining positionals, tokens after `--`, and a consumed/unconsumed marker per occurrence.
6. Check for built-in help or version flags for the selected command path before running required-argument validation.
7. Run each command scope's `decode_fn` with validation accumulation. Parent scopes only see their own local primitives plus inherited ones.
8. After decode, fail if any occurrence or positional token remains unclaimed.
9. Render failures through `Internal/Help` so the user sees both the specific error and the relevant usage/help block.

### Why `Zafu/Text/Parse` is not the whole engine

1. `Zafu/Text/Parse` is still central, but it should parse values, not own the entire argv grammar.
2. CLI parsing differs from text parsing because named options are order-insensitive and subcommand boundaries are semantic rather than purely lexical.
3. The design therefore uses `Zafu/Text/Parse` at the leaves and a dedicated argv matcher at the top level.
4. This keeps the dependency real without forcing awkward sequential-parser semantics onto option matching.

## Public API Sketch

### Entry points

1. `def command[a](name: String, args: Args[a]) -> Command[a]`
2. `def parse[a](config: ParseConfig, command: Command[a], argv: List[String]) -> ParseResult[a]`
3. `def help_doc[a](config: HelpConfig, command: Command[a], command_path: List[String]) -> Doc`
4. `def failure_doc[a](config: HelpConfig, command: Command[a], errors: NonEmptyChain[CliError]) -> Doc`
5. `def with_help_flag[a](command: Command[a]) -> Command[a]`
6. `def with_version_flag[a](command: Command[a], version_doc: Doc) -> Command[a]`

### Value-parser combinators

1. `def value_from_parse[a](parser: Parser[a], metavar: Doc) -> ValueParser[a]`
2. `def value_from_fn[a](parse_fn: String -> Result[Doc, a], metavar: Doc) -> ValueParser[a]`
3. `def string_value(metavar: Doc) -> ValueParser[String]`
4. `def int_value(metavar: Doc) -> ValueParser[Int]`
5. `def float_value(metavar: Doc) -> ValueParser[Float64]`
6. `def bool_value(metavar: Doc) -> ValueParser[Bool]`
7. `def enum_value[a](cases: NonEmptyList[(String, a)], metavar: Doc) -> ValueParser[a]`
8. `def map_value[a, b](value_parser: ValueParser[a], fn: a -> b) -> ValueParser[b]`
9. `def and_then_value[a, b](value_parser: ValueParser[a], fn: a -> Result[Doc, b]) -> ValueParser[b]`

### Low-level spelling and primitive builders

1. `def long(name: String) -> Spelling`
2. `def short(ch: Char) -> Spelling`
3. `def custom_name(prefix: String, name: String) -> Spelling`
4. `def allow_separate(spelling: Spelling) -> Spelling`
   Adds `SeparateToken` to the spelling, which means the spelling may consume the next argv element as its value.
5. `def allow_attached(spelling: Spelling) -> Spelling`
   Adds `AttachedToken`, which means the value may be attached directly to the same argv token, such as `-Iinclude`.
6. `def allow_equals(spelling: Spelling) -> Spelling`
   Adds `EqualsToken`, which means the spelling may use `--foo=bar` syntax.
7. `def clusterable(spelling: Spelling) -> Spelling`
   Marks a one-character short spelling as safe to appear in grouped short forms like `-xzvf`.
8. `def primitive[a](spec: PrimitiveSpec[a], info: ArgInfo) -> Args[a]`

### High-level argument constructors

1. `def flag(spellings: NonEmptyList[Spelling], info: ArgInfo) -> Args[Bool]`
2. `def flag_value[a](spellings: NonEmptyList[Spelling], value: a, info: ArgInfo) -> Args[a]`
3. `def count(spellings: NonEmptyList[Spelling], info: ArgInfo) -> Args[Int]`
4. `def option[a](value_parser: ValueParser[a], spellings: NonEmptyList[Spelling], info: ArgInfo) -> Args[a]`
5. `def option_optional_value[a](value_parser: ValueParser[a], spellings: NonEmptyList[Spelling], info: ArgInfo) -> Args[Option[a]]`
6. `def positional[a](value_parser: ValueParser[a], info: ArgInfo) -> Args[a]`
7. `def positional_optional[a](value_parser: ValueParser[a], info: ArgInfo) -> Args[Option[a]]`
8. `def rest[a](value_parser: ValueParser[a], info: ArgInfo) -> Args[List[a]]`
9. `def subcommands[a](commands: NonEmptyList[Command[a]], info: ArgInfo) -> Args[a]`

### Applicative and validation combinators

1. `def pure[a](value: a) -> Args[a]`
2. `def map[a, b](args: Args[a], fn: a -> b) -> Args[b]`
3. `def ap[a, b](ff: Args[a -> b], fa: Args[a]) -> Args[b]`
4. `def product[a, b](left: Args[a], right: Args[b]) -> Args[(a, b)]`
5. `def product_left[a, b](left: Args[a], right: Args[b]) -> Args[a]`
6. `def product_right[a, b](left: Args[a], right: Args[b]) -> Args[b]`
7. `def validate[a](args: Args[a], fn: a -> Result[Doc, a]) -> Args[a]`

### Cardinality and defaulting combinators

1. `def optional[a](arg: Args[a]) -> Args[Option[a]]`
2. `def many[a](arg: Args[a]) -> Args[List[a]]`
3. `def some[a](arg: Args[a]) -> Args[NonEmptyList[a]]`
4. `def with_default[a](arg: Args[a], value: a, rendered_default: Doc) -> Args[a]`
5. `many`, `some`, `optional`, and `with_default` should be limited to primitive or subcommand nodes. Applying them to an arbitrary composite `Args[a]` should be rejected during schema normalization.

### Help and metadata combinators

1. `def with_help[a](arg: Args[a], doc: Doc) -> Args[a]`
2. `def with_metavar[a](arg: Args[a], doc: Doc) -> Args[a]`
3. `def with_default_doc[a](arg: Args[a], doc: Doc) -> Args[a]`
4. `def with_group[a](arg: Args[a], doc: Doc) -> Args[a]`
5. `def hidden[a](arg: Args[a]) -> Args[a]`
6. `def with_aliases[a](command: Command[a], aliases: List[String]) -> Command[a]`
7. `def with_scope[a](arg: Args[a], scope: Scope) -> Args[a]`
8. `def example[a](command: Command[a], doc: Doc) -> Command[a]`

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

1. Phase 1: create `src/Zafu/Cli/Args/Internal/Core.bosatsu` and `src/Zafu/Cli/Args.bosatsu` with `ValueParser`, `ArgInfo`, `PrimitiveSpec`, `ArgsNode`, `SubcommandNode`, `Args`, `Command`, `CliError`, `ParseResult`, schema normalization, and an `Applicative[Args]` instance.
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
4. GNU-form tests for `--foo`, `--foo=bar`, and `--foo bar`, including the optional-value case where only some forms are enabled.
5. Negative-number tests to ensure `-1` remains positional unless a visible spelling requires otherwise.
6. Subcommand tests for nested help, aliases, inherited global flags, and unknown-command failures.
7. Validation tests to ensure applicative error accumulation reports multiple independent missing or invalid arguments together.
8. Schema-construction tests for rejected ambiguous specs such as duplicate spellings or positional-after-rest.
9. A real integration test or migration of `Zafu/Tool/JsonFormat.bosatsu` to confirm the API works for an existing command.

## Acceptance Criteria

1. `docs/design/144-design-a-zafu-cli-args-package.md` exists and documents the architecture, combinator inventory, implementation phases, acceptance criteria, risks, and rollout notes.
2. `src/Zafu/Cli/Args.bosatsu` exists and exports `ValueParser`, `ArgInfo`, `Args`, `Command`, `ParseConfig`, `HelpConfig`, `ParseResult`, and the combinator families described in this design.
3. `Args` exposes an applicative API and drives both parsing and help from the same normalized schema.
4. `ValueParser` integrates with `Zafu/Text/Parse` rather than inventing a second string-parser abstraction.
5. Help and failure rendering are built on `Zafu/Text/Pretty.Doc`.
6. The implementation supports `--long`, `--long=value`, `--long value`, `-s`, grouped short flags, attached short values, `--`, positionals, optional positionals, rest args, and custom prefixes when configured.
7. Optional-valued options can distinguish between `--foo`, `--foo=bar`, and `--foo bar` based on the configured `ValueForm` set, and help text renders that distinction explicitly.
8. Subcommands are supported, including command-local help and aliases.
9. The internal representation uses `ArgsNode` and `SubcommandNode`, and child commands are lowered through `subcommand_from_command` so there is no direct `Args` contains `Command` cycle.
10. Inherited named arguments can be declared explicitly and parsed on descendant command paths.
11. Ambiguous schema shapes are rejected during schema construction rather than resolved implicitly at runtime.
12. Tests cover help rendering, GNU-form compatibility, subcommands, inherited scope, negative-number positionals, duplicate detection, and validation accumulation.
13. `src/Zafu/Tool/JsonFormat.bosatsu` is migrated to the new package or an equivalent end-to-end fixture proves the same flag style.
14. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

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
