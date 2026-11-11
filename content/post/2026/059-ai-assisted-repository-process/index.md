---
title: "AI-Assisted Repository Development: A Unified Process"
date: 2026-10-30T23:09:00+11:00
draft: false
guidance: ["agent-management"]
tags: ["agents", "automation", "chatgpt", "ci", "codex", "github", "orchestration", "workflow"]
categories: ["Software Development", "LLM Instructions", "Automation"]
---

<!-- cspell:words agy Codex dogfood handoff handoffs inspectable librsvg rsvg workstream workstreams -->

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

The six circular entry points are grouped inside a **START HERE** frame. Choose one; all enter the same conversation/handoff intake before the appropriate work path is selected. The legend is in its own frame to the right of the main flow, away from the starting choices. Rectangles contain actions with one subsequent transition; diamonds contain mutually exclusive choices. Branch outcomes use standard D2 **connection labels** rather than source/target-arrowhead labels: ELK can allocate room for these captions. Long return lines include the **destination node ID** in the same caption. Visual inspection of the generated SVG is still required. Standard completion is anchored at the bottom, while exceptional deferred or abandoned outcomes may branch from the relevant stage.

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

The diagram includes a **large framed D2 legend** with actual example nodes for each actor, circle/rectangle/diamond/oval samples, and miniature arrows showing the exact five connector styles. The legend examples are visual documentation only, with no links to workflow nodes. Phase names remain in this catalogue and the source comments; the large nested phase frames were removed because they increased whitespace and forced lengthy connector routes. Each node retains its stable ID and actor colour. **Shared responsibility does not imply shared approval authority:** a Chat LLM may classify complexity, select a repair path or recommend a release, but cannot make a human-owned merge, visibility, history-rewrite or release decision without the required approval.

For branching decisions, a short standard D2 connection label identifies the outcome. Endpoint-attached arrowhead labels are deliberately avoided because D2 does not include them in its automatic label placement, making collisions likely around shared nodes. Long/backtracking captions include the destination node ID; full transition conditions remain in the node catalogue and D2 connection tooltips. The export pass places each caption above all connector strokes with a white backing and checks the entire SVG for caption-to-caption and caption-to-node overlaps, failing CI if they recur. The ELK layout does not guarantee precise label positions, and some crossings remain possible; edge colour and dash type distinguish long backtracking links.

## How different work enters the shared pipeline

