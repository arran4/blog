# Native SVG migration design — PR #283

**Decision:** Adopt **one authoritative, manually laid-out SVG** for both human and LLM consumption. Retain **every continuous, visible transition arrow** and add **internal links** to destination checkpoints. Replace D2 and ELK at cutover, not before semantic parity is proven.

**Status:** Design agreed; conversion not yet implemented. This document describes work on [PR #283](https://github.com/arran4/blog/pull/283), stacked on [PR #212](https://github.com/arran4/blog/pull/212). [PR #285](https://github.com/arran4/blog/pull/285) has overlapping changes and must be reconciled before merging. Do not autonomously merge this work.

## A. Why change the format?

The existing workflow has **80 documented process nodes**, **124 directed transitions**, **six START HERE entries**, and **three terminal outcomes**. The SVG already includes 80 node-level descriptions, but its root instructions still rely on the D2 file and the blog article. It is generated through D2/ELK, with separate embedding, label-moving and mask-processing steps.

Automatic layout and downstream SVG patching have repeatedly moved labels away from decisions, created competing overlaps and produced visual gaps. A native SVG lets us author and retain fixed geometry. The cost is that **we must maintain that geometry intentionally**; no new auto-layout engine should silently rearrange the document.

## B. Non-negotiable requirements

1. **One document and URL.** workflow.svg is sufficient to read and follow the process as raw XML. The article may explain it, but is not required for agents or navigation.
2. **All arrows remain.** A complete continuous line, terminating in an arrowhead, exists for *each* directed transition, including backtracking, cross-phase, defer and cancellation paths. Internal jump links are **additional** affordances, never substitutes for lines.
3. **Same state machine for human and LLM.** Condition text, checkpoints, permitted next nodes, roles, mandatory evidence and approval gates are represented once semantically. Human arrows/labels and machine traversal must agree.
4. **One editable source.** The SVG is the source for semantic content *and* visual geometry. No live D2/YAML/JSON sidecar becomes authoritative. Tooling may validate it or synchronize redundant labels **within the same file**, but not regenerate its layout.
5. **Static and portable.** No JavaScript, foreignObject, event handler, remote fonts/images/styles or network-dependent assets. It should work opened directly as an SVG document.
6. **Preserve process policy.** GitHub issues/PRs are the detailed evidence record; arran4/projects is the minimal cross-conversation handoff index. Human approvals are still required where specified. An SVG never grants an agent extra permissions.
7. **Stable node IDs and URLs.** Preserve identifiers such as WS03 and BG05 and the published workflow.svg path. Normal success stays near the bottom; exceptional ends may remain close to their triggering branch. Keep the six entry choices framed together and the legend separate.

## C. One-file authorship contract

### Semantic authority

Use one versioned JSON object as XML text under root SVG **metadata#workflow-model**. Proposed schema: **arran4-native-workflow/v1**.

| Model key | Required information |
| --- | --- |
| schema / workflowId / revision | Versioning and compatibility; not live PR status |
| entryPoints / terminalNodes | Exact entry and terminal node lists |
| nodes | ID-keyed nodes with kind (entry, action, decision, terminal), actor, visible title, short summary, full checkpoint instructions, expected evidence and human approval restrictions |
| transitions | Stable unique edge ID, from, to, short visible label, **full condition**, and type where needed (normal, backtrack, defer, cancel, etc.) |
| managementInstructions | Complete instructions for a fresh agent: assess current real-world stage, inspect current GitHub/Projects state, record evidence, obey human decisions, and continue only along justified edges |
| invariants | No dangling or unreachable nodes, approved actor restrictions, valid endings, appropriate branching/decision gates, and scenario-specific workflow rules |

The current article's detailed actor, **Enter from**, **Move to** and permission/evidence instructions must be migrated **without silently changing them**. For uncertain interpretations, record a migration question rather than invent a rule.

Do not embed a particular live PR state, private conversation contents or stale handoff status in the canonical process. Those are determined from live evidence while the process is followed.

### Visual authority

The SVG also contains manually positioned groups with fixed IDs and coordinates:

- One group per node: **id=node-ws03** and **data-node-id=WS03** (same for each node). Node groups contain visible shape/text and accessible title and desc.
- One group per transition: **id=transition-t-ws03-bg01**, **data-transition-id=t-ws03-bg01**, **data-from=WS03**, **data-to=BG01**.
- Every transition group contains a visible arrow path with explicit geometry and arrowhead; a short visible label where appropriate; and a same-document link **href=#node-bg01** on its label, optionally on the path as well.
- Detailed human-readable **title** and **desc** content stays beside its node for tooltips/accessibility. Their semantic wording is a **validated mirror** of the root JSON, not a second independent source.
- The original article is optional reading material. It must not claim to be the authoritative input to the final SVG.

**There is no XML magic that makes JSON and shapes stay synchronized.** Provide deterministic sync/check code. A sync command can regenerate only semantic mirrors (title/desc/text/IDs), not node coordinates, paths or manual routing. CI must reject mismatches rather than automatically committing a new layout.

### Representative XML contract

This is deliberately an **incomplete illustrative fragment**, not an imported replacement for the 80-node graph.

~~~xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16000 10000">
  <title>AI-assisted repository workflow</title>
  <desc>Follow arrows or jump to linked checkpoints.</desc>
  <metadata id="workflow-model" data-format="application/json">
    {
      "schema": "arran4-native-workflow/v1",
      "entryPoints": ["ST01", "ST02", "ST03", "ST04", "ST05", "ST06"],
      "terminalNodes": ["EN01", "EN02", "EN03"],
      "nodes": {
        "WS03": {
          "kind": "decision",
          "actor": "human-or-chat",
          "title": "Select discovery depth?",
          "instructions": "The full, previously approved WS03 instructions"
        }
      },
      "transitions": [
        {
          "id": "t-ws03-bg01",
          "from": "WS03",
          "to": "BG01",
          "label": "bug",
          "condition": "bug discovered"
        }
      ]
    }
  </metadata>
  <g id="node-ws03" data-node-id="WS03">
    <title>WS03 — Select discovery depth?</title>
    <desc>Synced human-readable checkpoint guidance</desc>
    <path d="M 100 100 L 300 40 L 500 100 L 300 160 Z"/>
    <text x="300" y="105">WS03 · Select discovery depth?</text>
  </g>
  <g id="transition-t-ws03-bg01"
     data-transition-id="t-ws03-bg01"
     data-from="WS03" data-to="BG01">
    <title>WS03 to BG01 — bug discovered</title>
    <path d="M 300 160 L 300 240 L 700 240"
          fill="none" marker-end="url(#arrowhead)"/>
    <a href="#node-bg01"><text x="380" y="225">bug → BG01</text></a>
  </g>
</svg>
~~~

The XML must be safely serialized (escape characters such as ampersands in JSON text as XML requires), preserve the SVG namespace and keep stable IDs. Fragment targets belong to node groups. The metadata schema itself is the authoritative meaning of each arrow; its **SVG path geometry must not be parsed to infer conditions**.

## D. Layout and navigation rules

### Fixed macro-layout

Place the main progression in intentionally spaced regions: start/intake, bug diagnosis, planning/specification, PR tree and execution, verification/review, release/close. Keep the sequence clearly readable across the page. A large artboard and comfortable zooming are acceptable. Use **dedicated perimeter gutters** for long feedback/cross-phase routes so they do not pass through unrelated text or diamonds.

Keep all 124 edges even where a different diagram design would prefer jump markers. Route long edges with deliberate orthogonal waypoints. Use consistent colour/dash/arrow styling to distinguish ordinary progression, rework and exceptional exits, but also provide text or tooltip descriptions so colour is never the only discriminator.

Decision labels belong close to the **originating decision**, not at an arbitrary midpoint of a long line. Stagger neighbouring labels gently when necessary. No white backing plates, cut-out masks, automatic caption relocation or hidden line segments. Label/line crossings should be minimized by routing, not post-render erasure. Preserve full route continuity and arrival arrowheads.

### Same-document navigation

Link each transition label to its **destination node** using a fragment URL (for example, **#node-bg01**). Where usable, make the arrow itself a clickable target, but avoid swallowing clicks on other nodes. A node may optionally include a "back to entry" or phase navigation link **within the same SVG**.

Browser support is a **verification item**: test the standalone file in Firefox and Chromium for clicking a fragment, useful framing/zoom and keyboard focus. If fragment navigation to groups does not focus them reliably, add static SVG view anchors (such as **#view-bg01**) with generated/viewBox-validated coordinates while retaining **node-bg01** as the stable semantic identity. No script dependency.

Opening an SVG using an HTML image element gives a **noninteractive image**; links do not work. The article should offer **Open full SVG** as a standalone document. See [MDN SVG linking](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/Linking) and [W3C SVG 2 fragment identifiers](https://www.w3.org/TR/SVG2/linking.html).

## E. How an LLM must consume the SVG

1. Retrieve **raw SVG XML** at the published SVG URL, not a GitHub blob HTML page, screenshot, or rasterized SVG.
2. Parse metadata#workflow-model and its schema; read managementInstructions.
3. Determine the real current checkpoint using the conversation and **live** repository, PR/issue and Projects state. Do not assume that a new conversation means the first node.
4. Read the node's actor, preconditions, evidence and human-only gates.
5. Evaluate only outgoing edges whose **from** equals that node, using their exact **condition** and current evidence.
6. If information is insufficient, or a human approval is required, seek the human decision or park. Never substitute a guessed transition.
7. Report current checkpoint, evidence, chosen permitted transition (if any), blocker and next checkpoint.

Embedded instructions are documentation, **not executable permissions**. A user or agent who can only view a raster image cannot be assumed to access metadata. Verify raw XML retrieval separately in each intended LLM client; if the client sanitizes or rasterizes SVG, supply the raw XML as text. The final SVG must not assume an article/D2 fallback exists.

## F. Validation and quality gates

| Test | Acceptance rule |
| --- | --- |
| XML / JSON | Well-formed SVG and valid complete versioned metadata, no duplicate IDs or unsupported model schema |
| Semantics | Every expected node, actor, condition, approval gate, entry/terminal meaning and edge equals the frozen PR #283 baseline unless a **separate semantic change** is approved |
| Graph | All nodes reachable from the six starts; valid terminal states; decision exits labeled; no dangling or missing transitions; mandatory human gates preserved |
| Graphics parity | Exactly one identifiable rendered node per model node; **exactly one continuous arrow per model transition** with matching ID/from/to; no invented visual routes |
| Navigation | Every link resolves to the same destination named in the transition; direct-open SVG fragments work in Firefox and Chromium; accessible title/desc exist |
| Geometry | No clipped/overlapping nodes, illegible decision captions or unacceptable label overlaps; arrows do not cut through node interiors; no cut-out/mask gaps |
| Security / portability | No script, event handlers, foreignObject, remote resources, unsafe hrefs or dependency on a sidecar; self-contained SVG renders offline |
| Publication | PNG derived from **validated committed SVG**, not a separate render of another source; original stable SVG/PNG URLs retained |
| LLM consumption | A raw-XML consumer, seeing no article or D2, correctly identifies the possible next transitions, evidence and required human approvals |

Geometry checks should include an **actual browser layout and screenshot**; simplistic character-width bounding estimates alone have previously produced misleading results. Automated checks do not replace a deliberate visual review of the full SVG and difficult crops.

### Required traversal examples

Cover planned change, reported bug/diagnosis/confirmation/regression, resuming a PR already at review without restarting planning, new-issue approval, PR forest dependencies with a blocked sibling, human UI verification after a PR, failed CI/hold, cancel/park, first-publication safety and release verification. An LLM passes only when its checkpoint/edge/permission decisions are correct against evidence, not when it merely summarizes the SVG.

## G. Migration order for PR #283

**M0: Freeze a baseline.** Extract the complete 80-node/124-edge inventory and existing node guidance, actors and exact conditions from the current branch. Compare D2, SVG and article; record conflicts for explicit resolution. Do not start manual layout until parity is repeatable.

**M1: Self-contained SVG without redesign.** Put full semantic metadata in the existing SVG and introduce stable node/transition element IDs and internal links. Add a native-SVG parser, semantic validator and raw-XML consumer tests. The existing D2 file is only a temporary comparison source during this phase.

**M2: Native pilot layout.** Manually route the WS03 and BG05 sections and surrounding return lines, keeping every full arrow. Test label placement, route gutters and internal jumps in both browsers; ensure LLM metadata traversal is unaffected. Review these pilot crops before broad edits.

**M3: Complete the manual artboard.** Rework the other phases with stable geometry, explicit long-route corridors, readable labels and linked endpoints. Keep the baseline inventory and full-document geometry tests green at every commit. Preserve node IDs, 6 starts, 3 ends, normal completion at bottom and exceptional outcomes near their branches.

**M4: Cut over CI.** A replacement workflow (for example, **validate-native-svg.yml**) checks the authoritative SVG and renders **workflow.png** from that checked SVG. CI does **not** regenerate SVG layout, silently rewrite paths or install D2/Go. Require browser navigation tests, semantic traversal scenarios and visual review.

**M5: Retire D2.** Only after M0–M4 pass and visual acceptance is explicit: delete **workflow.d2**, D2/ELK installation, instruction-injection script and auto-caption-placement scripts. Replace D2-specific validators/tests with native-SVG checks. Update **index.md** to say the SVG is authoritative, not the article or D2, while retaining the article as optional explanation. Keep the same workflow.svg and workflow.png URLs.

### File disposition at completion

| Existing file | Target |
| --- | --- |
| workflow.svg | **Only authoritative process and geometry file** |
| workflow.png | Checked raster export from workflow.svg |
| workflow.d2 | Removed after parity verified |
| embed-agent-instructions.py | Retired; node guidance belongs inside the SVG |
| protect-workflow-labels.py | Retired; manual positions and routes instead |
| render-diagrams.sh | Retired or reduced to validated SVG-to-PNG export |
| validate-workflow.py | Replaced with native SVG semantic, link and geometry checks |
| test_embed_agent_instructions.py / test_protect_workflow_labels.py | Replaced by SVG contract/navigation/LLM scenario tests |
| .github/workflows/render-d2-process.yml | Replaced with native SVG validation workflow |
| index.md | Updated to refer to SVG as canonical; optional human-facing narrative/catalogue |

### Definition of ready for review

- [ ] Complete 80-node, 124-edge semantic and visible-geometry parity; no unapproved workflow changes.
- [ ] All six grouped entries, three distinct ends, human approval/CI/release gates and core regression scenarios preserved.
- [ ] Every arrow continuous and visible; long feedback paths still traceable; no masking or arbitrary gaps.
- [ ] Every internal destination link works in standalone Firefox/Chromium and agrees with the semantic edge.
- [ ] Raw XML is sufficient for an LLM to follow the **same process** with the same authority limits.
- [ ] Native SVG validator, navigation tests, browser screenshots and PNG export pass.
- [ ] D2 is no longer needed for any authoring/validation/publication step.
- [ ] Human visual signoff and #212/#285 coordination complete. PR remains draft until then.

## Rejected alternatives and unresolved verification

Do **not** split the required process across multiple SVGs, replace long arrows with jump-only navigation, maintain a second active semantic source, or reintroduce D2-specific masking and label offsets.

Outstanding technical validation is deliberately limited to browser handling of fragments/zoom and whether target LLM clients expose raw SVG XML. Those are empirical tests, **not** reasons to change the agreed single-SVG/all-arrows architecture.

References: [SVG linking](https://www.w3.org/TR/SVG2/linking.html), [SVG links in image vs document mode](https://developer.mozilla.org/en-US/docs/Web/SVG/Guides/Linking), [accessible desc](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/desc), [accessible title](https://developer.mozilla.org/en-US/docs/Web/SVG/Reference/Element/title).
