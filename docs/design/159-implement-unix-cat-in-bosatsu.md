---
issue: 159
priority: 3
touch_paths:
  - docs/design/159-implement-unix-cat-in-bosatsu.md
  - src/Zafu/Tool/Cat.bosatsu
  - src/zafu_conf.json
depends_on: []
estimated_size: M
generated_at: 2026-03-29T21:51:50Z
---

# Design: implement Unix cat in Bosatsu

_Issue: #159 (https://github.com/johnynek/zafu/issues/159)_

## Summary

Add a new `Zafu/Tool/Cat` command that uses `Zafu/Cli/Args` for `FILE...` parsing and streams raw bytes from stdin/files to stdout with cat-compatible ordering, diagnostics, and exit behavior.

## Context
1. `src/Zafu/Tool/JsonFormat.bosatsu` is the only in-repo runnable tool today and already shows the expected `Main` plus `Zafu/Cli/Args` integration pattern.
2. `Zafu/Cli/Args` now supports positional rest arguments and built-in help rendering, which is enough to model `cat FILE...`.
3. `Bosatsu/IO/Core` exposes raw-handle APIs such as `stdin`, `stdout`, `open_file`, `read_bytes`, `write_bytes`, and `close`, so the implementation can copy bytes without UTF-8 decoding or whole-file buffering.
4. Issue #159 asks for a Unix `cat` clone in `Zafu/Tool` that uses the CLI args library and standard Bosatsu file/stdin/stdout I/O.

## Problem
1. The repository does not yet have a small tool that demonstrates the combination of positional CLI parsing, sequential file processing, and raw byte streaming.
2. Reusing the `JsonFormat` pattern of `read_all_bytes` plus UTF-8 decoding would be incorrect for `cat`, which must preserve arbitrary byte streams and work on large inputs.
3. The implementation needs explicit rules for zero operands, `-` operands, per-file errors, stdout failures, and the Bosatsu `Main` argv quirk that may prepend the executable name.

## Goals
1. Add a new `src/Zafu/Tool/Cat.bosatsu` package with a runnable `main: Main`.
2. Match the core `cat` data-path semantics: zero operands means stdin, `-` means stdin at that position, operands are processed left-to-right, and output bytes are written unchanged to stdout.
3. Keep memory usage bounded by streaming in fixed-size chunks instead of materializing whole files.
4. Use `Zafu/Cli/Args` for argument parsing and help instead of a hand-written argv parser.
5. Continue after source-specific input failures, emit stderr diagnostics, and return a non-zero exit code when any operand fails.

## Non-goals
1. Implementing the full BSD/GNU text-transformation flag matrix such as `-n`, `-b`, `-E`, `-T`, `-v`, or `-s` in this issue.
2. Changing `Zafu/Cli/Args` or the Bosatsu I/O runtime unless the tool implementation exposes a blocking gap.
3. Treating file contents as UTF-8 text or adding line-aware formatting behavior.

## Scope Decision
1. For this issue, "Unix `cat`" is interpreted as the core concatenation command: `FILE...` operands, stdin/stdout behavior, exit codes, and error handling.
2. This matches the issue body, which calls out CLI args plus file/stdin/stdout I/O and does not request presentation flags.
3. If full BSD/GNU flag parity is desired later, the same module can grow around the streaming core described here, but that is follow-up scope rather than a blocker for #159.

## Proposed Design

### Module layout
1. Add `src/Zafu/Tool/Cat.bosatsu` as the primary implementation file. It should contain the CLI schema, pure operand-planning helpers, streaming runtime, `main`, and a small top-level `tests` suite for the pure helpers.
2. Update `src/zafu_conf.json` to export `Zafu/Tool/Cat` so the tool participates in docs, build, and test flows like `Zafu/Tool/JsonFormat`.
3. No shared library changes are expected up front; the tool should stay leaf-scoped unless implementation proves otherwise.

### CLI surface
1. Model the command as `with_help_flag(command("cat", rest(string_value(text("FILE")), arg_info)))`.
2. Keep the existing `normalize_cli_args` pattern from `JsonFormat` so direct executable runs and `./bosatsu ... --run` behave consistently even if `Main` includes the command name in argv.
3. Zero operands are valid; the tool should translate them to a single stdin source rather than failing parse-time validation.
4. `--` should be supported via the default parse config so leading-dash file names can still be passed through.
5. The CLI layer should remain thin: it produces raw operand strings and leaves `-` handling plus path conversion to the planning step.

### Operand planning
1. Introduce a small local source model such as `StdinSource`, `FileSource(raw_name: String, path: Path)`, and `InvalidSource(raw_name: String)`.
2. `[]` becomes `[StdinSource]`.
3. `"-"` becomes `StdinSource` wherever it appears.
4. Any other operand is converted with `string_to_Path`; success yields `FileSource`, failure yields `InvalidSource`.
5. Preserve operand order exactly so `cat a - b` reads file `a`, then current stdin, then file `b`.
6. Keeping invalid paths as planned sources, rather than parse failures, makes error handling align with normal `cat`: diagnostics are per-operand and later operands can still run.

