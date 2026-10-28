#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
for name in overview planning implementation ci-recovery; do
  dot -Tsvg "$name.dot" -o "$name.svg"
done
