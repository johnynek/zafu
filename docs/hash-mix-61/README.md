# `mix_61` benchmark baseline

This directory records the benchmark evidence for the `Zafu/Abstract/Hash::mix_61`
multiply-reduce strategy chosen for issue #207.

Artifacts:

- `baseline-local.json`: metadata plus grouped strategy comparisons.
- `baseline-local.csv`: flat per-case measurements.

The checked-in JSON records a deterministic SHA-256 source fingerprint over the
benchmark-relevant Bosatsu and harness files instead of a git SHA. That keeps
the evidence reviewable from the checked-in tree itself, and
`scripts/hash_mix_benchmark_test.py` rejects stale fingerprints.

Regenerate the local baseline with:

```bash
scripts/benchmark_hash_mix61.sh
```

Workloads:

- `collection_hash`: sequence-style hash accumulation and finalization.
- `hash_map_hash`: unordered `HashMap` entry hashing plus map-hash accumulation.
- `hash_set_hash`: unordered `HashSet` entry hashing plus set-hash accumulation.

The benchmark package and the shipped unordered collection hashers both import
`Zafu/Abstract/Internal/Hash61`, so the recorded `hash_map_hash` and
`hash_set_hash` measurements exercise the same `sum_61_i64` reducer that
`Zafu/Collection/HashMap` and `Zafu/Collection/HashSet` use in production.

The public `HashMap.eq/hash` and `HashSet.eq/hash` adapters use caller-supplied
dictionaries, so the benchmark's synthetic key/item hash inputs measure the
shipped public adapter paths rather than the collections' internal HAMT cache
dictionaries.

Breaking API note:

- `HashSet.eq` and `HashSet.hash` now take the caller's `hash_item`
  dictionary.
- `HashMap.eq` and `HashMap.hash` now take both `hash_key` and `hash_value`
  dictionaries.

That change is intentional for issue #207: the public adapters now define
equality and hashing on the caller-visible quotient, rather than trusting the
collections' cached internal hashes or stored key semantics.

- `HashSet.eq/hash` operate on the quotient of visible items under
  `hash_item`.
- `HashMap.eq/hash` operate on the quotient of visible `(key, value)` entries
  under the caller-supplied pair semantics.

Strategies:

- `int_fallback`: the Int conversion multiply + canonical reduction fallback.
- `int64_limb_31`: a 31-bit Int64 limb decomposition that keeps multiplication in Int64.

Decision:

- `baseline-local.json` currently selects `int64_limb_31`.
- On the recorded macOS arm64 local run, `int_fallback` won the JVM cases, but
  `int64_limb_31` won every native `bosatsu_c` case by a much larger margin
  (roughly 6.3x to 10.1x faster).
- The merged design allows the fallback only if it is competitive on supported
  backends. These measurements do not support keeping the fallback as the public
  `mix_61` implementation, so `src/Zafu/Abstract/Hash.bosatsu` uses the
  benchmarked `int64_limb_31` strategy.
