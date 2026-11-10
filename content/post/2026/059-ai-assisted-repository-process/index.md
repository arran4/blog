---
title: "AI-Assisted Repository Development: A Unified Process"
date: 2026-10-30T23:09:00+11:00
draft: false
guidance: ["agent-management"]
tags: ["agents", "automation", "chatgpt", "ci", "codex", "github", "orchestration", "workflow"]
categories: ["Software Development", "LLM Instructions", "Automation"]
---

<!-- cspell:words agy Codex dogfood handoff handoffs inspectable librsvg rsvg txtar workstream workstreams -->

My repository development process is neither a rigid waterfall nor a collection of independent coding-agent prompts. It starts from an idea, bug, change, maintenance event, existing pull request, or release request. I use a **Chat LLM as a management and review companion**, coding agents for repository work when appropriate, and GitHub to preserve the specification and implementation history.

**This is the current process reference.** It is designed for both human readers and a fresh Chat LLM that needs to determine where a workstream stands, what evidence is missing, what action it can take, and what to do next. The diagram is one canonical, editable workflow, not eleven competing views. It models decision points, alternative routes, revisiting earlier work, and explicit endings.

Normally I maintain **one conversation per coherent workstream**. That conversation can manage several related issues and a dependency tree of pull requests; other conversations can manage other projects or branches at the same time. Conversation is part of the working design discussion, while GitHub issues, PRs, commits and the supporting project repositories preserve durable decisions and observable outcomes.

## Main process diagram

![Unified AI-assisted repository workflow](workflow.svg)

