# Bosatsu Coding Style (Fast Start)

This guide is for experienced programmers (or coding agents) who want to be productive in Bosatsu quickly.

## 1) Fast productivity loop

1. Bootstrap compiler/runtime once:

```bash
./bosatsu --fetch
```

2. Typecheck continuously while editing:

```bash
./bosatsu lib check
```

3. Keep incomplete code compiling with `todo(...)` stubs.

```bosatsu
def hard_function(x, y):
  todo((x, y))
```

This is a key iteration trick: stub unfinished logic, keep `lib check` green, and fill implementations incrementally.

4. Run tests when a unit of work is complete:

```bash
./bosatsu lib test
```

5. Validate publishability in CI/local without mutating repo config:

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

Use `loop` in most recursive traversals/accumulator code. It reads more like imperative state updates while staying pure and tail-recursive.

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

Use explicit `recur` when direct structural recursion is clearer (e.g., simple list/tree destructuring).

## 4) Prefer left-apply (`<-`) over deep nesting

Write sequential pipelines with `<-` instead of nested `match`/`if_Some`/`await` chains.

```bosatsu
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

## 5) Define local `def operator` for compact code

Bosatsu code is often clearer with local operators in math/logic-heavy files.

```bosatsu
def operator +(a, b): a.add(b)
def operator -(a, b): a.sub(b)
def operator *(a, b): a.mul(b)
def operator ==(a, b): a.eq_Int(b)
```

Guideline: define only the operators used heavily in that file; keep semantics obvious.

## 6) Define local helper functions for `<-` pipelines

Add small local/package-local helpers that return `Option`/`Prog` so `<-` pipelines stay flat and readable.

- Example helpers: `if_Some`, `parse_*`, `read_*`, `step_*`.
- Prefer tiny single-purpose helpers over one giant function.
- Package-local functions are inlined at compile time, so you can prioritize readability without runtime cost.

## 7) Practical quality bar

1. Keep APIs intentional with `export (...)`.
2. Use explicit `Option`/sum types for failure.
3. Add or update `tests` alongside behavior changes.
4. Before PR/release, run `scripts/test.sh`.

## 8) Pointers

- `../bosatsu/test_workspace/`: canonical language idioms and small examples.
- `../test_bo_repo/src/`: larger real-world Bosatsu examples (`Json`, `ParensProbs`, `Vector`).
- [Writing Bosatsu in 5 minutes](https://johnynek.github.io/bosatsu/writing_bosatsu_5_minutes.html): official quick syntax/workflow refresher.
