#!/usr/bin/env python3
"""Verify SVG-only semantics and guard against changes to paths and navigation."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("native_svg", HERE / "validate-native-svg.py")
native = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = native
spec.loader.exec_module(native)
S = "{http://www.w3.org/2000/svg}"
SOURCE = (HERE / "workflow.svg").read_text(encoding="utf-8")


def edited(callback):
    root = ET.fromstring(SOURCE)
    callback(root)
    return ET.tostring(root, encoding="unicode")


class NativeSvgTests(unittest.TestCase):
    def test_parity_and_required_branches(self):
        m = native.validate(SOURCE)
        self.assertEqual(len(m["nodes"]), 80)
        self.assertEqual(len(m["transitions"]), 124)
        self.assertEqual(m["schema"], "arran4-native-workflow/v1")
        edges = {(e["from"], e["to"]) for e in m["transitions"]}
        for edge in (("WS03", "BG01"), ("BG05", "BG09"), ("SP05", "CL05"),
                     ("RL02", "EN01"), ("RL08", "EN01"), ("CL05", "EN02"),
                     ("CL06", "EN03")):
            self.assertIn(edge, edges)
        self.assertTrue("GitHub" in m["managementInstructions"])

    def test_missing_graphics_is_rejected(self):
        def edit(root):
            for group in root.iter():
                for child in list(group):
                    if child.get("data-transition-id") == "ws03-bg01":
                        group.remove(child)
                        return
        with self.assertRaisesRegex(ValueError, "different arrow set"):
            native.validate(edited(edit))

    def test_bad_destination_is_rejected(self):
        def edit(root):
            group = next(g for g in root.iter(S+"g") if g.get("data-transition-id") == "ws03-bg01")
            for a in group.iter(S+"a"):
                a.set("href", "#node-invalid")
        with self.assertRaisesRegex(ValueError, "no destination link"):
            native.validate(edited(edit))

    def test_node_guidance_is_required(self):
        def edit(root):
            group = next(g for g in root.iter(S+"g") if g.get("data-workflow-node") == "BG05")
            group.remove(group.find(S+"desc"))
        with self.assertRaisesRegex(ValueError, "Missing accessible description"):
            native.validate(edited(edit))

    def test_metadata_cannot_lose_a_transition(self):
        def edit(root):
            md = next(el for el in root if el.tag == S+"metadata")
            model = json.loads(md.text)
            model["transitions"] = [e for e in model["transitions"] if e["id"] != "bg05-bg09"]
            md.text = json.dumps(model)
        with self.assertRaisesRegex(ValueError, "Expected 124"):
            native.validate(edited(edit))

    def test_terminal_frame_contains_one_row(self):
        native.validate(SOURCE)
        root = ET.fromstring(SOURCE)
        self.assertIsNotNone(next(g for g in root.iter(S+"g") if g.get("id") == "outcomes-frame"))
        for nid in ("EN01", "EN02", "EN03"):
            node = next(g for g in root.iter(S+"g") if g.get("id") == "node-"+nid.lower())
            self.assertIn("translate(", node.get("transform", ""))


if __name__ == "__main__":
    unittest.main()
