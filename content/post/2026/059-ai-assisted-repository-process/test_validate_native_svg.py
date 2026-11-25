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


    def test_reverse_arrival_links_are_checked(self):
        def edit(root):
            for anchor in root.iter(S+"a"):
                label = anchor.find(S+"text")
                if label is not None and label.get("data-route-end") == "arrival":
                    anchor.set("href", "#node-"+label.get("data-to").lower())
                    return
            raise AssertionError("No reverse arrival to mutate")
        with self.assertRaisesRegex(ValueError, "Incorrect forward/reverse caption link"):
            native.validate(edited(edit))

    def test_cl05_collects_exactly_nine_traceable_feeders(self):
        model = native.validate(SOURCE)
        sources = {edge["from"] for edge in model["transitions"] if edge["to"] == "CL05"}
        self.assertEqual(len(sources), 9)
        root = ET.fromstring(SOURCE)
        collector = next(g for g in root.iter(S+"g") if g.get("id") == "cl05-collector")
        labels = {a.get("href") for a in collector.iter(S+"a")}
        self.assertEqual(labels, {"#node-"+x.lower() for x in sources})

    def test_broken_cl05_collector_is_rejected(self):
        def edit(root):
            c = next(g for g in root.iter(S+"g") if g.get("id") == "cl05-collector")
            a = next(c.iter(S+"a"))
            c.remove(a)
        with self.assertRaisesRegex(ValueError, "collector labels"):
            native.validate(edited(edit))

    def test_short_decision_caption_cannot_enter_diamond(self):
        def edit(root):
            for text in root.iter(S+"text"):
                if text.get("data-from") == "SP02" and text.get("data-to") == "SP03":
                    text.set("y", "4013")
                    return
        with self.assertRaisesRegex(ValueError, "Caption overlaps node"):
            native.validate(edited(edit))

    def test_floating_caption_is_rejected(self):
        def edit(root):
            for label in root.iter(S+"text"):
                if label.get("data-from") == "SP02" and label.get("data-to") == "SP03":
                    label.set("x", "8947.6")
                    return
        with self.assertRaisesRegex(ValueError, "not adjacent to its own route"):
            native.validate(edited(edit))

    def test_caption_cannot_be_closer_to_an_unrelated_route(self):
        def edit(root):
            for label in root.iter(S+"text"):
                if label.get("data-from") == "RV10" and label.get("data-to") == "TR07" and not label.get("data-route-end"):
                    # This location has the correct caption adjacent to RV10→TR07
                    # but an injected unrelated connector goes through the text.
                    x, y = float(label.get("x")), float(label.get("y"))-10
                    group = next(g for g in root.iter(S+"g") if g.get("data-transition-id") == "rv09-rv10")
                    p = next(p for p in group.iter(S+"path") if "connection" in p.get("class", ""))
                    p.set("d", f"M {x-200} {y} L {x+200} {y}")
                    return
        with self.assertRaisesRegex(ValueError, "Caption ambiguous between"):
            native.validate(edited(edit))

    def test_long_route_needs_reverse_caption(self):
        def edit(root):
            for group in root.iter():
                for a in list(group):
                    label = a.find(S+"text") if a.tag == S+"a" else None
                    if label is not None and label.get("data-from") == "BG01" and label.get("data-to") == "BG02" and label.get("data-route-end") == "arrival":
                        group.remove(a)
                        return
        with self.assertRaisesRegex(ValueError, "Long route lacks bidirectional"):
            native.validate(edited(edit))

    def test_dogfood_and_completion_arrivals_repeat_decision(self):
        root = ET.fromstring(SOURCE)
        for target, outcome in (("TR04", "dogfood required"), ("CL01", "complete")):
            labels = [el for el in root.iter(S+"text")
                      if el.get("data-from") == "TR07" and el.get("data-to") == target]
            self.assertEqual(len(labels), 2)
            arrival = next(el for el in labels if el.get("data-route-end") == "arrival")
            self.assertEqual(arrival.text, "TR07 · " + outcome)

    def test_long_route_arrival_cannot_lose_outcome(self):
        def edit(root):
            label = next(el for el in root.iter(S+"text")
                         if el.get("data-from") == "TR07" and el.get("data-to") == "TR04"
                         and el.get("data-route-end") == "arrival")
            label.text = "TR07"
        with self.assertRaisesRegex(ValueError, "Arrival caption lacks source and outcome|Caption"):
            native.validate(edited(edit))

    def test_pr_tree_sequence_is_compact(self):
        root = ET.fromstring(SOURCE)
        nodes = {g.get("data-workflow-node"): g for g in root.iter(S+"g") if g.get("data-workflow-node")}
        a, b = (native._bounds(nodes[k]) for k in ("TR02", "TR03"))
        self.assertEqual(a[1], b[1])
        self.assertLess(a[2], b[0])
        native.validate(SOURCE)

    def test_duplicate_route_caption_is_rejected(self):
        def edit(root):
            import copy
            for group in root.iter():
                for a in list(group):
                    label = a.find(S+"text") if a.tag == S+"a" else None
                    if label is not None and label.get("data-from") == "BG01" and label.get("data-to") == "BG02" and label.get("data-route-end") == "arrival":
                        group.append(copy.deepcopy(a))
                        return
        with self.assertRaisesRegex(ValueError, "Duplicate route caption|Captions overlap"):
            native.validate(edited(edit))

    def test_vertical_caption_uses_near_edge_anchor(self):
        root = ET.fromstring(SOURCE)
        labels = {label.get("data-to"): label for label in root.iter(S+"text")
                  if label.get("data-from") == "SP02"}
        for target, line_x in (("SP03", 9124), ("SP04", 9924)):
            label = labels[target]
            x = float(label.get("x"))
            # Either side is valid: the nearest rendered text edge must
            # face the connector, without relying on a fixed side preference.
            self.assertIn("text-anchor:end" if x < line_x else "text-anchor:start",
                          label.get("style"))
            self.assertAlmostEqual(x, line_x, delta=20)
        native.validate(SOURCE)

    def test_long_route_end_positions_are_distinct(self):
        root = ET.fromstring(SOURCE)
        routes = {g.get("data-transition-id"): native._route_segments(g) for g in root.iter(S+"g") if g.get("data-transition-id")}
        for route in ("bg01-bg02", "rv04-rv05", "rv04-sp01", "ws04-bg01"):
            a, b = route.upper().split("-")
            labels = [label for label in root.iter(S+"text") if label.get("data-from") == a and label.get("data-to") == b]
            self.assertEqual(len(labels), 2)
            for label in labels:
                p = native._route_progress(native._caption_bounds(label), routes[route])
                if label.get("data-route-end") == "arrival":
                    self.assertGreaterEqual(p, .58)
                else:
                    self.assertLessEqual(p, .42)
                    self.assertIn(b, label.text)
        native.validate(SOURCE)


    def test_crossing_bridges_are_real_and_noninteractive(self):
        root = ET.fromstring(SOURCE)
        overlay = next(g for g in root.iter(S+"g")
                       if g.get("id") == "workflow-crossing-bridges")
        self.assertEqual(overlay.get("pointer-events"), "none")
        self.assertGreaterEqual(len(overlay.findall(S+"g")), 40)
        self.assertFalse(list(overlay.iter(S+"a")))
        native.validate(SOURCE)

    def test_crossing_bridge_ownership_is_checked(self):
        def edit(root):
            overlay = next(g for g in root.iter(S+"g")
                           if g.get("id") == "workflow-crossing-bridges")
            next(iter(overlay.findall(S+"g"))).set("data-over-route", "unknown-route")
        with self.assertRaisesRegex(ValueError, "invalid route ownership"):
            native.validate(edited(edit))

    def test_crossing_bridge_must_not_hide_node_or_label(self):
        def edit(root):
            overlay = next(g for g in root.iter(S+"g")
                           if g.get("id") == "workflow-crossing-bridges")
            bridge = next(iter(overlay.findall(S+"g")))
            circle = bridge.find(S+"circle")
            circle.set("cx", "9479")
            circle.set("cy", "3929")
        with self.assertRaisesRegex(ValueError, "not on both assigned routes|encroaches"):
            native.validate(edited(edit))


    def test_overlay_visual_coordinate_frame_matches_nested_drawing(self):
        root = ET.fromstring(SOURCE)
        nested = next(e for e in root.iter(S+"svg")
                      if "d2-svg" in e.get("class", "").split())
        x, y, _, _ = map(float, nested.get("viewBox").split())
        self.assertEqual((x, y), (-90, -91))
        for group_id in ("workflow-edge-label-overlay", "workflow-crossing-bridges"):
            overlay = next(g for g in root.iter(S+"g") if g.get("id") == group_id)
            self.assertEqual(overlay.get("transform"), "translate(90 91)")
        native.validate(SOURCE)

    def test_untranslated_labels_fail_visual_alignment(self):
        def edit(root):
            overlay = next(g for g in root.iter(S+"g")
                           if g.get("id") == "workflow-edge-label-overlay")
            overlay.attrib.pop("transform")
        with self.assertRaisesRegex(ValueError, "Visual coordinate frame mismatch"):
            native.validate(edited(edit))

if __name__ == "__main__":
    unittest.main()