A **new repository or first release** starts at [ST01](#node-st01), generally involves substantial [intent and Q&A](#node-pl01), explicit [repository bootstrap](#node-tr05), an initial roadmap, and a later [public opening audit](#node-rl04) if publishing the code publicly.

A **feature, major improvement or minor improvement** shares [ST02](#node-st02). These are overlapping classifications, not separate implementation engines. A bounded additive feature may move from baseline inspection directly to [issue reconciliation](#node-sp01); a major architectural change normally takes multiple rounds of questioning, contradiction detection and a [PR dependency tree](#node-tr02).

A **bug** starts at [ST03](#node-st03). It may be a straightforward fix after analysis, or a longer investigation. For interactive UI problems, particularly Flutter, I may reproduce the issue directly and supply debugger output, screenshots and observations to the Chat LLM. The [debugging decision](#node-bg02) can instead delegate analysis to chat or a coding model. Once the root cause is credible, the ordinary issue, PR and review cycle applies.

An **automated version bump, tooling correction, security/audit finding or upgrade** starts at [ST04](#node-st04). It may be an entire workstream, or it may be incorporated into a feature or bug fix. An existing [PR or CI problem](#node-st05) can enter at review, and a release-only request [ST06](#node-st06) can go straight to release planning.

## The question-and-answer loop is part of development

I commonly begin with a long voice description covering my desired outcome, preferred implementation and constraints. The Chat LLM must not assume that this is a complete specification. It should ask targeted [clarifying questions](#node-pl02), [identify contradictions](#node-pl03), and surface choices or ambiguities for [discussion and deferral](#node-pl04). These are separate, **mergeable** activities that can repeat until enough is settled to proceed.

"Enough" does not mean every decision is finished. Some concerns belong in follow-up issues. If a material assumption changes during implementation, review returns to [intent](#node-pl01) or [issue reconciliation](#node-sp01). The current issue and PR specification must then be reconciled with the new understanding; do not scatter duplicate issues merely because the task was revised.

The same process runs while debugging: my answers and the Chat LLM's questions can be interleaved. A coding model may uncover new facts that invalidate a design assumption. That is a normal backtrack, not necessarily a failed task.

## Issues, PRs, conversations and a dependency tree

**GitHub issues and pull requests are the durable specification and evidence**: requirements, acceptance scenarios, dependencies, working implementation, review findings and resolving keywords. Chat conversations preserve evolving discussion and rationale, but a fresh agent should be able to reconstruct actionable expectations from GitHub. I also use [arran4/projects](https://github.com/arran4/projects) for portfolio and roadmap state and [arran4/public-relations](https://github.com/arran4/public-relations) for announcement planning, assets and communications.

At [SP01](#node-sp01), search the current issue register before adding anything. At [SP02](#node-sp02), verify that an existing issue actually matches the work; update it with implementation details or clarify changed scope. Creation of an issue or major change to a human-owned issue requires the appropriate [human decision](#node-sp03). Keep PR descriptions and closing keywords consistent so GitHub can resolve the *correct* issues, rather than merely checking for the presence of "Fixes #..." text.

For large work, [TR02](#node-tr02) produces a **PR tree**: a dependency and conflict graph, not necessarily a linear stack. Two siblings may be independently mergeable, while a child PR waits on a parent. Agents can develop as much of the tree as feasible within a selected **dogfood, testable or completion milestone**. [TR03](#node-tr03) chooses a branch whose prerequisites are satisfied; when one branch is blocked by a conflict or review, an independent sibling can progress. After each merge, reassess descendants against updated bases and tests. Never assume a graphically nearby PR is safe to merge.

## Implementation and continuous review

At [EX01](#node-ex01), ask whether the Chat LLM can safely implement a **small, well-understood change directly**, given its tools and test access. Otherwise the Chat LLM creates a concrete [coding prompt](#node-ex02) for Codex, Agy or another capable worker. The coding agent may run in a container with broad permission to build, test and generate a complete PR tree. This is distinct from authorising merges, releases, history rewrites or unrelated scope changes.

The coding agent publishes real branches, commits and PRs with tests and links. At [RV01](#node-rv01), the Chat LLM independently inspects the actual cumulative diff, relevant PR head, issue requirements, PR dependency bases, review comments and CI. It must not treat an agent's completion message as proof. At [RV07](#node-rv07), I also review the direction and test the result where appropriate.

A **simple merge conflict or minor fix** can be handled by me or directly by the Chat LLM where its tools permit; publish and review again. A complex bug, conflict or code defect should get a focused coding-agent prompt. A disagreement with the design goes back to the Q&A loop; a mismatch against the issue register goes back to issue reconciliation. Each review pass asks what is actually wrong and selects the earliest useful stage to revisit.

### CI and verification expectations

Use real tests liberally, including focused scenarios, integration tests and local tooling. It is acceptable for an agent to use substantial local build/test resources. For public repositories I place considerable weight on GitHub CI and its test matrix. For private repositories, quota or infrastructure limits may make CI unavailable: classify that as **missing evidence**, not a pass. Use trusted local verification and disclose what remains unverified; required branch protections and checks still apply.

A new commit makes evidence from an earlier head insufficient for newly affected checks. Non-actionable infra or quota failures can be recorded and set aside only when project policy allows; real failing tests must be resolved. A passing check does not replace independent review. Human approval is needed before a merge.

## Merge, issue closeout and release

[RV10](#node-rv10) checks whether another PR in the tree is ready, whether the desired milestone has been reached or whether some dependencies remain blocked. At the chosen closeout point the Chat LLM performs [CL01](#node-cl01): verify issue status, resolving keywords, implementation notes, tests, remaining defects and superseded PRs. Then check [dependent or upstream work](#node-cl02), update [Projects](#node-cl03) and update [Public Relations](#node-cl04).

The Chat LLM should recommend **no release, patch, minor or major** from the merged change set and roadmap at [RL01](#node-rl01). A routine patch release can use previously approved automation policy where it exists; otherwise a human decides whether to release, wait, or defer. The definitive GitHub Actions implementation remains the [canonical CI/CD guidance](/blog/guidance/ci-cd/): validation before immutable tags, one publishing owner, explicit tag-context release workflow and verification of actual artifacts.

**First publication or making a private repository public is a separate gate.** Inspect code and full repository history for secrets, personal information, licences, copyright ownership, external links, documentation, release quality and provenance. If cleanup requires rewriting Git history or force-pushing, obtain explicit informed approval first; never treat this as routine. The release workflow runs only after the applicable publication gates.

After a completed or deferred milestone, reconcile trackers and any needed announcements. Conclude as [completed](#node-en01), [deferred or blocked](#node-en02) with a resumption trigger, or [abandoned](#node-en03) with the reasons recorded. A new phase can start another pass through the same workflow.

## Actor responsibilities and limitations

| Actor | Responsible for | Limitations and controls |
| --- | --- | --- |
| **Human** | Goals, voice descriptions, design answers and challenges, interactive debugging, PR direction, merge, publicity and exceptional release/rewrite consent | May defer or abandon; not expected to manually maintain routine labels or metadata |
| **Human or Chat LLM** | Shared analysis/routing decisions: discovery depth, debugging strategy, issue sufficiency, PR-tree selection, implementation route, evidence review, next branch, and release recommendation | Either may decide within accepted scope and available tools; only the human can exercise the reserved merge/publication/irreversible authority |
| **Chat LLM** | Research, Q&A, contradictions, issue/PR specification, prompt creation, PR-tree selection, review, CI interpretation, GitHub administration, closeout and trackers | May lack repository or terminal access; state must be checked with tools. Small direct fixes are conditional on capability and verification. Never claim a tool action or a passing check without evidence |
| **Coding LLM** | Container-based implementation, debugging, tests, commits, PR tree creation, complex corrections | No independent authority over human-owned decisions; existing issue and PR specifications govern scope. A completed run is not a reviewed result |
| **GitHub / CI** | Durable issues and PRs, current commits and branches, checks, release workflows, labels, publication and merge results | A failed, pending or absent check is not approval; branches and bot messages may be stale; repository policies must be respected |

Repository-specific developer instructions, [blog guidance](/blog/guidance/) and applicable agent skills can inform implementation, but they are **inputs to a node**, not a separate compulsory stage in this diagram.

## Instructions to a fresh management LLM

Read this article and the canonical `workflow.d2` source. At intake, read the current [arran4/projects](https://github.com/arran4/projects) record and, when a conversation link is supplied, maintain a minimal handoff pointer. Never copy detailed issue/PR information into Projects or assume an old handoff is current. For bug work, specify regression and visible scenario evidence and verify the diagnosis with the human after the PR when needed. Treat each node ID as a **checkpoint, not a mandatory sequential checklist**. First inspect the target repository, PRs/issues and the latest conversation context. Report the current node, concrete evidence, unresolved decisions, and the permitted next node(s). If the work is already at review, do not restart planning without reason. If a major design conflict appears, do not force a superficial patch: return to clarification and reconcile the issues.

At each checkpoint: identify the workstream, inspect actual GitHub state, find the current actor and action, distinguish automatic routing from human approval, perform authorised work, verify tool results, then record the transition and any blocker. A Chat LLM without GitHub capabilities must say so and prepare an actionable prompt or human step instead of pretending it updated a PR. Conversely, when it *can* maintain an issue, PR description or merge-readiness state, it should not bounce routine administration to the coding worker.

Use these compact status fields when resuming a conversation:

| Field | Expected content |
| --- | --- |
| Workstream | Repository, objective, conversation context and milestone |
| Current node | One of the IDs linked below, plus actual GitHub refs |
| Specification | Canonical issues, PRs and accepted decisions |
| PR tree | Parent/child/sibling relationships, blockers and mergeable leaves |
| Verification | Tests, current head, CI classification and gaps |
| Next action | Exact action, responsible actor, and any human approval required |
| Exit | Completed, deferred with trigger, or abandoned |

## Projects handoff versus the actual work record

My [Projects repository](https://github.com/arran4/projects) is a **cross-conversation parking, resumption and coordination index**. When I supply a conversation URL, the Chat LLM reads the current owning repository file, checks overlapping notes/PRs, and records a concise resumption pointer. It does **not** mirror the conversation or maintain another complete issue tracker. The current issue descriptions, pull requests, tests and GitHub state remain the source of task detail. When a conversation pauses or a blocker arises, update Projects with the link, next action and resumption trigger; when work closes, reconcile it. Routine low-risk Projects-only note PRs may be merged autonomously under that repository's special policy, unlike substantial changes or PRs in other repositories.

## Debugging, tests, and visual verification

For a defect, Chat first gathers reproduction evidence at [BG01](#node-bg01). At [BG02](#node-bg02), the owner chooses **Chat diagnosis**, **a coding agent** (Chat prepares a focused prompt for the human to hand off), or **human investigation** (Chat supplies steps, rationale, flow, expected outcomes and specific questions). [BG05](#node-bg05) is a decision: a plausible cause proceeds to [BG09](#node-bg09) to specify a regression test, while contradictory results return to reproduction or design. If Chat can safely make a small fix, [EX05](#node-ex05) explicitly takes the **Chat direct fix** route.

Tests are not limited to unit tests. A good PR should update the original bug's regression test where practical, add or refine unit/integration checks, and include broad behavior-proving **TXTAR/txtar-style** or equivalent scenario tests and example output visible in the PR. [QA01](#node-qa01) evaluates that evidence before the review decision. No automated test suite is assumed to prove a UI is correct just because it passes.

After the PR exists, [RV12](#node-rv12) decides if the diagnosis or UI needs an additional human check. [RV15](#node-rv15) chooses a Playwright/other reliable visual harness where it exists, or gives the human a build, run, steps and evidence request. Screenshots, videos or scenario captures should be attached to the PR or made available in chat. [RV14](#node-rv14) routes wrong diagnoses **back to bug investigation**, faulty implementations back to correction, and only confirmed outcomes toward human merge approval.

## Layout and exceptional outcomes

A **circle** at the top represents a starting request; the bottom completion node represents successful finish. Exceptional outcomes such as a blocked check, pending approval or abandoned work do not need to be at the absolute bottom. [TR04](#node-tr04) is now reachable via [RV10](#node-rv10) → [TR07](#node-tr07), so intermediate dogfood verification is a real checkpoint rather than an orphaned node. [RL04](#node-rl04) is an audit process followed by [RL09](#node-rl09), the safety decision; [RL08](#node-rl08) is a release-verification decision.

## Example scenario runs to validate the process

These are **proposed examples for review**, not claims that a particular historical workstream followed them. Each trace uses the node IDs from the canonical diagram. They intentionally expose differences in how I work, and can be corrected without inventing a separate process diagram. The listed nodes are the principal checkpoints; routine intermediate transitions are sometimes condensed in prose. Questions after each example are intended to reveal missing decisions or incorrect routes.

### Scenario A — Small bug, investigated by me, fixed directly by chat

**Situation:** I reproduce a straightforward defect, identify the likely cause and provide a concise explanation. Chat has sufficient repository write and test access to make a tiny correction.

**Trace:** [ST03](#node-st03) → intake ([WS01–WS04](#node-ws01)) → [BG01](#node-bg01) → [BG02](#node-bg02) → [BG06](#node-bg06) → [BG03](#node-bg03) → [BG05](#node-bg05) → [BG09](#node-bg09). Alternatively [BG02](#node-bg02) → [BG07](#node-bg07) → [BG08](#node-bg08) delegates diagnosis to a coding agent. If more evidence is required, return to [BG01](#node-bg01); otherwise proceed through issues, coding implementation and the PR review.

**Evidence:** A matching existing issue, focused regression test, current PR diff, working CI or disclosed missing verification, review and human merge approval. Then the closeout checks [CL01–CL04](#node-cl01) and [RL01–RL02](#node-rl01) may end at [EN01](#node-en01) with **no immediate release**.

**Review question:** Should a tiny correction skip GitHub issue creation when an existing issue or PR already captures its specification, and where do we record the reason?

### Scenario B — Flutter UI bug with interactive diagnosis and coding-agent correction

**Situation:** Automated tests do not reproduce a UI refresh issue. I run the application and debugger, report observations to chat and delegate the actual repair.

**Trace:** [ST03](#node-st03) → [BG01](#node-bg01) → [BG02](#node-bg02) → [BG03](#node-bg03) → [BG05](#node-bg05). If more evidence is needed, return to [BG01](#node-bg01); otherwise use [SP01](#node-sp01) → [TR01](#node-tr01) → [EX01](#node-ex01) → [EX02](#node-ex02) → [EX03](#node-ex03) → [EX04](#node-ex04) → [RV01](#node-rv01).

**Review loop:** [RV02](#node-rv02) → [RV03](#node-rv03) → [RV04](#node-rv04). The reviewed PR passes through [RV12](#node-rv12) → [RV15](#node-rv15) and either [RV13](#node-rv13) for my live UI test or [RV16](#node-rv16) for automated visual proof. If [RV14](#node-rv14) finds the diagnosis incorrect, return to [BG01](#node-bg01); if the code is wrong, route through [RV06](#node-rv06) → [EX02](#node-ex02). Only a reviewed and approved result reaches [RV09](#node-rv09).

**Review question:** When the coding agent cannot interact with the UI, should [BG03](#node-bg03) be an explicit repeatable handoff for every test iteration?

### Scenario C — Minor feature, short Q&A and one implementation PR

**Situation:** I describe a bounded feature to chat. The agent reviews the current code, asks only the essential questions and updates an existing issue or proposes one for approval.

**Trace:** [ST02](#node-st02) → [WS01](#node-ws01) → [WS02](#node-ws02) → [WS03](#node-ws03) → [SP01](#node-sp01). If the requirement is unclear, switch through [PL01](#node-pl01) → [PL02](#node-pl02) → [PL03](#node-pl03) → [PL04](#node-pl04) → [PL05](#node-pl05). Then [SP02–SP04](#node-sp02) → [TR01](#node-tr01) → [EX01](#node-ex01) → [EX02–EX04](#node-ex02) → [RV01–RV09](#node-rv01).

**Evidence:** Updated issue requirements, one scoped PR with tests, review and resolving keywords. A minor feature **does not automatically imply a minor version release**; [RL01](#node-rl01) makes a recommendation against the accumulated changes.

**Review question:** Is the proposed issue approval a standard gate for minor features, or should an already authorised workstream permit routine issue updates without interrupting me?

### Scenario D — Major change, iterative clarification and a branching PR tree

**Situation:** A long voice brief initiates a substantial redesign. Chat inspects the code and finds contradictions. Several rounds of questions are needed; the roadmap produces multiple issues and a PR dependency tree with independent siblings.

**Trace:** [ST02](#node-st02) → [WS01–WS03](#node-ws01) → [PL01](#node-pl01) → [PL02](#node-pl02) → [PL03](#node-pl03) → [PL04](#node-pl04) → [PL02](#node-pl02) (repeat as needed) → [PL05](#node-pl05) → [SP01–SP04](#node-sp01) → [TR01](#node-tr01) → [TR02](#node-tr02) → [TR03](#node-tr03).

**PR-tree loop:** [EX01–EX04](#node-ex01) → [RV01–RV09](#node-rv01) → [RV10](#node-rv10) → [TR03](#node-tr03). If one PR's required parent is blocked, work on a different independent sibling. Review can take [RV04](#node-rv04) → [SP01](#node-sp01) when issues need correction, or [RV04](#node-rv04) → [PL01](#node-pl01) when the architectural intent changes. Human testing can target an intermediate dogfood milestone.

**Evidence:** Durable issue tree and cross-links, explicit parent dependencies, stack bases, reviews and milestones. After the chosen milestone, complete the issue/PR audit and consider a major or minor release based on the actual compatibility changes.

**Review question:** Is [RV10](#node-rv10) → [TR07](#node-tr07) → [TR04](#node-tr04) the right place for the dogfood checkpoint, or should it precede more PR merges?

### Scenario E — Automated update plus CI quota limitation

**Situation:** A dependency-bump PR or audit finding arrives while other work is underway. Chat classifies it, reuses the current workstream if related, and delegates any required code changes.

**Trace:** [ST04](#node-st04) → [WS01–WS03](#node-ws01) → [SP01–SP04](#node-sp01) → [TR01](#node-tr01) → [EX01](#node-ex01) → [EX02–EX04](#node-ex02) → [RV01](#node-rv01) → [RV02](#node-rv02).

**Quota branch:** On a private repository with unavailable CI, [RV02](#node-rv02) records missing evidence and [RV17](#node-rv17) explicitly classifies whether required checks block progress. Where policy permits non-required CI to be set aside, continue only after appropriate independent review; if mandatory checks are unsatisfied, enter [EN02](#node-en02) with a resume trigger, rather than calling CI green. Public repositories can rely on their available CI alongside extensive local tests.

**Review question:** Should a purely automated, already-reviewed dependency PR route directly from issue reconciliation to PR review, bypassing coding entirely?

### Scenario F — First release, public-opening audit, or abandonment

**Situation:** A new project needs setup, extensive planning, a testable implementation and ultimately a public repository.

**Trace:** [ST01](#node-st01) → [WS01–WS03](#node-ws01) → [PL01–PL05](#node-pl01) → [SP01–SP04](#node-sp01) → [TR05](#node-tr05) → [TR01–TR03](#node-tr01) → implementation and review → closeout → [RL01](#node-rl01) → [RL02](#node-rl02) → [RL03](#node-rl03) → [RL04](#node-rl04) → [RL09](#node-rl09) → [RL05](#node-rl05) → [RL06](#node-rl06) → [RL07](#node-rl07) → [RL08](#node-rl08) → [EN01](#node-en01).

**Alternative ends:** A design found unsuitable at [PL05](#node-pl05) can be deferred to [EN02](#node-en02) with its open questions, or abandoned at [EN03](#node-en03), with issues and PRs reconciled. A release can also be deferred without discarding the completed development milestone.

**Review question:** Should opening the repository to the public occur *before* the first release, after it, or be an independent gate based on the repository's publicity policy?

### Review record for these examples

For each scenario, record whether the **entry, owner, evidence, decision, backtracking target, milestone and ending** match actual use. A changed scenario should update both the example and the canonical node transitions. If a scenario identifies a necessary additional edge, add it to `workflow.d2` and the destination sections rather than relying on narrative exceptions.


## Node catalogue

The ID is stable across D2, the blog, and the raw SVG's per-node machine-readable description. Each section states its owner, practical action, incoming context and allowed exits. Choose **one** outgoing transition from a diamond; rectangles describe work that has one next step. Normal completion is at the bottom, while exceptional stops may sit near the branch that triggers them.

### Starting points

#### ST01 — Initial release {#node-st01}

**Actor:** Human. **State:** Start a new project or first release. A new project or first public version.

**Enter from:** Pick this circle in the framed **START HERE** group.

**Move to:** [WS01 Open one workstream](#node-ws01) **when repo/initial**.

#### ST02 — Planned change {#node-st02}

**Actor:** Human. **State:** Ask for a feature or improvement. A feature or change of any size; classify scope later.

**Enter from:** Pick this circle in the framed **START HERE** group.

**Move to:** [WS01 Open one workstream](#node-ws01) **when planned change**.

#### ST03 — Bug or defect {#node-st03}

**Actor:** Human. **State:** Describe what is not working. An observed failure, including interactive Flutter problems.

**Enter from:** Pick this circle in the framed **START HERE** group.

**Move to:** [WS01 Open one workstream](#node-ws01) **when enter workstream**.

#### ST04 — Maintenance {#node-st04}

**Actor:** Human. **State:** Keep dependencies and tooling current. Manual or automated upkeep; also may be folded into another workstream.

**Enter from:** Pick this circle in the framed **START HERE** group.

**Move to:** [WS01 Open one workstream](#node-ws01) **when maintenance / audit**.

#### ST05 — Existing work {#node-st05}

**Actor:** Human. **State:** Resume an issue, PR or stalled task. Resume an existing issue, PR tree or review checkpoint.

**Enter from:** Pick this circle in the framed **START HERE** group.

**Move to:** [WS01 Open one workstream](#node-ws01) **when enter workstream**.

#### ST06 — Release request {#node-st06}

**Actor:** Human. **State:** Publish work that is already merged. Release-only entry that does not require new code.

**Enter from:** Pick this circle in the framed **START HERE** group.

**Move to:** [WS01 Open one workstream](#node-ws01) **when enter workstream**.

### Workstream intake and Projects handoff

#### WS01 — Open one workstream {#node-ws01}

**Actor:** Chat LLM. **State:** Keep related work in a single chat. Carry objective, linked GitHub state and next action; multiple independent chats may run.

**Enter from:** [ST01 Initial release](#node-st01) (repo/initial); [ST02 Planned change](#node-st02) (planned change); [ST04 Maintenance](#node-st04) (maintenance / audit); [ST03 Bug or defect](#node-st03) (enter workstream); [ST05 Existing work](#node-st05) (enter workstream); [ST06 Release request](#node-st06) (enter workstream).

**Move to:** [WS06 Read Projects handoff](#node-ws06) **when read handoff**.

#### WS02 — Inspect current baseline {#node-ws02}

**Actor:** Chat LLM. **State:** Check the code and outstanding work. Check current repository state, existing specifications and outstanding dependencies.

**Enter from:** [WS05 Save conversation link](#node-ws05) (inspect repository).

**Move to:** [WS04 Choose the starting route?](#node-ws04) **when classify entry**.

#### WS03 — Select discovery depth? {#node-ws03}

**Actor:** Human or Chat LLM. **State:** Choose how much planning is needed. Choose proportionate analysis; do not demand a full roadmap for a trivial fix.

**Enter from:** [WS04 Choose the starting route?](#node-ws04) (planned change).

**Move to:** [PL01 State detailed intent](#node-pl01) **when major / initial / unclear**; [SP01 Reconcile GitHub issues](#node-sp01) **when minor / clear / routine**; [BG01 Capture reproduction](#node-bg01) **when bug discovered**.

#### WS04 — Choose the starting route? {#node-ws04}

**Actor:** Human or Chat LLM. **State:** Route this request to the right process. Route the entry as new work, bug, resumed PR or release-only.

**Enter from:** [WS02 Inspect current baseline](#node-ws02) (classify entry).

**Move to:** [WS03 Select discovery depth?](#node-ws03) **when planned change**; [BG01 Capture reproduction](#node-bg01) **when reported bug**; [RV01 Inspect actual PR state](#node-rv01) **when resume PR**; [RL01 Recommend release intent](#node-rl01) **when release-only**.

#### WS05 — Save conversation link {#node-ws05}

**Actor:** Chat LLM. **State:** Record a resumption pointer in Projects. If given a conversation link, add it to the owning arran4/projects file alongside the relevant issue/PR; do not replicate active work details.

**Enter from:** [WS06 Read Projects handoff](#node-ws06) (register supplied conversation link).

**Move to:** [WS02 Inspect current baseline](#node-ws02) **when inspect repository**.

#### WS06 — Read Projects handoff {#node-ws06}

**Actor:** Chat LLM. **State:** Check related conversations and blockers. Read current arran4/projects, matching repo handoff and overlapping updates; use it as a between-chat index not as a live issue tracker.

**Enter from:** [WS01 Open one workstream](#node-ws01) (read handoff).

**Move to:** [WS05 Save conversation link](#node-ws05) **when register supplied conversation link**.

### Bug diagnosis and regression evidence

#### BG01 — Capture reproduction {#node-bg01}

**Actor:** Human. **State:** Show how the bug happens. Share observed and expected behaviour, stack traces, device or UI observations.

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (bug discovered); [BG05 Cause confirmed?](#node-bg05) (not reproduced); [WS04 Choose the starting route?](#node-ws04) (reported bug); [RV14 Observed behavior correct?](#node-rv14) (diagnosis wrong).

**Move to:** [BG02 How to debug?](#node-bg02) **when evidence**.

#### BG02 — How to debug? {#node-bg02}

**Actor:** Human or Chat LLM. **State:** Choose who should investigate it. Select human interactive, Chat LLM research or Coding LLM investigation.

**Enter from:** [BG01 Capture reproduction](#node-bg01) (evidence).

**Move to:** [BG06 Prepare human diagnosis](#node-bg06) **when human diagnosis**; [BG04 Chat diagnoses bug](#node-bg04) **when Chat diagnosis**; [BG07 Prepare coding-agent diagnosis](#node-bg07) **when coding-agent diagnosis**.

#### BG03 — Interactive diagnosis {#node-bg03}

**Actor:** Human. **State:** Reproduce and inspect the issue together. Especially for Flutter: reproduce with the human, copy evidence and results back to chat.

**Enter from:** [EX01 Who implements?](#node-ex01) (human UI debugging); [BG06 Prepare human diagnosis](#node-bg06) (instructions provided).

**Move to:** [BG05 Cause confirmed?](#node-bg05) **when copy findings**.

#### BG04 — Chat diagnoses bug {#node-bg04}

**Actor:** Chat LLM. **State:** Inspect code and explain the evidence. Investigate code or ask for focused coding-agent debugging when needed.

**Enter from:** [BG02 How to debug?](#node-bg02) (Chat diagnosis).

**Move to:** [BG05 Cause confirmed?](#node-bg05) **when analysis**.

#### BG05 — Cause confirmed? {#node-bg05}

**Actor:** Human or Chat LLM. **State:** Decide whether the diagnosis fits. Compare candidate cause to observed failure and decide if more diagnosis is required.

**Enter from:** [BG03 Interactive diagnosis](#node-bg03) (copy findings); [BG04 Chat diagnoses bug](#node-bg04) (analysis); [BG08 Coding-agent investigation](#node-bg08) (agent evidence).

**Move to:** [BG01 Capture reproduction](#node-bg01) **when not reproduced**; [PL01 State detailed intent](#node-pl01) **when needs redesign**; [BG09 Specify regression coverage](#node-bg09) **when confirmed**.

#### BG06 — Prepare human diagnosis {#node-bg06}

**Actor:** Chat LLM. **State:** Explain steps and request specific evidence. Explain the suspected cause, why human testing helps, step-by-step checks, expected observations, process and explicit questions.

**Enter from:** [BG02 How to debug?](#node-bg02) (human diagnosis).

**Move to:** [BG03 Interactive diagnosis](#node-bg03) **when instructions provided**.

#### BG07 — Prepare coding-agent diagnosis {#node-bg07}

**Actor:** Chat LLM. **State:** Write a focused investigation prompt. Give the human a coding-agent prompt with reproduction, context, tests and expected diagnostic evidence.

**Enter from:** [BG02 How to debug?](#node-bg02) (coding-agent diagnosis).

**Move to:** [BG08 Coding-agent investigation](#node-bg08) **when diagnostic prompt**.

#### BG08 — Coding-agent investigation {#node-bg08}

**Actor:** Coding LLM. **State:** Investigate with repository tools and tests. Reproduce the issue, gather test or log evidence and report findings without assuming the original hypothesis was correct.

**Enter from:** [BG07 Prepare coding-agent diagnosis](#node-bg07) (diagnostic prompt).

**Move to:** [BG05 Cause confirmed?](#node-bg05) **when agent evidence**.

#### BG09 — Specify regression coverage {#node-bg09}

**Actor:** Chat LLM. **State:** Plan a test for the original failure. Specify a regression test and appropriate TXTAR/txtar or broad scenario evidence that demonstrates the behaviour.

**Enter from:** [BG05 Cause confirmed?](#node-bg05) (confirmed).

**Move to:** [SP01 Reconcile GitHub issues](#node-sp01) **when regression test planned**.

### Clarification, contradictions and GitHub specification

#### PL01 — State detailed intent {#node-pl01}

**Actor:** Human. **State:** Explain the goal, constraints and examples. Describe what, why, constraints, examples and desired approach; answer and ask questions.

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (major / initial / unclear); [BG05 Cause confirmed?](#node-bg05) (needs redesign); [PL05 Enough specified?](#node-pl05) (not enough); [RV04 What needs changing?](#node-rv04) (requirements conflict); [RL09 Public exposure safe?](#node-rl09) (unsafe exposure).

**Move to:** [PL02 Ask clarifying questions](#node-pl02) **when draft intent**.

#### PL02 — Ask clarifying questions {#node-pl02}

**Actor:** Chat LLM. **State:** Ask what is missing or unclear. Ask targeted questions; revise scope after every material change.

**Enter from:** [PL01 State detailed intent](#node-pl01) (draft intent); [PL07 Contradictions resolved?](#node-pl07) (more questions).

**Move to:** [PL03 Contradictions found?](#node-pl03) **when questions answered**.

#### PL03 — Contradictions found? {#node-pl03}

**Actor:** Chat LLM. **State:** Check for incompatible requirements. Challenge incompatible requirements, tests or architecture; revisit earlier decisions.

**Enter from:** [PL02 Ask clarifying questions](#node-pl02) (questions answered).

**Move to:** [PL04 Resolve ambiguities](#node-pl04) **when contradictions found**; [PL05 Enough specified?](#node-pl05) **when no contradictions**.

#### PL04 — Resolve ambiguities {#node-pl04}

**Actor:** Human. **State:** Agree on answers or defer open questions. Discuss alternatives, settle contradictions, or defer non-blocking questions explicitly.

**Enter from:** [PL03 Contradictions found?](#node-pl03) (contradictions found).

**Move to:** [PL07 Contradictions resolved?](#node-pl07) **when answers recorded**.

#### PL05 — Enough specified? {#node-pl05}

**Actor:** Human or Chat LLM. **State:** Decide whether there is enough to start. Advance when sufficient, not necessarily complete; otherwise loop or park.

**Enter from:** [PL03 Contradictions found?](#node-pl03) (no contradictions); [PL07 Contradictions resolved?](#node-pl07) (resolved or deferred).

**Move to:** [PL01 State detailed intent](#node-pl01) **when not enough**; [CL05 Park Projects handoff](#node-cl05) **when defer**; [CL06 Retire Projects handoff](#node-cl06) **when abandon**; [SP01 Reconcile GitHub issues](#node-sp01) **when sufficient**.

#### PL07 — Contradictions resolved? {#node-pl07}

**Actor:** Human or Chat LLM. **State:** Decide whether more questions are needed. Confirm conflicts were resolved, deferred or need another round of clarification.

**Enter from:** [PL04 Resolve ambiguities](#node-pl04) (answers recorded).

**Move to:** [PL02 Ask clarifying questions](#node-pl02) **when more questions**; [PL05 Enough specified?](#node-pl05) **when resolved or deferred**.

#### SP01 — Reconcile GitHub issues {#node-sp01}

**Actor:** Chat LLM. **State:** Match the work to existing GitHub issues. Search existing issues and PRs; align expected outcomes and acceptance cases.

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (minor / clear / routine); [PL05 Enough specified?](#node-pl05) (sufficient); [RV04 What needs changing?](#node-rv04) (issue/spec mismatch); [BG09 Specify regression coverage](#node-bg09) (regression test planned).

**Move to:** [SP02 Issue record adequate?](#node-sp02) **when reconcile**.

#### SP02 — Issue record adequate? {#node-sp02}

**Actor:** Human or Chat LLM. **State:** Check whether an issue covers the work. Check missing tests, issue ownership, resolving scope and change implications.

**Enter from:** [SP01 Reconcile GitHub issues](#node-sp01) (reconcile).

**Move to:** [SP03 Request issue approval](#node-sp03) **when new issue / major reframe**; [SP04 Persist accepted spec](#node-sp04) **when existing issues valid**.

#### SP03 — Request issue approval {#node-sp03}

**Actor:** Human. **State:** Get approval for new or rewritten issues. Approve new issue creation or significant scope changes; maintain existing records when authorised.

**Enter from:** [SP02 Issue record adequate?](#node-sp02) (new issue / major reframe).

**Move to:** [SP05 Issue approval received?](#node-sp05) **when approval requested**.

#### SP04 — Persist accepted spec {#node-sp04}

**Actor:** Chat LLM. **State:** Record agreed requirements in GitHub. Record decisions, open questions, criteria and dependencies in GitHub and linked conversation.

**Enter from:** [SP02 Issue record adequate?](#node-sp02) (existing issues valid); [SP05 Issue approval received?](#node-sp05) (approved).

**Move to:** [SP06 Repository already exists?](#node-sp06) **when spec saved**.

#### SP05 — Issue approval received? {#node-sp05}

**Actor:** Human. **State:** Check whether the changed scope is approved. Approve an entirely new issue or significant change of specification, or hold it until clarified.

**Enter from:** [SP03 Request issue approval](#node-sp03) (approval requested).

**Move to:** [SP04 Persist accepted spec](#node-sp04) **when approved**; [CL05 Park Projects handoff](#node-cl05) **when not approved**.

#### SP06 — Repository already exists? {#node-sp06}

**Actor:** Human or Chat LLM. **State:** Choose existing source or bootstrap. After accepted requirements are recorded, choose an existing repository or approved new repo bootstrap.

**Enter from:** [SP04 Persist accepted spec](#node-sp04) (spec saved).

**Move to:** [TR01 Work size and dependency?](#node-tr01) **when existing repository**; [TR05 Bootstrap repository](#node-tr05) **when new approved repo**.

### PR-tree planning and dogfood checkpoints

#### TR01 — Work size and dependency? {#node-tr01}

**Actor:** Human or Chat LLM. **State:** Decide whether one PR is enough. Choose scope from dependencies and likely conflicts, not arbitrary linear stacking.

**Enter from:** [TR05 Bootstrap repository](#node-tr05) (repository ready); [SP06 Repository already exists?](#node-sp06) (existing repository).

**Move to:** [TR02 Plan PR dependency tree](#node-tr02) **when complex / dependent**; [EX01 Who implements?](#node-ex01) **when single PR**.

#### TR02 — Plan PR dependency tree {#node-tr02}

**Actor:** Chat LLM. **State:** Map PR dependencies and merge order. Map sibling PRs that can merge independently and dependent children that must wait.

**Enter from:** [TR01 Work size and dependency?](#node-tr01) (complex / dependent).

**Move to:** [TR03 Select runnable node](#node-tr03) **when tree dependencies**.

#### TR03 — Select runnable node {#node-tr03}

**Actor:** Human or Chat LLM. **State:** Pick work that is ready and unblocked. Choose a ready node; if one branch blocks, advance an independent sibling.

**Enter from:** [TR02 Plan PR dependency tree](#node-tr02) (tree dependencies); [RV10 More work in PR tree?](#node-rv10) (next sibling / child); [TR07 Dogfood milestone needed?](#node-tr07) (more work first).

**Move to:** [TR06 Runnable branch available?](#node-tr06) **when check dependency status**.

#### TR04 — Dogfood checkpoint {#node-tr04}

**Actor:** Human. **State:** Test a useful intermediate milestone. Confirm which portion of the tree is sufficient to test or merge now.

**Enter from:** [TR07 Dogfood milestone needed?](#node-tr07) (dogfood required).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when test milestone**.

#### TR05 — Bootstrap repository {#node-tr05}

**Actor:** Chat LLM. **State:** Set up the repo, tests and documentation. After human scope approval, initialise the repository, essential CI, documentation and licence, delegating source setup to the coding model as needed.

**Enter from:** [SP06 Repository already exists?](#node-sp06) (new approved repo).

**Move to:** [TR01 Work size and dependency?](#node-tr01) **when repository ready**.

#### TR06 — Runnable branch available? {#node-tr06}

**Actor:** Human or Chat LLM. **State:** Choose ready work, defer or cancel. Check PR dependencies to find an unblocked node or preserve a blocker/cancellation.

**Enter from:** [TR03 Select runnable node](#node-tr03) (check dependency status).

**Move to:** [EX01 Who implements?](#node-ex01) **when unblocked node**; [CL05 Park Projects handoff](#node-cl05) **when all blocked**; [CL06 Retire Projects handoff](#node-cl06) **when cancel**.

#### TR07 — Dogfood milestone needed? {#node-tr07}

**Actor:** Human or Chat LLM. **State:** Decide whether to test the milestone. After a PR-tree checkpoint, decide if a runnable milestone needs human testing before closeout.

**Enter from:** [RV10 More work in PR tree?](#node-rv10) (milestone reached).

**Move to:** [TR04 Dogfood checkpoint](#node-tr04) **when dogfood required**; [CL01 Audit issues and PRs](#node-cl01) **when no more testing**; [TR03 Select runnable node](#node-tr03) **when more work first**.

### Implementation

#### EX01 — Who implements? {#node-ex01}

**Actor:** Human or Chat LLM. **State:** Choose between a direct fix and an agent. For small changes try direct Chat LLM fix when able; otherwise write a prompt for Codex/Agy.

**Enter from:** [TR01 Work size and dependency?](#node-tr01) (single PR); [TR06 Runnable branch available?](#node-tr06) (unblocked node).

**Move to:** [EX05 Chat direct fix](#node-ex05) **when tiny + chat capable**; [EX02 Prepare implementation](#node-ex02) **when coding model**; [BG03 Interactive diagnosis](#node-bg03) **when human UI debugging**.

#### EX02 — Prepare implementation {#node-ex02}

**Actor:** Chat LLM. **State:** Write an actionable implementation prompt. Specify accepted issue state, exact branch, constraints, tests, dependency tree and expected PRs.

**Enter from:** [EX01 Who implements?](#node-ex01) (coding model); [RV06 Complex correction](#node-rv06) (corrective prompt).

**Move to:** [EX03 Code and test locally](#node-ex03) **when prompt approved**.

#### EX03 — Code and test locally {#node-ex03}

**Actor:** Coding LLM. **State:** Build the change and run real tests. Use agent in interactive or YOLO container; iterate on code, tests and generator output.

**Enter from:** [EX02 Prepare implementation](#node-ex02) (prompt approved).

**Move to:** [EX04 Publish PR tree](#node-ex04) **when tests and code**.

#### EX04 — Publish PR tree {#node-ex04}

**Actor:** Coding LLM. **State:** Push code and open linked pull requests. Push real commits and create the promised PRs, with explicit dependent bases and linked issues.

**Enter from:** [EX03 Code and test locally](#node-ex03) (tests and code).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when published**.

#### EX05 — Chat direct fix {#node-ex05}

**Actor:** Chat LLM. **State:** Make and test a small change in chat. Use available tooling to edit and test an isolated authorised branch, publish an inspectable PR.

**Enter from:** [EX01 Who implements?](#node-ex01) (tiny + chat capable).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when published**.

### Test evidence, PR review and UI verification

#### QA01 — Check test evidence {#node-qa01}

**Actor:** Chat LLM. **State:** Review unit, regression and broad scenarios. Assess updated regression tests, integration coverage, TXTAR/txtar CLI or API examples and visible end-to-end evidence in PR.

**Enter from:** [RV17 Required CI available?](#node-rv17) (checks acceptable).

**Move to:** [RV03 Review correctness?](#node-rv03) **when tests assessed**.

#### RV01 — Inspect actual PR state {#node-rv01}

**Actor:** Chat LLM. **State:** Inspect what the PR actually contains. Verify published commits, comments, PR metadata, dependencies and fresh tests.

**Enter from:** [TR04 Dogfood checkpoint](#node-tr04) (test milestone); [EX04 Publish PR tree](#node-ex04) (published); [EX05 Chat direct fix](#node-ex05) (published); [RV05 Small repair](#node-rv05) (republished); [WS04 Choose the starting route?](#node-ws04) (resume PR).

**Move to:** [RV02 Inspect CI evidence](#node-rv02) **when current head**.

#### RV02 — Inspect CI evidence {#node-rv02}

**Actor:** Chat LLM. **State:** Read check results and missing evidence. Required checks cannot be marked passed if absent; rerun or use accepted alternatives.

**Enter from:** [RV01 Inspect actual PR state](#node-rv01) (current head).

**Move to:** [RV17 Required CI available?](#node-rv17) **when check required CI**.

#### RV03 — Review correctness? {#node-rv03}

**Actor:** Human or Chat LLM. **State:** Compare the PR with requirements and tests. Check behaviour, issue match, closing keywords, test quality, conflicts and merge ordering.

**Enter from:** [QA01 Check test evidence](#node-qa01) (tests assessed).

**Move to:** [RV04 What needs changing?](#node-rv04) **when findings**.

#### RV04 — What needs changing? {#node-rv04}

**Actor:** Human or Chat LLM. **State:** Choose the right correction or review path. Route repair to smallest appropriate stage, including back to Q&A and issue specifications.

**Enter from:** [RV03 Review correctness?](#node-rv03) (findings); [RV08 Merge approved?](#node-rv08) (changes requested); [RV12 Extra verification needed?](#node-rv12) (human objections).

**Move to:** [RV05 Small repair](#node-rv05) **when simple conflict/fix**; [RV06 Complex correction](#node-rv06) **when complex repair**; [PL01 State detailed intent](#node-pl01) **when requirements conflict**; [SP01 Reconcile GitHub issues](#node-sp01) **when issue/spec mismatch**; [RV07 Human PR review](#node-rv07) **when ready**; [CL06 Retire Projects handoff](#node-cl06) **when work no longer wanted**.

#### RV05 — Small repair {#node-rv05}

**Actor:** Human. **State:** Fix a straightforward issue or conflict. Resolve trivial conflict or tiny fix; Chat may patch when authorised, then republish and review.

**Enter from:** [RV04 What needs changing?](#node-rv04) (simple conflict/fix).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when republished**.

#### RV06 — Complex correction {#node-rv06}

**Actor:** Chat LLM. **State:** Send a focused request to a coding agent. Produce targeted prompt for Codex/Agy; repair existing branch/PR when safe.

**Enter from:** [RV04 What needs changing?](#node-rv04) (complex repair); [RV14 Observed behavior correct?](#node-rv14) (patch faulty).

**Move to:** [EX02 Prepare implementation](#node-ex02) **when corrective prompt**.

#### RV07 — Human PR review {#node-rv07}

**Actor:** Human. **State:** Read and test the proposed changes. Read changes, test where appropriate, request redesign, defer, or approve.

**Enter from:** [RV04 What needs changing?](#node-rv04) (ready).

**Move to:** [RV12 Extra verification needed?](#node-rv12) **when review feedback**.

#### RV08 — Merge approved? {#node-rv08}

**Actor:** Human. **State:** Decide whether this PR may be merged. Explicit approval; passing CI or model readiness is not merge authority.

**Enter from:** [RV12 Extra verification needed?](#node-rv12) (normal PR accepted); [RV14 Observed behavior correct?](#node-rv14) (verified).

**Move to:** [RV04 What needs changing?](#node-rv04) **when changes requested**; [CL05 Park Projects handoff](#node-cl05) **when hold**; [CL06 Retire Projects handoff](#node-cl06) **when cancel work**; [RV09 Merge eligible node](#node-rv09) **when approved**.

#### RV09 — Merge eligible node {#node-rv09}

**Actor:** GitHub / CI. **State:** Merge a reviewed, eligible pull request. Merge only valid, approved PR with required checks and dependency prerequisites satisfied.

**Enter from:** [RV08 Merge approved?](#node-rv08) (approved).

**Move to:** [RV10 More work in PR tree?](#node-rv10) **when merged**.

#### RV10 — More work in PR tree? {#node-rv10}

**Actor:** Human or Chat LLM. **State:** Continue another PR or close the milestone. Update bases and conflicts; choose another ready sibling or pause dependent branch.

**Enter from:** [RV09 Merge eligible node](#node-rv09) (merged).

**Move to:** [TR03 Select runnable node](#node-tr03) **when next sibling / child**; [CL05 Park Projects handoff](#node-cl05) **when remaining work blocked**; [TR07 Dogfood milestone needed?](#node-tr07) **when milestone reached**.

#### RV12 — Extra verification needed? {#node-rv12}

**Actor:** Human or Chat LLM. **State:** Choose normal review or more evidence. After PR review, route bug/UI evidence to verification, objections to repair, otherwise human merge decision.

**Enter from:** [RV07 Human PR review](#node-rv07) (review feedback).

**Move to:** [RV04 What needs changing?](#node-rv04) **when human objections**; [RV15 Who verifies the UI?](#node-rv15) **when bug or UI proof**; [RV08 Merge approved?](#node-rv08) **when normal PR accepted**.

#### RV13 — Human verifies behavior {#node-rv13}

**Actor:** Human. **State:** Provide build and practical test steps. Run application or build locally, check the proposed bug diagnosis or UI change and return precise observations.

**Enter from:** [RV15 Who verifies the UI?](#node-rv15) (human interactive).

**Move to:** [RV14 Observed behavior correct?](#node-rv14) **when human findings**.

#### RV14 — Observed behavior correct? {#node-rv14}

**Actor:** Human or Chat LLM. **State:** Accept evidence or reinvestigate failures. Check visual/manual/automated evidence and route a wrong diagnosis to bug intake or a faulty patch to repair.

**Enter from:** [RV13 Human verifies behavior](#node-rv13) (human findings); [RV16 Automate visual proof](#node-rv16) (automated captures).

**Move to:** [RV08 Merge approved?](#node-rv08) **when verified**; [BG01 Capture reproduction](#node-bg01) **when diagnosis wrong**; [RV06 Complex correction](#node-rv06) **when patch faulty**.

#### RV15 — Who verifies the UI? {#node-rv15}

**Actor:** Human or Chat LLM. **State:** Choose automated proof or human testing. Use Playwright or a reliable UI harness where suitable, otherwise human interactive device/local testing.

**Enter from:** [RV12 Extra verification needed?](#node-rv12) (bug or UI proof).

**Move to:** [RV13 Human verifies behavior](#node-rv13) **when human interactive**; [RV16 Automate visual proof](#node-rv16) **when Playwright or UI harness**.

#### RV16 — Automate visual proof {#node-rv16}

**Actor:** Coding LLM. **State:** Attach UI captures or scenario results. Coding LLM or Chat tooling: Produce Playwright UI tests, golden captures or scenario previews in PR/chat for verification.

**Enter from:** [RV15 Who verifies the UI?](#node-rv15) (Playwright or UI harness).

**Move to:** [RV14 Observed behavior correct?](#node-rv14) **when automated captures**.

#### RV17 — Required CI available? {#node-rv17}

**Actor:** Chat LLM. **State:** Check whether required checks are satisfied. Evaluate required checks, pending, failure and private quota; do not claim missing CI has passed.

**Enter from:** [RV02 Inspect CI evidence](#node-rv02) (check required CI).

**Move to:** [QA01 Check test evidence](#node-qa01) **when checks acceptable**; [CL05 Park Projects handoff](#node-cl05) **when required checks blocked**.

### Closeout, cross-chat handoffs and trackers

#### CL01 — Audit issues and PRs {#node-cl01}

**Actor:** Chat LLM. **State:** Confirm that the right issues are resolved. Check Fixes/Closes references, issue statuses, acceptance evidence, final implementation notes.

**Enter from:** [TR07 Dogfood milestone needed?](#node-tr07) (no more testing).

**Move to:** [CL02 Notify dependencies](#node-cl02) **when issues correct**.

#### CL02 — Notify dependencies {#node-cl02}

**Actor:** Chat LLM. **State:** Update anything that depends on this work. Check version constraints, dependent PRs, projects and actionable update notices.

**Enter from:** [CL01 Audit issues and PRs](#node-cl01) (issues correct).

**Move to:** [CL03 Refresh Projects handoff](#node-cl03) **when notify**.

#### CL03 — Refresh Projects handoff {#node-cl03}

**Actor:** Chat LLM. **State:** Keep only current links and next steps. Update arran4/projects with roadmap, workstream and current milestone.

**Enter from:** [CL02 Notify dependencies](#node-cl02) (notify).

**Move to:** [CL04 Update PR repository](#node-cl04) **when tracker current**.

#### CL04 — Update PR repository {#node-cl04}

**Actor:** Chat LLM. **State:** Record announcement tasks and readiness. Update arran4/public-relations with accurate materials or future campaign tasks.

**Enter from:** [CL03 Refresh Projects handoff](#node-cl03) (tracker current).

**Move to:** [RL01 Recommend release intent](#node-rl01) **when evaluate version**.

#### CL05 — Park Projects handoff {#node-cl05}

**Actor:** Chat LLM. **State:** Save the blocker and resumption link. When pausing, update arran4/projects with current chat link, blocker, next action and relevant issue/PR, not duplicate task details.

**Enter from:** [PL05 Enough specified?](#node-pl05) (defer); [RV08 Merge approved?](#node-rv08) (hold); [RV10 More work in PR tree?](#node-rv10) (remaining work blocked); [RL02 Publish now?](#node-rl02) (defer release); [RL05 History rewrite needed?](#node-rl05) (rewrite consent pending); [RL08 Release verified?](#node-rl08) (publishing failed); [SP05 Issue approval received?](#node-sp05) (not approved); [TR06 Runnable branch available?](#node-tr06) (all blocked); [RV17 Required CI available?](#node-rv17) (required checks blocked).

**Move to:** [EN02 Deferred / blocked](#node-en02) **when handoff parked**.

#### CL06 — Retire Projects handoff {#node-cl06}

**Actor:** Chat LLM. **State:** Keep useful links, mark work stopped. When abandoning, preserve a concise reason and link, without pretending source issues or PRs were completed.

**Enter from:** [PL05 Enough specified?](#node-pl05) (abandon); [RV04 What needs changing?](#node-rv04) (work no longer wanted); [RV08 Merge approved?](#node-rv08) (cancel work); [TR06 Runnable branch available?](#node-tr06) (cancel).

**Move to:** [EN03 Abandoned](#node-en03) **when closure recorded**.

### Release and first-publication safety

#### RL01 — Recommend release intent {#node-rl01}

**Actor:** Human or Chat LLM. **State:** Choose whether and how to release this work. Use accepted scope, roadmap, merged changes and release guidance; patch may be routine if authorised.

**Enter from:** [CL04 Update PR repository](#node-cl04) (evaluate version); [WS04 Choose the starting route?](#node-ws04) (release-only).

**Move to:** [RL02 Publish now?](#node-rl02) **when release recommendation**.

#### RL02 — Publish now? {#node-rl02}

**Actor:** Human. **State:** Decide whether it is time to publish. May choose no release, normal versioned release, or delayed/public opening.

**Enter from:** [RL01 Recommend release intent](#node-rl01) (release recommendation).

**Move to:** [EN01 Completed](#node-en01) **when no release / done**; [CL05 Park Projects handoff](#node-cl05) **when defer release**; [RL03 First public opening?](#node-rl03) **when release approved**.

#### RL03 — First public opening? {#node-rl03}

**Actor:** Human. **State:** Check whether the repo must become public. If private-to-public, require broader quality, provenance, licence, copyright and link checks.

**Enter from:** [RL02 Publish now?](#node-rl02) (release approved).

**Move to:** [RL07 Run release workflow](#node-rl07) **when already public / private release**; [RL04 Audit public exposure](#node-rl04) **when first public opening**.

#### RL04 — Audit public exposure {#node-rl04}

**Actor:** Chat LLM. **State:** Inspect secrets, licences and history. Inspect repository history, links, copyright, documentation, quality and release assets.

**Enter from:** [RL03 First public opening?](#node-rl03) (first public opening).

**Move to:** [RL09 Public exposure safe?](#node-rl09) **when audit completed**.

#### RL05 — History rewrite needed? {#node-rl05}

**Actor:** Human. **State:** Ask before rewriting published Git history. Force-push or rewrite only on explicit informed approval; consider collaborators and tags.

**Enter from:** [RL09 Public exposure safe?](#node-rl09) (safe to proceed).

**Move to:** [RL06 Approve visibility change](#node-rl06) **when no rewrite / approved rewrite**; [CL05 Park Projects handoff](#node-cl05) **when rewrite consent pending**.

#### RL06 — Approve visibility change {#node-rl06}

**Actor:** Human. **State:** Approve making the repository public. Make public only after verified audit and approval.

**Enter from:** [RL05 History rewrite needed?](#node-rl05) (no rewrite / approved rewrite).

**Move to:** [RL07 Run release workflow](#node-rl07) **when public approved**.

#### RL07 — Run release workflow {#node-rl07}

**Actor:** GitHub / CI. **State:** Run the approved tagging and release action. Use documented release-safe action to tag and publish; no duplicate release publisher.

**Enter from:** [RL03 First public opening?](#node-rl03) (already public / private release); [RL06 Approve visibility change](#node-rl06) (public approved); [RL08 Release verified?](#node-rl08) (retry release).

**Move to:** [RL08 Release verified?](#node-rl08) **when workflow complete**.

#### RL08 — Release verified? {#node-rl08}

**Actor:** Chat LLM. **State:** Check tags, assets and distribution. Confirm actual tag, release, packages and downstream impact; update tracker and announcements.

**Enter from:** [RL07 Run release workflow](#node-rl07) (workflow complete).

**Move to:** [EN01 Completed](#node-en01) **when confirmed**; [CL05 Park Projects handoff](#node-cl05) **when publishing failed**; [RL07 Run release workflow](#node-rl07) **when retry release**.

#### RL09 — Public exposure safe? {#node-rl09}

**Actor:** Human or Chat LLM. **State:** Decide if audit findings block publication. Review secrets, licensing, ownership and history audit results; substantial unresolved exposure returns to specification.

**Enter from:** [RL04 Audit public exposure](#node-rl04) (audit completed).

**Move to:** [RL05 History rewrite needed?](#node-rl05) **when safe to proceed**; [PL01 State detailed intent](#node-pl01) **when unsafe exposure**.

### Terminal outcomes

#### EN01 — Completed {#node-en01}

**Actor:** GitHub / CI. **State:** The agreed milestone is finished. Work and any authorised release completed; issue and tracker state reconciled.

**Enter from:** [RL02 Publish now?](#node-rl02) (no release / done); [RL08 Release verified?](#node-rl08) (confirmed).

**Move to:** Terminal node; no further workflow transition.

#### EN02 — Deferred / blocked {#node-en02}

**Actor:** GitHub / CI. **State:** Record what is blocked and when to resume. Record what remains, owner, dependency, and the condition for resuming.

**Enter from:** [CL05 Park Projects handoff](#node-cl05) (handoff parked).

**Move to:** Terminal node; no further workflow transition.

#### EN03 — Abandoned {#node-en03}

**Actor:** Human. **State:** Stop the work and record why. Document cancellation, superseded PRs, issue closure/retention and change of direction.

**Enter from:** [CL06 Retire Projects handoff](#node-cl06) (closure recorded).

**Move to:** Terminal node; no further workflow transition.

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