### Streaming runtime
1. Use raw byte APIs, not UTF-8 helpers, for the data path.
2. Implement a small `pump_handle` loop with `read_bytes` and `write_bytes` over a fixed chunk size such as `64 * 1024` bytes.
3. A manual loop is preferred over `read_all_bytes` because it keeps memory bounded and over `copy_bytes` because it lets the tool distinguish source read failures from stdout write failures.
4. For `FileSource`, open the file with `open_file(path, Read)`, stream it to stdout, and close the handle on both success and failure paths.
5. For `StdinSource`, stream directly from `stdin` without closing it.
6. Repeated `-` operands naturally reuse the same stdin handle, so later occurrences observe whatever input remains after earlier reads, which matches Unix `cat`.

### Error handling and exit codes
1. Parse failure should mirror `JsonFormat`: render the CLI failure doc to stderr and return exit code `2`.
2. `--help` should render to stdout and return exit code `0`.
3. `InvalidSource`, `open_file` failures, and source-side read failures should print `cat: <operand>: <reason>` to stderr, set `had_error = True`, and continue to the next operand.
4. Stdout write failures should stop the run immediately because later operands cannot succeed once the sink is broken.
5. `BrokenPipe` should be handled specially at the top level: return a non-zero code without an extra generic stderr line, which is closer to native `cat` pipeline behavior than emitting a second error banner.
6. Final exit code should be `0` on a clean run and `1` if any runtime operand or output error occurred.

### Testing strategy
1. Keep automated tests focused on the pure helpers inside `src/Zafu/Tool/Cat.bosatsu`: argv normalization, zero-operand defaulting, `-` mapping, order preservation, and invalid-path classification.
2. Validate the effectful streaming behavior with repo-level manual smoke tests rather than trying to mock handles inside Bosatsu unit tests.
3. Compare the new tool with `/bin/cat` for stdin-only mode.
4. Compare the new tool with `/bin/cat` for multiple regular files in order.
5. Compare the new tool with `/bin/cat` for mixed operands such as `file - file`.
6. Compare the new tool with `/bin/cat` for missing-file handling where later successful operands must still be emitted.
7. Compare the new tool with `/bin/cat` for binary payload passthrough using `cmp` or equivalent byte comparison.

## Implementation Plan
1. Phase 1: add `src/Zafu/Tool/Cat.bosatsu` with the CLI schema, `normalize_cli_args`, local source types, and pure planning helpers/tests.
2. Phase 2: implement the chunked byte pump and the per-source execution helpers, including `open_file` and `close` management for file operands.
3. Phase 3: wire `run` and `main`, stderr diagnostics, exit-code bookkeeping, and `BrokenPipe` handling.
4. Phase 4: update `src/zafu_conf.json` to export `Zafu/Tool/Cat`.
5. Phase 5: run `./bosatsu lib check`, `./bosatsu lib test`, and manual parity smoke commands against `/bin/cat`.

## Acceptance Criteria
1. `docs/design/159-implement-unix-cat-in-bosatsu.md` documents this architecture, plan, acceptance criteria, risks, and rollout notes.
2. `src/Zafu/Tool/Cat.bosatsu` exists and exports a runnable `main: Main`.
3. `src/Zafu/Tool/Cat.bosatsu` uses `Zafu/Cli/Args` for `FILE...` parsing instead of a hand-written argv parser.
4. `src/Zafu/Tool/Cat.bosatsu` streams bytes with `read_bytes` and `write_bytes`, or an equivalently raw byte API, and never decodes payload data as UTF-8.
5. Running the tool with no operands copies stdin to stdout byte-for-byte.
6. Operand order is preserved, and `-` reads stdin at the position where it appears.
7. Source-specific failures print a diagnostic naming the operand, do not prevent later valid operands from being processed, and cause a final exit code of `1`.
8. Stdout failures terminate the run immediately and do not emit an extra generic top-level error line for `BrokenPipe`.
9. `src/zafu_conf.json` exports `Zafu/Tool/Cat`.
10. `./bosatsu lib check` passes.
11. `./bosatsu lib test` passes.
12. Manual smoke comparisons against `/bin/cat` succeed for stdin-only, mixed-operand, missing-file, and binary-file cases.

## Risks and Mitigations
1. Risk: accidentally using UTF-8 helpers would corrupt binary inputs or reject arbitrary byte streams.
Mitigation: keep the payload path entirely on `Bytes` APIs and reserve `write_utf8` for diagnostics and help only.
2. Risk: file handles leak on error paths because `Prog` does not provide a built-in bracket helper.
Mitigation: centralize file-source execution in a helper that explicitly closes opened handles on both success and recovered failure branches.
3. Risk: Bosatsu `Path` parsing is stricter than native Unix filename handling.
Mitigation: preserve the raw operand for diagnostics, classify conversion failures as per-source runtime errors, and continue processing later operands.
4. Risk: stdout failures are hard to separate from source read failures if the implementation uses a single opaque copy helper.
Mitigation: prefer an explicit `read_bytes` and `write_bytes` loop so the code knows whether the error came from the source or the sink.
5. Risk: the Bosatsu runtime may pass argv with the executable name included in some execution modes.
Mitigation: reuse the same normalization pattern already proven in `Zafu/Tool/JsonFormat`.

## Rollout Notes
1. This is a leaf-tool addition and should land with no behavior changes to existing library packages.
2. Merge the new tool and `src/zafu_conf.json` export in the same change so docs and build flows immediately see the package.
3. After merge, `Zafu/Tool/Cat` becomes the canonical in-repo example of positional rest args plus raw byte streaming in Bosatsu.
4. If maintainers later want BSD or GNU flag parity, build it as follow-up work on top of the same source-planning and streaming core rather than expanding this issue mid-flight.
