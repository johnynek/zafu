# zafu

Useful Bosatsu code, starting with a `Vector` implementation.

## Layout

- `src/Zafu/Vector.bosatsu`: vector implementation and property tests.
- `src/zafu_conf.json`: Bosatsu library configuration.
- `bosatsu_libs.json`: maps library name to source root.
- `scripts/test.sh`: runs `lib check`, `lib test`, and dry-run `lib publish`.

## Setup

1. Fetch Bosatsu CLI/runtime:

```bash
./bosatsu --fetch
```

## Local validation

```bash
scripts/test.sh
```

This runs:

1. `./bosatsu lib check`
2. `./bosatsu lib test`
3. Dry-run style publish via `scripts/publish_bosatsu_libs.sh --dry-run` with `URI_BASE=https://example.invalid/`

## CI and release

- CI (`.github/workflows/ci.yml`) runs the same check/test/dry-run publish on pull requests.
- Release (`.github/workflows/release.yml`) triggers on `vX.Y.Z` tags, verifies the tagged commit is on `main`, publishes `.bosatsu_lib` files, and uploads them to the GitHub Release page.
