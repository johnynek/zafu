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
5. Internally, `Args[a]` should be modeled first as a non-public typed `enum` whose variants may introduce existential intermediate types and explicit choice nodes.
6. Bosatsu supports that encoding directly, which makes it reasonable to store the combinator structure itself as the primary representation.
7. Parsing and help generation can then walk that `Args[a]` tree directly or compile it to normalized `Schema` and `ChoiceSchema` artifacts as later passes.
8. This is applicative in the public API, but not a plain sequential parser internally. Named options are order-insensitive, so the interpreter still needs a normalization step before consuming argv.

### Representation choice: existential `Args` enum vs compiled schema-only

1. Bosatsu supports existential type binders on enum variants, so a non-public `enum Args[a]` can encode `Map`, `Map2`, `OrElse`, `Validate`, and related nodes directly.
2. That makes an ADT-first design viable and preferable here.
3. Advantages of the ADT-first design:
4. there is one explicit source of truth for combinators
5. help generation can walk the same structure the parser compiler and choice normalizer see
6. subcommands stay explicit in the recursive representation
7. laws and normalization rules are easier to explain against the stored value
8. Costs of the ADT-first design:
9. the compiler from `Args[a]` into a normalized `Schema` and decode plan is a little more work
10. some variants introduce existential intermediate types, so the internal implementation is less first-order than a plain record
11. Those costs are acceptable because the enum is non-public and Bosatsu supports the needed existential encoding explicitly.
12. A compiled-only `schema + decode_fn` representation is still useful, but it should be the derived execution form, not the primary stored representation.
13. Making `OrElse` explicit in the stored ADT is important for v1 because help rendering and ambiguity checks need to understand exclusivity directly rather than trying to infer it from arbitrary validation code.

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

1. Sketch: `struct ValueParser[a](parse_fn: String -> Result[Doc, a], metavar: Doc, choices: Option[NonEmptyList[(String, Doc)]])`.
2. `parse_fn` returns `Doc` errors so parse failures can be rendered directly in CLI errors without losing structure.
3. `metavar` is used by help rendering and usage lines.
4. `choices` is optional metadata for enumerated values and richer help output. Using `Option[NonEmptyList[...]]` avoids a meaningless `Some([])` state.
5. Main constructors are `value_from_parse`, `value_from_fn`, `string_value`, `int_value`, `float_value`, `bool_value`, `enum_value`, `map_value`, and `and_then_value`.

### `ArgInfo`

1. Sketch: `struct ArgInfo(help: Option[Doc], metavar_override: Option[Doc], group_id: Option[String], hidden: Bool, default_doc: Option[Doc], examples: List[Doc])`.
2. `ArgInfo.examples` is for argument-local examples such as `--color=always` or `-Iinclude`. Command-level full invocation examples stay on `Command[a]`.
3. `ArgInfo` otherwise holds help-facing metadata only. It does not affect low-level matching except where `metavar_override` changes rendered usage.
4. `group_id` names the logical help section an argument belongs to, but the rendered group heading text lives separately in a merged `GroupDocs` map.
5. Metadata combinators such as `with_help`, `with_group`, `with_example`, `hidden`, and `with_default_doc` are record updates over `ArgInfo`, while `with_group_docs` adds subtree-level group heading docs.

### `GroupDocs`

1. Sketch: `type GroupDocs = HashMap[String, Doc]`.
2. `GroupDocs` maps stable `group_id` values to rendered section headings or descriptions.
3. Nested `with_group_docs` wrappers merge these maps so outer definitions win on duplicate keys while missing keys are inherited from inner scopes.

### `Args[a]`

1. Publicly opaque.
2. Internally it should be a non-public existential enum, sketched as:
3. `enum Args[a]: Pure(value: a) | Primitive(spec: PrimitiveSpec[a], info: ArgInfo) | Map[b](source: Args[b], fn: b -> a) | Map2[b, c](left: Args[b], right: Args[c], fn: (b, c) -> a) | OrElse(left: Args[a], right: Args[a]) | Validate[b](source: Args[b], fn: b -> Result[Doc, a], label: Doc) | WithGroupDocs(source: Args[a], group_docs: GroupDocs) | Subcommands(commands: NonEmptyList[Subcommand[Args, a]], info: ArgInfo)`.
4. `Map`, `Map2`, and `Validate` are where existential variant binders are useful: each variant may introduce hidden intermediate types that are not part of the outer `a`.
5. `OrElse` is a structural choice node, not an opaque backtracking parser escape hatch. It must survive normalization so both parsing and help can understand exclusivity.
6. Parsing and help generation first walk `Args[a]`, then compile it into normalized `Schema`, `ChoiceSchema`, and decode plans over a shared `MatchState`.
7. `Args` must expose an `Applicative[Args]` instance through `Zafu/Abstract/Applicative`.
8. Error accumulation should use `Zafu/Control/Result.applicative_combine_Err` with `Zafu/Collection/NonEmptyChain[CliError]`.

