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

Do not force one receiver rule onto an entire module.
Choose the API shape that makes the call read naturally.

The question is:

> What should feel like the receiver here?

There are three common answers:

1. the flowing subject value,
2. the dictionary that selects semantics,
3. no receiver at all, in which case plain prefix style is fine.

## Usage style

The library API and the file-local import style should reinforce each other.
If an operation is designed to read with dot-apply, we should normally write it that way.
If an operation is designed around a dictionary, that dictionary should usually be the receiver.

Preferred shapes:

```bosatsu
foo.traverse(traverse_List, applicative_Option, x -> ...)
items.fold_map(foldable_List, monoid_String, render)
partial.and_then(semigroup_Error, recover)
applicative_Option.pure(value)
applicative_Option.map2(left, right, add)
semigroup_String.combine(left, right)
monoid_Int_add.empty()
```

Avoid mixed shapes that hide the intended center of gravity:

```bosatsu
traverse(foo, traverse_List, applicative_Option, x -> ...)
pure(applicative_Option, value)
left.map2(applicative_Option, right, add)
combine(semigroup_String, left, right)
empty(monoid_Int_add)
```

Prefix style is still fine when the dot form is not clearer, but the default should be to make the code read the way the API was designed.

## Naming style for instances

The canonical exported name for a dictionary instance is:

```text
typeclass_Type
```

Examples:

```bosatsu
eq_Int
ord_String
hash_List
foldable_Array
traverse_List
applicative_Option
semigroup_String
monoid_Int_add
```

If the instance has a meaningful variant, append it after the type:

```bosatsu
semigroup_Int_add
semigroup_Int_mul
monoid_List_concat
```

For file-local helpers, use the same pattern when possible, and add `_local` only when that actually helps:

```bosatsu
foldable_List_local
applicative_Eval
applicative_Writer
```

Avoid reversed names like `option_applicative`.
They are harder to scan, and they break the repo-wide naming rhythm.

## Import style

Prefer the shortest name that is clear in the current file.

Rules:

1. If there is no conflict, import the function with its plain name.
2. If there is a conflict, use the shortest meaningful alias.
3. The function that is central in a file should usually get the shortest name.
4. The name after `.` is the imported identifier, so import the name you want the call site to read.

Examples:

```bosatsu
from Zafu/Abstract/Traverse import traverse
from Zafu/Abstract/Applicative import (
  pure,
  map as map_app,
  map2,
)
```

Good:

```bosatsu
items.traverse(traverse_List, applicative_Option, fn)
app.pure(value)
app.map2(left, right, fn)
value.map_app(app, fn)
```

Bad:

```bosatsu
items.traverse_Traverse(traverse_List, applicative_Option, fn)
left.map2_Applicative(app, right, fn)
value.map_Applicative(app, fn)
```

The old `name_Typeclass` alias pattern should only appear when it is truly the best available name.
In most cases it is just noise.
If a conflict forces an alias, prefer a short functional alias like `map_app` over a copied name like `map_Applicative`.

## 1. Subject-first when there is a distinguished flowing value

Use subject-first when the operation is primarily about consuming, transforming, traversing, or sequencing one value that users will want to keep piping through code.

Examples:

```bosatsu
map(fa, app, fn)
void(fa, app)
foldl(fa, foldable, init, fn)
fold_map(fa, foldable, monoid, fn)
traverse(fa, traverse_f, app, fn)
and_then(result, fn)
and_then(partial, semi, fn)
```

This supports both chained style and left-apply:

```bosatsu
foo.filter(selectfn).traverse(traverse_List, applicative_Option, x -> ...)

selected = foo.filter(selectfn)
x <- selected.traverse(traverse_List, applicative_Option, x -> ...)
```

When an operation is subject-first, prefer subject dot-apply at the call site:

```bosatsu
foo.map(app, fn)
foo.fold_map(foldable, monoid, fn)
foo.traverse(traverse_f, app, fn)
partial.and_then(semi, fn)
```

## 2. Dictionary-first when the call is mainly selecting semantics

Use dictionary-first when the operation is mainly about choosing an algebra, relation, or capability, and there is no single flowing subject value.

Examples:

```bosatsu
eq_inst.eq(left, right)
ord_inst.cmp(left, right)
hash_inst.hash(value)
semi.combine(left, right)
monoid.empty()
app.pure(value)
```

These are semantics-first calls.
The dictionary is the interesting part, not any one data argument.

When readable, prefer dictionary dot-apply:

```bosatsu
eq_Int.eq(left, right)
semigroup_String.combine(left, right)
semigroup_String.combine_all_option(parts)
monoid_Int_add.empty()
monoid_Int_add.combine_all(values)
applicative_Option.pure(value)
```

## 3. Do not invent a value receiver when the data arguments are peers

If an operation takes several peer values of the same conceptual kind, do not force one of them to look like the owner of the call.

This is the important correction for Applicative-style combinators.

Good:

```bosatsu
app.map2(fx, fy, fn)
app.product2(fx, fy)
app.product_left(fx, fy)
semi.combine(left, right)
```

Bad:

```bosatsu
fx.map2(app, fy, fn)
fx.product2(app, fy)
left.combine(semi, right)
```

