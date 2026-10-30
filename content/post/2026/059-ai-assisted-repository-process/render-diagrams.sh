#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
command -v d2 >/dev/null || { echo "Install D2 v0.9.0 to render workflow.d2" >&2; exit 1; }
d2 --layout=elk --theme=300 workflow.d2 workflow.svg
grep -q 'data-d2-version=' workflow.svg
echo 'Rendered the canonical workflow.d2 -> workflow.svg'