### `PrimitiveSpec[a]`, `Subcommand[f, a]`, `ChoiceSchema[a]`, and compiled `Schema`

1. `PrimitiveSpec[a]` is the typed payload of the `Primitive` enum case: `struct PrimitiveSpec[a](kind: PrimitiveKind[a], cardinality: Cardinality, scope: Scope)`.
2. `PrimitiveKind[a]` should have variants like `FlagValue(spellings: NonEmptyList[Spelling], when_present: a)`, `NamedValue(spellings: NonEmptyList[Spelling], value_parser: ValueParser[a])`, `Positional(value_parser: ValueParser[a])`, and `Rest(value_parser: ValueParser[a])`.
3. `Subcommand[f: +(+* -> *), a: +*]` is the recursive child type used by the `Subcommands` variant: `struct Subcommand[f: +(+* -> *), a: +*](name: String, aliases: List[String], summary: Option[Doc], description: Option[Doc], footer: Option[Doc], args: f[a])`.
4. `ChoiceSchema[a]` is the normalized form of an `OrElse` tree: it records branch match domains, rendered choice docs, and the branch decoder selection rules.
5. `Schema` is the compiled normalized form derived from non-choice parts of `Args[a]`; it is what the lexer and argv matcher consume after the ADT has been walked.
6. The key point is that the recursive internal representation is `Args[a]` plus `Subcommand[Args, a]`, while `Schema` and `ChoiceSchema[a]` are later compiled artifacts rather than the stored source of truth.

### `Command[a]`

1. Sketch: `struct Command[a](name: String, summary: Option[Doc], description: Option[Doc], footer: Option[Doc], aliases: List[String], args: Args[a])`.
2. A command is the public root wrapper. The recursive internal child type is `Subcommand[Args, a]`, not `Command[a]`.
3. `subcommands` should accept child `Command[a]` values at the public API boundary, but internally lower them through `subcommand_from_command[a](command: Command[a]) -> Subcommand[Args, a]`.
4. That decomposition keeps the public root wrapper separate from the recursive ADT while still allowing subcommands to be expressed by reusing full child command definitions.
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
6. Repetition such as `zero_or_more` and `one_or_more` belongs inside `PrimitiveSpec[a]` via `Cardinality`; it should not be encoded as a wrapper around arbitrary `Args[a]`.
7. Subcommand choice is not a `PrimitiveSpec[a]`; it is a `Subcommands` enum branch plus a decoder that dispatches into the chosen child `Subcommand[Args, a]`.
8. All high-level constructors should lower either to `PrimitiveSpec[a]` plus `primitive`, or to `Subcommand[Args, a]` plus `subcommands`.

### Choice domains and exclusivity

1. `or_else` must be planned in v1 as an explicit `OrElse` node in the internal ADT, not deferred to a later redesign.
2. `OrElse` is a structural choice combinator, not parser backtracking. Normalization computes the match domain of each branch from visible spellings, positional slots, and subcommand loci.
3. Branches in an `OrElse` tree must be either provably disjoint or provably identical in match domain. Overlapping branches that would make ownership ambiguous are rejected during schema normalization.
4. When two branches have the same atomic match domain, normalization can collapse idempotent cases such as `arg.or_else(arg)`.
5. The compiled `ChoiceSchema[a]` is consumed by both the decoder and the help renderer, so usage lines and option tables can show exclusivity directly.
6. This is how `--compact`, `--spaces2`, and `--spaces4` can be rendered as a disjoint choice in help without relying on `validate`.

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

