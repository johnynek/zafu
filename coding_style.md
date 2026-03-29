# Bosatsu Coding Style (Fast Start)

This guide is for experienced programmers (or coding agents) who want to be productive in Bosatsu quickly.

## 1) Fast productivity loop

1. Bootstrap compiler/runtime once:

```bash
./bosatsu --fetch
```

2. Typecheck continuously while editing:

```bash
./bosatsu check --warn
```

`--warn` keeps postponable lint diagnostics visible without failing the run.

3. Keep incomplete code compiling with `todo(...)` stubs.

```bosatsu
def hard_function(x, y):
  todo((x, y))
```

This is a key iteration trick: stub unfinished logic, keep `lib check` green, and fill implementations incrementally.

4. Run tests during iteration:

```bash
./bosatsu test --warn
```

5. Before a PR/release, run the strict local gate:

```bash
./bosatsu check
./bosatsu test
```

6. Validate publishability in CI/local without mutating repo config:

```bash
scripts/test.sh
```

## 2) File shape and modeling

1. Start each file with exactly one `package`.
2. Keep imports/exports explicit.
3. Use `enum`/`struct` for data modeling; use `match` for branching.
4. Keep tests as values (`Assertion`, `TestSuite`) in the package.

Minimal skeleton:

```bosatsu
package Zafu/Thing

export (Thing(), solve, tests)

enum Thing:
  A
  B(value: Int)

def solve(t: Thing) -> Int:
  match t:
    case A: 0
    case B(v): v

tests = TestSuite("thing tests", [
  Assertion(solve(B(2)).eq_Int(2), "solve B"),
])
```

## 3) Preferred control-flow style

### Prefer `loop` to `recur`

`loop` vs `recur` is about tail recursion semantics, not about integer vs structural recursion.

- `loop`: recursion must be tail-recursive; it compiles to a `while` loop.
- `recur`: allows both tail and non-tail recursion; tail-recursive forms may compile to a loop, non-tail forms do not.

Use `loop` by default for iterative/tail-recursive code paths when you want guaranteed loop lowering.

```bosatsu
def sum_to(n: Int) -> Int:
  def go(rem: Int, acc: Int) -> Int:
    loop rem:
      case _ if cmp_Int(rem, 0) matches GT:
        go(rem.sub(1), acc.add(rem))
      case _:
        acc
  go(n, 0)
```

Use `recur` when non-tail recursion is intentional or when it is the clearer expression of the algorithm.

## 4) Prefer left-apply (`<-`) over deep nesting

Write sequential pipelines with `<-` instead of nested `match`/`if_Some`/`await` chains.
`if_Some` is not built in; define it locally (or import your shared helper).
Keep continuation/callback arguments last so APIs work well with both dot-apply and `<-`.

```bosatsu
def if_Some(o: Option[a], fn: a -> Option[b]) -> Option[b]:
  match o:
    case Some(a):
      fn(a)
    case None:
      None

parsed <- parse_number_token(s).if_Some()
(rest, token, is_int_token) = parsed
f <- string_to_Float64(token).if_Some()
Some((rest, f))
```

For effectful code (`Prog`), use:

```bosatsu
_ <- println("hello").await()
now <- now_mono.await()
pure(duration_to_nanos(now))
```

## 5) Prefer Bosatsu-native patterns over ceremony

Prefer concise pattern syntax over tearing values down and rebuilding them by hand.

- Use `matches` for predicate-style checks.
- Prefer record destructuring and struct update syntax when working with structs.
- Prefer combined patterns and literal/string pattern matches over nested `match` chains.
- Prefer total-pattern lambdas when the shape is already known.

```bosatsu
ParseState { remaining, ... } = state

if value matches "":
  ...

match input:
  case "true" | "True": True
  case "false" | "False": False
  case _: todo(input)

next = ParseState { remaining: tail, ..state }
```

## 6) Keep typeclass calls readable

- Use subject-first when one value is flowing through a pipeline: `fa.traverse(traverse_List, applicative_Option, fn)`.
- Use dictionary-first for capabilities and peer-value combinators: `app.pure(value)`, `eq_inst.eq(left, right)`, `app.map2(fx, fy, fn)`.
- Keep callback arguments last.
- Prefer the shortest clear imported names over noisy aliases like `traverse_Traverse` when a shorter import works.

For the full rule set, see `typeclass_design.md`.

## 7) Define local `def operator` for compact code

Bosatsu code is often clearer with local operators in math/logic-heavy files.

```bosatsu
def operator +(a, b): a.add(b)
def operator -(a, b): a.sub(b)
def operator *(a, b): a.mul(b)
def operator ==(a, b): a.eq_Int(b)
```

Guideline: define only the operators used heavily in that file; keep semantics obvious.

## 8) Define local helper functions for `<-` pipelines

Add small local/package-local helpers that return `Option`/`Prog` so `<-` pipelines stay flat and readable.

- Example helpers: `if_Some`, `parse_*`, `read_*`, `step_*`.
- Prefer tiny single-purpose helpers over one giant function.
- Package-local functions are inlined at compile time, so you can prioritize readability without runtime cost.

## 9) Practical quality bar

1. Keep APIs intentional with `export (...)`.
2. Keep `Internal` types and test packages out of public exports unless there is a clear reason.
3. Reuse Predef/collection/typeclass helpers before adding new local helpers.
4. Preserve specialized bulk operations (`fold_map`, `combine_all`, `map2_Gen`) when they exist; avoid accidentally quadratic rewrites.
5. Use explicit `Option`/sum types for failure.
6. Add or update `tests` alongside behavior changes.
7. Before PR/release, run `scripts/test.sh`.

## 10) Pointers

- [Bosatsu Language Guide](https://johnynek.github.io/bosatsu/language_guide.html): full language reference.
- [Writing Bosatsu in 5 minutes](https://johnynek.github.io/bosatsu/writing_bosatsu_5_minutes.html): official quick syntax/workflow refresher.
