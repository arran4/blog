#!/usr/bin/env python3
"""Validate the structure and reachability of the authoritative D2 process."""

from __future__ import annotations

import collections
import re
from pathlib import Path

SOURCE = Path(__file__).with_name("workflow.d2")
ARTICLE = Path(__file__).with_name("index.md")

NODES = re.compile(
    r'^ *([A-Z]{2}\d{2}): "(?:[^"\\]|\\.)*" \{\n(?P<body>.*?)^ *\}',
    re.MULTILINE | re.DOTALL,
)
# Diamond outcomes belong next to their originating decision. The SVG export
# staggers near-source captions and validates label/node clearance.
EDGE_BLOCKS = re.compile(
    r"^((?:start\.)?[A-Z]{2}\d{2}) -> ([A-Z]{2}\d{2}): \{\n(?P<body>.*?)^\}",
    re.MULTILINE | re.DOTALL,
)
EDGES = re.compile(
    r"^(?:start\.)?([A-Z]{2}\d{2}) -> ([A-Z]{2}\d{2}): \{",
    re.MULTILINE,
)
STARTS = ("ST01", "ST02", "ST03", "ST04", "ST05", "ST06")
ENDS = ("EN01", "EN02", "EN03")


def validate(source: str, article: str) -> None:
    nodes: dict[str, str] = {}
    for match in NODES.finditer(source):
        node_id = match.group(1)
        shape = re.search(r"^\s*shape: ([a-z]+)\s*$", match.group("body"), re.MULTILINE)
        if not shape or node_id in nodes:
            raise ValueError(f"Duplicate or malformed node {node_id}")
        nodes[node_id] = shape.group(1)
    if len(nodes) < 75:
        raise ValueError(f"Expected a complete diagram, found {len(nodes)} states")

    outgoing: dict[str, list[str]] = collections.defaultdict(list)
    incoming: dict[str, list[str]] = collections.defaultdict(list)
    edges = EDGES.findall(source)
    for edge in EDGE_BLOCKS.finditer(source):
        source_id, target_id = edge.group(1), edge.group(2)
        body = edge.group("body")
        if "target-arrowhead.label:" in body:
            raise ValueError(f"Unsupported target-end caption on {source_id} -> {target_id}")
        is_decision = nodes.get(source_id) == "diamond"
        source_label = re.search(r'^  source-arrowhead\.label: "([^"]+)"
    for source_id, target_id in edges:
        if source_id not in nodes or target_id not in nodes:
            raise ValueError(f"Dangling edge: {source_id} -> {target_id}")
        outgoing[source_id].append(target_id)
        incoming[target_id].append(source_id)
    for node_id, shape in nodes.items():
        exits = outgoing[node_id]
        if len(exits) > 1 and shape != "diamond":
            raise ValueError(f"{node_id} has {len(exits)} exits but is not a decision")
        if shape == "diamond" and len(exits) < 2:
            raise ValueError(f"{node_id} is a decision without alternative exits")
        if not exits and node_id not in ENDS:
            raise ValueError(f"Unintended dead-end node {node_id}")
        if node_id in ENDS and exits:
            raise ValueError(f"Terminator has outgoing edges: {node_id}")
        anchor = f"{{#node-{node_id.lower()}}}"
        if anchor not in article:
            raise ValueError(f"No article anchor for {node_id}")

    if not all(nodes.get(start) == "circle" for start in STARTS):
        raise ValueError("All entry points must be circles")
    if not all(nodes.get(end) == "oval" for end in ENDS):
        raise ValueError("All terminators must be ovals")
    if 'label: "START HERE' not in source or "start: {" not in source:
        raise ValueError("Starting choices must be grouped in a start frame")
    if "near: bottom-center" not in source:
        raise ValueError("Normal completion must remain at the bottom")
    if "near: center-right" not in source:
        raise ValueError("Legend should stay away from start choices")
    if "TR07" not in incoming["TR04"]:
        raise ValueError("Dogfood checkpoint must be reachable from a decision")

    visited = set(STARTS)
    queue = collections.deque(STARTS)
    while queue:
        for target in outgoing[queue.popleft()]:
            if target not in visited:
                visited.add(target)
                queue.append(target)
    unreachable = sorted(set(nodes) - visited)
    if unreachable:
        raise ValueError(f"Unreachable states: {unreachable}")
    print(f"Validated {len(nodes)} reachable process nodes, {len(edges)} edges, "
          f"{sum(shape == 'diamond' for shape in nodes.values())} decisions")


def main() -> None:
    validate(SOURCE.read_text(encoding="utf-8"), ARTICLE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
, body, re.MULTILINE)
        normal_label = re.search(r'^  label: "([^"]+)"
    for source_id, target_id in edges:
        if source_id not in nodes or target_id not in nodes:
            raise ValueError(f"Dangling edge: {source_id} -> {target_id}")
        outgoing[source_id].append(target_id)
        incoming[target_id].append(source_id)
    for node_id, shape in nodes.items():
        exits = outgoing[node_id]
        if len(exits) > 1 and shape != "diamond":
            raise ValueError(f"{node_id} has {len(exits)} exits but is not a decision")
        if shape == "diamond" and len(exits) < 2:
            raise ValueError(f"{node_id} is a decision without alternative exits")
        if not exits and node_id not in ENDS:
            raise ValueError(f"Unintended dead-end node {node_id}")
        if node_id in ENDS and exits:
            raise ValueError(f"Terminator has outgoing edges: {node_id}")
        anchor = f"{{#node-{node_id.lower()}}}"
        if anchor not in article:
            raise ValueError(f"No article anchor for {node_id}")

    if not all(nodes.get(start) == "circle" for start in STARTS):
        raise ValueError("All entry points must be circles")
    if not all(nodes.get(end) == "oval" for end in ENDS):
        raise ValueError("All terminators must be ovals")
    if 'label: "START HERE' not in source or "start: {" not in source:
        raise ValueError("Starting choices must be grouped in a start frame")
    if "near: bottom-center" not in source:
        raise ValueError("Normal completion must remain at the bottom")
    if "near: center-right" not in source:
        raise ValueError("Legend should stay away from start choices")
    if "TR07" not in incoming["TR04"]:
        raise ValueError("Dogfood checkpoint must be reachable from a decision")

    visited = set(STARTS)
    queue = collections.deque(STARTS)
    while queue:
        for target in outgoing[queue.popleft()]:
            if target not in visited:
                visited.add(target)
                queue.append(target)
    unreachable = sorted(set(nodes) - visited)
    if unreachable:
        raise ValueError(f"Unreachable states: {unreachable}")
    print(f"Validated {len(nodes)} reachable process nodes, {len(edges)} edges, "
          f"{sum(shape == 'diamond' for shape in nodes.values())} decisions")


def main() -> None:
    validate(SOURCE.read_text(encoding="utf-8"), ARTICLE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
, body, re.MULTILINE)
        if is_decision and not source_label:
            raise ValueError(f"Decision outcome needs a near-source caption: {source_id} -> {target_id}")
        if not is_decision and source_label:
            raise ValueError(f"Only decisions may use source-end captions: {source_id} -> {target_id}")
        if source_label and normal_label:
            raise ValueError(f"Duplicate caption on {source_id} -> {target_id}")
        caption = source_label or normal_label
        if caption and "→" in caption.group(1) and not caption.group(1).endswith(target_id):
            raise ValueError(f"Incorrect destination in edge caption {source_id} -> {target_id}")
    for source_id, target_id in edges:
        if source_id not in nodes or target_id not in nodes:
            raise ValueError(f"Dangling edge: {source_id} -> {target_id}")
        outgoing[source_id].append(target_id)
        incoming[target_id].append(source_id)
    for node_id, shape in nodes.items():
        exits = outgoing[node_id]
        if len(exits) > 1 and shape != "diamond":
            raise ValueError(f"{node_id} has {len(exits)} exits but is not a decision")
        if shape == "diamond" and len(exits) < 2:
            raise ValueError(f"{node_id} is a decision without alternative exits")
        if not exits and node_id not in ENDS:
            raise ValueError(f"Unintended dead-end node {node_id}")
        if node_id in ENDS and exits:
            raise ValueError(f"Terminator has outgoing edges: {node_id}")
        anchor = f"{{#node-{node_id.lower()}}}"
        if anchor not in article:
            raise ValueError(f"No article anchor for {node_id}")

    if not all(nodes.get(start) == "circle" for start in STARTS):
        raise ValueError("All entry points must be circles")
    if not all(nodes.get(end) == "oval" for end in ENDS):
        raise ValueError("All terminators must be ovals")
    if 'label: "START HERE' not in source or "start: {" not in source:
        raise ValueError("Starting choices must be grouped in a start frame")
    if "near: bottom-center" not in source:
        raise ValueError("Normal completion must remain at the bottom")
    if "near: center-right" not in source:
        raise ValueError("Legend should stay away from start choices")
    if "TR07" not in incoming["TR04"]:
        raise ValueError("Dogfood checkpoint must be reachable from a decision")

    visited = set(STARTS)
    queue = collections.deque(STARTS)
    while queue:
        for target in outgoing[queue.popleft()]:
            if target not in visited:
                visited.add(target)
                queue.append(target)
    unreachable = sorted(set(nodes) - visited)
    if unreachable:
        raise ValueError(f"Unreachable states: {unreachable}")
    print(f"Validated {len(nodes)} reachable process nodes, {len(edges)} edges, "
          f"{sum(shape == 'diamond' for shape in nodes.values())} decisions")


def main() -> None:
    validate(SOURCE.read_text(encoding="utf-8"), ARTICLE.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
