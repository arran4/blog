#!/usr/bin/env python3
"""Validate the self-contained workflow SVG; do not regenerate or reposition it."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path

Q = lambda name: "{http://www.w3.org/2000/svg}" + name
SOURCE = Path(__file__).with_name("workflow.svg")
STARTS = {f"ST{i:02d}" for i in range(1, 7)}
ENDS = {"EN01", "EN02", "EN03"}
DECISIONS = {"WS03", "WS04", "BG05", "SP05", "RV08", "RL02", "RL08"}


def validate(source: str) -> dict:
    root = ET.fromstring(source)
    if root.tag != Q("svg") or not root.get("viewBox"):
        raise ValueError("Invalid SVG root or viewBox")
    if any(e.tag in {Q("script"), Q("foreignObject")} for e in root.iter()):
        raise ValueError("SVG must remain script-free and self-contained")
    if any(k.startswith("on") for e in root.iter() for k in e.attrib):
        raise ValueError("Unsafe event handler in SVG")

    metadata = [e for e in root if e.tag == Q("metadata") and e.get("id") == "workflow-model"]
    if len(metadata) != 1:
        raise ValueError("Exactly one workflow-model is required")
    model = json.loads(metadata[0].text or "")
    if model.get("schema") != "arran4-native-workflow/v1":
        raise ValueError("Unsupported workflow-model schema")
    nodes, transitions = model.get("nodes"), model.get("transitions")
    if not isinstance(nodes, dict) or len(nodes) != 80:
        raise ValueError("Expected 80 workflow nodes")
    if not isinstance(transitions, list) or len(transitions) != 124:
        raise ValueError("Expected 124 workflow transitions")
    if set(model.get("entryPoints", [])) != STARTS or set(model.get("terminalNodes", [])) != ENDS:
        raise ValueError("Entry or termination state mismatch")
    guidance = model.get("managementInstructions", "")
    if not isinstance(guidance, str) or len(guidance) < 500:
        raise ValueError("Missing management instructions")
    if model.get("nodeDescriptionSelector") != "g[data-workflow-node] > desc":
        raise ValueError("Missing node description lookup")
    if "human" not in guidance.lower() or "project" not in guidance.lower():
        raise ValueError("Human authorization or Projects guidance missing")

    drawn = {}
    for group in root.iter(Q("g")):
        nid = group.get("data-workflow-node")
        if not nid:
            continue
        if nid not in nodes or nid in drawn or group.get("id") != "node-" + nid.lower():
            raise ValueError(f"Duplicate or invalid node {nid}")
        desc = group.find(Q("desc"))
        if desc is None or desc.get("id") != "agent-node-" + nid.lower():
            raise ValueError(f"Missing accessible description for {nid}")
        body = "".join(desc.itertext())
        if not body.startswith(nid + " — ") or any(x not in body for x in ("Actor:", "Enter from:", "Move to:")):
            raise ValueError(f"Incomplete checkpoint instructions for {nid}")
        drawn[nid] = group
    if set(drawn) != set(nodes):
        raise ValueError("Graphical and semantic nodes differ")

    edges, outgoing = {}, defaultdict(list)
    for edge in transitions:
        a, b, eid = edge.get("from"), edge.get("to"), edge.get("id")
        if a not in nodes or b not in nodes or eid != a.lower() + "-" + b.lower() or eid in edges:
            raise ValueError("Invalid or duplicated semantic transition")
        if not edge.get("condition"):
            raise ValueError(f"Missing transition condition {eid}")
        edges[eid] = edge
        outgoing[a].append(b)
    for nid, node in nodes.items():
        kind = node.get("kind")
        if kind not in {"entry", "action", "decision", "terminal"}:
            raise ValueError(f"Invalid checkpoint kind {nid}")
        if nid in ENDS and (outgoing[nid] or kind != "terminal"):
            raise ValueError(f"Invalid terminal {nid}")
        if nid not in ENDS and not outgoing[nid]:
            raise ValueError(f"Unexpected dead end {nid}")
        if len(outgoing[nid]) > 1 and kind not in {"decision", "entry"}:
            raise ValueError(f"Multiple exits without decision {nid}")
        if kind == "decision" and len(outgoing[nid]) < 2:
            raise ValueError(f"Single-exit decision {nid}")
    if any(nodes[nid]["kind"] != "decision" for nid in DECISIONS):
        raise ValueError("A required decision changed kind")

    visited, queue = set(STARTS), deque(STARTS)
    while queue:
        for next_id in outgoing[queue.popleft()]:
            if next_id not in visited:
                visited.add(next_id)
                queue.append(next_id)
    if visited != set(nodes):
        raise ValueError("Unreachable states: " + repr(sorted(set(nodes)-visited)))
    if not {"BG01", "PL01", "BG09"}.issubset(outgoing["BG05"]):
        raise ValueError("Bug diagnosis routes missing")

    drawn_edges = {}
    for group in root.iter(Q("g")):
        eid = group.get("data-transition-id")
        if eid is None:
            continue
        if eid in drawn_edges or eid not in edges or group.get("id") != "transition-" + eid:
            raise ValueError(f"Duplicate or unknown arrow {eid}")
        if group.get("data-from") != edges[eid]["from"] or group.get("data-to") != edges[eid]["to"]:
            raise ValueError(f"Wrong arrow endpoints {eid}")
        paths = [e for e in group.iter(Q("path")) if "connection" in e.get("class", "").split()]
        if len(paths) != 1 or not paths[0].get("d") or not paths[0].get("marker-end"):
            raise ValueError(f"Missing continuous arrow {eid}")
        if paths[0].get("mask"):
            raise ValueError(f"Masked arrow {eid}")
        links = {e.get("href") for e in group.iter(Q("a"))}
        if "#node-" + edges[eid]["to"].lower() not in links:
            raise ValueError(f"Arrow has no destination link {eid}")
        drawn_edges[eid] = group
    if set(drawn_edges) != set(edges):
        raise ValueError("The SVG has a different arrow set from the model")

    for a in root.iter(Q("a")):
        target = a.get("href", "")
        if not target.startswith("#node-") or target[6:].upper() not in nodes:
            raise ValueError("Broken or external link " + target)
    frame = next((e for e in root.iter(Q("g")) if e.get("id") == "outcomes-frame"), None)
    if frame is None or frame.find(Q("rect")) is None:
        raise ValueError("Missing finish frame")
    y = []
    for nid in sorted(ENDS):
        node = drawn[nid]
        ellipse = next((e for e in node.iter(Q("ellipse"))), None)
        translation = re.search(r"translate\(([-\d.]+)\s+([-\d.]+)\)", node.get("transform", ""))
        if ellipse is None or translation is None:
            raise ValueError(f"Terminal must be repositioned oval {nid}")
        y.append(float(ellipse.get("cy"))+float(translation.group(2)))
    if max(y)-min(y) > 5:
        raise ValueError("Terminals must share a horizontal row")

    return model


def main() -> None:
    model = validate(SOURCE.read_text(encoding="utf-8"))
    print(f"Validated native SVG: {len(model['nodes'])} nodes, {len(model['transitions'])} arrows")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, ET.ParseError) as exc:
        print("Native SVG validation failed:", exc, file=sys.stderr)
        raise SystemExit(1) from exc
