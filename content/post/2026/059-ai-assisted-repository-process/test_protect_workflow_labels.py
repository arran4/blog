#!/usr/bin/env python3
"""Regressions for close staggered branch captions and continuous routes."""

from __future__ import annotations

import base64
import importlib.util
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE = Path(__file__).with_name("protect-workflow-labels.py")
spec = importlib.util.spec_from_file_location("protect_workflow_labels", MODULE)
layout = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = layout
spec.loader.exec_module(layout)

NS = "{http://www.w3.org/2000/svg}"


def make_svg(labels: tuple[str, ...] = ("bug", "deep", "clear"),
             overlap_static: bool = False) -> bytes:
    # Source decision fills (100,100)-(420,200); paths remain continuous.
    shapes = ('<g data-workflow-node="AA01"><g class="shape">'
              '<path d="M 100 150 L 260 100 L 420 150 L 260 200 Z" />'
              '</g></g>')
    shapes += "".join(
        f'<g data-workflow-node="AB{i:02d}"><g class="shape">'
        f'<rect x="{4000+i*100}" y="100" width="50" height="50"/>'
        '</g></g>' for i in range(79))
    edges = ""
    for i, label in enumerate(labels):
        dest = f"AB{i:02d}"
        name = base64.b64encode(f"(AA01 -&gt; {dest})[0]".encode()).decode()
        x = 140 + i*120
        edges += (f'<g class="{name}"><path class="connection" '
                  f'd="M {x} 200 L {x} 700"/>'
                  f'<text x="250" y="500" style="text-anchor:middle;'
                  f'font-size:18px">{label}</text></g>')
    if overlap_static:
        # A normal, non-decision caption is checked as well.
        name = base64.b64encode(b"(AB00 -&gt; AB01)[0]").decode()
        edges += (f'<g class="{name}"><path class="connection" d="M 0 0 L 0 900"/>'
                  '<text x="4025" y="130" style="font-size:18px">'
                  'BROKEN</text></g>')
    return ('<svg xmlns="http://www.w3.org/2000/svg">'
            + shapes + edges + '</svg>').encode()


class LayoutTests(unittest.TestCase):
    def test_branch_labels_stay_near_decision_and_stagger(self):
        data = make_svg()
        result, moved = layout.protect(data, min_labels=3)
        self.assertEqual(moved, 3)
        root = ET.fromstring(result)
        overlay = root.find(f"{NS}g[@id='workflow-edge-label-overlay']")
        self.assertIsNotNone(overlay)
        self.assertEqual(len(overlay.findall(f"{NS}text")), 3)
        self.assertFalse(overlay.findall(f"{NS}rect"))  # no line gaps
        ys = [float(label.get("y")) for label in overlay.findall(f"{NS}text")]
        self.assertEqual(len(set(ys)), 3)
        self.assertTrue(all(200 < y < 320 for y in ys), ys)
        self.assertTrue(all("paint-order:stroke fill" in text.get("style", "")
                            for text in overlay.findall(f"{NS}text")))
        # Original connector path geometry is untouched.
        original = ET.fromstring(data)
        paths = [el.get("d") for el in original.iter(f"{NS}path")
                 if el.get("class") == "connection"]
        rendered = [el.get("d") for el in root.iter(f"{NS}path")
                    if el.get("class") == "connection"]
        self.assertEqual(paths, rendered)

    def test_long_branch_caption_must_stay_close(self):
        result, moved = layout.protect(make_svg(("return to requirements → AB00",
                                                "needs a rewrite → AB01",
                                                "ready → AB02")), min_labels=3)
        self.assertEqual(moved, 3)
        root = ET.fromstring(result)
        texts = root.find(f"{NS}g[@id='workflow-edge-label-overlay']").findall(f"{NS}text")
        self.assertTrue(all(float(t.get("y")) < 350 for t in texts))

    def test_static_label_over_node_fails(self):
        with self.assertRaisesRegex(ValueError, "overlaps a node"):
            layout.protect(make_svg(overlap_static=True), min_labels=4)

    def test_double_processing_rejected(self):
        once, _ = layout.protect(make_svg(), min_labels=3)
        with self.assertRaisesRegex(ValueError, "already positioned"):
            layout.protect(once, min_labels=3)


if __name__ == "__main__":
    unittest.main()
