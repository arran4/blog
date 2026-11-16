#!/usr/bin/env python3
"""Organize generated workflow SVG source by process meaning, without moving art.

This pass runs after D2/ELK, guidance embedding and connector-label placement.
It preserves existing paint order, paths, positions, styles, text glyph content
and links. It adds XML whitespace, process-section comments and route metadata.
When the native SVG replaces D2, keep its semantic formatting contract.
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
XML = "http://www.w3.org/XML/1998/namespace"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)
Q = lambda name: f"{{{SVG}}}{name}"

NODE = re.compile(r'^\s*([A-Z]{2}\d{2}): "')
EDGE = re.compile(r'^\((?:start\.)?([A-Z]{2}\d{2}) -> ([A-Z]{2}\d{2})\)\[(\d+)\]$')
D2_EDGE = re.compile(r'^((?:start\.)?[A-Z]{2}\d{2}) -> ([A-Z]{2}\d{2}): \{', re.M)
PHASE = re.compile(r'^# Phase: (\S+)', re.M)
PREFIX = "WORKFLOW: "
# Never introduce XML indentation *inside* visible SVG text / tspans or
# authored CSS, titles, descriptions and JSON metadata.
TEXT_CONTENT = {Q(x) for x in ("text", "tspan", "textPath", "style", "title",
                               "desc", "metadata")}
PHASE_TITLES = {
    "start": "START HERE: six entry choices",
    "intake": "Intake, current state and conversation handoff",
    "debug": "Bug reproduction, diagnosis and regression",
    "spec": "Planning, specification and issue approval",
    "tree": "PR dependencies, work selection and dogfooding",
    "execution": "Implementation and coding-agent handoff",
    "review": "PR, CI and human/automated verification",
    "close": "Closeout, Projects reconciliation and exceptional exits",
    "release": "Publication and release decisions",
    "end": "Completed, deferred or abandoned",
}


def phase_inventory(d2: str) -> tuple[dict[str, str], set[tuple[str, str]]]:
    phases: dict[str, str] = {}
    phase = None
    for line in d2.splitlines():
        match = PHASE.match(line)
        if match:
            phase = match.group(1)
            continue
        node = NODE.match(line)
        if node and phase:
            if node.group(1) in phases:
                raise ValueError(f"Repeated D2 node {node.group(1)}")
            phases[node.group(1)] = phase
    expected = {(a.removeprefix("start."), b) for a, b in D2_EDGE.findall(d2)}
    if not phases or not expected:
        raise ValueError("D2 node/transition inventory missing")
    return phases, expected


def route(group: ET.Element) -> tuple[str, str] | None:
    if group.tag != Q("g"):
        return None
    klass = group.get("class", "").split()
    if not klass:
        return None
    try:
        original = base64.b64decode(klass[0], validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    match = EDGE.fullmatch(html.unescape(original))
    return (match.group(1), match.group(2)) if match else None


def node_inside(child: ET.Element) -> ET.Element | None:
    if child.tag == Q("g") and child.get("data-workflow-node"):
        return child
    if child.tag == Q("a"):
        return next((g for g in child.iter(Q("g"))
                     if g.get("data-workflow-node")), None)
    return None


def safe_comment(text: str) -> ET.Element:
    # XML comments must not contain "--" or end with "-".
    return ET.Comment(PREFIX + re.sub(r"-{2,}", "—", text).rstrip("-"))


def strip_generated_comments(root: ET.Element) -> None:
    for parent in root.iter():
        for child in list(parent):
            if child.tag is ET.Comment and (child.text or "").startswith(PREFIX):
                parent.remove(child)


def annotate(svg: ET.Element, phases: dict[str, str],
             edges: set[tuple[str, str]]) -> tuple[int, int]:
    diagram = next((child for child in svg if child.tag == Q("svg")
                    and "d2-svg" in child.get("class", "").split()), None)
    if diagram is None:
        raise ValueError("Expected D2 diagram sub-SVG")
    revised: list[ET.Element] = []
    found_nodes: set[str] = set()
    found_edges: set[tuple[str, str]] = set()
    current_phase = None
    in_edges = False
    for child in list(diagram):
        node = node_inside(child)
        edge = route(child)
        if node is not None:
            node_id = node.get("data-workflow-node")
            if node_id not in phases or node_id in found_nodes:
                raise ValueError(f"Missing or duplicate process node: {node_id}")
            phase = phases[node_id]
            if phase != current_phase:
                revised.append(safe_comment("PHASE / " + PHASE_TITLES.get(phase, phase)))
                current_phase = phase
            desc = next((c for c in node if c.tag == Q("desc")), None)
            title = (desc.text or "").splitlines()[0] if desc is not None else node_id
            revised.append(safe_comment("NODE / " + title.strip()))
            found_nodes.add(node_id)
        elif edge is not None:
            paths = [part for part in child
                     if part.tag == Q("path")
                     and "connection" in part.get("class", "").split()]
            if len(paths) != 1 or not paths[0].get("d", "").strip():
                raise ValueError(f"Transition has no complete path: {edge}")
            if not in_edges:
                revised.append(safe_comment("TRANSITIONS / complete directed route graph"))
                in_edges = True
            if edge not in edges or edge in found_edges:
                raise ValueError(f"Missing or duplicate process transition: {edge}")
            child.set("data-from", edge[0])
            child.set("data-to", edge[1])
            child.set("data-transition-id", f"{edge[0].lower()}-{edge[1].lower()}")
            revised.append(safe_comment("ROUTE / " + edge[0] + " -> " + edge[1]))
            found_edges.add(edge)
        elif child.tag == Q("g") and child.get("class", "") == "bGVnZW5k":
            revised.append(safe_comment("LEGEND / actors, shapes and routes"))
        elif child.tag == Q("g") and child.get("class", "") == "c3RhcnQ=":
            revised.append(safe_comment("START FRAME / entrypoint boundary"))
        revised.append(child)
    if found_nodes != set(phases):
        raise ValueError(f"Node inventory mismatch: missing {sorted(set(phases)-found_nodes)}")
    if found_edges != edges:
        raise ValueError(f"Transition inventory mismatch: missing {sorted(edges-found_edges)}")
    diagram[:] = revised
    return len(found_nodes), len(found_edges)


def indent_semantically(elem: ET.Element, level: int = 0) -> None:
    if elem.tag in TEXT_CONTENT or elem.get(f"{{{XML}}}space") == "preserve":
        return
    children = list(elem)
    if not children:
        return
    if elem.text is None or not elem.text.strip():
        elem.text = "\n" + "  " * (level + 1)
    for index, child in enumerate(children):
        indent_semantically(child, level + 1)
        if child.tail is None or not child.tail.strip():
            is_last = index == len(children) - 1
            major = (child.tag is ET.Comment
                     and any(t in (child.text or "") for t in
                             ("PHASE /", "TRANSITIONS /", "START FRAME /")))
            # A blank line separates semantic units; inner SVG markup remains
            # conventionally indented without affecting paint order.
            block = (elem.tag == Q("svg")
                     and (node_inside(child) is not None
                          or (child.tag == Q("g") and child.get("data-transition-id"))
                          or major))
            child.tail = ("\n\n" if block and not is_last else "\n") + (
                "  " * (level if is_last else level + 1))


def format_svg(svg_bytes: bytes, d2_source: str, *,
               min_nodes: int = 80, min_edges: int = 124) -> tuple[bytes, int, int]:
    parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
    root = ET.fromstring(svg_bytes, parser=parser)
    if root.tag != Q("svg"):
        raise ValueError("Not an SVG document")
    phases, edges = phase_inventory(d2_source)
    if len(phases) < min_nodes or len(edges) < min_edges:
        raise ValueError("Incomplete source graph")

    strip_generated_comments(root)
    metadata = next((child for child in root if child.tag == Q("metadata")
                     and child.get("id") == "agent-workflow-instructions-v1"), None)
    if metadata is None:
        raise ValueError("Missing management-LLM metadata")
    payload = json.loads(metadata.text or "")
    pretty = json.dumps(payload, ensure_ascii=False, indent=2)
    metadata.text = "\n" + "\n".join("    " + line for line in pretty.splitlines()) + "\n  "

    nodes, transitions = annotate(root, phases, edges)
    root[:] = ([safe_comment("MANAGEMENT INSTRUCTIONS / raw XML metadata"), metadata,
               safe_comment("PRESENTATION / phases, checkpoints and continuous arrows")]
               + [child for child in root if child is not metadata])
    # Repeated runs are stable. All comments and indentation are rebuilt.
    indent_semantically(root)
    return (ET.tostring(root, encoding="utf-8", xml_declaration=True),
            nodes, transitions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, default=Path("workflow.svg"))
    parser.add_argument("--d2", type=Path, default=Path("workflow.d2"))
    args = parser.parse_args()
    output, nodes, edges = format_svg(args.svg.read_bytes(),
                                     args.d2.read_text(encoding="utf-8"))
    args.svg.write_bytes(output)
    print(f"Semantically formatted SVG: {nodes} nodes, {edges} transitions")


if __name__ == "__main__":
    main()
