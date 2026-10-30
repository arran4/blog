#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

command -v d2 >/dev/null || { echo "Install D2 v0.9.0 to render workflow.d2" >&2; exit 1; }

# Every D2 process node must have a stable article anchor. The D2 source is
# deliberately the authoritative input; missing documentation is a build error.
count=0
while IFS= read -r id; do
  [[ -n "$id" ]] || continue
  anchor="#node-${id,,}"
  if ! grep -Fq "{${anchor}}" index.md; then
    echo "Missing article heading anchor: ${anchor}" >&2
    exit 1
  fi
  count=$((count + 1))
done < <(sed -nE 's/^  ([A-Z]{2}[0-9]{2}): .*/\1/p' workflow.d2)
if (( count < 50 )); then
  echo "Expected a full workflow catalogue; found only ${count} nodes" >&2
  exit 1
fi

version="$(d2 --version)"
case "$version" in
  v0.9.*|v0.10.*|v1.*) ;;
  *)
    echo "D2 $version uses the older PNG renderer; install D2 v0.9.0 or newer to avoid Playwright." >&2
    exit 1
    ;;
esac

d2 --layout=elk --theme=300 workflow.d2 workflow.svg
# The PNG renderer defaults to a larger scale. This tall diagram exceeds its
# 32768-pixel frame-height limit at that scale, so render at 1x instead.
d2 --layout=elk --theme=300 --scale=1 workflow.d2 workflow.png
grep -q 'data-d2-version=' workflow.svg
test -s workflow.png
echo "Rendered ${count} linked workflow nodes to workflow.svg and workflow.png (D2 ${version})"
