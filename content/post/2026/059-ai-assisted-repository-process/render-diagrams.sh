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
done < <(sed -nE 's/^ *([A-Z]{2}[0-9]{2}): .*/\1/p' workflow.d2)
if (( count < 50 )); then
  echo "Expected a full workflow catalogue; found only ${count} nodes" >&2
  exit 1
fi

# A Go-installed, tagged D2 may display an older '-HEAD' version string.
# CI pins the module version; do not infer renderer capabilities from --version.
# Fail fast on orphaned states, unlabeled decisions or an incomplete start frame.
python3 validate-workflow.py
d2 --layout=elk --theme=300 workflow.d2 workflow.svg
# Attach each node's current actor, purpose, evidence and permitted transitions
# as inert XML descriptions. The root also receives JSON process instructions.
# PNG rendering ignores these non-visual SVG elements.
python3 embed-agent-instructions.py --svg workflow.svg --article index.md --d2 workflow.d2
# A final diagram-wide geometry audit moves captions above all connector
# strokes, adds white knockouts and rejects label/node or label/label overlap.
python3 protect-workflow-labels.py --svg workflow.svg
# D2's raster exporter uses a very tall internal frame for this workflow and
# exceeds its 32768-pixel limit even with --scale=1. Rasterise the authoritative
# SVG instead; this keeps both outputs derived from one D2 render.
command -v rsvg-convert >/dev/null || {
  echo "rsvg-convert not found; install librsvg2-bin (or the Gentoo librsvg tool)" >&2
  exit 1
}
# Export at 8000px so 26pt diagram labels remain legible when the PNG is opened
# at its natural size; the SVG remains the zoomable, lossless version.
rsvg-convert --format=png --width=8000 --output=workflow.png workflow.svg
grep -q 'data-d2-version=' workflow.svg
grep -q 'agent-workflow-instructions-v1' workflow.svg
test -s workflow.png
echo "Rendered ${count} linked workflow nodes to workflow.svg and workflow.png"
