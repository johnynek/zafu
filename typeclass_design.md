# Typeclass API Design

## Purpose

Bosatsu does not have implicit instance resolution or a Rust-style trait method system.
In Zafu, typeclasses are explicit dictionary values.

That means argument order matters a lot.
It affects:

- whether dot-chaining reads naturally,
- whether left-apply (`<-`) helps flatten code,
- whether explicit dictionaries feel like a small annotation or like the whole API.

This document gives the default design rule for new typeclasses and new generic operations.
It is guidance for future work, not a statement that the current code already follows it everywhere.

## Main rule

Do not choose one first-argument rule for an entire typeclass module.
Choose the first argument per operation.

The question is:

> What is the center of gravity of this call?

There are two main cases.

## 1. Subject-first when there is a distinguished flowing value

Use subject-first when the operation is primarily about consuming, transforming, traversing, or sequencing a value that users will want to keep piping through code.

This is the rule that preserves dot-chaining.

Examples:

```bosatsu
map(fa, app, fn)
foldl(fa, foldable, init, fn)
fold_map(fa, foldable, monoid, fn)
traverse(fa, traverse_f, app, fn)
and_then(result, fn)
and_then(partial, semi, fn)
```

This style supports both:

```bosatsu
foo.filter(selectfn).traverse(traverse_List, applicative_Option, x -> ...)
```

and:

```bosatsu
selected = foo.filter(selectfn)
x <- selected.traverse(traverse_List, applicative_Option)
```

The important property is that the value being worked on stays in the first position.

## 2. Dictionary-first when the call is mainly selecting semantics

Use dictionary-first when the operation is primarily about choosing an algebra, relation, or capability, and there is no distinguished subject value to act as a receiver.

Examples:

```bosatsu
eq(eq_inst, left, right)
cmp(ord_inst, left, right)
hash(hash_inst, value)
combine(semi, left, right)
empty(monoid)
pure(app, value)
```

These calls are not naturally about "doing something to `left`" or "doing something to `value`" in the same way that `map` or `traverse` are.
They are mainly about choosing which semantics to use.

This is why relation and algebra typeclasses naturally read dictionary-first.

## 3. Continuation functions go last

If an operation takes a continuation, mapping function, predicate, or callback, put that function last.

Examples:

```bosatsu
map(fa, app, fn)
foldl(fa, foldable, init, fn)
traverse(fa, traverse_f, app, fn)
flat_map(ma, monad, fn)
```

This matters for readability in both direct calls and left-apply style.

## 4. How to order multiple dictionaries

When an operation is subject-first and needs more than one explicit dictionary, use this order:

1. the subject value,
2. the dictionary that explains the subject's structure or primary capability,
3. dictionaries that describe how results are combined, accumulated, compared, or effected,
4. ordinary non-function arguments,
5. continuation functions.

Short mnemonic:

> subject, shape, effect/algebra, data, lambda

Examples:

```bosatsu
traverse(fa, traverse_f, app, fn)
sequence(fga, traverse_f, app)
fold_map(fa, foldable, monoid, fn)
combine_all(fa, foldable, monoid)
traverse_void(fa, foldable, app, fn)
minimum_option(fa, foldable, ord_inst)
contains(fa, foldable, eq_inst, target)
and_then(partial, semi, fn)
```

The important distinction is between:

- the dictionary that tells us how to work with the subject itself, and
- the dictionary that tells us how to combine or interpret results while doing that work.

So for the common cases:

- `traverse(fa, traverse_f, app, fn)`
  `traverse_f` comes before `app` because we first need to know how to walk `fa`, then how to accumulate the effects.
- `fold_map(fa, foldable, monoid, fn)`
  `foldable` comes before `monoid` because we first need to know how to iterate the structure, then how to accumulate mapped results.
- `combine_all(fa, foldable, monoid)`
  same rule: structure first, accumulation second.
- `contains(fa, foldable, eq_inst, target)`
  `foldable` comes before `eq_inst` because traversal of `fa` is the outer operation; equality is used inside that traversal.

If there is no subject, then this rule does not apply.
In that case, fall back to dictionary-first.

## 5. Do not invent a receiver when the data arguments are peers

Some operations have multiple value arguments, but they are peers rather than a receiver plus inputs.

For those, do not force subject-first just to make method syntax possible.

Examples:

```bosatsu
combine(semi, left, right)
eq(eq_inst, left, right)
cmp(ord_inst, left, right)
```

`left` is not really the "owner" of the call here.
The operation is about the dictionary and the relation/algebra it defines.

