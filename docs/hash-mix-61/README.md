# `mix_61` benchmark baseline

This directory records the benchmark evidence for the `Zafu/Abstract/Hash::mix_61`
multiply-reduce strategy chosen for issue #207.

Artifacts:

- `baseline-local.json`: metadata plus grouped strategy comparisons.
- `baseline-local.csv`: flat per-case measurements.

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

Strategies:

- `int_fallback`: the Int conversion multiply + canonical reduction fallback.
- `int64_limb_31`: a 31-bit Int64 limb decomposition that keeps multiplication in Int64.

Decision:

- `baseline-local.json` currently selects `int64_limb_31`.
- On the recorded macOS arm64 local run, `int_fallback` won the JVM cases, but
  `int64_limb_31` won every native `bosatsu_c` case by a much larger margin
  (roughly 8.7x to 10.5x faster).
- The merged design allows the fallback only if it is competitive on supported
  backends. These measurements do not support keeping the fallback as the public
  `mix_61` implementation, so `src/Zafu/Abstract/Hash.bosatsu` uses the
  benchmarked `int64_limb_31` strategy.