1. Normalize the `Command[a]` tree into command-local `Schema` values, `ChoiceSchema[a]` values, visible spelling indexes, and merged `GroupDocs` environments.
2. The first normalization pass walks the internal `Args[a]` ADT and lowers each child `Command[a]` through `subcommand_from_command`.
3. During normalization, compile each `OrElse` tree into a `ChoiceSchema[a]` and reject overlapping ambiguous branches.
4. Use the visible schema to lex raw `argv: List[String]` into occurrences. The lexer must be schema-aware so `-1` can remain positional when no visible `-1` spelling exists.
5. Resolve the command path by walking positional tokens against the current node's subcommand table until no child matches.
6. Build a `MatchState` for the selected path. It should retain named occurrences, remaining positionals, tokens after `--`, a consumed/unconsumed marker per occurrence, and the choice-local ownership facts needed to resolve `OrElse`.
7. Check for built-in help or version flags for the selected command path before running required-argument validation.
8. Run each command scope's decoder with validation accumulation. `OrElse` nodes select a branch from `ChoiceSchema[a]`, while parent scopes still see only their own local primitives plus inherited ones.
9. After decode, fail if any occurrence or positional token remains unclaimed.
10. Render failures through `Internal/Help` so the user sees both the specific error and the relevant usage/help block.

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
6. `def zero_or_more[a](value_parser: ValueParser[a], spellings: NonEmptyList[Spelling], info: ArgInfo) -> Args[List[a]]`
7. `def one_or_more[a](value_parser: ValueParser[a], spellings: NonEmptyList[Spelling], info: ArgInfo) -> Args[NonEmptyList[a]]`
8. `def positional[a](value_parser: ValueParser[a], info: ArgInfo) -> Args[a]`
9. `def positional_optional[a](value_parser: ValueParser[a], info: ArgInfo) -> Args[Option[a]]`
10. `def rest[a](value_parser: ValueParser[a], info: ArgInfo) -> Args[List[a]]`
11. `def subcommands[a](commands: NonEmptyList[Command[a]], info: ArgInfo) -> Args[a]`

### Applicative, choice, and validation combinators

1. `def pure[a](value: a) -> Args[a]`
2. `def map[a, b](args: Args[a], fn: a -> b) -> Args[b]`
3. `def map2[a, b, c](left: Args[a], right: Args[b], fn: (a, b) -> c) -> Args[c]`
4. `def product[a, b](left: Args[a], right: Args[b]) -> Args[(a, b)]`
5. `def product_left[a, b](left: Args[a], right: Args[b]) -> Args[a]`
6. `def product_right[a, b](left: Args[a], right: Args[b]) -> Args[b]`
7. `def or_else[a](left: Args[a], right: Args[a]) -> Args[a]`
8. `def validate[a, b](args: Args[a], fn: a -> Result[Doc, b]) -> Args[b]`
9. The ergonomic public combinator should be `map2`; `ap` remains derivable from the `Applicative[Args]` instance but does not need to be the primary surface combinator in the design.

### Defaulting combinators

1. `def optional[a](arg: Args[a]) -> Args[Option[a]]`
2. `def with_default[a](arg: Args[a], value: a, rendered_default: Doc) -> Args[a]`
3. `optional` and `with_default` do not change the visible ownership shape of an argument, so they can remain wrappers on `Args[a]`.
4. Repetition stays on primitive constructors so `OrElse` normalization can still compare branch domains directly.

### Help and metadata combinators

1. `def with_help[a](arg: Args[a], doc: Doc) -> Args[a]`
2. `def with_metavar[a](arg: Args[a], doc: Doc) -> Args[a]`
3. `def with_default_doc[a](arg: Args[a], doc: Doc) -> Args[a]`
4. `def with_group[a](arg: Args[a], group_id: String) -> Args[a]`
5. `def with_group_docs[a](args: Args[a], group_docs: HashMap[String, Doc]) -> Args[a]`
6. `def with_example[a](arg: Args[a], doc: Doc) -> Args[a]`
7. `def hidden[a](arg: Args[a]) -> Args[a]`
8. `def with_aliases[a](command: Command[a], aliases: List[String]) -> Command[a]`
9. `def with_scope[a](arg: Args[a], scope: Scope) -> Args[a]`
10. `def example[a](command: Command[a], doc: Doc) -> Command[a]`
11. `with_group` assigns membership in a logical help group. `with_group_docs` provides the rendered headings for those ids, and nested `with_group_docs` maps merge so outer definitions win on duplicate keys while missing keys are inherited from inner scopes.

### Choice and exclusivity in v1

