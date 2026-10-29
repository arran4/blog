#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if ! command -v d2 >/dev/null 2>&1; then
  echo "D2 CLI not found; install v0.9.0 or newer from https://d2lang.com" >&2
  exit 1
fi
count=0
while IFS= read -r -d '' source; do
  output="${source%.d2}.svg"
  echo "Rendering ${source} -> ${output}"
  d2 --layout=elk --theme=300 "${source}" "${output}"
  grep -q '<svg' "${output}" || { echo "Invalid SVG: ${output}" >&2; exit 1; }
  count=$((count+1))
done < <(find . -type f -name '*.d2' -print0 | sort -z)
if (( count < 11 )); then
  echo "Expected at least 11 diagrams; found ${count}" >&2
  exit 1
fi
echo "Rendered ${count} D2 diagrams."
