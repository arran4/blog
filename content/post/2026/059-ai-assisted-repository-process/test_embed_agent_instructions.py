#!/usr/bin/env python3
"""Regression tests for node-level guidance embedded in the generated SVG."""

import importlib.util
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

MODULE = Path(__file__).with_name("embed-agent-instructions.py")
spec = importlib.util.spec_from_file_location("svg_agent_guidance", MODULE)
guidance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guidance)

SVG = """<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink">
<a href="./#node-aa01" xlink:href="./#node-aa01"><g class="decision"><text>AA01</text><title>Existing tooltip</title></g></a>
<a href="./#node-bb02" xlink:href="./#node-bb02"><g class="action"><text>BB02</text></g></a>
</svg>"""
D2 = 'AA01: "Review?"\nBB02: "Done"\n'
ARTICLE = """## Instructions to a fresh management LLM

Check the evidence and obtain human consent before merging.

## Node catalogue

### Review

#### AA01 — Review? {#node-aa01}

**Actor:** Human or Chat LLM. **State:** Compare <risk> & evidence.

**Enter from:** [BB02 Done](#node-bb02).

**Move to:** [BB02 Done](#node-bb02) **when approved**.

#### BB02 — Done {#node-bb02}

**Actor:** GitHub / CI. **State:** Verify the result.

**Enter from:** [AA01 Review?](#node-aa01).

**Move to:** Terminal state; no outgoing edges.

## Notes

Other prose should not be included in a node's instructions.
"""
NS = "{http://www.w3.org/2000/svg}"


class EmbeddingTests(unittest.TestCase):
    def test_embeds_node_local_descriptions_and_machine_readable_metadata(self):
        output = guidance.embed(SVG, ARTICLE, D2)
        root = ET.fromstring(output)
        metadata = root.find(f"{NS}metadata")
        self.assertEqual(metadata.get("id"), "agent-workflow-instructions-v1")
        payload = json.loads(metadata.text)
        self.assertEqual(set(payload["nodes"]), {"AA01", "BB02"})
        self.assertIn("human consent", payload["management_instructions"])
        self.assertIn("**Move to:**", payload["nodes"]["AA01"]["instructions"])
        decisions = [
            g for g in root.iter(f"{NS}g")
            if g.get("data-workflow-node") == "AA01"
        ]
        self.assertEqual(len(decisions), 1)
        desc = decisions[0].find(f"{NS}desc")
        self.assertIn("risk", desc.text)
        self.assertIn("& evidence", desc.text)
        self.assertIn("when approved", desc.text)
        self.assertNotIn("Other prose should not", desc.text)
        self.assertIsNotNone(decisions[0].find(f"{NS}title"))
        self.assertEqual(len(list(root.iter(f"{NS}a"))), 2)
        self.assertNotIn("<script", output)

    def test_missing_catalogue_entry_fails(self):
        with self.assertRaisesRegex(ValueError, "mismatch"):
            guidance.embed(SVG, ARTICLE.replace("#### BB02 — Done", "#### CC02 — Done"), D2)

    def test_svg_with_missing_link_fails(self):
        with self.assertRaisesRegex(ValueError, "Node link mismatch"):
            guidance.embed(SVG.replace('href="./#node-bb02"', 'href="./#not-a-node"'), ARTICLE, D2)

    def test_duplicate_injection_fails_instead_of_corrupting_svg(self):
        once = guidance.embed(SVG, ARTICLE, D2)
        with self.assertRaisesRegex(ValueError, "already annotated"):
            guidance.embed(once, ARTICLE, D2)


if __name__ == "__main__":
    unittest.main()
