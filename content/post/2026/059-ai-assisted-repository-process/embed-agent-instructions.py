#!/usr/bin/env python3
"""Attach inert SVG descriptions to D2 nodes, using the blog's node catalogue."""

from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
NODE_SOURCE = re.compile(r"^([A-Z]{2}\d{2}): ", re.MULTILINE)
HEADING = re.compile(
    r"^#### ([A-Z]{2}\d{2}) — (.+?) \{#node-([a-z]{2}\d{2})\}[ \t]*$",
    re.MULTILINE,
)
LINKED_GROUP = re.compile(
    r'(?P<open><a\b(?=[^>]*\bhref="\./#node-(?P<id>[a-z]{2}\d{2})")[^>]*>\s*<g\b[^>]*)(?P<close>>)'
)
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
METADATA_ID = "agent-workflow-instructions-v1"


def section(markdown: str, heading: str) -> str:
    match = re.search(rf"(?m)^## {re.escape(heading)}[ \t]*$", markdown)
    if not match:
        raise ValueError(f"Missing article section: {heading}")
    remainder = markdown[match.end():]
    next_heading = re.search(r"(?m)^## ", remainder)
    return remainder[:next_heading.start() if next_heading else None].strip()


def catalogue(markdown: str, d2: str) -> dict[str, dict[str, str]]:
    ids = NODE_SOURCE.findall(d2)
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("No D2 nodes or duplicated D2 IDs")
    docs: dict[str, dict[str, str]] = {}
    for match in HEADING.finditer(markdown):
        node_id, title, anchor = match.groups()
        if node_id.lower() != anchor:
            raise ValueError(f"Mismatched article anchor: {node_id}")
        tail = markdown[match.end():]
        stop = re.search(r"(?m)^#{2,4} ", tail)
        instructions = tail[:stop.start() if stop else None].strip()
        if node_id in docs or not all(
            token in instructions for token in ("**Actor:**", "**Enter from:**", "**Move to:**")
        ):
            raise ValueError(f"Duplicate or incomplete article instructions: {node_id}")
        docs[node_id] = {"title": title.strip(), "instructions": instructions}
    if set(ids) != set(docs):
        raise ValueError(
            f"D2/article mismatch: missing={sorted(set(ids)-set(docs))}; "
            f"extra={sorted(set(docs)-set(ids))}"
        )
    return docs


def readable_instructions(node_id: str, doc: dict[str, str]) -> str:
    plain = MARKDOWN_LINK.sub(r"\1", doc["instructions"])
    plain = plain.replace("**", "").replace(chr(96), "")
    return f"{node_id} — {doc['title']}\n{plain}"


def embed(svg: str, markdown: str, d2: str) -> str:
    docs = catalogue(markdown, d2)
    guidance = section(markdown, "Instructions to a fresh management LLM")
    if METADATA_ID in svg or 'data-workflow-node="' in svg:
        raise ValueError("SVG already annotated; regenerate a clean SVG from D2 first")
    seen: list[str] = []

    def annotate(match: re.Match[str]) -> str:
        node_id = match.group("id").upper()
        if node_id not in docs:
            raise ValueError(f"Unrecognized SVG node {node_id}")
        seen.append(node_id)
        desc = html.escape(readable_instructions(node_id, docs[node_id]), quote=False)
        return (
            match.group("open")
            + f' data-workflow-node="{node_id}"'
            + match.group("close")
            + f'<desc id="agent-node-{node_id.lower()}" xml:lang="en">{desc}</desc>'
        )

    svg = LINKED_GROUP.sub(annotate, svg)
    if len(seen) != len(docs) or len(set(seen)) != len(seen) or set(seen) != set(docs):
        raise ValueError(f"Node link mismatch; expected {len(docs)}, found {len(seen)}")
    payload = {
        "schema": "agent-workflow-node-guidance/v1",
        "source": "index.md",
        "diagram_source": "workflow.d2",
        "management_instructions": guidance,
        "nodes": docs,
    }
    encoded = html.escape(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        quote=False,
    )
    root_match = re.search(r"<svg\b[^>]*>", svg)
    if root_match is None:
        raise ValueError("Not an SVG document")
    metadata = (
        f'<metadata id="{METADATA_ID}" data-format="application/json">'
        f"{encoded}</metadata>"
    )
    svg = svg[:root_match.end()] + metadata + svg[root_match.end():]

    root = ET.fromstring(svg)
    md_element = root.find(f"{{{SVG_NS}}}metadata")
    if md_element is None or md_element.get("id") != METADATA_ID:
        raise ValueError("SVG metadata was not injected at the root")
    parsed = json.loads(md_element.text or "")
    if set(parsed["nodes"]) != set(docs):
        raise ValueError("JSON node catalogue mismatch")
    for node_id in docs:
        group = next(
            (
                g for g in root.iter(f"{{{SVG_NS}}}g")
                if g.get("data-workflow-node") == node_id
            ),
            None,
        )
        if group is None:
            raise ValueError(f"Missing node graphics group: {node_id}")
        desc = group.find(f"{{{SVG_NS}}}desc")
        if desc is None or desc.get("id") != f"agent-node-{node_id.lower()}":
            raise ValueError(f"Missing node-local description: {node_id}")
        if not (desc.text or "").startswith(f"{node_id} — "):
            raise ValueError(f"Truncated node-local description: {node_id}")
    return svg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--svg", type=Path, default=Path("workflow.svg"))
    parser.add_argument("--article", type=Path, default=Path("index.md"))
    parser.add_argument("--d2", type=Path, default=Path("workflow.d2"))
    args = parser.parse_args()
    result = embed(
        args.svg.read_text(encoding="utf-8"),
        args.article.read_text(encoding="utf-8"),
        args.d2.read_text(encoding="utf-8"),
    )
    args.svg.write_text(result, encoding="utf-8")
    print(f"Embedded guidance in {len(NODE_SOURCE.findall(args.d2.read_text(encoding='utf-8')))} SVG nodes")


if __name__ == "__main__":
    main()
