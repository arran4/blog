#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

# workflow.svg is the only authoritative source of process and geometry.
python3 validate-native-svg.py
command -v rsvg-convert >/dev/null || {
  echo "Install rsvg-convert (librsvg2-bin) to export workflow.png" >&2
  exit 1
}

# The large artboard needs a high-resolution raster for legible label text.
rsvg-convert --format=png --width=14000 --output=workflow.png workflow.svg
test -s workflow.png
echo "Validated native SVG; derived workflow.png from workflow.svg"