1. `or_else` should be part of the v1 design. It is too common to defer.
2. `Args[a]` does not need a full `Alternative` instance unless a lawful `empty` emerges, but it should expose a first-class `or_else[a](left: Args[a], right: Args[a]) -> Args[a]`.
3. Because `or_else` is structural, help rendering can show branch exclusivity automatically, for example by rendering `(--compact | --spaces2 | --spaces4)` in usage and an exclusive-choice section in option help.
4. `validate` remains for semantic checks that do not affect ownership shape, but it is not the mechanism for telling help about exclusive argument families.

### Mutually exclusive flags as explicit choice nodes

1. `JsonFormat`-style mode selection should be modeled with `or_else` over atomic flag or option constructors, not by combining independent flags and rejecting illegal combinations with `validate`.
2. For example, `flag_value([long("compact")], compact_mode, info).or_else(flag_value([long("spaces2")], spaces2_mode, info)).or_else(flag_value([long("spaces4")], spaces4_mode, info))` is an introspectable exclusive choice.
3. If the mode also has a default when no flag is passed, that default should be added with `with_default` around the choice node so the exclusivity information remains visible to help generation.
4. This keeps automatic help honest: the renderer can show that those flags are disjoint because the disjointness lives in the `OrElse` tree itself.

## Help Rendering

1. Help rendering should consume normalized `Schema`, `ChoiceSchema[a]`, merged `GroupDocs`, and `Command` metadata.
2. The same normalized structures used for parsing must drive usage lines, option tables, positional sections, subcommand listings, default text, and examples.
3. Rendering should be built from `Zafu/Text/Pretty.Doc` so wrapping is width-sensitive and section layout stays deterministic.
4. Required rendered sections are `Usage`, command description, positional arguments, named options grouped by `group_id`, subcommands, examples, and footer text.
5. Hidden items are omitted by default but may be shown through `HelpConfig`.
6. Failure docs should include the error block before usage, not instead of usage.
7. `RequestedHelp` for a subcommand should render that subcommand's section, not the root command's section.
8. Group rendering should use the merged `GroupDocs` environment: if an arg has no `group_id`, or if its `group_id` is missing from the merged map, it renders in the default ungrouped section.
9. `OrElse` groups should render both in usage lines and in option help so mutually exclusive branches are visible without reading prose.

## Implementation Plan

1. Phase 1: create `src/Zafu/Cli/Args/Internal/Core.bosatsu` and `src/Zafu/Cli/Args.bosatsu` with `ValueParser`, `ArgInfo`, `GroupDocs`, `PrimitiveSpec`, `Subcommand[f, a]`, the existential internal `Args` enum with `Map2` and `OrElse`, `Command`, `CliError`, `ParseResult`, schema normalization, and an `Applicative[Args]` instance.
2. Phase 2: implement `src/Zafu/Cli/Args/Internal/Lex.bosatsu` for schema-aware argv tokenization, short-cluster expansion, `--` handling, attached values, and unknown-option detection.
3. Phase 3: implement `src/Zafu/Cli/Args/Internal/Decode.bosatsu` for command-path selection, occurrence consumption, `OrElse` branch selection, inherited-scope handling, validation accumulation, and leftover detection.
4. Phase 4: implement `src/Zafu/Cli/Args/Internal/Help.bosatsu` for usage/help/failure rendering using `Zafu/Text/Pretty`, including exclusive-choice rendering and group-doc merging.
5. Phase 5: add built-in value parsers backed by `Zafu/Text/Parse`, plus convenience constructors such as `flag`, `option`, `zero_or_more`, `one_or_more`, `positional`, `rest`, and `subcommands`.
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
8. `or_else` tests for disjoint branches, identical-domain idempotence, and rejected overlapping ambiguous branches.
9. Help tests for exclusive-choice rendering and grouped option sections with merged `GroupDocs`.
10. Schema-construction tests for rejected ambiguous specs such as duplicate spellings or positional-after-rest.
11. A real integration test or migration of `Zafu/Tool/JsonFormat.bosatsu` to confirm the API works for an existing command.

## Acceptance Criteria

