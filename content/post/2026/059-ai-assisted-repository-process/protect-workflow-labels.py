#!/usr/bin/env python3
"""Stagger decision-edge captions close to their source, without breaking lines.

D2's source-end labels overlap when several outgoing routes share a decision.
Move only those decision labels a short, variable distance from the source
node; keep other D2 labels in place. Check all captions against every workflow
node and each other. Text gets a subtle glyph-only halo, not a white rectangle:
connector paths are never cut, shortened or repainted.
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)
Q = lambda name: f"{{{SVG}}}{name}"
FONT = re.compile(r"font-size:\s*([\d.]+)px")
NUM = re.compile(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")
EDGE = re.compile(r"^\(([A-Z]{2}\d{2}) -> ([A-Z]{2}\d{2})\)\[\d+\]$")
OVERLAY_ID = "workflow-edge-label-overlay"
# Every offset is in SVG units. Branch labels should be next to the diamond,
# not centered somewhere on a long backtracking connector.
VERTICAL_STAGGER = (0, 16, 32, 48, 64, 80)
HORIZONTAL_STAGGER = (0, 16, 32, 48, 64, 88)


@dataclass(frozen=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    def intersects(self, other: "Bounds") -> bool:
        return (min(self.right, other.right) > max(self.left, other.left)
                and min(self.bottom, other.bottom) > max(self.top, other.top))


def node_shape(group: ET.Element) -> ET.Element:
    container = next((el for el in group if el.tag == Q("g")
                      and "shape" in el.get("class", "").split()), None)
    if container is None or len(container) != 1:
        raise ValueError(f"Unrecognized node shape: {group.get('data-workflow-node')}")
    return container[0]


def node_bounds(shape: ET.Element) -> Bounds:
    a = {k: float(v) for k, v in shape.attrib.items()
         if k in {"x", "y", "width", "height", "cx", "cy", "rx", "ry", "r"}}
    if shape.tag == Q("rect"):
        return Bounds(a["x"], a["y"], a["x"] + a["width"], a["y"] + a["height"])
    if shape.tag in (Q("ellipse"), Q("circle")):
        rx, ry = a.get("rx", a.get("r")), a.get("ry", a.get("r"))
        return Bounds(a["cx"] - rx, a["cy"] - ry, a["cx"] + rx, a["cy"] + ry)
    if shape.tag == Q("path"):
        coords = [float(v) for v in NUM.findall(shape.get("d", ""))]
        if not coords or len(coords) % 2:
            raise ValueError("Cannot calculate D2 node path bounds")
        return Bounds(min(coords[::2]), min(coords[1::2]),
                      max(coords[::2]), max(coords[1::2]))
    raise ValueError(f"Unsupported SVG shape {shape.tag}")


def label_bounds(text: ET.Element, x: float | None = None,
                 y: float | None = None) -> Bounds:
    try:
        x = float(text.get("x", "")) if x is None else x
        y = float(text.get("y", "")) if y is None else y
        size = float(FONT.search(text.get("style", "")).group(1))
    except (AttributeError, ValueError) as exc:
        raise ValueError("Unpositioned SVG connector caption") from exc
    caption = "".join(text.itertext())
    if not caption.strip():
        raise ValueError("Blank SVG connector caption")
    # A deliberately conservative estimate for D2's monospaced italic labels,
    # including the small two-pixel glyph outline. No white backing plate.
    width = size * 0.70 * len(caption) + 12.0
    left = x if "text-anchor:start" in text.get("style", "") else x - width / 2.0
    return Bounds(left, y - size - 6.0, left + width, y + size * 0.30 + 6.0)


def edge_identity(group: ET.Element) -> tuple[str, str] | None:
    cls = group.get("class", "").split()
    if not cls:
        return None
    try:
        key = html.unescape(base64.b64decode(cls[0], validate=True).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    match = EDGE.fullmatch(key)
    return (match.group(1), match.group(2)) if match else None


def path_origin(path: ET.Element) -> tuple[float, float, int]:
    coords = [float(v) for v in NUM.findall(path.get("d", ""))]
    if len(coords) < 4:
        raise ValueError("Cannot read connector starting direction")
    return coords[0], coords[1], -1 if coords[3] < coords[1] else 1


def choose_placement(element: ET.Element, x: float, y: float, direction: int,
                     node: Bounds, index: int, total: int,
                     occupied: list[Bounds], node_boxes: list[Bounds]
                     ) -> tuple[float, float, Bounds]:
    initial = label_bounds(element)
    width = initial.right - initial.left
    preferred_sides = (-1, 1) if index < total / 2 else (1, -1)
    choices: list[tuple[float, float, float, Bounds]] = []
    # Small stagger by outgoing-branch index, followed by adaptive increments
    # only where labels would otherwise touch each other or a node.
    for extra_y in VERTICAL_STAGGER:
        for side in preferred_sides:
            for extra_x in HORIZONTAL_STAGGER:
                px = x + side * (width / 2.0 + 14.0 + extra_x)
                py = ((node.bottom + 28.0 + (index % 3) * 14.0 + extra_y)
                      if direction >= 0
                      else (node.top - 10.0 - (index % 3) * 14.0 - extra_y))
                box = label_bounds(element, px, py)
                if any(box.intersects(n) for n in node_boxes):
                    continue
                if any(box.intersects(other) for other in occupied):
                    continue
                score = (extra_y * 2.0 + extra_x * 1.3
                         + (0.0 if side == preferred_sides[0] else 8.0))
                choices.append((score, px, py, box))
        if choices and min(choice[0] for choice in choices) < extra_y * 2:
            break
    if not choices:
        raise ValueError(f"No close, non-overlapping caption position at {x:.0f},{y:.0f}")
    _, px, py, box = min(choices, key=lambda c: c[0])
    return px, py, box


def protect(svg_data: bytes, min_labels: int = 70, min_nodes: int = 75
            ) -> tuple[bytes, int]:
    root = ET.fromstring(svg_data)
    if root.find(f".//{Q('g')}[@id='{OVERLAY_ID}']") is not None:
        raise ValueError("SVG connector captions already positioned")
    nodes: dict[str, tuple[Bounds, bool]] = {}
    for group in root.iter(Q("g")):
        node_id = group.get("data-workflow-node")
        if node_id is not None:
            shape = node_shape(group)
            nodes[node_id] = (node_bounds(shape), shape.tag == Q("path"))
    if len(nodes) < min_nodes:
        raise ValueError(f"Expected all workflow node outlines; found {len(nodes)}")
    node_boxes = [bounds for bounds, _ in nodes.values()]
    caption_groups: list[tuple[ET.Element, ET.Element, ET.Element,
                                tuple[str, str] | None]] = []
    for group in root.iter(Q("g")):
        path = next((child for child in group if child.tag == Q("path")
                     and "connection" in child.get("class", "").split()), None)
        if path is None:
            continue
        for element in (child for child in group if child.tag == Q("text")):
            caption_groups.append((group, element, path, edge_identity(group)))
    if len(caption_groups) < min_labels:
        raise ValueError(f"Expected at least {min_labels} connector captions; "
                         f"found {len(caption_groups)}")

    occupied: list[Bounds] = []
    decisions: dict[str, list[tuple[ET.Element, ET.Element, ET.Element]]] = {}
    static: list[tuple[ET.Element, ET.Element]] = []
    for group, element, path, edge in caption_groups:
        if edge and edge[0] in nodes and nodes[edge[0]][1]:
            decisions.setdefault(edge[0], []).append((group, element, path))
        else:
            static.append((group, element))
    for _, element in static:
        box = label_bounds(element)
        caption = "".join(element.itertext())
        if any(box.intersects(n) for n in node_boxes):
            raise ValueError(f"Connector caption {caption!r} overlaps a node")
        if any(box.intersects(other) for other in occupied):
            raise ValueError(f"Connector caption {caption!r} overlaps another label")
        occupied.append(box)

    moved = 0
    for source, routes in sorted(decisions.items()):
        node = nodes[source][0]
        routes.sort(key=lambda item: path_origin(item[2])[0])
        for index, (_, text, path) in enumerate(routes):
            x, y, direction = path_origin(path)
            px, py, box = choose_placement(text, x, y, direction, node,
                                           index, len(routes), occupied, node_boxes)
            text.set("x", f"{px:.2f}")
            text.set("y", f"{py:.2f}")
            occupied.append(box)
            moved += 1

    # Paint labels last, but preserve every connector path unchanged. Only a
    # tight outline around glyphs protects legibility at incidental crossings.
    overlay = ET.Element(Q("g"), {"id": OVERLAY_ID,
                                  "aria-label": "Staggered connector labels"})
    for group, element, _, _ in caption_groups:
        group.remove(element)
        style = element.get("style", "").rstrip(";")
        element.set("style", style
                    + ";paint-order:stroke fill;stroke:#ffffff;"
                    + "stroke-width:2px;stroke-linejoin:round")
        overlay.append(element)
    root.append(overlay)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), moved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, default=Path("workflow.svg"))
    args = parser.parse_args()
    rendered, moved = protect(args.svg.read_bytes())
    args.svg.write_bytes(rendered)
    print(f"Staggered {moved} decision captions near their nodes; "
          "no caption collisions or connector backing gaps")


if __name__ == "__main__":
    main()
