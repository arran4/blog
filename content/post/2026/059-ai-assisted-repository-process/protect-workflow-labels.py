#!/usr/bin/env python3
"""Keep every D2 connector caption readable in the exported workflow SVG.

D2/ELK places regular edge captions well but its SVG painter draws some later
routes over earlier captions. Put labels above the connector layer, give them
small opaque white backing plates, and reject label-to-label/node collisions.
The labels, nodes and routes remain authored in the canonical workflow.d2.
"""

from __future__ import annotations

import argparse
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
OVERLAY_ID = "workflow-edge-label-overlay"


@dataclass(frozen=True)
class Bounds:
    left: float
    top: float
    right: float
    bottom: float

    def intersects(self, other: "Bounds") -> bool:
        return (min(self.right, other.right) > max(self.left, other.left)
                and min(self.bottom, other.bottom) > max(self.top, other.top))


def node_bounds(group: ET.Element) -> Bounds:
    shape = next((el for el in group if el.tag == Q("g")
                  and "shape" in el.get("class", "").split()), None)
    if shape is None or len(shape) != 1:
        raise ValueError(f"Unsupported D2 shape for {group.get('data-workflow-node')}")
    el = shape[0]
    a = {k: float(v) for k, v in el.attrib.items()
         if k in {"x", "y", "width", "height", "cx", "cy", "rx", "ry", "r"}}
    if el.tag == Q("rect"):
        return Bounds(a["x"], a["y"], a["x"] + a["width"], a["y"] + a["height"])
    if el.tag in (Q("ellipse"), Q("circle")):
        rx, ry = a.get("rx", a.get("r")), a.get("ry", a.get("r"))
        return Bounds(a["cx"] - rx, a["cy"] - ry, a["cx"] + rx, a["cy"] + ry)
    if el.tag == Q("path"):
        coords = [float(v) for v in NUM.findall(el.get("d", ""))]
        if not coords or len(coords) % 2:
            raise ValueError("Cannot calculate D2 path bounds")
        return Bounds(min(coords[::2]), min(coords[1::2]),
                      max(coords[::2]), max(coords[1::2]))
    raise ValueError(f"Unsupported SVG shape {el.tag}")


def label_bounds(text: ET.Element) -> Bounds:
    try:
        x, y = float(text.get("x", "")), float(text.get("y", ""))
        size = float(FONT.search(text.get("style", "")).group(1))
    except (AttributeError, ValueError) as exc:
        raise ValueError("Unpositioned SVG connector caption") from exc
    if text.get("text-anchor") == "start":
        anchor = "start"
    else:
        anchor = "middle"  # D2 text-anchor is normally encoded in CSS.
    caption = "".join(text.itertext())
    if not caption.strip():
        raise ValueError("Blank SVG connector caption")
    # D2's label font is monospace italic. 0.70em is an intentionally
    # conservative advance (the rendered font is about 0.60em per glyph).
    # Also reserve generous padding for the white backing rectangle.
    width = size * 0.70 * len(caption) + 14.0
    left = x if anchor == "start" else x - width / 2.0
    return Bounds(left, y - size * 1.0 - 6.0,
                  left + width, y + size * 0.30 + 6.0)


def protect(svg_data: bytes) -> tuple[bytes, int]:
    root = ET.fromstring(svg_data)
    if root.find(f".//{Q('g')}[@id='{OVERLAY_ID}']") is not None:
        raise ValueError("SVG connector captions already protected")
    overlay = ET.Element(Q("g"), {"id": OVERLAY_ID,
                                  "aria-label": "Legible connector labels"})
    nodes: list[tuple[str, Bounds]] = []
    for group in root.iter(Q("g")):
        node_id = group.get("data-workflow-node")
        if node_id is not None:
            nodes.append((node_id, node_bounds(group)))
    if len(nodes) < 75:
        raise ValueError(f"Expected all workflow node outlines; found {len(nodes)}")

    captions: list[tuple[str, Bounds]] = []
    for group in root.iter(Q("g")):
        if not any(child.tag == Q("path") and
                   "connection" in child.get("class", "").split()
                   for child in group):
            continue
        texts = [child for child in group if child.tag == Q("text")]
        for element in texts:
            bounds = label_bounds(element)
            caption = "".join(element.itertext())
            captions.append((caption, bounds))
            for other, other_bounds in captions[:-1]:
                if bounds.intersects(other_bounds):
                    raise ValueError(f"Overlapping connector labels: {other!r} / {caption!r}")
            for node_id, node_box in nodes:
                if bounds.intersects(node_box):
                    raise ValueError(f"Connector label {caption!r} overlaps node {node_id}")
            group.remove(element)
            # Backing plates hide *all* intersecting connector strokes,
            # including later edges; labels paint last, above every route.
            ET.SubElement(overlay, Q("rect"), {
                "x": f"{bounds.left:.2f}", "y": f"{bounds.top:.2f}",
                "width": f"{bounds.right - bounds.left:.2f}",
                "height": f"{bounds.bottom - bounds.top:.2f}",
                "rx": "4", "fill": "#FFFFFF",
                "class": "connector-label-backing",
                "pointer-events": "none",
            })
            overlay.append(element)

    if len(captions) < 70:
        raise ValueError(f"Too few D2 edge labels; found {len(captions)}")
    if not captions:
        raise ValueError("No connector captions to protect")
    root.append(overlay)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True), len(captions)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, default=Path("workflow.svg"))
    args = parser.parse_args()
    rendered, count = protect(args.svg.read_bytes())
    args.svg.write_bytes(rendered)
    print(f"Protected {count} connector captions; no label/label or label/node overlaps")


if __name__ == "__main__":
    main()
