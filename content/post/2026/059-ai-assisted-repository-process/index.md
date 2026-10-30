---
title: "AI-Assisted Repository Development: A Unified Process"
date: 2026-10-30T17:20:00+11:00
draft: false
guidance: ["agent-management"]
tags: ["agents", "automation", "chatgpt", "ci", "codex", "github", "orchestration", "workflow"]
categories: ["Software Development", "LLM Instructions", "Automation"]
---

<!-- cspell:words agy Codex dogfood handoff handoffs inspectable workstream workstreams -->

My repository development process is neither a rigid waterfall nor a collection of independent coding-agent prompts. It starts from an idea, bug, change, maintenance event, existing pull request, or release request. I use a **Chat LLM as a management and review companion**, coding agents for repository work when appropriate, and GitHub to preserve the specification and implementation history.

**This is the current process reference.** It is designed for both human readers and a fresh Chat LLM that needs to determine where a workstream stands, what evidence is missing, what action it can take, and what to do next. The diagram is one canonical, editable workflow, not eleven competing views. It models decision points, alternative routes, revisiting earlier work, and explicit endings.

Normally I maintain **one conversation per coherent workstream**. That conversation can manage several related issues and a dependency tree of pull requests; other conversations can manage other projects or branches at the same time. Conversation is part of the working design discussion, while GitHub issues, PRs, commits and the supporting project repositories preserve durable decisions and observable outcomes.

## Main process diagram

![Unified AI-assisted repository workflow](workflow.svg)

