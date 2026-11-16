#!/usr/bin/env python3
"""Protect semantically readable SVG source without changing rendered content."""

from __future__ import annotations

import base64
import importlib.util
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE = Path(__file__).with_name("format-workflow-svg.py")
spec = importlib.util.spec_from_file_location("format_workflow_svg", MODULE)
fmt = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fmt
spec.loader.exec_module(fmt)

NS = "{http://www.w3.org/2000/svg}"


def sample() -> tuple[bytes, str]:
    cls = base64.b64encode(b"(WS03 -&gt; BG01)[0]").decode()
    model = json.dumps({"schema": "example", "management_instructions": "First inspect the PR."})
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg">'
           f'<metadata id="agent-workflow-instructions-v1">{model}</metadata>'
           f'<svg class="d2-svg"><g class="c3RhcnQ="><rect width="5"/></g>'
           f'<a href="#other"><g data-workflow-node="WS03"><desc>WS03 — Decide'
           f'\nActor: Human\n\nMove to: BG01</desc><g class="shape">'
           f'<path d="M 0 0 L 10 10"/></g>'
           f'<text x="10" y="20"><tspan>Choice</tspan><tspan> One</tspan></text>'
           f'</g></a><a href="#other"><g data-workflow-node="BG01">'
           f'<desc>BG01 — Debug</desc><rect width="8"/></g></a>'
           f'<g class="{cls}"><path class="connection" '
           f'd="M 10 20 L 40 20" marker-end="url(#arrow)"/></g></svg>'
           f'<g id="workflow-edge-label-overlay"><text x="8" y="9">bug</text></g>'
           f'</svg>')
    d2 = ('# Phase: intake\n'
          'WS03: "Select" {\n  shape: diamond\n}\n'
          '# Phase: debug\nBG01: "Debug" {\n  shape: rectangle\n}\n'
          'WS03 -> BG01: {\n  label: "bug"\n}\n')
    return svg.encode(), d2


class SemanticFormatTests(unittest.TestCase):
    def test_semantic_sections_and_original_shapes(self):
        raw, d2 = sample()
        out, nodes, edges = fmt.format_svg(raw, d2, min_nodes=2, min_edges=1)
        self.assertEqual((nodes, edges), (2, 1))
        doc = out.decode()
        for marker in ("PHASE / Intake", "PHASE / Bug reproduction",
                       "NODE / WS03", "NODE / BG01",
                       "TRANSITIONS /", "ROUTE / WS03 -> BG01"):
            self.assertIn(marker, doc)
        self.assertIn('\n      "schema": "example"', doc)
        self.assertIn("CAPTION /", doc)
        before = ET.fromstring(raw)
        after = ET.fromstring(out)
        self.assertEqual([e.get("d") for e in before.iter(f"{NS}path")],
                         [e.get("d") for e in after.iter(f"{NS}path")])
        self.assertEqual(["".join(e.itertext()) for e in before.iter(f"{NS}text")],
                         ["".join(e.itertext()) for e in after.iter(f"{NS}text")])
        self.assertEqual([e.get("href") for e in before.iter(f"{NS}a")],
                         [e.get("href") for e in after.iter(f"{NS}a")])
        self.assertEqual(json.loads(before.find(f"{NS}metadata").text),
                         json.loads(after.find(f"{NS}metadata").text))
        route = next(e for e in after.iter(f"{NS}g")
                     if e.get("data-transition-id") == "ws03-bg01")
        self.assertEqual(route.get("data-from"), "WS03")
        self.assertEqual(route.get("data-to"), "BG01")

    def test_idempotent_and_no_tspan_whitespace_added(self):
        raw, d2 = sample()
        once, _, _ = fmt.format_svg(raw, d2, min_nodes=2, min_edges=1)
        twice, _, _ = fmt.format_svg(once, d2, min_nodes=2, min_edges=1)
        self.assertEqual(once, twice)
        self.assertIn(b'<text x="10" y="20"><tspan>Choice</tspan>'
                      b'<tspan> One</tspan></text>', once)

    def test_missing_edge_rejected(self):
        raw, d2 = sample()
        with self.assertRaisesRegex(ValueError, "Transition has no complete path"):
            fmt.format_svg(raw.replace(b'class="connection"', b'class="other"'),
                           d2, min_nodes=2, min_edges=1)

    def test_missing_node_rejected(self):
        raw, d2 = sample()
        with self.assertRaisesRegex(ValueError, "Missing or duplicate process node"):
            fmt.format_svg(raw.replace(b'data-workflow-node="BG01"',
                                       b'data-workflow-node="ZZ99"'),
                           d2, min_nodes=2, min_edges=1)


if __name__ == "__main__":
    unittest.main()