By contrast, these are still receiver-like operations even though they mention more than one value:

```bosatsu
map2(fa, app, fb, fn)
product_left(fa, app, fb)
```

Those read as extending work on an existing effectful value `fa`, so subject-first still makes sense.

## 6. Constructors and projections are usually dictionary-first

Operations that construct a value from a typeclass alone, or project another capability from it, should usually remain dictionary-first.

Examples:

```bosatsu
pure(app, value)
empty(monoid)
monoid_to_semigroup(monoid)
ord_to_eq(ord_inst)
combine_fn(semi)
```

There is no flowing subject to preserve in these calls.

## Recommended defaults for common typeclasses

### Eq, Ord, Hash

Dictionary-first.

Examples:

```bosatsu
eq(eq_inst, left, right)
cmp(ord_inst, left, right)
hash(hash_inst, value)
```

Rationale: these choose comparison or hashing semantics for peer values.

### Semigroup, Monoid

Dictionary-first for the abstract algebra operations.

Examples:

```bosatsu
combine(semi, left, right)
combine_all_option(semi, items)
empty(monoid)
combine(monoid, left, right)
combine_all(monoid, items)
```

Rationale: these are algebra-first operations over peer values.

Concrete data structure modules may still expose value-centric helpers when that improves ergonomics, but the generic abstract operations should treat the algebra as the semantic center.

### Applicative

Mixed.

Use dictionary-first for operations with no subject:

```bosatsu
pure(app, value)
```

Use subject-first for operations over existing effectful values:

```bosatsu
map(fa, app, fn)
map2(fa, app, fb, fn)
ap(ff, app, fa)
product_left(fa, app, fb)
product_right(fa, app, fb)
void(fa, app)
```

Rationale: `pure` selects an effect, but `map` and friends continue work on an existing subject.

### Foldable

Subject-first.

Examples:

```bosatsu
foldl(fa, foldable, init, fn)
foldr(fa, foldable, init, fn)
fold_map(fa, foldable, monoid, fn)
combine_all(fa, foldable, monoid)
combine_all_option(fa, foldable, semi)
traverse_void(fa, foldable, app, fn)
contains(fa, foldable, eq_inst, target)
minimum_option(fa, foldable, ord_inst)
```

Rationale: these are all operations on a structure that users will often want to chain.
When another dictionary is needed, `Foldable` stays first among dictionaries because it governs the subject structure.

### Traverse

Subject-first.

Examples:

```bosatsu
traverse(fa, traverse_f, app, fn)
sequence(fga, traverse_f, app)
map(fa, traverse_f, fn)
```

Rationale: the traversed structure is the receiver-like subject; the applicative is secondary.
So the ordering is subject, then `Traverse`, then `Applicative`, then the callback.

Preferred shape for chained code:

```bosatsu
foo.filter(selectfn).traverse(traverse_List, applicative_Option, x -> ...)
```

Not:

```bosatsu
traverse_List.traverse(applicative_Option, foo, x -> ...)
```

### Monad

Subject-first.

Examples:

```bosatsu
flat_map(ma, monad, fn)
flatten(mma, monad)
```

If lawfulness requires an extra algebra dictionary, keep the monadic subject first:

```bosatsu
and_then(partial, semi, fn)
```

Rationale: monadic sequencing is usually the core pipeline in user code.
The extra algebra dictionary is auxiliary to the sequencing subject, so it comes after the subject and before the callback.

## How to design a new typeclass API

When adding a new typeclass or a new operation, use this checklist:

1. Write the call the way you expect users to read it in normal code.
2. Write the same call in a chained style.
3. Write the same call in a left-apply style if it is effectful or sequential.
4. Ask whether there is a single flowing subject value.
5. Ask whether the data arguments are peers.
6. Ask whether the operation is really selecting semantics from a dictionary.
7. Put any continuation function last.

If there is a single flowing subject, it should usually be first.
If there is not, the dictionary should usually be first.

## Things to avoid

- Do not make every operation dictionary-first just because typeclasses are explicit.
- Do not make every operation subject-first just to enable method syntax.
- Do not use one blanket rule for an entire module when different operations have different centers of gravity.
- Do not put callbacks in the middle of the argument list.
- Do not treat symmetric peer operations as if one operand were the natural receiver.

## Short version

Use subject-first for pipeline operations.
Use dictionary-first for semantics-selection operations.
Keep continuation functions last.
When extra dictionaries are needed, put them after the subject and before the callback.