The value-receiver form looks arbitrary because neither peer is actually more central than the other.
Let the dictionary be the receiver instead.

Tie-breaker:
if both the value and the dictionary feel like plausible receivers, prefer the value receiver only when the operation is a unary chain step on one flowing value.

Examples:

```bosatsu
fa.void(app)
app.map2(fx, fy, fn)
```

`fa.void(app)` keeps a chain moving.
`app.map2(fx, fy, fn)` avoids pretending that `fx` owns a peer-value combination.

## 4. Continuation functions go last

If an operation takes a continuation, mapping function, predicate, or callback, put it last.

Examples:

```bosatsu
map(fa, app, fn)
foldl(fa, foldable, init, fn)
traverse(fa, traverse_f, app, fn)
app.map2(fx, fy, fn)
partial.and_then(semi, fn)
```

This matters for direct calls, dot-apply, and left-apply.

## 5. How to order multiple dictionaries

When there is a single flowing subject, use:

> subject, shape, effect/algebra, data, lambda

Examples:

```bosatsu
fa.traverse(traverse_f, app, fn)
fa.fold_map(foldable, monoid, fn)
fa.combine_all(foldable, monoid)
fa.contains(foldable, eq_inst, target)
partial.and_then(semi, fn)
```

The shape dictionary comes before secondary dictionaries because it explains how we are working with the subject.

Examples:

- `fa.traverse(traverse_f, app, fn)`
  `traverse_f` explains how to walk `fa`; `app` explains how to accumulate effects.
- `fa.fold_map(foldable, monoid, fn)`
  `foldable` explains iteration; `monoid` explains accumulation.
- `fa.contains(foldable, eq_inst, target)`
  `foldable` explains traversal; `eq_inst` is used inside that traversal.

When there is no flowing subject and the dictionary is the receiver, use:

> primary dictionary, peer values, other data, lambda

Examples:

```bosatsu
app.map2(fx, fy, fn)
app.product3(fx, fy, fz)
semi.combine(left, right)
monoid.combine_all(items)
```

## Recommended defaults for common typeclasses

### Eq, Ord, Hash

Dictionary-first.

Examples:

```bosatsu
eq(eq_inst, left, right)
cmp(ord_inst, left, right)
hash(hash_inst, value)
```

### Semigroup, Monoid

Dictionary-first.

Examples:

```bosatsu
semi.combine(left, right)
semi.combine_all_option(items)
monoid.empty()
monoid.combine(left, right)
monoid.combine_all(items)
```

These are algebra-first operations over peer values.

### Applicative

Mixed.

Use dictionary-first for capability selection and peer-value combinators:

```bosatsu
app.pure(value)
app.map2(fx, fy, fn)
app.ap(ff, fa)
app.product_left(fx, fy)
app.product2(fx, fy)
```

Use subject-first for unary transformations on one flowing value:

```bosatsu
fa.map(app, fn)
fa.void(app)
```

`void` is the instructive edge case.
Both `fa` and `app` are plausible receivers, but `fa.void(app)` reads better because it is a unary chain step on the flowing value.

### Foldable

Subject-first.

Examples:

```bosatsu
fa.foldl(foldable, init, fn)
fa.fold_map(foldable, monoid, fn)
fa.combine_all(foldable, monoid)
fa.traverse_void(foldable, app, fn)
```

### Traverse

Subject-first.

Examples:

```bosatsu
fa.traverse(traverse_f, app, fn)
fga.sequence(traverse_f, app)
fa.map(traverse_f, fn)
```

Preferred chained form:

```bosatsu
foo.filter(selectfn).traverse(traverse_List, applicative_Option, x -> ...)
```

### Monad

Subject-first.

Examples:

```bosatsu
ma.flat_map(monad, fn)
partial.and_then(semi, fn)
```

The sequencing subject is still the center of gravity.

## How to design a new typeclass API

When adding a new typeclass or a new operation:

1. Write the call the way you want users to read it in normal code.
2. Write the same call in the dot style you expect people to prefer.
3. If it is effectful, write the left-apply form too.
4. Ask whether there is exactly one flowing subject value.
5. Ask whether the data arguments are peers.
6. Ask whether the dictionary is really selecting semantics.
7. Put callback arguments last.
8. Choose the shortest local names that keep the file readable.

If there is one flowing subject, it should usually be the receiver.
If the values are peers, the dictionary should usually be the receiver.
If there is no natural receiver, plain dictionary-first prefix style is fine.

## Things to avoid

- Do not make every operation subject-first just to enable method syntax.
- Do not make every operation dictionary-first just because typeclasses are explicit.
- Do not make one peer value pretend to own a call that is really about a dictionary.
- Do not keep long imported names when a short unambiguous name is available.
- Do not introduce naming schemes that fight the repo-wide `typeclass_Type` pattern.
- Do not put callbacks in the middle of the argument list.
- Do not treat symmetric peer operations as if one operand were the natural receiver.

## Short version

Use subject-first for unary pipeline operations.
Use dictionary-first for capabilities, algebras, and peer-value combinators.
Keep continuation functions last.
When extra dictionaries are needed, put them after the subject and before the callback.
