#!/usr/bin/env python3
"""Structural regression checks for the canonical D2 process diagram.

Keep this intentionally dependency-free. It catches workflow topology errors
before a renderer produces a deceptively plausible but incomplete SVG.
"""

import re
import unittest
from collections import defaultdict, deque
from pathlib import Path

SOURCE = Path(__file__).with_name("workflow.d2")
NODE = re.compile(
    r'^[ \t]*([A-Z]{2}\d{2}): "(?:[^"\\]|\\.)*" \{\n'
    r'(?P<body>[\s\S]*?)^[ \t]*\}',
    re.MULTILINE,
)
EDGE = re.compile(
    r"^((?:start_here\.)?[A-Z]{2}\d{2}) -> "
    r"((?:start_here\.)?[A-Z]{2}\d{2}): \{",
    re.MULTILINE,
)


def parse():
    source = SOURCE.read_text(encoding="utf-8")
    nodes = {}
    for match in NODE.finditer(source):
        node_id = match.group(1)
        if node_id in nodes:
            raise ValueError(f"Duplicate node ID: {node_id}")
        shape = re.search(r"(?m)^[ \t]*shape: (\w+)$", match.group("body"))
        if not shape:
            raise ValueError(f"No shape for node {node_id}")
        nodes[node_id] = shape.group(1)
    edges = [
        (from_id.rsplit(".", 1)[-1], to_id.rsplit(".", 1)[-1])
        for from_id, to_id in EDGE.findall(source)
    ]
    return source, nodes, edges


class WorkflowTopologyTests(unittest.TestCase):
    def test_start_choices_are_in_one_frame(self):
        source, nodes, edges = parse()
        self.assertIn('start_here: {\n  label: "START HERE', source)
        self.assertEqual({n for n in nodes if n.startswith("ST")}, {
            "ST01", "ST02", "ST03", "ST04", "ST05", "ST06"
        })
        for node in ("ST01", "ST02", "ST03", "ST04", "ST05", "ST06"):
            self.assertEqual(nodes[node], "circle")
            self.assertIn(f"start_here.{node} -> WS01", source)

    def test_every_step_is_reachable(self):
        _, nodes, edges = parse()
        self.assertGreaterEqual(len(nodes), 70)
        self.assertEqual(len(set(edges)), len(edges))
        for left, right in edges:
            self.assertIn(left, nodes)
            self.assertIn(right, nodes)
        adjacent = defaultdict(list)
        for left, right in edges:
            adjacent[left].append(right)
        reached = {n for n in nodes if n.startswith("ST")}
        pending = deque(reached)
        while pending:
            for target in adjacent[pending.popleft()]:
                if target not in reached:
                    reached.add(target)
                    pending.append(target)
        self.assertEqual(reached, set(nodes), f"Unreachable nodes: {sorted(set(nodes)-reached)}")
        self.assertIn(("EX04", "TR04"), edges)
        self.assertIn(("EX05", "TR04"), edges)
        self.assertIn(("TR04", "RV01"), edges)

    def test_branching_activities_use_decision_diamonds(self):
        _, nodes, edges = parse()
        outbound = defaultdict(int)
        for a, _ in edges:
            outbound[a] += 1
        for node_id, count in outbound.items():
            if count > 1:
                self.assertEqual(
                    nodes[node_id], "diamond",
                    f"{node_id}: {count} outgoing edges must be a decision"
                )
        for ending in ("EN01", "EN02", "EN03"):
            self.assertEqual(nodes[ending], "oval")
            self.assertEqual(outbound[ending], 0)

    def test_projects_and_bug_routes_are_explicit(self):
        _, nodes, edges = parse()
        must_exist = {
            ("WS01", "WS04"), ("WS05", "EN02"),
            ("WS06", "EN03"), ("BG02", "BG08"),
            ("BG02", "BG06"), ("BG02", "BG04"),
            ("BG05", "BG07"), ("BG07", "SP01"),
            ("RV11", "RV12"), ("RV11", "RV13"),
            ("RV14", "RV04"), ("RL04", "RL09"),
            ("RL10", "RL08"),
        }
        self.assertTrue(must_exist.issubset(set(edges)), sorted(must_exist-set(edges)))
        self.assertEqual(nodes["BG05"], "diamond")
        self.assertEqual(nodes["PL03"], "diamond")
        self.assertEqual(nodes["RL08"], "diamond")

    def test_long_routes_include_destinations(self):
        source, _, _ = parse()
        for left, right in (
            ("BG05", "PL01"), ("WS03", "BG01"),
            ("RV04", "PL01"), ("RV14", "RV04"),
        ):
            m = re.search(
                rf"(?m)^{left} -> {right}: \{{\n(?P<body>[\s\S]*?)^\}}",
                source,
            )
            self.assertIsNotNone(m)
            self.assertRegex(m.group("body"), rf"target-arrowhead.label: .+{right}")


if __name__ == "__main__":
    unittest.main()
