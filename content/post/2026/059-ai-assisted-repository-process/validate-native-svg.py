#!/usr/bin/env python3
"""Validate the self-contained workflow SVG; do not regenerate or reposition it."""
from __future__ import annotations

import json
import math
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


def _bounds(group: ET.Element) -> tuple[float, float, float, float]:
    shape_group = next((g for g in group if g.tag == Q("g")
                        and "shape" in g.get("class", "").split()), None)
    if shape_group is None or len(shape_group) != 1:
        raise ValueError("Missing or ambiguous node shape")
    shape = shape_group[0]
    if shape.tag == Q("rect"):
        x, y = float(shape.get("x")), float(shape.get("y"))
        bounds = (x, y, x + float(shape.get("width")), y + float(shape.get("height")))
    elif shape.tag == Q("ellipse"):
        x, y = float(shape.get("cx")), float(shape.get("cy"))
        rx, ry = float(shape.get("rx")), float(shape.get("ry"))
        bounds = (x - rx, y - ry, x + rx, y + ry)
    elif shape.tag == Q("path"):
        numbers = [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", shape.get("d", ""))]
        if len(numbers) < 4 or len(numbers) % 2:
            raise ValueError("Invalid node path geometry")
        bounds = (min(numbers[::2]), min(numbers[1::2]),
                  max(numbers[::2]), max(numbers[1::2]))
    else:
        raise ValueError("Unsupported workflow node shape")
    translation = re.search(r"translate\(([-\d.]+)\s+([-\d.]+)\)", group.get("transform", ""))
    if translation:
        dx, dy = float(translation.group(1)), float(translation.group(2))
        bounds = (bounds[0] + dx, bounds[1] + dy,
                  bounds[2] + dx, bounds[3] + dy)
    return bounds


def _intersects(a: tuple[float, float, float, float],
                b: tuple[float, float, float, float]) -> bool:
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def _caption_bounds(label: ET.Element) -> tuple[float, float, float, float]:
    style = label.get("style", "")
    match = re.search(r"font-size:(\d+(?:\.\d+)?)px", style)
    if match is None:
        raise ValueError("Workflow caption lacks explicit font size")
    size = float(match.group(1))
    x, y = float(label.get("x")), float(label.get("y"))
    text = "".join(label.itertext())
    if not text:
        raise ValueError("Empty workflow caption")
    # Conservative monospaced glyph widths, with a little breathing room.
    width = len(text) * size * 0.71 + 16
    anchor = re.search(r"text-anchor:(middle|start|end)", style)
    if anchor is None:
        raise ValueError("Route caption lacks supported text anchor")
    if anchor.group(1) == "start":
        left, right = x - 8, x + width - 8
    elif anchor.group(1) == "end":
        left, right = x - width + 8, x + 8
    else:
        left, right = x - width / 2, x + width / 2
    return (left, y - size - 8, right, y + size * 0.25 + 5)


# Captions are attached to actual polyline geometry, not merely to an empty
# rectangle somewhere between two nodes. Current SVG uses M/L and zero-length
# S bends inherited from its original layout.
LONG_ROUTE_LENGTH = 4000
MAX_CAPTION_GAP = 23
MIN_ROUTE_ADVANTAGE = 4


def _route_segments(group):
    path = next(p for p in group.iter(Q("path"))
                if "connection" in p.get("class", "").split())
    data = path.get("d", "")
    tokens = re.findall(r"[MLS]|-?\d+(?:\.\d+)?", data)
    if re.sub(r"[\s,]+", "", data) != "".join(tokens):
        raise ValueError("Unsupported route geometry")
    segments = []
    point = None
    i = 0
    while i < len(tokens):
        command = tokens[i]
        n = 4 if command == "S" else 2
        values = tuple(map(float, tokens[i+1:i+1+n]))
        i += n + 1
        end = values[-2:]
        if command == "S" and (values[:2] != point or end != point):
            raise ValueError("Non-degenerate curve requires explicit distance support")
        if point is not None and command != "M" and math.dist(point, end) > .01:
            segments.append((*point, *end))
        point = end
    if not segments:
        raise ValueError("Empty route")
    return segments


def _segment_gap(box, segment):
    x, y, X, Y = segment
    def gap(px, py):
        return math.hypot(max(0, box[0]-px, px-box[2]),
                          max(0, box[1]-py, py-box[3]))
    # Nearly orthogonal strokes are conservatively bounded by their extent.
    if abs(X-x) < 1 or abs(Y-y) < 1:
        return math.hypot(max(0, box[0]-max(x,X), min(x,X)-box[2]),
                          max(0, box[1]-max(y,Y), min(y,Y)-box[3]))
    # Distance to a rectangle is convex along a straight segment.
    lo, hi = 0., 1.
    for _ in range(22):
        a, b = (2*lo+hi)/3, (lo+2*hi)/3
        if gap(x+a*(X-x), y+a*(Y-y)) < gap(x+b*(X-x), y+b*(Y-y)):
            hi = b
        else:
            lo = a
    t = (lo+hi)/2
    return min(gap(x,y), gap(X,Y), gap(x+t*(X-x),y+t*(Y-y)))


def _route_gap(box, segments):
    return min(_segment_gap(box, segment) for segment in segments)


def _route_progress(box, segments):
    """Fraction along the route nearest the caption's conservative centre."""
    x, y = (box[0]+box[2])/2, (box[1]+box[3])/2
    best = (float("inf"), 0.)
    at = 0.
    for px, py, X, Y in segments:
        dx, dy = X-px, Y-py
        length = math.hypot(dx, dy)
        t = max(0., min(1., ((x-px)*dx+(y-py)*dy)/(length*length)))
        distance = math.hypot(x-px-t*dx, y-py-t*dy)
        if distance < best[0]:
            best = (distance, at+t*length)
        at += length
    return best[1]/at


def _check_route_readability(root: ET.Element, drawn: dict,
                             edges: dict, drawn_edges: dict) -> None:
    node_boxes = {id: _bounds(group) for id, group in drawn.items()}
    caption_boxes = []
    captions = {}
    arrivals = 0
    route_segments = {eid: _route_segments(group) for eid, group in drawn_edges.items()}
    endpoint_labels = defaultdict(set)
    for anchor in root.iter(Q("a")):
        for label in anchor:
            if label.tag != Q("text"):
                continue
            from_id, to_id = label.get("data-from"), label.get("data-to")
            if not from_id or not to_id:
                continue
            eid = from_id.lower() + "-" + to_id.lower()
            if eid not in edges:
                raise ValueError(f"Caption for nonexistent route: {eid}")
            placement = label.get("data-route-end")
            expected_link = f"#node-{from_id.lower()}" if placement == "arrival" else f"#node-{to_id.lower()}"
            if anchor.get("href") != expected_link:
                raise ValueError(f"Incorrect forward/reverse caption link for {eid}")
            if placement == "arrival":
                arrivals += 1
            bbox = _caption_bounds(label)
            for nid, node_box in node_boxes.items():
                if _intersects(bbox, node_box):
                    raise ValueError(f"Caption overlaps node {nid}: {eid}")
            for prior_id, prior_box in caption_boxes:
                if _intersects(bbox, prior_box):
                    raise ValueError(f"Captions overlap: {prior_id}, {eid}")
            if (placement or "primary") in endpoint_labels[eid]:
                raise ValueError(f"Duplicate route caption: {eid} ({placement or 'primary'})")
            own_gap = _route_gap(bbox, route_segments[eid])
            if not 3 <= own_gap <= MAX_CAPTION_GAP:
                raise ValueError(f"Caption is not adjacent to its own route: {eid} ({own_gap:.1f})")
            for other_id, segments in route_segments.items():
                if other_id != eid and _route_gap(bbox, segments) < own_gap + MIN_ROUTE_ADVANTAGE:
                    raise ValueError(f"Caption ambiguous between {eid} and {other_id}")
            length = sum(math.hypot(X-x, Y-y) for x,y,X,Y in route_segments[eid])
            if length >= LONG_ROUTE_LENGTH and not eid.startswith("st") and not eid.endswith("-cl05"):
                progress = _route_progress(bbox, route_segments[eid])
                if (placement == "arrival" and progress < .59) or (placement != "arrival" and progress > .41):
                    raise ValueError(f"Long route caption is at the wrong end: {eid}")
                if placement != "arrival" and to_id not in "".join(label.itertext()):
                    raise ValueError(f"Long departure caption lacks destination ID: {eid}")
            endpoint_labels[eid].add(placement or "primary")
            caption_boxes.append((eid, bbox))
            if not placement:
                captions[eid] = label
    if len(captions) < 75 or arrivals < 30:
        raise ValueError("Lost primary or bidirectional route annotations")

    # Long routes have a forward caption and reverse arrival, except the
    # common START intake and the explicitly source-labelled CL05 collector.
    for eid, segments in route_segments.items():
        length = sum(math.hypot(X-x, Y-y) for x,y,X,Y in segments)
        if length >= LONG_ROUTE_LENGTH and not eid.startswith("st") and not eid.endswith("-cl05"):
            kinds = endpoint_labels[eid]
            if "arrival" not in kinds or not ({"primary", "departure"} & kinds):
                raise ValueError(f"Long route lacks bidirectional labels: {eid}")
    tr02, tr03, rv10 = (node_boxes[n] for n in ("TR02", "TR03", "RV10"))
    if abs(tr02[1]-tr03[1]) > 1 or tr02[2] >= rv10[0] + (rv10[2]-rv10[0])/2:
        raise ValueError("TR02 must sit left of RV10, aligned with TR03")
    for eid, segments in route_segments.items():
        if "tr02" not in eid and _route_gap(tr02, segments) < 1:
            raise ValueError(f"Unrelated route crosses TR02: {eid}")

    # The short SP02 routes are in the middle of their usable vertical legs,
    # rather than clipped to the issue-record decision diamond.
    for eid in ("sp02-sp03", "sp02-sp04"):
        label = captions.get(eid)
        if label is None:
            raise ValueError(f"Missing issue decision caption: {eid}")
        path = next(p for p in drawn_edges[eid].iter(Q("path"))
                    if "connection" in p.get("class", "").split())
        nums = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", path.get("d"))]
        middle = (nums[1] + nums[3]) / 2
        if abs(float(label.get("y")) - middle) > 42:
            raise ValueError(f"Short route caption should be near midpoint: {eid}")
    # All PL05 decisions should clear the source diamond, including abandon.
    diamond = node_boxes["PL05"]
    for eid, label in captions.items():
        if eid.startswith("pl05-") and _intersects(_caption_bounds(label),
                                                   (diamond[0]-12, diamond[1]-12,
                                                    diamond[2]+12, diamond[3]+12)):
            raise ValueError(f"PL05 outcome is on the decision: {eid}")

    # All nine CL05 routes are distinct in the semantic model, but converge
    # graphically into one clearly arrowed bus. Each feeder has its own
    # arrowhead and a distinct clickable source badge below the collector.
    incoming = {e["from"] for e in edges.values() if e["to"] == "CL05"}
    merged = {e.get("data-from") for e in drawn_edges.values()
              if e.get("data-merged-into") == "cl05-collector"}
    if merged != incoming or len(incoming) != 9:
        raise ValueError("CL05 collector feeder inventory mismatch")
    collector = next((g for g in root.iter(Q("g")) if g.get("id") == "cl05-collector"), None)
    if collector is None or collector.get("data-route-collector") != "CL05":
        raise ValueError("CL05 collector missing")
    trunk = collector.find(Q("path"))
    if trunk is None or not trunk.get("marker-end") or not trunk.get("d"):
        raise ValueError("CL05 collector has no directional trunk")
    badge_sources = set()
    for anchor in collector.iter(Q("a")):
        href = anchor.get("href", "")
        if not href.startswith("#node-"):
            raise ValueError("CL05 collector badge missing reverse link")
        badge = href[6:].upper()
        if badge in badge_sources or badge not in incoming or anchor.find(Q("text")) is None:
            raise ValueError("Duplicated or invalid CL05 source badge")
        if (anchor.find(Q("text")).text or "").strip() != badge:
            raise ValueError("CL05 badge label not aligned with its source")
        badge_sources.add(badge)
    if badge_sources != incoming:
        raise ValueError("CL05 collector labels do not cover incoming routes")
    for source in incoming:
        route = drawn_edges[source.lower() + "-cl05"]
        path = next(p for p in route.iter(Q("path")) if "connection" in p.get("class", "").split())
        if not re.search(r"\s8790$", path.get("d", "")):
            raise ValueError(f"CL05 feeder misses common collector: {source}")

def _check_crossing_bridges(root: ET.Element, drawn: dict, drawn_edges: dict) -> None:
    """Ensure decorative line jumps describe real crossings, not semantic junctions."""
    overlay = next((g for g in root.iter(Q("g"))
                    if g.get("id") == "workflow-crossing-bridges"), None)
    if overlay is None or overlay.get("pointer-events") != "none":
        raise ValueError("Missing non-interactive crossing bridge overlay")
    bridges = list(overlay.findall(Q("g")))
    if not 40 <= len(bridges) <= 124:
        raise ValueError("Unexpected crossing bridge inventory")
    node_boxes = [_bounds(node) for node in drawn.values()]
    label_boxes = [_caption_bounds(el) for el in root.iter(Q("text"))
                   if el.get("data-from") and el.get("data-to")]
    seen = []
    route_segments = {key: _route_segments(group) for key, group in drawn_edges.items()}

    for bridge in bridges:
        ids = bridge.get("data-crossing-between", "").split()
        over = bridge.get("data-over-route")
        if len(ids) != 2 or ids[0] == ids[1] or any(x not in drawn_edges for x in ids) or over not in ids:
            raise ValueError("Crossing bridge has invalid route ownership")
        circle, stroke = bridge.find(Q("circle")), bridge.find(Q("path"))
        if circle is None or stroke is None or bridge.find(Q("a")) is not None:
            raise ValueError("Crossing bridge lacks decorative geometry")
        x, y = float(circle.get("cx")), float(circle.get("cy"))
        if not (8 <= float(circle.get("r", "0")) <= 12):
            raise ValueError("Crossing bridge gap is oversized")
        if any(math.dist((x, y), pt) < 20 for pt in seen):
            raise ValueError("Crossing bridges overlap")
        seen.append((x, y))
        point_box = (x, y, x + .01, y + .01)
        for eid in ids:
            if _route_gap(point_box, route_segments[eid]) > 2:
                raise ValueError("Crossing bridge is not on both assigned routes")
        over_path = next(p for p in drawn_edges[over].iter(Q("path"))
                         if "connection" in p.get("class", "").split())
        if stroke.get("stroke") != over_path.get("stroke"):
            raise ValueError("Crossing bridge is not colored like its foreground route")
        if not stroke.get("d", "").startswith("M ") or stroke.get("class") == "connection":
            raise ValueError("Crossing bridge must not replace a process connector")
        if any(_segment_gap(box, (x, y, x, y)) < 22 for box in node_boxes + label_boxes):
            raise ValueError("Crossing bridge encroaches on a node or label")


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

    _check_route_readability(root, drawn, edges, drawn_edges)
    _check_crossing_bridges(root, drawn, drawn_edges)

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
