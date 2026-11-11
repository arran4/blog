#!/usr/bin/env python3
"""Prevent regressions in connector-label protection and visual clearance."""

from __future__ import annotations

import importlib.util
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE = Path(__file__).with_name("protect-workflow-labels.py")
spec = importlib.util.spec_from_file_location("protect_workflow_labels", MODULE)
protect_mod = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = protect_mod
spec.loader.exec_module(protect_mod)

NS = "{http://www.w3.org/2000/svg}"


def svg(labels, node_x=400):
    connection = "".join(
        f'<g class="edge-{i}"><path class="connection" d="M 0 0 L 500 0" />'
        f'<text x="{x}" y="{y}" style="font-size:18px">{value}</text></g>'
        for i, (x, y, value) in enumerate(labels)
    )
    return (f'<svg xmlns="http://www.w3.org/2000/svg">'
            + "".join(
                f'<g data-workflow-node="AA{i:02d}"><g class="shape">'
                f'<rect x="{node_x + i * 200}" y="100" width="50" height="50" />'
                f'</g></g>' for i in range(80)
            ) + connection + '</svg>').encode()


class ProtectionTests(unittest.TestCase):
    def test_places_connector_text_above_edges_with_backing(self):
        output, n = protect_mod.protect(svg([(100, 20 + i * 50, "NEXT")
                                             for i in range(70)]))
        root = ET.fromstring(output)
        overlay = root.find(f"{NS}g[@id='workflow-edge-label-overlay']")
        self.assertIsNotNone(overlay)
        self.assertEqual(n, 70)
        self.assertEqual(len(overlay.findall(f"{NS}rect")), 70)
        self.assertEqual(len(overlay.findall(f"{NS}text")), 70)
        for edge in root.findall(f"{NS}g"):
            if edge.get("class", "").startswith("edge-"):
                self.assertEqual(len(edge.findall(f"{NS}text")), 0)

    def test_rejects_two_labels_on_the_same_space(self):
        data = svg([(100, 20, "APPROVED")] * 70)
        with self.assertRaisesRegex(ValueError, "Overlapping connector labels"):
            protect_mod.protect(data)

    def test_rejects_label_covering_node(self):
        data = svg([(425, 125, "NODE")] +
                   [(100, 250 + i * 50, "NEXT") for i in range(69)])
        with self.assertRaisesRegex(ValueError, "overlaps node"):
            protect_mod.protect(data)

    def test_double_protection_is_an_error(self):
        output, _ = protect_mod.protect(svg([(100, 20 + i * 50, "NEXT")
                                               for i in range(70)]))
        with self.assertRaisesRegex(ValueError, "already protected"):
            protect_mod.protect(output)


if __name__ == "__main__":
    unittest.main()