[Open full SVG](workflow.svg) · [Open PNG export](workflow.png) · [Edit D2 source](workflow.d2) · [Browse node catalogue](#node-catalogue)

This is a large diagram intended to be opened and zoomed. The PNG export is an easier-to-read alternative in Firefox when the SVG automatically resizes. Each D2 node contains an ID, a **header and brief purpose**, actor colour, a detailed hover description and a link back to its corresponding section in this article. The embedded image may not expose the links, so open the SVG itself or use the catalogue below. The `.d2` source is also suitable for a coding or management agent to read directly; do not rely on visual interpretation alone.

### Diagram conventions

| Element | Meaning |
| --- | --- |
| **Circle** | Independent starting point; different starts may enter different phases |
| **Rectangle** | Activity, observable state or system action |
| **Diamond** | Decision with labelled conditional exits; not automatically an approval |
| **Oval** | Terminal outcome: completed, deferred/blocked or abandoned |
| Amber | **Human** — intent, interactive debugging, review, consequential decisions |
| Blue | **Chat LLM** — investigation, Q&A, prompts, specifications, PR management and review |
| Violet | **Coding LLM** — Codex/Agy or another coding agent operating in a repository/container |
| Green | **GitHub / CI** — durable issues/PRs, checks, merges, releases and recorded final state |

The diagram is grouped by **phase**, not by a strict single actor per lane: each phase can involve several actors. The colours and the explicit actor field in the node descriptions distinguish responsibility. Long feedback edges are intentionally present because work can return to the right earlier state instead of creating a new issue or session mechanically.

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
| **Chat LLM** | Research, Q&A, contradictions, issue/PR specification, prompt creation, PR-tree selection, review, CI interpretation, GitHub administration, closeout and trackers | May lack repository or terminal access; state must be checked with tools. Small direct fixes are conditional on capability and verification. Never claim a tool action or a passing check without evidence |
| **Coding LLM** | Container-based implementation, debugging, tests, commits, PR tree creation, complex corrections | No independent authority over human-owned decisions; existing issue and PR specifications govern scope. A completed run is not a reviewed result |
| **GitHub / CI** | Durable issues and PRs, current commits and branches, checks, release workflows, labels, publication and merge results | A failed, pending or absent check is not approval; branches and bot messages may be stale; repository policies must be respected |

Repository-specific developer instructions, [blog guidance](/blog/guidance/) and applicable agent skills can inform implementation, but they are **inputs to a node**, not a separate compulsory stage in this diagram.

## Instructions to a fresh management LLM

Read this article and the canonical `workflow.d2` source. Treat each node ID as a **checkpoint, not a mandatory sequential checklist**. First inspect the target repository, PRs/issues and the latest conversation context. Report the current node, concrete evidence, unresolved decisions, and the permitted next node(s). If the work is already at review, do not restart planning without reason. If a major design conflict appears, do not force a superficial patch: return to clarification and reconcile the issues.

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

## Node catalogue

The headings below are generated from the canonical D2 nodes. Each lists the actor, purpose, input paths and conditional exits; following the links is sufficient to navigate the process without visually decoding the SVG.

### Starting points

#### ST01 — Initial release {#node-st01}

**Actor:** Human. **State:** Repository + first release. A new project or first public version.

**Enter from:** Independent starting point.

**Move to:** [WS01 Open one workstream](#node-ws01) **when repo/initial**.

#### ST02 — Planned change {#node-st02}

**Actor:** Human. **State:** Feature, minor or major. A feature or change of any size; classify scope later.

**Enter from:** Independent starting point.

**Move to:** [WS01 Open one workstream](#node-ws01) **when planned change**.

#### ST03 — Bug or defect {#node-st03}

**Actor:** Human. **State:** Observed behaviour. An observed failure, including interactive Flutter problems.

**Enter from:** Independent starting point.

**Move to:** [BG01 Capture reproduction](#node-bg01) **when bug**.

#### ST04 — Maintenance {#node-st04}

**Actor:** Human. **State:** Dependencies, tooling, audit. Manual or automated upkeep; also may be folded into another workstream.

**Enter from:** Independent starting point.

**Move to:** [WS01 Open one workstream](#node-ws01) **when maintenance / audit**.

#### ST05 — Existing work {#node-st05}

**Actor:** Human. **State:** PR, CI, stalled task. Resume an existing issue, PR tree or review checkpoint.

**Enter from:** Independent starting point.

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when resume current PR**.

#### ST06 — Release request {#node-st06}

**Actor:** Human. **State:** Already merged work. Release-only entry that does not require new code.

**Enter from:** Independent starting point.

**Move to:** [RL01 Recommend release intent](#node-rl01) **when release-only**.

### Workstream intake

#### WS01 — Open one workstream {#node-ws01}

**Actor:** Chat LLM. **State:** One chat, many related PRs. Carry objective, linked GitHub state and next action; multiple independent chats may run.

**Enter from:** [ST01 Initial release](#node-st01) (repo/initial); [ST02 Planned change](#node-st02) (planned change); [ST04 Maintenance](#node-st04) (maintenance / audit).

**Move to:** [WS02 Inspect current baseline](#node-ws02) **when inspect**.

#### WS02 — Inspect current baseline {#node-ws02}

**Actor:** Chat LLM. **State:** Code, issues, PRs, releases. Check current repository state, existing specifications and outstanding dependencies.

**Enter from:** [WS01 Open one workstream](#node-ws01) (inspect).

**Move to:** [WS03 Select discovery depth?](#node-ws03) **when classify**.

#### WS03 — Select discovery depth? {#node-ws03}

**Actor:** Chat LLM. **State:** Bug, small or architectural. Choose proportionate analysis; do not demand a full roadmap for a trivial fix.

**Enter from:** [WS02 Inspect current baseline](#node-ws02) (classify).

**Move to:** [PL01 State detailed intent](#node-pl01) **when major / initial / unclear**; [SP01 Reconcile GitHub issues](#node-sp01) **when minor / clear / routine**; [BG01 Capture reproduction](#node-bg01) **when bug discovered**.

### Bug diagnosis

#### BG01 — Capture reproduction {#node-bg01}

**Actor:** Human. **State:** Logs, steps, environment. Share observed and expected behaviour, stack traces, device or UI observations.

**Enter from:** [ST03 Bug or defect](#node-st03) (bug); [WS03 Select discovery depth?](#node-ws03) (bug discovered); [BG05 Confirm defect hypothesis](#node-bg05) (not reproduced).

**Move to:** [BG02 How to debug?](#node-bg02) **when evidence**.

#### BG02 — How to debug? {#node-bg02}

**Actor:** Chat LLM. **State:** Size, complexity, tooling. Select human interactive, Chat LLM research or Coding LLM investigation.

**Enter from:** [BG01 Capture reproduction](#node-bg01) (evidence).

**Move to:** [BG03 Interactive diagnosis](#node-bg03) **when interactive UI**; [BG04 Delegate diagnosis](#node-bg04) **when delegate**.

#### BG03 — Interactive diagnosis {#node-bg03}

**Actor:** Human. **State:** Run UI, debugger, device. Especially for Flutter: reproduce with the human, copy evidence and results back to chat.

**Enter from:** [BG02 How to debug?](#node-bg02) (interactive UI); [EX01 Who implements?](#node-ex01) (human UI debugging).

**Move to:** [BG05 Confirm defect hypothesis](#node-bg05) **when copy findings**.

#### BG04 — Delegate diagnosis {#node-bg04}

**Actor:** Chat LLM. **State:** Chat or coding model. Investigate code or ask for focused coding-agent debugging when needed.

**Enter from:** [BG02 How to debug?](#node-bg02) (delegate).

**Move to:** [BG05 Confirm defect hypothesis](#node-bg05) **when analysis**.

#### BG05 — Confirm defect hypothesis {#node-bg05}

**Actor:** Chat LLM. **State:** Evidence, regression test. Compare candidate cause to observed failure and decide if more diagnosis is required.

**Enter from:** [BG03 Interactive diagnosis](#node-bg03) (copy findings); [BG04 Delegate diagnosis](#node-bg04) (analysis).

**Move to:** [BG01 Capture reproduction](#node-bg01) **when not reproduced**; [SP01 Reconcile GitHub issues](#node-sp01) **when cause sufficient**; [PL01 State detailed intent](#node-pl01) **when needs redesign**.

### Clarification and specification

#### PL01 — State detailed intent {#node-pl01}

**Actor:** Human. **State:** Voice, prose, examples. Describe what, why, constraints, examples and desired approach; answer and ask questions.

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (major / initial / unclear); [BG05 Confirm defect hypothesis](#node-bg05) (needs redesign); [PL05 Enough specified?](#node-pl05) (not enough); [RV04 What needs changing?](#node-rv04) (requirements conflict); [RL04 Audit public exposure](#node-rl04) (fundamental quality failure).

**Move to:** [PL02 Ask clarifying questions](#node-pl02) **when draft intent**.

#### PL02 — Ask clarifying questions {#node-pl02}

**Actor:** Chat LLM. **State:** Missing requirements. Ask targeted questions; revise scope after every material change.

**Enter from:** [PL01 State detailed intent](#node-pl01) (draft intent); [PL04 Resolve ambiguities](#node-pl04) (more questions).

**Move to:** [PL03 Find contradictions](#node-pl03) **when questions answered**.

#### PL03 — Find contradictions {#node-pl03}

**Actor:** Chat LLM. **State:** Conflicts and trade-offs. Challenge incompatible requirements, tests or architecture; revisit earlier decisions.

**Enter from:** [PL02 Ask clarifying questions](#node-pl02) (questions answered).

**Move to:** [PL04 Resolve ambiguities](#node-pl04) **when conflicts identified**.

#### PL04 — Resolve ambiguities {#node-pl04}

**Actor:** Human. **State:** Choose or defer decisions. Discuss alternatives, settle contradictions, or defer non-blocking questions explicitly.

**Enter from:** [PL03 Find contradictions](#node-pl03) (conflicts identified).

**Move to:** [PL02 Ask clarifying questions](#node-pl02) **when more questions**; [PL05 Enough specified?](#node-pl05) **when decisions/deferred**.

#### PL05 — Enough specified? {#node-pl05}

**Actor:** Human. **State:** Proceed, continue, defer. Advance when sufficient, not necessarily complete; otherwise loop or park.

**Enter from:** [PL04 Resolve ambiguities](#node-pl04) (decisions/deferred).

**Move to:** [PL01 State detailed intent](#node-pl01) **when not enough**; [EN02 Deferred / blocked](#node-en02) **when defer**; [EN03 Abandoned](#node-en03) **when abandon**; [SP01 Reconcile GitHub issues](#node-sp01) **when sufficient**.

#### SP01 — Reconcile GitHub issues {#node-sp01}

**Actor:** Chat LLM. **State:** Specification register. Search existing issues and PRs; align expected outcomes and acceptance cases.

**Enter from:** [WS03 Select discovery depth?](#node-ws03) (minor / clear / routine); [BG05 Confirm defect hypothesis](#node-bg05) (cause sufficient); [PL05 Enough specified?](#node-pl05) (sufficient); [RV04 What needs changing?](#node-rv04) (issue/spec mismatch).

**Move to:** [SP02 Issue record adequate?](#node-sp02) **when reconcile**.

#### SP02 — Issue record adequate? {#node-sp02}

**Actor:** Chat LLM. **State:** Create, update, reuse. Check missing tests, issue ownership, resolving scope and change implications.

**Enter from:** [SP01 Reconcile GitHub issues](#node-sp01) (reconcile).

**Move to:** [SP03 Request issue approval](#node-sp03) **when new issue / major reframe**; [SP04 Persist accepted spec](#node-sp04) **when existing issues valid**.

#### SP03 — Request issue approval {#node-sp03}

**Actor:** Human. **State:** New or material rewrite. Approve new issue creation or significant scope changes; maintain existing records when authorised.

**Enter from:** [SP02 Issue record adequate?](#node-sp02) (new issue / major reframe).

**Move to:** [SP04 Persist accepted spec](#node-sp04) **when approved**; [EN02 Deferred / blocked](#node-en02) **when not approved yet**.

#### SP04 — Persist accepted spec {#node-sp04}

**Actor:** Chat LLM. **State:** Issues + PR descriptions. Record decisions, open questions, criteria and dependencies in GitHub and linked conversation.

**Enter from:** [SP03 Request issue approval](#node-sp03) (approved); [SP02 Issue record adequate?](#node-sp02) (existing issues valid).

**Move to:** [TR01 Work size and dependency?](#node-tr01) **when existing repository**; [TR05 Bootstrap repository](#node-tr05) **when new repository approved**.

### PR-tree planning

#### TR01 — Work size and dependency? {#node-tr01}

**Actor:** Chat LLM. **State:** Single PR or PR tree. Choose scope from dependencies and likely conflicts, not arbitrary linear stacking.

**Enter from:** [SP04 Persist accepted spec](#node-sp04) (existing repository); [TR05 Bootstrap repository](#node-tr05) (repository ready).

**Move to:** [TR02 Plan PR dependency tree](#node-tr02) **when complex / dependent**; [EX01 Who implements?](#node-ex01) **when single PR**.

#### TR02 — Plan PR dependency tree {#node-tr02}

**Actor:** Chat LLM. **State:** Conflict and merge ordering. Map sibling PRs that can merge independently and dependent children that must wait.

**Enter from:** [TR01 Work size and dependency?](#node-tr01) (complex / dependent).

**Move to:** [TR03 Select runnable node](#node-tr03) **when tree dependencies**.

#### TR03 — Select runnable node {#node-tr03}

**Actor:** Chat LLM. **State:** Milestone + unblocked branch. Choose a ready node; if one branch blocks, advance an independent sibling.

**Enter from:** [TR02 Plan PR dependency tree](#node-tr02) (tree dependencies); [RV10 More work in PR tree?](#node-rv10) (next sibling / child).

**Move to:** [EX01 Who implements?](#node-ex01) **when ready node**; [EN02 Deferred / blocked](#node-en02) **when all nodes blocked**; [EN03 Abandoned](#node-en03) **when cancel milestone**.

#### TR05 — Bootstrap repository {#node-tr05}

**Actor:** Chat LLM. **State:** Source, CI, licence and docs. After human scope approval, initialise the repository, essential CI, documentation and licence, delegating source setup to the coding model as needed.

**Enter from:** [SP04 Persist accepted spec](#node-sp04) (new repository approved).

**Move to:** [TR01 Work size and dependency?](#node-tr01) **when repository ready**.

#### TR04 — Milestone gate {#node-tr04}

**Actor:** Human. **State:** Dogfood, testable, complete. Confirm which portion of the tree is sufficient to test or merge now.

**Enter from:** Independent starting point.

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when test milestone**.

### Implementation

#### EX01 — Who implements? {#node-ex01}

**Actor:** Chat LLM. **State:** Chat patch, coding agent, human. For small changes try direct Chat LLM fix when able; otherwise write a prompt for Codex/Agy.

**Enter from:** [TR01 Work size and dependency?](#node-tr01) (single PR); [TR03 Select runnable node](#node-tr03) (ready node).

**Move to:** [EX05 Direct small patch](#node-ex05) **when tiny + chat capable**; [EX02 Prepare implementation](#node-ex02) **when coding model**; [BG03 Interactive diagnosis](#node-bg03) **when human UI debugging**.

#### EX02 — Prepare implementation {#node-ex02}

**Actor:** Chat LLM. **State:** Prompt + branch + tests. Specify accepted issue state, exact branch, constraints, tests, dependency tree and expected PRs.

**Enter from:** [EX01 Who implements?](#node-ex01) (coding model); [RV06 Complex correction](#node-rv06) (corrective prompt).

**Move to:** [EX03 Code and test locally](#node-ex03) **when prompt approved**.

#### EX03 — Code and test locally {#node-ex03}

**Actor:** Coding LLM (Codex/Agy). **State:** Coding LLM in container. Use agent in interactive or YOLO container; iterate on code, tests and generator output.

**Enter from:** [EX02 Prepare implementation](#node-ex02) (prompt approved).

**Move to:** [EX04 Publish PR tree](#node-ex04) **when tests and code**.

#### EX04 — Publish PR tree {#node-ex04}

**Actor:** Coding LLM (Codex/Agy). **State:** Branches and draft PRs. Push real commits and create the promised PRs, with explicit dependent bases and linked issues.

**Enter from:** [EX03 Code and test locally](#node-ex03) (tests and code).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when published**.

#### EX05 — Direct small patch {#node-ex05}

**Actor:** Chat LLM. **State:** Chat LLM, if capable. Use available tooling to edit and test an isolated authorised branch, publish an inspectable PR.

**Enter from:** [EX01 Who implements?](#node-ex01) (tiny + chat capable).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when published**.

### Review, CI and merging

#### RV01 — Inspect actual PR state {#node-rv01}

**Actor:** Chat LLM. **State:** Diff, head, issue, ancestry. Verify published commits, comments, PR metadata, dependencies and fresh tests.

**Enter from:** [ST05 Existing work](#node-st05) (resume current PR); [TR04 Milestone gate](#node-tr04) (test milestone); [EX04 Publish PR tree](#node-ex04) (published); [EX05 Direct small patch](#node-ex05) (published); [RV05 Small repair](#node-rv05) (republished).

**Move to:** [RV02 Classify CI signal](#node-rv02) **when current head**.

#### RV02 — Classify CI signal {#node-rv02}

**Actor:** Chat LLM. **State:** Passed, failed, pending, quota. Required checks cannot be marked passed if absent; rerun or use accepted alternatives.

**Enter from:** [RV01 Inspect actual PR state](#node-rv01) (current head).

**Move to:** [RV03 Review correctness?](#node-rv03) **when CI evidence / disclosed gaps**; [EN02 Deferred / blocked](#node-en02) **when required CI blocked**.

#### RV03 — Review correctness? {#node-rv03}

**Actor:** Chat LLM. **State:** Human + Chat evidence. Check behaviour, issue match, closing keywords, test quality, conflicts and merge ordering.

**Enter from:** [RV02 Classify CI signal](#node-rv02) (CI evidence / disclosed gaps).

**Move to:** [RV04 What needs changing?](#node-rv04) **when findings**.

#### RV04 — What needs changing? {#node-rv04}

**Actor:** Chat LLM. **State:** Simple, complex, spec, ready. Route repair to smallest appropriate stage, including back to Q&A and issue specifications.

**Enter from:** [RV03 Review correctness?](#node-rv03) (findings); [RV07 Human PR review](#node-rv07) (human objections); [RV08 Merge approved?](#node-rv08) (changes requested).

**Move to:** [RV05 Small repair](#node-rv05) **when simple conflict/fix**; [RV06 Complex correction](#node-rv06) **when complex repair**; [PL01 State detailed intent](#node-pl01) **when requirements conflict**; [SP01 Reconcile GitHub issues](#node-sp01) **when issue/spec mismatch**; [RV07 Human PR review](#node-rv07) **when ready**; [EN03 Abandoned](#node-en03) **when work no longer wanted**.

#### RV05 — Small repair {#node-rv05}

**Actor:** Human. **State:** Human or Chat directly. Resolve trivial conflict or tiny fix; Chat may patch when authorised, then republish and review.

**Enter from:** [RV04 What needs changing?](#node-rv04) (simple conflict/fix).

**Move to:** [RV01 Inspect actual PR state](#node-rv01) **when republished**.

#### RV06 — Complex correction {#node-rv06}

**Actor:** Chat LLM. **State:** Prompt to coding model. Produce targeted prompt for Codex/Agy; repair existing branch/PR when safe.

**Enter from:** [RV04 What needs changing?](#node-rv04) (complex repair).

**Move to:** [EX02 Prepare implementation](#node-ex02) **when corrective prompt**.

#### RV07 — Human PR review {#node-rv07}

**Actor:** Human. **State:** Direction + test milestone. Read changes, test where appropriate, request redesign, defer, or approve.

**Enter from:** [RV04 What needs changing?](#node-rv04) (ready).

**Move to:** [RV04 What needs changing?](#node-rv04) **when human objections**; [RV08 Merge approved?](#node-rv08) **when review accepted**.

#### RV08 — Merge approved? {#node-rv08}

**Actor:** Human. **State:** Current PR only. Explicit approval; passing CI or model readiness is not merge authority.

**Enter from:** [RV07 Human PR review](#node-rv07) (review accepted).

**Move to:** [RV04 What needs changing?](#node-rv04) **when changes requested**; [EN02 Deferred / blocked](#node-en02) **when hold**; [EN03 Abandoned](#node-en03) **when cancel work**; [RV09 Merge eligible node](#node-rv09) **when approved**.

#### RV09 — Merge eligible node {#node-rv09}

**Actor:** GitHub / CI. **State:** GitHub merge action. Merge only valid, approved PR with required checks and dependency prerequisites satisfied.

**Enter from:** [RV08 Merge approved?](#node-rv08) (approved).

**Move to:** [RV10 More work in PR tree?](#node-rv10) **when merged**.

#### RV10 — More work in PR tree? {#node-rv10}

**Actor:** Chat LLM. **State:** Parallel siblings, blockers. Update bases and conflicts; choose another ready sibling or pause dependent branch.

**Enter from:** [RV09 Merge eligible node](#node-rv09) (merged).

**Move to:** [TR03 Select runnable node](#node-tr03) **when next sibling / child**; [CL01 Audit issues and PRs](#node-cl01) **when milestone complete**; [EN02 Deferred / blocked](#node-en02) **when remaining work blocked**.

### Closeout and trackers

#### CL01 — Audit issues and PRs {#node-cl01}

**Actor:** Chat LLM. **State:** Keywords + real completion. Check Fixes/Closes references, issue statuses, acceptance evidence, final implementation notes.

**Enter from:** [RV10 More work in PR tree?](#node-rv10) (milestone complete).

**Move to:** [CL02 Notify dependencies](#node-cl02) **when issues correct**.

#### CL02 — Notify dependencies {#node-cl02}

**Actor:** Chat LLM. **State:** Upstream + downstream. Check version constraints, dependent PRs, projects and actionable update notices.

**Enter from:** [CL01 Audit issues and PRs](#node-cl01) (issues correct).

**Move to:** [CL03 Update Projects repo](#node-cl03) **when notify**.

#### CL03 — Update Projects repo {#node-cl03}

**Actor:** Chat LLM. **State:** Ideas, work and position. Update arran4/projects with roadmap, workstream and current milestone.

**Enter from:** [CL02 Notify dependencies](#node-cl02) (notify).

**Move to:** [CL04 Update PR repository](#node-cl04) **when tracker current**.

#### CL04 — Update PR repository {#node-cl04}

**Actor:** Chat LLM. **State:** Announcement readiness. Update arran4/public-relations with accurate materials or future campaign tasks.

**Enter from:** [CL03 Update Projects repo](#node-cl03) (tracker current).

**Move to:** [RL01 Recommend release intent](#node-rl01) **when evaluate version**.

### Release and public opening

#### RL01 — Recommend release intent {#node-rl01}

**Actor:** Chat LLM. **State:** None, patch, minor, major. Use accepted scope, roadmap, merged changes and release guidance; patch may be routine if authorised.

**Enter from:** [ST06 Release request](#node-st06) (release-only); [CL04 Update PR repository](#node-cl04) (evaluate version).

**Move to:** [RL02 Publish now?](#node-rl02) **when release recommendation**.

#### RL02 — Publish now? {#node-rl02}

**Actor:** Human. **State:** Decision or defer. May choose no release, normal versioned release, or delayed/public opening.

**Enter from:** [RL01 Recommend release intent](#node-rl01) (release recommendation).

**Move to:** [EN01 Completed](#node-en01) **when no release / done**; [EN02 Deferred / blocked](#node-en02) **when defer release**; [RL03 First public opening?](#node-rl03) **when release approved**.

#### RL03 — First public opening? {#node-rl03}

**Actor:** Human. **State:** Visibility and history. If private-to-public, require broader quality, provenance, licence, copyright and link checks.

**Enter from:** [RL02 Publish now?](#node-rl02) (release approved).

**Move to:** [RL07 Run release workflow](#node-rl07) **when already public / private release**; [RL04 Audit public exposure](#node-rl04) **when first public opening**.

#### RL04 — Audit public exposure {#node-rl04}

**Actor:** Chat LLM. **State:** Links, secrets, licences. Inspect repository history, links, copyright, documentation, quality and release assets.

**Enter from:** [RL03 First public opening?](#node-rl03) (first public opening).

**Move to:** [RL05 History rewrite needed?](#node-rl05) **when audit findings**; [PL01 State detailed intent](#node-pl01) **when fundamental quality failure**.

#### RL05 — History rewrite needed? {#node-rl05}

**Actor:** Human. **State:** Explicit destructive consent. Force-push or rewrite only on explicit informed approval; consider collaborators and tags.

**Enter from:** [RL04 Audit public exposure](#node-rl04) (audit findings).

**Move to:** [RL06 Approve visibility change](#node-rl06) **when no rewrite / approved rewrite**; [EN02 Deferred / blocked](#node-en02) **when rewrite consent pending**.

#### RL06 — Approve visibility change {#node-rl06}

**Actor:** Human. **State:** Human-publication gate. Make public only after verified audit and approval.

**Enter from:** [RL05 History rewrite needed?](#node-rl05) (no rewrite / approved rewrite).

**Move to:** [RL07 Run release workflow](#node-rl07) **when public approved**.

#### RL07 — Run release workflow {#node-rl07}

**Actor:** GitHub / CI. **State:** Tag dispatch + publisher. Use documented release-safe action to tag and publish; no duplicate release publisher.

**Enter from:** [RL03 First public opening?](#node-rl03) (already public / private release); [RL06 Approve visibility change](#node-rl06) (public approved).

**Move to:** [RL08 Verify published result](#node-rl08) **when workflow complete**.

#### RL08 — Verify published result {#node-rl08}

**Actor:** Chat LLM. **State:** Artifacts, downstream. Confirm actual tag, release, packages and downstream impact; update tracker and announcements.

**Enter from:** [RL07 Run release workflow](#node-rl07) (workflow complete).

**Move to:** [EN01 Completed](#node-en01) **when confirmed**; [EN02 Deferred / blocked](#node-en02) **when publishing failed**.

### Terminal outcomes

#### EN01 — Completed {#node-en01}

**Actor:** GitHub / CI. **State:** Verified milestone. Work and any authorised release completed; issue and tracker state reconciled.

**Enter from:** [RL02 Publish now?](#node-rl02) (no release / done); [RL08 Verify published result](#node-rl08) (confirmed).

**Move to:** Terminal state; a new workstream or recorded trigger is required to resume.

#### EN02 — Deferred / blocked {#node-en02}

**Actor:** GitHub / CI. **State:** Reason + resumption trigger. Record what remains, owner, dependency, and the condition for resuming.

**Enter from:** [PL05 Enough specified?](#node-pl05) (defer); [SP03 Request issue approval](#node-sp03) (not approved yet); [TR03 Select runnable node](#node-tr03) (all nodes blocked); [RV02 Classify CI signal](#node-rv02) (required CI blocked); [RV08 Merge approved?](#node-rv08) (hold); [RV10 More work in PR tree?](#node-rv10) (remaining work blocked); [RL02 Publish now?](#node-rl02) (defer release); [RL05 History rewrite needed?](#node-rl05) (rewrite consent pending); [RL08 Verify published result](#node-rl08) (publishing failed).

**Move to:** Terminal state; a new workstream or recorded trigger is required to resume.

#### EN03 — Abandoned {#node-en03}

**Actor:** Human. **State:** Reason + consequences. Document cancellation, superseded PRs, issue closure/retention and change of direction.

**Enter from:** [PL05 Enough specified?](#node-pl05) (abandon); [TR03 Select runnable node](#node-tr03) (cancel milestone); [RV04 What needs changing?](#node-rv04) (work no longer wanted); [RV08 Merge approved?](#node-rv08) (cancel work).

**Move to:** Terminal state; a new workstream or recorded trigger is required to resume.

## Notes

This process intentionally leaves choices reversible. A human may change the scope, abandon a line of development, park work for later, or take a different ready branch in a PR tree. A CI quota failure, coding-agent exit, or conflict does not automatically mean the specification failed. The diagram describes **how decisions are made and persisted**, not a guarantee that every path always runs.

The current workstream can span several coding sessions and PRs. An issue may outlive one implementation attempt and a PR tree may serve one milestone without exhausting the roadmap. If the workflow has changed while work is in progress, reconcile the durable records and continue from the correct node; do not silently apply obsolete plans.

### Maintaining this diagram

Edit only `workflow.d2` and the relevant written node description; run `bash render-diagrams.sh` from the page bundle to update both `workflow.svg` and `workflow.png`, or let the PR's D2 rendering workflow do so. Commit the text and resulting SVG together. Preserve node IDs when their meaning stays stable so links and LLM checkpoints do not break. If adding a node, specify actor, description, all decision exits and how it affects issue or PR state.

## References

- [Canonical CI/CD workflow and release safety](/blog/guidance/ci-cd/)
- [Projects and roadmap register](https://github.com/arran4/projects)
- [Public Relations planning and announcements](https://github.com/arran4/public-relations)
- [D2 language and CLI](https://d2lang.com/)