1. `docs/design/144-design-a-zafu-cli-args-package.md` exists and documents the architecture, combinator inventory, implementation phases, acceptance criteria, risks, and rollout notes.
2. `src/Zafu/Cli/Args.bosatsu` exists and exports `ValueParser`, `ArgInfo`, `Args`, `Command`, `ParseConfig`, `HelpConfig`, `ParseResult`, and the combinator families described in this design.
3. `Args` exposes an applicative API plus `or_else`, and is stored internally as a non-public existential enum that is compiled into normalized schema, choice-schema, and decode artifacts used by parsing and help.
4. `ValueParser` integrates with `Zafu/Text/Parse` rather than inventing a second string-parser abstraction.
5. Help and failure rendering are built on `Zafu/Text/Pretty.Doc`.
6. The implementation supports `--long`, `--long=value`, `--long value`, `-s`, grouped short flags, attached short values, `--`, positionals, optional positionals, rest args, and custom prefixes when configured.
7. Optional-valued options can distinguish between `--foo`, `--foo=bar`, and `--foo bar` based on the configured `ValueForm` set, and help text renders that distinction explicitly.
8. Subcommands are supported, including command-local help and aliases.
9. The internal representation uses the existential `Args` enum plus `Subcommand[Args, a]`, `Map2`, and `OrElse`, and child commands are lowered through `subcommand_from_command`.
10. Inherited named arguments can be declared explicitly and parsed on descendant command paths.
11. Ambiguous schema shapes are rejected during schema construction rather than resolved implicitly at runtime.
12. `or_else` is supported in v1, and help rendering can show mutually exclusive branches automatically from the stored choice structure.
13. Grouped help output is keyed by `group_id`, with `with_group_docs` merge semantics documented and tested.
14. Repetition constructors such as `zero_or_more` and `one_or_more` are exposed as primitive builders rather than wrappers over arbitrary `Args[a]`.
15. Tests cover help rendering, GNU-form compatibility, subcommands, inherited scope, negative-number positionals, duplicate detection, exclusive-choice rendering, `or_else` ambiguity checks, group-doc merging, and validation accumulation.
16. `src/Zafu/Tool/JsonFormat.bosatsu` is migrated to the new package or an equivalent end-to-end fixture proves the same flag style.
17. `./bosatsu lib check`, `./bosatsu lib test`, and `scripts/test.sh` pass.

## Risks and Mitigations

1. Risk: trying to support every CLI spelling directly in high-level combinators will bloat the API.
Mitigation: keep a small set of high-level builders layered on top of one explicit low-level `primitive` plus `Spelling` model.

2. Risk: optional-valued options can become ambiguous with following positionals.
Mitigation: default optional values to attached-only forms such as `--color=always`, and reject or require explicit opt-in for ambiguous separate-token variants.

3. Risk: parent and child command scopes can fight over the same occurrence.
Mitigation: make scope explicit with `Local` and `Inherited`, normalize scope ownership up front, and add path-scoped tests.

4. Risk: `or_else` can admit subtly overlapping branches that are hard to reason about.
Mitigation: compile `OrElse` into `ChoiceSchema[a]`, reject overlapping ambiguous domains during normalization, and keep repetition attached to primitive constructors so domains stay comparable.

5. Risk: help rendering and parse behavior can drift if they are built from separate representations.
Mitigation: both features must consume the same normalized `Schema` and `ChoiceSchema[a]`.

6. Risk: schema-aware lexing may become expensive on large command trees.
Mitigation: precompute visible spelling indexes per command path and keep lexing to a single pass over argv.

## Rollout Notes

1. Land this as an additive module family under `Zafu/Cli`; no existing public API should break.
2. Keep the default configuration GNU-like so common CLIs are easy to express, but ship the low-level `Spelling` escape hatch in the first version so unusual APIs do not require parser forks.
3. Use `Zafu/Tool/JsonFormat.bosatsu` as the first in-repo adopter after the core package lands.
4. Ship `or_else` in the first version as part of the core representation rather than treating it as follow-up work.
5. Defer shell completion, env/config fallbacks, and any full `Alternative` instance until real command migrations show whether they are needed beyond `or_else`.
6. Once the core schema is stable, follow-up work can add completion or manpage generation on top of the same `Schema` and `ChoiceSchema[a]` without changing parse semantics.

## Open Questions

1. Should inherited global options be opt-in through `with_scope(Inherited)` only, or should root-command named options be inherited by default?
2. What exact normalization rule should `or_else` use for identical-domain branches that differ only in help text or default docs?
3. Should optional-value options ever be allowed to consume the next argv element, or should v1 keep them attached-only to avoid ambiguity?