[Open full SVG](workflow.svg) · [Open PNG export](workflow.png) · [Edit D2 source](workflow.d2) · [Browse node catalogue](#node-catalogue)

This is a large diagram intended to be opened and zoomed. The PNG export is an easier-to-read alternative in Firefox when the SVG automatically resizes. The diagram's node text has been enlarged to 26 points, with 21-point connection labels, so the PNG is more readable at full resolution. It is rasterised from the same D2-generated SVG using `rsvg-convert` at a width of 8,000 pixels, avoiding D2's raster frame-height limit for this unusually tall diagram. Each D2 node shows an **ID, a title and a short plain-language description directly in the shape**, along with its actor colour; its longer hover description and link to the corresponding article section remain available. The embedded image may not expose the links, so open the SVG itself or use the catalogue below. The `.d2` source is also suitable for a coding or management agent to read directly; do not rely on visual interpretation alone.

### Machine-readable agent instructions inside the SVG

The generated SVG is also an **agent-readable process reference**. In addition to the existing short hover tooltips, its SVG groups contain standard non-visible `<desc>` elements at the corresponding workflow nodes. For example, the graphics group associated with `WS03` contains the accepted actor, current-state instructions, entry paths and conditional transitions from [the WS03 catalogue entry](#node-ws03). This guidance is embedded **beside the node**, not merely in a global XML comment.

At the SVG document root, `<metadata id="agent-workflow-instructions-v1">` contains the **shared** management-LLM instructions, the original source paths, the number of nodes and the lookup rule `g[data-workflow-node] > desc`. It **does not repeat the node catalogue**. A parser locates `g[data-workflow-node="WS03"] > desc` to read WS03's instructions directly in their corresponding graphics group.

These elements are **inert documentation, not executable instructions**. The issue register, PRs, human approvals and live repository evidence still determine what an agent is authorised to do. Reading the SVG as an image (including the PNG or an HTML image tag) does not expose its hidden XML content; fetch or parse the raw SVG when machine-readable guidance is needed.

The article remains the **single editable source of truth**. `embed-agent-instructions.py` exports each node's instructions to exactly one SVG `<desc>` after D2 rendering, validates that every diagram node has a matching article section, then produces the PNG from that same SVG. The root metadata contains no duplicate node instructions. An exported, standalone SVG necessarily contains a generated copy of its source article's guidance; avoiding even that export copy would require fetching the article separately, losing standalone usability. This experimental step is isolated in a [stacked PR](https://github.com/arran4/blog/pulls) so it can be removed without affecting the normal D2 diagram.

### Diagram conventions

| Element | Meaning |
| --- | --- |
| **Circle** | Independent starting point; different starts may enter different phases |
| **Rectangle** | Activity, observable state or system action |
| **Diamond** | Decision with labelled conditional exits; not automatically an approval |
| **Oval** | Terminal outcome: completed, deferred/blocked or abandoned |
| Amber | **Human** — intent, interactive debugging, review, consequential decisions |
| Blue | **Chat LLM** — investigation, Q&A, prompts, specifications, PR management and review |
| Teal | **Human or Chat LLM** — either can make an ordinary routing/analysis decision when enough evidence exists |
| Violet | **Coding LLM** — Codex/Agy or another coding agent operating in a repository/container |
| Green | **GitHub / CI** — durable issues/PRs, checks, merges, releases and recorded final state |
| Solid blue connector | Normal progress |
| Solid green connector | Accepted, approved or completed transition |
| Dashed orange connector | Backtracking, correction or rework |
| Dashed grey connector | Deferred, pending or blocked |
| Solid red connector | Abandoned or cancelled |

The diagram includes a **large detached D2 legend** with actual example nodes for each actor, circle/rectangle/diamond/oval samples, and miniature arrows showing the exact five connector styles. The legend examples are visual documentation only, with no links to workflow nodes. Only the entry choices share a frame; the remaining phases use source comments and this catalogue rather than large whitespace-producing frames. Each node retains its stable ID and actor colour. **Shared responsibility does not imply shared approval authority:** a Chat LLM may classify complexity, select a repair path or recommend a release, but cannot make a human-owned merge, visibility, history-rewrite or release decision without the required approval.

Branching outcomes use short arrowhead labels: usually near the source, but near the destination for long edges and crowded decisions. Those longer labels include the destination node ID. Exact transition conditions remain in the node catalogue and D2 connection tooltips. The ELK layout does not guarantee precise label positions, and some crossings remain possible; edge colour and dash type distinguish long backtracking links.

## How to use this process

The framed **START HERE — CHOOSE ONE ENTRY POINT** area contains six circles ([ST01–ST06](#node-st01)). They are alternative starts, not six consecutive tasks. Every start goes through [WS01](#node-ws01) and [WS04](#node-ws04), so a conversation can register its supplied link with [arran4/projects](https://github.com/arran4/projects), inspect fresh GitHub state, and then branch into planning, debugging, existing-PR review or release. The start frame must remain visually together; the legend is a detached reference, not a process step.

**GitHub issues and pull requests hold the detailed requirements and implementation evidence.** Projects is a lightweight between-conversation coordination index: the conversation URL, owning repository/project, current milestone, next action, and an actual blocker or resumption trigger. Do not duplicate every issue, transcript, review finding or PR status into Projects. Read the current Projects record before editing it to avoid overwriting another conversation's newer checkpoint. Routine, low-risk Projects-only Markdown updates follow that repository's separate policy for short-lived, autonomously merged PRs; substantive changes still receive human review.

[WS05](#node-ws05) records a lightweight checkpoint when work is blocked or deliberately paused; [WS06](#node-ws06) updates that handoff following human-authorised abandonment. [CL03](#node-cl03) reconciles the Projects pointer when a chosen milestone completes. A break, multiple active conversations, or a blocked PR can therefore be resumed from the coordination record without treating it as another canonical issue tracker.

## Clarification, issues and branching PRs

For a large idea, [PL02](#node-pl02) asks questions and [PL03](#node-pl03) is now a real **decision**: if contradictions exist, [PL04](#node-pl04) resolves them and returns to questions; if none remain, [PL05](#node-pl05) decides whether enough is specified. The goal is sufficient acceptance criteria, not perfect upfront design. A material conflict discovered later returns to planning or issue reconciliation instead of merely patching a symptom.

[SP01–SP05](#node-sp01) preserve issue/PR specifications. Issue creation and major issue scope changes require the appropriate human decision; small, already-authorised issue updates may proceed routinely. A new repository follows [TR05](#node-tr05) bootstrap; an existing one proceeds without it. [TR02](#node-tr02) plans **dependent and independent sibling PRs** rather than forcing a single linear stack. [TR03](#node-tr03) selects an unblocked, runnable PR.

## Bug investigations, regression tests and diagnosis review

[BG02](#node-bg02) chooses **three distinct investigation routes**. Chat can investigate directly at [BG04](#node-bg04) and, if it has actual code/test access, later implement a [chat direct fix](#node-ex05). If an interactive debugger, UI or device is needed, chat writes a justified, reproducible [request for the human](#node-bg08), who performs [BG03](#node-bg03) and returns logs and observations. If a coding agent is more suitable, chat prepares an actionable [diagnostic prompt](#node-bg06), the coding agent investigates at [BG09](#node-bg09), and the findings return to [BG05](#node-bg05).

[BG05](#node-bg05) decides whether the diagnosis is supported. Missing evidence returns to reproduction; a design-level discovery goes back to planning; a supported cause proceeds to [BG07](#node-bg07), which defines the **regression proof** to add or update. That should include the smallest focused test where practical *and*, where appropriate, a larger end-to-end, `txtar`, integration or scenario test that demonstrates recognisable behaviour from the PR. The implementing actor actually writes and runs those tests at [EX03](#node-ex03) or [EX05](#node-ex05); merely promising a test is insufficient.

A generated PR does not prove that the initial bug analysis was right. After CI and code review, [RV11–RV14](#node-rv11) choose manual testing, automated proof, or an evidence-only route. The human can run a local build or UI and confirm the original failure is actually gone at [RV12](#node-rv12). When reliable automation is available, [RV13](#node-rv13) uses Playwright, screenshots, rendered prototypes, scenarios or other accessible test frameworks. Attach reproducible evidence to the PR or provide the preview in chat. Rejected results return to correction; the merge decision remains [human-owned](#node-rv08).

## Testable milestones, review and release gates

The previously unreachable [TR04](#node-tr04) is now entered **from both PR publication routes**, [EX04](#node-ex04) and [EX05](#node-ex05). It is a diamond deciding whether the current dogfood milestone needs additional testing; [TR06](#node-tr06) prepares that plan when appropriate. All published PRs still enter [RV01](#node-rv01) for real diff, issue, dependency and CI verification. CI that is missing, blocked by quota, or stale is never described as green. No PR merges without the applicable explicit human approval.

An ordinary process **rectangle has one outgoing continuation**; alternatives are diamonds. This also applies to issue approval, runnable-PR selection, CI classification and release verification. Long or backtracking lines use **destination node IDs** in their near-end annotations so a reader can follow them across the diagram. For crowded decisions, some labels sit near their destinations instead of obscuring the diamond.

At release time, [RL04](#node-rl04) performs the public-opening audit and [RL09](#node-rl09) decides whether that audit passed. [RL10](#node-rl10) checks the actual published assets and [RL08](#node-rl08) makes the final success/failure decision. Major failures can return to the relevant specification; missing consent or unresolved publication failures are parked with a resume trigger.

**Terminal layout rule:** the ordinary successful end [EN01](#node-en01) belongs at the end of the main path, toward the bottom. Exceptional [EN02](#node-en02) (deferred/blocked) and [EN03](#node-en03) (abandoned) may appear near their actual decision branches to avoid unnecessary long lines. This is an intention for D2 layout, not a claim that ELK can guarantee exact placement.

## Instructions to a fresh management LLM

Treat each node ID as a **checkpoint, not a rigid waterfall**. Start by reading the applicable GitHub issues/PRs, the latest linked conversation context and the **current Projects coordination file**. If the human supplies a conversation URL, use it as a resume pointer in Projects when appropriate; do not invent the URL. Keep canonical specifications and acceptance cases in GitHub issues/PRs. In Projects, record only the owning workstream, conversation link, milestone, blocker and next actionable handoff. Re-read current Projects `main` and overlapping relevant PRs before routine updates, and follow its own low-risk autonomous-merge policy rather than applying that policy to unrelated repositories.

At each node: identify the current actor; check real repo/CI state; follow the labelled conditions; ask for human consent on reserved decisions; create or update regression and scenario evidence; and verify that any claimed GitHub write actually occurred. Do not invent testing or merge results. If human UI/debugger help is needed, explain the reason, steps, expected output and exact question. If a coding agent is needed, provide a prompt with branch, issue, reproduction, evidence, tests and intended PR. If work is blocked or ends, update the Projects handoff without copying the entire issue register.

| Status field | Evidence to retain |
| --- | --- |
| Workstream | Repository, current aim, supplied conversation link and Projects pointer |
| Canonical specification | Issue/PR URLs, accepted decisions, prerequisites and acceptance tests |
| PR dependency tree | Current head, parent/child/sibling dependencies, tests and mergeable leaves |
| Diagnosis and proof | Actual reproduction, regression test, `txtar` or scenario, UI/automation evidence |
| Routing | Current node ID, condition, responsible human/Chat/coding actor |
| Handoff | Next concrete action, owner, obstacle and resumption trigger |
| Ending | Verified completed milestone, parked checkpoint or human-authorised abandonment |

## Example scenario runs to validate the diagram

These are proposed traces for human correction, not a statement that every historic task used them. Each refers to actual graph nodes and shows the relevant branching decision.

### Scenario A — Reproducible bug fixed directly by chat

[ST03](#node-st03) → [WS01](#node-ws01) → [WS04](#node-ws04) → [WS02](#node-ws02) → [WS03](#node-ws03) → [BG01](#node-bg01) → [BG02](#node-bg02) → [BG04](#node-bg04) → [BG05](#node-bg05) → [BG07](#node-bg07) → [SP01](#node-sp01). After requirements are accepted, [TR01](#node-tr01) chooses one PR, and [EX01](#node-ex01) chooses [EX05](#node-ex05), the **chat direct fix**. The PR passes [TR04](#node-tr04), [RV01](#node-rv01), review, and [RV11](#node-rv11) → [RV14](#node-rv14) before human merge approval. The regression test should actually fail before the fix and pass afterward when feasible.

**Check:** Does a tiny, verified chat fix need a new issue when an existing PR already records its scope?

### Scenario B — Interactive Flutter bug, mistaken first diagnosis

[ST03](#node-st03) → [WS01](#node-ws01) → [WS04](#node-ws04) → [WS02](#node-ws02) → [WS03](#node-ws03) → [BG01](#node-bg01) → [BG02](#node-bg02) → [BG08](#node-bg08) → [BG03](#node-bg03) → [BG05](#node-bg05). The human runs the requested debugger steps; if findings do not support the hypothesis, return to [BG01](#node-bg01). A confirmed cause is captured at [BG07](#node-bg07); a coding agent may investigate via [BG06](#node-bg06) → [BG09](#node-bg09). After a PR exists, [RV11](#node-rv11) → [RV12](#node-rv12) asks the human to verify the original UI fault. If still wrong, [RV14](#node-rv14) sends it back to [RV04](#node-rv04), possibly back to [PL01](#node-pl01) or [SP01](#node-sp01).

**Check:** Should human verification be repeated on every new PR head for this UI bug?

### Scenario C — Minor feature with automated UI proof

[ST02](#node-st02) → [WS01](#node-ws01) → [WS04](#node-ws04) → [WS02](#node-ws02) → [WS03](#node-ws03) → [SP01](#node-sp01) → [SP02](#node-sp02) → [SP04](#node-sp04) → [SP05](#node-sp05) → [TR01](#node-tr01) → [EX01](#node-ex01) → coding implementation → [TR04](#node-tr04) → [TR06](#node-tr06) → [RV01](#node-rv01). If the UI is testable through Playwright or a good preview framework, [RV11](#node-rv11) → [RV13](#node-rv13) gathers proof for the human to inspect.

**Check:** Which UI checks should still require a person to run the built application?

### Scenario D — Major change with a branching PR tree

[ST02](#node-st02) → [WS01](#node-ws01) → [WS04](#node-ws04) → [WS02](#node-ws02) → [WS03](#node-ws03) → [PL01](#node-pl01) → [PL02](#node-pl02) → [PL03](#node-pl03). If contradictory, visit [PL04](#node-pl04) and then ask again; otherwise [PL05](#node-pl05) → GitHub issue reconciliation → [TR01](#node-tr01) → [TR02](#node-tr02) → [TR03](#node-tr03). Each runnable sibling gets its own reviewed PR. [RV10](#node-rv10) either returns to [TR03](#node-tr03) or closes the milestone. On pause, [WS05](#node-ws05) records the conversation pointer, blocker and next action—not the entire PR forest.

**Check:** Is the chosen dogfood checkpoint explicit enough for dependent PRs?

### Scenario E — Paused dependency update

[ST04](#node-st04) → [WS01](#node-ws01) → [WS04](#node-ws04) → [WS02](#node-ws02) → [WS03](#node-ws03) → issue/PR update → implementation → [RV01](#node-rv01). If required CI is blocked, [RV02](#node-rv02) → [WS05](#node-ws05) → [EN02](#node-en02). Projects retains the conversation URL, GitHub PR link and actual resumption trigger; the technical CI diagnosis stays in GitHub.

**Check:** When CI is unavailable but not required, can trusted local `txtar` or scenario evidence satisfy the review policy?

### Scenario F — Initial release and public-opening audit

[ST01](#node-st01) → [WS01](#node-ws01) → [WS04](#node-ws04) → [WS02](#node-ws02) → [WS03](#node-ws03) → detailed planning → accepted specs → [SP05](#node-sp05) → [TR05](#node-tr05) → implementation and PR verification → closeout → [RL01](#node-rl01) → [RL02](#node-rl02) → [RL03](#node-rl03) → [RL04](#node-rl04) → [RL09](#node-rl09) → [RL05](#node-rl05) → [RL06](#node-rl06) → [RL07](#node-rl07) → [RL10](#node-rl10) → [RL08](#node-rl08) → [EN01](#node-en01).

**Check:** When does first public visibility need to occur relative to a private/test release?

## Node catalogue

Each step below is generated from the D2 node IDs and transitions for this revision. The visible shape gives the short action; this catalogue describes the actor, entry conditions and permitted next steps. A state with several outgoing transitions must be a diamond, not an unexplained process fork.

### Starting points — choose one

#### ST01 — Initial release {#node-st01}

**Actor:** Human. **Shape:** circle. **State:** Begin a new repository or initial release. A new project or first public version

**Enter from:** No incoming edge: choose this starting point from the entry frame.

**Move to:** [WS01 Open one workstream](#node-ws01) **when start**

#### ST02 — Planned change {#node-st02}

**Actor:** Human. **Shape:** circle. **State:** Request a feature or improvement. A feature or change of any size; classify scope later

**Enter from:** No incoming edge: choose this starting point from the entry frame.

**Move to:** [WS01 Open one workstream](#node-ws01) **when start**

#### ST03 — Bug or defect {#node-st03}

**Actor:** Human. **Shape:** circle. **State:** Report unexpected behaviour to be fixed. An observed failure, including interactive Flutter problems

**Enter from:** No incoming edge: choose this starting point from the entry frame.

**Move to:** [WS01 Open one workstream](#node-ws01) **when start**

#### ST04 — Maintenance {#node-st04}

**Actor:** Human. **Shape:** circle. **State:** Start dependency, tooling or audit upkeep. Manual or automated upkeep; also may be folded into another workstream

**Enter from:** No incoming edge: choose this starting point from the entry frame.

**Move to:** [WS01 Open one workstream](#node-ws01) **when start**

#### ST05 — Existing work {#node-st05}

**Actor:** Human. **Shape:** circle. **State:** Resume an issue, PR or paused conversation. Resume an existing issue, PR tree or review checkpoint

**Enter from:** No incoming edge: choose this starting point from the entry frame.

**Move to:** [WS01 Open one workstream](#node-ws01) **when start**

#### ST06 — Release request {#node-st06}

**Actor:** Human. **Shape:** circle. **State:** Consider releasing already merged work. Release-only entry that does not require new code

**Enter from:** No incoming edge: choose this starting point from the entry frame.

**Move to:** [WS01 Open one workstream](#node-ws01) **when start**

### Workstream intake and Projects handoffs

#### WS01 — Open one workstream {#node-ws01}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Open or resume one focused conversation. Keep one coherent workstream in chat, linking its canonical issues, PRs and Project coordination record.

**Enter from:** [ST01 Initial release](#node-st01) (start); [ST02 Planned change](#node-st02) (start); [ST03 Bug or defect](#node-st03) (start); [ST04 Maintenance](#node-st04) (start); [ST05 Existing work](#node-st05) (start); [ST06 Release request](#node-st06) (start)

**Move to:** [WS04 Register conversation in Projects](#node-ws04) **when register chat**

#### WS02 — Inspect current baseline {#node-ws02}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Inspect issues, PRs and the current code. Re-read the current GitHub baseline and the Projects coordination record before making new assumptions.

**Enter from:** [WS04 Register conversation in Projects](#node-ws04) (load state)

**Move to:** [WS03 Select discovery depth?](#node-ws03) **when classify**

#### WS03 — Select discovery depth? {#node-ws03}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Choose planning, debugging or resumption. Route the request by its actual goal; all starts go through Projects coordination; do not force major planning for routine tasks.

**Enter from:** [WS02 Inspect current baseline](#node-ws02) (classify)

**Move to:** [PL01 State detailed intent](#node-pl01) **when complex / unclear**; [SP01 Reconcile GitHub issues](#node-sp01) **when clear change**; [BG01 Capture reproduction](#node-bg01) **when bug**; [RV01 Inspect actual PR state](#node-rv01) **when resume PR**; [RL01 Recommend release intent](#node-rl01) **when release only**

#### WS04 — Register conversation in Projects {#node-ws04}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Link this chat and its current objective. When given a conversation URL, add or update a lightweight Projects coordination pointer in the owning repo/project file; do not mirror issue details.

**Enter from:** [WS01 Open one workstream](#node-ws01) (register chat)

**Move to:** [WS02 Inspect current baseline](#node-ws02) **when load state**

#### WS05 — Park checkpoint in Projects {#node-ws05}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Store blockers, next action and chat link. Before a pause, record only the source PR/issue links, current blocker, resume condition and conversation URL in Projects; routine low-risk Projects changes may be autonomously merged under its own policy.

**Enter from:** [PL05 Enough specified?](#node-pl05) (defer); [SP03 Issue change approved?](#node-sp03) (pending approval); [TR03 Runnable PR available?](#node-tr03) (all blocked); [RV02 CI evidence usable?](#node-rv02) (required CI blocked); [RV08 Merge approved?](#node-rv08) (hold); [RV10 More work in PR tree?](#node-rv10) (remaining blocked); [RL02 Publish now?](#node-rl02) (defer release); [RL09 Public audit passed?](#node-rl09) (audit blocked); [RL05 History rewrite needed?](#node-rl05) (rewrite consent pending); [RL08 Release verified?](#node-rl08) (publication failed)

**Move to:** [EN02 Deferred or blocked](#node-en02) **when checkpoint parked**

#### WS06 — Close Projects handoff {#node-ws06}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Record cancellation without a second tracker. On human-authorised abandonment, record why the work stopped and update or remove stale Projects handoff links, preserving canonical issues/PR history.

**Enter from:** [PL05 Enough specified?](#node-pl05) (abandon); [TR03 Runnable PR available?](#node-tr03) (cancelled); [RV04 What needs changing?](#node-rv04) (cancelled); [RV08 Merge approved?](#node-rv08) (cancel)

**Move to:** [EN03 Abandoned](#node-en03) **when cancel recorded**

### Bug diagnosis and regression proof

#### BG01 — Capture reproduction {#node-bg01}

**Actor:** Human or Chat LLM. **Shape:** rectangle. **State:** Record steps to reproduce and expected results. Capture reproduction, observed-versus-expected behaviour, logs, versions, screenshots and context.

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (bug); [BG05 Root cause supported?](#node-bg05) (insufficient evidence)

**Move to:** [BG02 Who investigates?](#node-bg02) **when reproduction recorded**

#### BG02 — Who investigates? {#node-bg02}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Route to chat, coding agent or human. Select human interactive, Chat LLM research or Coding LLM investigation

**Enter from:** [BG01 Capture reproduction](#node-bg01) (reproduction recorded)

**Move to:** [BG08 Request human investigation](#node-bg08) **when human debug**; [BG04 Chat investigates](#node-bg04) **when chat debug**; [BG06 Prepare coding-agent diagnosis](#node-bg06) **when agent debug**

#### BG03 — Human interactive investigation {#node-bg03}

**Actor:** Human. **Shape:** rectangle. **State:** Run the app and report findings to chat. Execute local UI or debugger steps from the Chat LLM request and return reproducible evidence.

**Enter from:** [BG08 Request human investigation](#node-bg08) (human steps shared)

**Move to:** [BG05 Root cause supported?](#node-bg05) **when human findings**

#### BG04 — Chat investigates {#node-bg04}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Analyse evidence and try a small fix. Investigate directly where tools allow; a verified fix proceeds through issue and PR workflow, otherwise escalate with focused evidence.

**Enter from:** [BG02 Who investigates?](#node-bg02) (chat debug)

**Move to:** [BG05 Root cause supported?](#node-bg05) **when chat findings**

#### BG05 — Root cause supported? {#node-bg05}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Check the diagnosis against the evidence. Evaluate whether logs, reproduction, tests and human feedback support the root cause; loop or reframe if they do not.

**Enter from:** [BG03 Human interactive investigation](#node-bg03) (human findings); [BG04 Chat investigates](#node-bg04) (chat findings); [BG09 Coding agent diagnoses](#node-bg09) (agent findings)

**Move to:** [BG01 Capture reproduction](#node-bg01) **when insufficient evidence**; [PL01 State detailed intent](#node-pl01) **when needs redesign**; [BG07 Specify regression proof](#node-bg07) **when cause supported**

#### BG06 — Prepare coding-agent diagnosis {#node-bg06}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Write the prompt, evidence and test request. Supply the coding-agent investigation prompt to the human with reproduction, hypotheses, testing expectations and exact PR/issue context.

**Enter from:** [BG02 Who investigates?](#node-bg02) (agent debug)

**Move to:** [BG09 Coding agent diagnoses](#node-bg09) **when coding prompt**

#### BG07 — Specify regression proof {#node-bg07}

**Actor:** Human or Chat LLM. **Shape:** rectangle. **State:** Plan a failing test and scenario evidence. Specify the test to add or update, with unit, txtar, integration or scenario proof that would demonstrate the bug and prevent a recurrence; implement it with the fix later.

**Enter from:** [BG05 Root cause supported?](#node-bg05) (cause supported)

**Move to:** [SP01 Reconcile GitHub issues](#node-sp01) **when regression criteria**

#### BG08 — Request human investigation {#node-bg08}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Explain why and provide runnable steps. Explain why a manual device/UI debugger run is needed, give steps, flowchart or rationale, and ask the human for exact observations and output.

**Enter from:** [BG02 Who investigates?](#node-bg02) (human debug)

**Move to:** [BG03 Human interactive investigation](#node-bg03) **when human steps shared**

#### BG09 — Coding agent diagnoses {#node-bg09}

**Actor:** Coding LLM. **Shape:** rectangle. **State:** Run investigations and return evidence. Investigate the prepared prompt in a repository/worktree, run experiments and tests, and send findings back to Chat LLM for verification; do not self-approve the diagnosis.

**Enter from:** [BG06 Prepare coding-agent diagnosis](#node-bg06) (coding prompt)

**Move to:** [BG05 Root cause supported?](#node-bg05) **when agent findings**

### Clarification and contradictions

#### PL01 — State detailed intent {#node-pl01}

**Actor:** Human. **Shape:** rectangle. **State:** Explain the goal, constraints and examples. Describe what, why, constraints, examples and desired approach; answer and ask questions

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (complex / unclear); [BG05 Root cause supported?](#node-bg05) (needs redesign); [PL05 Enough specified?](#node-pl05) (not ready); [RV04 What needs changing?](#node-rv04) (design mismatch); [RL09 Public audit passed?](#node-rl09) (fundamental failure)

**Move to:** [PL02 Ask clarifying questions](#node-pl02) **when clarify**

#### PL02 — Ask clarifying questions {#node-pl02}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Ask what is missing or unclear. Ask targeted questions; revise scope after every material change

**Enter from:** [PL01 State detailed intent](#node-pl01) (clarify); [PL04 Resolve contradictions](#node-pl04) (decisions revised)

**Move to:** [PL03 Contradictions found?](#node-pl03) **when compare requirements**

#### PL03 — Contradictions found? {#node-pl03}

**Actor:** Chat LLM. **Shape:** diamond. **State:** Check whether requirements disagree. Search for conflicts in requirements, design, scope, tests and assumptions; route yes to resolution and no to sufficiency check.

**Enter from:** [PL02 Ask clarifying questions](#node-pl02) (compare requirements)

**Move to:** [PL04 Resolve contradictions](#node-pl04) **when conflict found**; [PL05 Enough specified?](#node-pl05) **when no conflict**

#### PL04 — Resolve contradictions {#node-pl04}

**Actor:** Human. **Shape:** rectangle. **State:** Discuss, decide or defer conflicting needs. Decide between conflicting requirements, ask follow-up questions, then recheck the revised specification.

**Enter from:** [PL03 Contradictions found?](#node-pl03) (conflict found)

**Move to:** [PL02 Ask clarifying questions](#node-pl02) **when decisions revised**

#### PL05 — Enough specified? {#node-pl05}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Decide whether there is enough to start. Advance when sufficient, not necessarily complete; otherwise loop or park

**Enter from:** [PL03 Contradictions found?](#node-pl03) (no conflict)

**Move to:** [PL01 State detailed intent](#node-pl01) **when not ready**; [WS05 Park checkpoint in Projects](#node-ws05) **when defer**; [WS06 Close Projects handoff](#node-ws06) **when abandon**; [SP01 Reconcile GitHub issues](#node-sp01) **when sufficient**

### GitHub issue and specification decisions

#### SP01 — Reconcile GitHub issues {#node-sp01}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Match the work to existing GitHub issues. Search existing issues and PRs; align expected outcomes and acceptance cases

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (clear change); [BG07 Specify regression proof](#node-bg07) (regression criteria); [PL05 Enough specified?](#node-pl05) (sufficient); [RV04 What needs changing?](#node-rv04) (issue mismatch)

**Move to:** [SP02 Issue record adequate?](#node-sp02) **when inspect issue**

#### SP02 — Issue record adequate? {#node-sp02}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Check whether an issue covers the work. Check missing tests, issue ownership, resolving scope and change implications

**Enter from:** [SP01 Reconcile GitHub issues](#node-sp01) (inspect issue)

**Move to:** [SP03 Issue change approved?](#node-sp03) **when approval needed**; [SP04 Persist accepted spec](#node-sp04) **when existing issue valid**

#### SP03 — Issue change approved? {#node-sp03}

**Actor:** Human. **Shape:** diamond. **State:** Approve a new issue or major rewrite. Decide whether an issue should be created or materially rewritten; routine authorised updates to existing issues need no fresh approval.

**Enter from:** [SP02 Issue record adequate?](#node-sp02) (approval needed)

**Move to:** [SP04 Persist accepted spec](#node-sp04) **when approved**; [WS05 Park checkpoint in Projects](#node-ws05) **when pending approval**

#### SP04 — Persist accepted spec {#node-sp04}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Keep approved detail in issues and PRs. Record canonical requirements and acceptance checks in issues and PR descriptions, not duplicated into Projects.

**Enter from:** [SP02 Issue record adequate?](#node-sp02) (existing issue valid); [SP03 Issue change approved?](#node-sp03) (approved)

**Move to:** [SP05 New repository required?](#node-sp05) **when recorded**

#### SP05 — New repository required? {#node-sp05}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Choose bootstrap or an existing repo. After recording canonical issue/spec requirements, decide if a new repository needs bootstrapping or an existing repository can proceed.

**Enter from:** [SP04 Persist accepted spec](#node-sp04) (recorded)

**Move to:** [TR05 Bootstrap repository](#node-tr05) **when new repo**; [TR01 Work size and dependency?](#node-tr01) **when existing repo**

### PR tree and dogfood milestones

#### TR01 — Work size and dependency? {#node-tr01}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Decide whether one PR is enough. Choose scope from dependencies and likely conflicts, not arbitrary linear stacking

**Enter from:** [SP05 New repository required?](#node-sp05) (existing repo); [TR05 Bootstrap repository](#node-tr05) (bootstrapped)

**Move to:** [TR02 Plan PR dependency tree](#node-tr02) **when dependent PRs**; [EX01 Who implements?](#node-ex01) **when single PR**

#### TR02 — Plan PR dependency tree {#node-tr02}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Map PR dependencies and merge order. Map sibling PRs that can merge independently and dependent children that must wait

**Enter from:** [TR01 Work size and dependency?](#node-tr01) (dependent PRs)

**Move to:** [TR03 Runnable PR available?](#node-tr03) **when tree ready**

#### TR03 — Runnable PR available? {#node-tr03}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Choose an unblocked branch or park work. Choose an independently runnable leaf; if none is available record why work is blocked; cancel only with human agreement.

**Enter from:** [TR02 Plan PR dependency tree](#node-tr02) (tree ready); [RV10 More work in PR tree?](#node-rv10) (next PR)

**Move to:** [EX01 Who implements?](#node-ex01) **when runnable**; [WS05 Park checkpoint in Projects](#node-ws05) **when all blocked**; [WS06 Close Projects handoff](#node-ws06) **when cancelled**

#### TR05 — Bootstrap repository {#node-tr05}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Set up the repo, tests and documentation. After human scope approval, initialise the repository, essential CI, documentation and licence, delegating source setup to the coding model as needed

**Enter from:** [SP05 New repository required?](#node-sp05) (new repo)

**Move to:** [TR01 Work size and dependency?](#node-tr01) **when bootstrapped**

#### TR04 — Dogfood verification needed? {#node-tr04}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Decide how to test this PR milestone. This reachable gate follows publication of each PR; decide whether to prepare an explicit dogfood/UI test before review.

**Enter from:** [EX04 Publish PR tree](#node-ex04) (PR published); [EX05 Chat direct fix](#node-ex05) (PR published)

**Move to:** [TR06 Prepare dogfood test plan](#node-tr06) **when dogfood needed**; [RV01 Inspect actual PR state](#node-rv01) **when standard review**

#### TR06 — Prepare dogfood test plan {#node-tr06}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Ask for human or automated milestone proof. Select practical UI/dogfood steps, Playwright, screenshot, prototype, txtar or scenario evidence for the current PR milestone, and attach or request evidence for review.

**Enter from:** [TR04 Dogfood verification needed?](#node-tr04) (dogfood needed)

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when test plan linked**

### Implementation

#### EX01 — Who implements? {#node-ex01}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Use chat directly or prompt a coding agent. Chat should fix small scoped changes itself when it has adequate access and verification; otherwise delegate with a prompt.

**Enter from:** [TR01 Work size and dependency?](#node-tr01) (single PR); [TR03 Runnable PR available?](#node-tr03) (runnable)

**Move to:** [EX05 Chat direct fix](#node-ex05) **when chat direct**; [EX02 Prepare implementation](#node-ex02) **when coding agent**

#### EX02 — Prepare implementation {#node-ex02}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Write a runnable prompt with test criteria. Include branch, canonical issue acceptance criteria, PR dependencies, regression tests and txtar/scenario/integration tests where helpful.

**Enter from:** [EX01 Who implements?](#node-ex01) (coding agent); [RV06 Complex correction](#node-rv06) (corrective prompt)

**Move to:** [EX03 Code and test locally](#node-ex03) **when prompt accepted**

#### EX03 — Code and test locally {#node-ex03}

**Actor:** Coding LLM. **Shape:** rectangle. **State:** Implement the change and prove its behaviour. Write or update unit and larger end-to-end, txtar, integration or scenario proof, then run tests and inspect output.

**Enter from:** [EX02 Prepare implementation](#node-ex02) (prompt accepted)

**Move to:** [EX04 Publish PR tree](#node-ex04) **when tested implementation**

#### EX04 — Publish PR tree {#node-ex04}

**Actor:** Coding LLM. **Shape:** rectangle. **State:** Push code and open linked pull requests. Coding LLM (Codex/Agy): Push real commits and create the promised PRs, with explicit dependent bases and linked issues

**Enter from:** [EX03 Code and test locally](#node-ex03) (tested implementation)

**Move to:** [TR04 Dogfood verification needed?](#node-tr04) **when PR published**

#### EX05 — Chat direct fix {#node-ex05}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Fix a small change and run its tests. Directly implement when capable, add focused regression and scenario proof, publish to PR, otherwise delegate to EX02.

**Enter from:** [EX01 Who implements?](#node-ex01) (chat direct)

**Move to:** [TR04 Dogfood verification needed?](#node-tr04) **when PR published**

### Review, CI and human verification

#### RV01 — Inspect actual PR state {#node-rv01}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Inspect what the PR actually contains. Verify published commits, comments, PR metadata, dependencies and fresh tests

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (resume PR); [TR04 Dogfood verification needed?](#node-tr04) (standard review); [TR06 Prepare dogfood test plan](#node-tr06) (test plan linked); [RV05 Small repair](#node-rv05) (republished)

**Move to:** [RV02 CI evidence usable?](#node-rv02) **when current head**

#### RV02 — CI evidence usable? {#node-rv02}

**Actor:** Chat LLM. **Shape:** diamond. **State:** Distinguish passing, missing and blocked CI. Check current head and mandatory CI evidence, distinguish missing quota from actual success; route required blocked checks to coordination hold.

**Enter from:** [RV01 Inspect actual PR state](#node-rv01) (current head)

**Move to:** [RV03 Review correctness?](#node-rv03) **when CI usable**; [WS05 Park checkpoint in Projects](#node-ws05) **when required CI blocked**

#### RV03 — Review correctness? {#node-rv03}

**Actor:** Human or Chat LLM. **Shape:** rectangle. **State:** Review the requirements and regression proof. Review correctness, test quality, realistic high-level txtar/scenario coverage, issue/PR traceability and code-level tests.

**Enter from:** [RV02 CI evidence usable?](#node-rv02) (CI usable)

**Move to:** [RV04 What needs changing?](#node-rv04) **when findings**

#### RV04 — What needs changing? {#node-rv04}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Choose the right correction or review path. Route repair to smallest appropriate stage, including back to Q&A and issue specifications

**Enter from:** [RV03 Review correctness?](#node-rv03) (findings); [RV14 Review evidence accepted?](#node-rv14) (incorrect or unproven); [RV08 Merge approved?](#node-rv08) (changes requested)

**Move to:** [RV05 Small repair](#node-rv05) **when small fix**; [RV06 Complex correction](#node-rv06) **when complex fix**; [PL01 State detailed intent](#node-pl01) **when design mismatch**; [SP01 Reconcile GitHub issues](#node-sp01) **when issue mismatch**; [RV07 Human PR review](#node-rv07) **when reviewable**; [WS06 Close Projects handoff](#node-ws06) **when cancelled**

#### RV05 — Small repair {#node-rv05}

**Actor:** Human. **Shape:** rectangle. **State:** Fix a straightforward issue or conflict. Resolve trivial conflict or tiny fix; Chat may patch when authorised, then republish and review

**Enter from:** [RV04 What needs changing?](#node-rv04) (small fix)

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when republished**

#### RV06 — Complex correction {#node-rv06}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Send a focused request to a coding agent. Produce targeted prompt for Codex/Agy; repair existing branch/PR when safe

**Enter from:** [RV04 What needs changing?](#node-rv04) (complex fix)

**Move to:** [EX02 Prepare implementation](#node-ex02) **when corrective prompt**

#### RV07 — Human PR review {#node-rv07}

**Actor:** Human. **Shape:** rectangle. **State:** Review changes and verify user-facing results. Review the PR and test meaningful UI or bug behaviour; delegate screenshots, Playwright or prototypes when they can provide reliable evidence.

**Enter from:** [RV04 What needs changing?](#node-rv04) (reviewable)

**Move to:** [RV11 What verification is needed?](#node-rv11) **when review evidence**

#### RV08 — Merge approved? {#node-rv08}

**Actor:** Human. **Shape:** diamond. **State:** Decide whether this PR may be merged. Explicit approval; passing CI or model readiness is not merge authority

**Enter from:** [RV14 Review evidence accepted?](#node-rv14) (accepted)

**Move to:** [RV04 What needs changing?](#node-rv04) **when changes requested**; [WS05 Park checkpoint in Projects](#node-ws05) **when hold**; [WS06 Close Projects handoff](#node-ws06) **when cancel**; [RV09 Merge eligible node](#node-rv09) **when human approved**

#### RV09 — Merge eligible node {#node-rv09}

**Actor:** GitHub / CI. **Shape:** rectangle. **State:** Merge a reviewed, eligible pull request. Merge only valid, approved PR with required checks and dependency prerequisites satisfied

**Enter from:** [RV08 Merge approved?](#node-rv08) (human approved)

**Move to:** [RV10 More work in PR tree?](#node-rv10) **when merged**

#### RV10 — More work in PR tree? {#node-rv10}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Continue siblings or close the milestone. Update bases and conflicts; choose another ready sibling or pause dependent branch

**Enter from:** [RV09 Merge eligible node](#node-rv09) (merged)

**Move to:** [TR03 Runnable PR available?](#node-tr03) **when next PR**; [CL01 Audit issues and PRs](#node-cl01) **when milestone complete**; [WS05 Park checkpoint in Projects](#node-ws05) **when remaining blocked**

#### RV11 — What verification is needed? {#node-rv11}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Choose manual, automated or none. After reviewing the PR, decide whether interactive UI/bug proof or automated Playwright/scenario evidence is needed; do not assume an earlier bug hypothesis was correct.

**Enter from:** [RV07 Human PR review](#node-rv07) (review evidence)

**Move to:** [RV12 Human verifies the result](#node-rv12) **when human / device**; [RV13 Automate the proof](#node-rv13) **when automated / preview**; [RV14 Review evidence accepted?](#node-rv14) **when no extra test**

#### RV12 — Human verifies the result {#node-rv12}

**Actor:** Human. **Shape:** rectangle. **State:** Run the change and confirm real behaviour. Run a local or installed build, reproduce the original bug, test changed UI and report whether the analysis/PR actually solved it; return discrepancies for revision.

**Enter from:** [RV11 What verification is needed?](#node-rv11) (human / device)

**Move to:** [RV14 Review evidence accepted?](#node-rv14) **when user findings**

#### RV13 — Automate the proof {#node-rv13}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Use Playwright, scenarios or previews. Provide or delegate trusted UI automation, Playwright, screenshots, previews, integration tests or txtar/scenario evidence, attached to PR or shared for human assessment.

**Enter from:** [RV11 What verification is needed?](#node-rv11) (automated / preview)

**Move to:** [RV14 Review evidence accepted?](#node-rv14) **when automation findings**

#### RV14 — Review evidence accepted? {#node-rv14}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Fix objections or request merge approval. Compare manual and automated results against issue requirements and original bug hypothesis; route incorrect analysis back to diagnosis or issue correction.

**Enter from:** [RV11 What verification is needed?](#node-rv11) (no extra test); [RV12 Human verifies the result](#node-rv12) (user findings); [RV13 Automate the proof](#node-rv13) (automation findings)

**Move to:** [RV04 What needs changing?](#node-rv04) **when incorrect or unproven**; [RV08 Merge approved?](#node-rv08) **when accepted**

### Closeout and coordinating repositories

#### CL01 — Audit issues and PRs {#node-cl01}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Check issues, tests and PR closeout evidence. Verify canonical issues, resolving keywords, regression and scenario proof, remaining blockers and correct PR merge state.

**Enter from:** [RV10 More work in PR tree?](#node-rv10) (milestone complete)

**Move to:** [CL02 Notify dependencies](#node-cl02) **when issues checked**

#### CL02 — Notify dependencies {#node-cl02}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Update anything that depends on this work. Check version constraints, dependent PRs, projects and actionable update notices

**Enter from:** [CL01 Audit issues and PRs](#node-cl01) (issues checked)

**Move to:** [CL03 Sync Projects coordination](#node-cl03) **when dependency updates**

#### CL03 — Sync Projects coordination {#node-cl03}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Update conversation pointer and resume state. Keep the arran4/projects handoff index current at milestone closeout; issues/PRs carry implementation detail, Projects links conversation, status, blockers and next action.

**Enter from:** [CL02 Notify dependencies](#node-cl02) (dependency updates)

**Move to:** [CL04 Update PR repository](#node-cl04) **when checkpoint current**

#### CL04 — Update PR repository {#node-cl04}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Record announcement tasks and readiness. Update arran4/public-relations with accurate materials or future campaign tasks

**Enter from:** [CL03 Sync Projects coordination](#node-cl03) (checkpoint current)

**Move to:** [RL01 Recommend release intent](#node-rl01) **when announcement reviewed**

### Release and public opening

#### RL01 — Recommend release intent {#node-rl01}

**Actor:** Human or Chat LLM. **Shape:** rectangle. **State:** Choose whether and how to release this work. Use accepted scope, roadmap, merged changes and release guidance; patch may be routine if authorised

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (release only); [CL04 Update PR repository](#node-cl04) (announcement reviewed)

**Move to:** [RL02 Publish now?](#node-rl02) **when recommend version**

#### RL02 — Publish now? {#node-rl02}

**Actor:** Human. **Shape:** diamond. **State:** Decide whether it is time to publish. May choose no release, normal versioned release, or delayed/public opening

**Enter from:** [RL01 Recommend release intent](#node-rl01) (recommend version)

**Move to:** [EN01 Completed](#node-en01) **when no release needed**; [WS05 Park checkpoint in Projects](#node-ws05) **when defer release**; [RL03 First public opening?](#node-rl03) **when release approved**

#### RL03 — First public opening? {#node-rl03}

**Actor:** Human. **Shape:** diamond. **State:** Check whether the repo must become public. If private-to-public, require broader quality, provenance, licence, copyright and link checks

**Enter from:** [RL02 Publish now?](#node-rl02) (release approved)

**Move to:** [RL07 Run release workflow](#node-rl07) **when already public**; [RL04 Audit public exposure](#node-rl04) **when first public opening**

#### RL04 — Audit public exposure {#node-rl04}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Inspect history, secrets, links and licences. Inspect repository history, links, copyright, documentation, quality and release assets

**Enter from:** [RL03 First public opening?](#node-rl03) (first public opening)

**Move to:** [RL09 Public audit passed?](#node-rl09) **when audit findings**

#### RL05 — History rewrite needed? {#node-rl05}

**Actor:** Human. **Shape:** diamond. **State:** Ask before rewriting published Git history. Force-push or rewrite only on explicit informed approval; consider collaborators and tags

**Enter from:** [RL09 Public audit passed?](#node-rl09) (audit clear)

**Move to:** [RL06 Approve visibility change](#node-rl06) **when no rewrite / approved**; [WS05 Park checkpoint in Projects](#node-ws05) **when rewrite consent pending**

#### RL06 — Approve visibility change {#node-rl06}

**Actor:** Human. **Shape:** rectangle. **State:** Approve making the repository public. Make public only after verified audit and approval

**Enter from:** [RL05 History rewrite needed?](#node-rl05) (no rewrite / approved)

**Move to:** [RL07 Run release workflow](#node-rl07) **when public approved**

#### RL07 — Run release workflow {#node-rl07}

**Actor:** GitHub / CI. **Shape:** rectangle. **State:** Run the approved tagging and release action. Use documented release-safe action to tag and publish; no duplicate release publisher

**Enter from:** [RL03 First public opening?](#node-rl03) (already public); [RL06 Approve visibility change](#node-rl06) (public approved)

**Move to:** [RL10 Inspect published assets](#node-rl10) **when workflow complete**

#### RL08 — Release verified? {#node-rl08}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Confirm the actual published result. Decide whether published assets, tag, package, repository visibility and downstream checks really succeeded; otherwise record failed release.

**Enter from:** [RL10 Inspect published assets](#node-rl10) (observed artifacts)

**Move to:** [EN01 Completed](#node-en01) **when verified**; [WS05 Park checkpoint in Projects](#node-ws05) **when publication failed**

#### RL09 — Public audit passed? {#node-rl09}

**Actor:** Human or Chat LLM. **Shape:** diamond. **State:** Decide if publication requirements are met. Determine whether secret, history, licence, link and quality checks are adequate; unresolved fundamental issues return to design, while blocking items pause release.

**Enter from:** [RL04 Audit public exposure](#node-rl04) (audit findings)

**Move to:** [RL05 History rewrite needed?](#node-rl05) **when audit clear**; [PL01 State detailed intent](#node-pl01) **when fundamental failure**; [WS05 Park checkpoint in Projects](#node-ws05) **when audit blocked**

#### RL10 — Inspect published assets {#node-rl10}

**Actor:** Chat LLM. **Shape:** rectangle. **State:** Check tag, packages and downstream state. Inspect actual GitHub tag, release, uploaded artifacts, package/overlay and visibility after the release workflow, then hand off the outcome for confirmation.

**Enter from:** [RL07 Run release workflow](#node-rl07) (workflow complete)

**Move to:** [RL08 Release verified?](#node-rl08) **when observed artifacts**

### Terminal outcomes

#### EN01 — Completed {#node-en01}

**Actor:** GitHub / CI. **Shape:** oval. **State:** Finish the verified milestone at the end. Work and any authorised release completed; issue and tracker state reconciled

**Enter from:** [RL02 Publish now?](#node-rl02) (no release needed); [RL08 Release verified?](#node-rl08) (verified)

**Move to:** Terminal state; retain the outcome and supporting issue/PR evidence.

#### EN02 — Deferred or blocked {#node-en02}

**Actor:** GitHub / CI. **Shape:** oval. **State:** Record the blocker and how to resume. Record a concrete resumption trigger, owner, conversation URL and authoritative issue/PR links in Projects when applicable.

**Enter from:** [WS05 Park checkpoint in Projects](#node-ws05) (checkpoint parked)

**Move to:** Terminal state; retain the outcome and supporting issue/PR evidence.

#### EN03 — Abandoned {#node-en03}

**Actor:** Human. **Shape:** oval. **State:** Record why and close the handoff. Explicitly abandon the work and reconcile obsolete issues/PRs, with a concise Projects coordination update.

**Enter from:** [WS06 Close Projects handoff](#node-ws06) (cancel recorded)

**Move to:** Terminal state; retain the outcome and supporting issue/PR evidence.

## Notes

This process intentionally leaves choices reversible. A human may change the scope, abandon a line of development, park work for later, or take a different ready branch in a PR tree. A CI quota failure, coding-agent exit, or conflict does not automatically mean the specification failed. The diagram describes **how decisions are made and persisted**, not a guarantee that every path always runs.

The current workstream can span several coding sessions and PRs. An issue may outlive one implementation attempt and a PR tree may serve one milestone without exhausting the roadmap. If the workflow has changed while work is in progress, reconcile the durable records and continue from the correct node; do not silently apply obsolete plans.

### Installing and rendering with existing tools

Use a package manager or Go's module-aware installer rather than piping remote shell scripts into a shell. With Go 1.27 or newer (required by D2 v0.9.0), the explicit installation command is:

```bash
go install github.com/d2lang/d2@v0.9.0
d2 --version
```

If an appropriate D2 ebuild is maintained on the system, prefer installing or upgrading that ebuild with Portage. The image export uses an installed `rsvg-convert` from librsvg. The checked-in `render-diagrams.sh` validates the node anchors and emits both the SVG and the scaled PNG. A different D2 version may produce different diagram routing even when the source stays unchanged.

### Maintaining this diagram

Edit `workflow.d2` and the matching node description in `index.md`; run `bash render-diagrams.sh` from the page bundle to regenerate `workflow.svg` with the embedded agent guidance and its `workflow.png` export, or let the PR's renderer workflow do so. Do not edit embedded SVG instructions directly. Commit the text and resulting SVG together. Preserve node IDs when their meaning stays stable so links and LLM checkpoints do not break. If adding a node, specify actor, description, all decision exits and how it affects issue or PR state.

## References

- [Canonical CI/CD workflow and release safety](/blog/guidance/ci-cd/)
- [Projects and roadmap register](https://github.com/arran4/projects)
- [Public Relations planning and announcements](https://github.com/arran4/public-relations)
- [D2 language and CLI](https://d2lang.com/)
