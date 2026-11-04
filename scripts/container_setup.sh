#!/usr/bin/env bash
# MergeXO executes this standalone script as root before the repository checkout.
set -euo pipefail

case "$(uname -s)/$(uname -m)" in
  Linux/x86_64)
    arch=x64
    jdk_sha=8b9b611d917e3dfd8419d3566b5949226f69b052fed7e109c1368add1dfe8711
    ;;
  Linux/aarch64)
    arch=aarch64
    jdk_sha=3e4eca7ead088f080af1476007decf010a240a1eb4e1e78c54fa32fbcc347084
    ;;
  *) echo "Container setup supports Linux amd64/arm64" >&2; exit 1 ;;
esac

staging_dir="$(mktemp -d)"
trap 'rm -rf "$staging_dir"' EXIT

# CI uses ubuntu-latest's default Temurin 17; pin the same JDK major here.
curl --fail --location --retry 3 --output "$staging_dir/jdk.tar.gz" \
  "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.21%2B9/OpenJDK17U-jdk_${arch}_linux_hotspot_17.0.21_9.tar.gz"
printf '%s  %s\n' "$jdk_sha" "$staging_dir/jdk.tar.gz" | sha256sum --check --status
mkdir -p /opt/mergexo-jdk
tar -xzf "$staging_dir/jdk.tar.gz" -C /opt/mergexo-jdk --strip-components=1
# Exports in setup cannot change the parent worker: install commands on its PATH.
for binary in /opt/mergexo-jdk/bin/*; do
  ln -sf "$binary" "/usr/local/bin/${binary##*/}"
done
java -version

# Native Bosatsu builds and the documentation workflow need these CI packages.
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  libgc1 libgc-dev pkg-config pandoc python3
rm -rf /var/lib/apt/lists/*
