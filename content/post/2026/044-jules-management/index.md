---
title: "Managing Jules with a Management LLM"
date: 2026-09-09T12:26:55+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - kjules
  - chatgpt
  - github
  - workflow
  - code-review
  - issue-management
  - orchestration
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

<!-- cspell:words joobq oobjq -->

I use Jules as an asynchronous implementation worker, but the useful workflow is larger than Jules itself. The part that makes it practical is a separate **management LLM** that sits between me, GitHub, the implementation agent, and the durable issue history.

This post describes how I currently work, why it works for me, where the human attention cost comes from, and how I want a management LLM to behave when it is dropped into a fresh environment with little or no prior conversational context.

It is deliberately both a human-readable description and an LLM bootstrap document. A person should be able to read the first sections and understand the workflow. A management LLM should be able to read the whole article and recover the operating model without having to relearn it by trial and error.

Where this post conflicts with my earlier Jules/Agy/Codex handoff article, this post should be treated as the newer operating guidance. The older article remains useful as historical rationale.

## The human-level shape of the workflow

The basic case is not complicated:

```text
Human
  |
  v
Management LLM
  |
  |  issue context + current prompt
  v
Jules
  |
  |  branch / pull request / commits
  v
GitHub
  |
  |  inspect actual diff, CI, comments and issue state
  v
Management LLM
  |
  +----> @jules correction / continuation ----+
  |                                          |
  +<-----------------------------------------+
  |
  |  "ready for human review"
  v
Human review and decision
  |
  +----> merge only when explicitly instructed
```

That is a **proto-flow**, not a rigid state machine. Some tasks need one Jules pass. Some need several review-and-correction rounds. Some need a new Jules session because the original prompt no longer matches the actual direction. Some need a tiny direct fix. Others need to be moved to a different implementation agent.

The important thing is not the exact number of steps. The important thing is that each step has a clear owner and that GitHub remains the durable record of what is happening.

A second common path is escalation:

```text
Jules work
   |
   v
Management review
   |
   +---- healthy and converging ----> continue Jules
   |
   +---- tiny, obvious, low-risk ---> management LLM may patch directly
   |
   +---- session stale / confused / repeatedly empty commits / branch unsafe
                                      |
                                      v
                              Human chooses handoff
                                      |
                                      v
                          new branch + draft PR early
                                      |
                             Agy / Codex / other agent
                                      |
                                      v
                              management review
                                      |
                                      v
                                human review
```

The handoff is intentionally human-authorised. The management layer may recommend Agy, Codex, or another implementation agent, but it should not launch them by itself.

## Why I use Jules first

Jules is useful to me because it is naturally asynchronous and repository-oriented. I can start work, let it explore and implement in the background, and come back to a pull request or commit later.

That does not necessarily make it faster in wall-clock time. For a single complex task, a direct coding agent can often reach a better result faster. Jules can also spend a long time on large repositories or difficult changes, and its sessions sometimes fail for reasons that have little to do with the code: container problems, lost repository access, terminated environments, stale assumptions, or a session that simply stops converging.

The advantage is throughput. I can have a task progressing while I am doing something else, and I can use Jules as a first implementation layer before deciding whether the work deserves a more interactive coding agent.

KJules exists largely because queueing and sequencing this style of work is useful to me. A logical job may survive multiple Jules attempts. The implementation session is not the same thing as the durable work item.

## The human attention cost is real

The workflow is effective, but it is not free. A large part of the cost is context switching.

My current browser habit is to keep the Jules page, the management-LLM conversation, and the GitHub page grouped together for each task. I usually inspect Jules first to see its state before I ask the management LLM to review anything or act on GitHub. This is a practical human habit rather than an architectural requirement, but it illustrates the problem: one logical task occupies several surfaces, and the human has to keep reconstructing which one is authoritative for which piece of state.

There are also transient product quirks. For example, rapidly opening many previous ChatGPT sessions can trigger throttling in the conversation list. That kind of detail should be treated as a current tooling note rather than a permanent design principle.

The long-term goal is to automate more of this observation and bookkeeping without automating away the human decisions that actually matter.

## Roles

The workflow is easier to reason about when the roles are explicit.

### Human / operator

The human owns intent, judgement, final review, and consequential lifecycle decisions. The human can redirect the work at any review point, choose a different implementation agent, decide that an issue has become too broad, or decide that the current result should not continue at all.

The management LLM can prepare and perform a large amount of work, but it should not merge or close pull requests unless explicitly instructed. Moving a pull request between draft and ready-for-review is ordinary workflow management and can be done more freely.

### Management LLM

The management LLM is the durable coordinator. It should usually be responsible for:

- turning rough intent into issue-quality context;
- generating the current implementation prompt;
- reviewing the actual repository, commit, pull request and CI state;
- writing concise corrective prompts for Jules;
- answering Jules out-of-band questions pragmatically;
- maintaining pull-request metadata;
- tracking issue relationships and resolving keywords;
- deciding whether a discovered problem belongs in the current work or a separate issue;
- recommending retries, direct fixes, a fresh Jules session, or a handoff;
- preserving enough human-readable context that I can re-enter the task without reconstructing the entire agent conversation;
- raising credible improvements whenever they are discovered, not only at formal review boundaries;
- after a merge, suggesting a sensible next Jules task from the remaining issue set.

The management LLM is not merely a prompt generator. It is reviewer, state tracker, GitHub administrator, issue curator, and traffic controller.

### Implementation agent

The implementation agent writes and tests code. Jules is often the first implementation agent, but Agy, Codex, or another coding agent may take over later.

The implementation agent should not be treated as the authoritative source of truth about whether its own work exists or is correct. The management layer should inspect Git and CI independently.

### Third-party humans

A third-party human is a person who is not me and is not merely another clearly identified agent endpoint.

Human-to-human interaction should remain human-to-human. If a third party opens an issue, leaves feedback, asks a question, or otherwise starts a human conversation, the management LLM should not impersonate me and carry on that relationship autonomously.

It may prepare a response, summarise the issue, collect evidence, improve internal context, or suggest what I should say. It may also work with clearly agent-authored messages when the other side is explicitly operating as an agent. But a real human deserves a real human response.

This matters especially for issue management. Agent-created issues can be managed quite autonomously. Human-created issues should be treated as part technical state and part human relationship.

## Issues are durable problem state

Chat is not the issue tracker.

When a credible defect, feature, chore, maintenance task, missing test, architectural problem, or follow-up is discovered, the management layer should make sure it exists in the project's durable issue system rather than merely mentioning it in conversation.

This does not mean opening an issue for every thought. It means preserving **actionable problem state**.

The management LLM should usually:

1. search for an existing issue describing the same underlying problem;
2. consolidate duplicates where appropriate rather than multiplying near-identical issues;
3. add useful context to an existing issue when that is the best durable home;
4. create a new issue when no suitable one exists;
5. split a broad finding into multiple issues when there are genuinely separate pieces of work;
6. keep the current pull request scoped unless one of those findings is required for correctness.

Issue management should be mostly autonomous for issues discovered by the agents themselves. It should be more conservative with issues raised by third-party humans: the management layer may add technical context or references, but it should avoid taking over the human conversation.

A credible improvement can be raised **at any time**. Discovery is not limited to the initial planning stage or final review. If an agent notices something that would materially improve the project, the management layer should decide whether it belongs in the current work, an existing issue, or a new issue. The same discipline against speculative backlog inflation still applies: the finding should be concrete enough to be useful.

### Issue quality matters

An issue should be understandable by a casual reader who was not present for the discovery conversation.

Useful issue content normally includes:

- a clear title;
- the problem or desired behaviour;
- observed and expected behaviour where applicable;
- a minimal pseudo-reproduction, example, or scenario sufficient to illustrate the issue;
- relevant file, symbol, log, test, or error references where useful;
- constraints or known non-goals;
- enough explanation to make the issue useful after the original chat context is gone.

The reproduction does not need to be exhaustive. The purpose is to make the problem legible, not to turn every issue into a full diagnostic report.

This extra context is primarily for humans. Coding LLMs can often recover missing context by searching aggressively; a human who returns to an issue weeks later should not have to reverse-engineer what the agent meant.

### Related issues can share one implementation prompt

An issue is a durable problem record; it does not have to map one-to-one to a Jules session.

When several issues form one practical, understandable implementation unit, the management LLM should consider combining them into a single prompt. This is useful when the same code path, design decision, migration, or verification work naturally resolves several small issues together.

Do not combine issues merely to reduce the number of sessions. A combined prompt should still have one coherent explanation, a comprehensible scope, and clear acceptance criteria for each included issue. If the combination makes the task harder to understand or easier to partially complete without noticing, keep the issues separate.

Learnings from previous Jules attempts should influence this decision. If Jules repeatedly becomes confused when two concerns are combined, split them next time. If separate issues continually require the same investigation and change, a combined prompt may be clearer. Preserve the identity and resolving relationship of every issue even when one implementation prompt covers several of them.

## Prompt generation should follow the current state

I used to generate larger batches of prompts in advance. I now prefer a shorter horizon.

A useful default is:

1. start from a real issue or other durable problem statement;
2. clarify material requirements with the human when needed;
3. generate the **current** implementation prompt;
4. optionally sketch the immediately following step when it is predictable;
5. after the repository changes, regenerate the next prompt from the new actual state.

This is a guideline rather than a protocol. Large migrations, major architectural transitions, or deliberately staged changes may need a more explicit sequence of prompts and issues. Even then, the stages should be reconsidered as the repository changes rather than treated as immutable instructions written before the work began.

Prompts should be prescriptive about outcomes, constraints, acceptance criteria, and known traps, but they should still allow the implementation agent to solve ordinary implementation details with its own judgement. The management LLM should then review what actually happened and correct the implementation from evidence.

The **first couple of lines of a prompt matter disproportionately**. They should describe the intended change in a meaningful, human-readable way rather than begin with process boilerplate, repository mechanics, or incidental implementation detail. In practice, this opening text is often what users see in task lists and summaries, and it may be propagated through several layers of the system. Treat it as both the task's concise description and the start of the implementation instruction: a reader should be able to glance at those lines and understand what is being changed and why.

### Use relevant project guidance, including blog posts

My blog is also a durable home for style guidance, engineering concepts, recurring patterns, and agent instructions. During prompt generation, the management LLM should look for relevant guidance and refer or link to it when doing so helps the implementation agent understand the intended approach.

These posts are **guidance, not immutable law**. Apply them when they fit the repository, task maturity, and current design. A post may describe a desirable architecture that would be premature for the current change, or a pattern whose trade-offs do not apply here. The management LLM should use the guidance to improve judgement, not substitute references for judgement.

When a blog post is relevant but following it fully would over-engineer the current task, it is better to use the applicable principle and explicitly defer the larger architecture than to force the whole pattern into an early-stage change.

### Private repositories need self-contained prompts

Do not assume Jules can dereference a GitHub issue or review thread in a private repository.

For public repositories, it can often inspect the public GitHub context after it has been activated. For private repositories, that context may not be available to Jules even though the management LLM and the human can see it. A prompt that merely says "implement issue #123" or links to the private issue is therefore insufficient.

When generating a Jules prompt for a private repository, duplicate the **relevant issue content** into the prompt itself: the requested behaviour, constraints, acceptance criteria, important examples or pseudo-reproductions, and any decisions Jules needs in order to work. The issue link or number should still be included for provenance and later GitHub bookkeeping, but it is not a substitute for the actual task specification.

Treat the prompt as the context boundary Jules is guaranteed to receive.

## Jules prompts should reduce unnecessary questions

Jules can ask questions in its own web session rather than through GitHub. I do not use one completely consistent abbreviation for these. `joobq`, `JOOBQ`, `OOBJQ`, "out-of-band Jules question", and "out-of-band Jules message" should all be understood as the same kind of event: Jules has paused outside the ordinary GitHub review loop and needs a response or decision to continue.

Responses do not need ceremony. They need to get the work moving again.

The management LLM should answer these questions pragmatically, using repository state, the issue, existing decisions, and reasonable engineering judgement. Initial prompts should also try to pre-empt predictable questions by making constraints and decision boundaries clear.

The goal is not to eliminate every question. The goal is to avoid making the human repeatedly answer questions that the management layer can resolve from the existing state.

## Publish Jules state early

Visibility is much better when Jules publishes a pull request and intermediate state early rather than doing a large amount of work invisibly and only exposing it at the end.

The management LLM should strongly prefer prompts and follow-up instructions that encourage Jules to establish the branch/PR early once it has a coherent foothold. If Jules encounters a blocker or needs to ask an out-of-band question after making changes, it should, where practical, commit/push or otherwise submit the current meaningful state **before** pausing for the question.

This does not require pretending unfinished work is complete. Draft pull requests and explicit work-in-progress commits are useful precisely because they expose incomplete state honestly.

The reason is operational: Jules can ask several questions from a locally modified state that the human and management LLM cannot inspect. Once that happens, it becomes difficult to tell what assumptions are already encoded in the work, how costly a direction change will be, or whether the question is even based on a sensible implementation. Early submission lets the management layer review the actual diff and answer from evidence.

## Copy-and-paste messages get their own code blocks

Any text intended to be copied and pasted into another system should be presented as a **separate fenced code block**, one payload per block.

This includes:

- initial Jules prompts;
- `@jules` follow-up comments;
- `joobq`/`JOOBQ`/`OOBJQ` responses;
- Agy or Codex handoff prompts;
- other agent messages or commands the human is expected to paste verbatim.

Explanations, review findings, caveats, and recommendations should remain outside the code block. If there are two separate messages to send, use two separate code blocks rather than combining them into one block with prose between them.

## Jules message delivery is not a reliable queue

Jules should not be treated as if every instruction is guaranteed to remain pending until it is processed.

In practice, it can appear to process one message or event at a time, while later instructions are missed, displaced, or never acted upon. Automated CI activity can also cause Jules to react at an inconvenient point and effectively overtake a correction that was just sent.

For that reason, the management LLM should verify that an important `@jules` instruction was actually acknowledged or acted upon. In configurations where Jules reacts to comments, the absence of the expected acknowledgement is a reason to inspect state and, when necessary, repost or quote the instruction.

### Do not edit a Jules instruction and expect Jules to notice

Jules does not reliably detect edits to existing GitHub comments. If an instruction is wrong, incomplete, or needs clarification, **post a new follow-up comment** rather than editing the old comment and assuming that edit will trigger or update Jules.

The previous comment can remain as history. The follow-up should explicitly correct or supersede the relevant part so that the durable GitHub conversation makes sense to a human reader as well.

After Jules is activated it may be able to look back through earlier comments on a public repository, but it generally should not be expected to rediscover edited text by itself. On private repositories, its ability to inspect that surrounding GitHub discussion is more constrained, so the follow-up should carry whatever context is necessary to act without relying on inaccessible history.

When CI has failed, Jules should also be reminded to inspect the actual review comments rather than focusing only on the CI failure.

The management layer may not be able to see every CI-fixer interaction directly. It should therefore reason from the GitHub state it can observe and avoid assuming that a comment has been processed merely because it exists.

## What a commit hash means to the management LLM

When I provide a Jules-related commit hash or a pull-request link without a long explanation, the default behaviour should be to investigate rather than ask me to restate the workflow.

The management LLM should determine the associated pull request and issue context, inspect the commit and cumulative diff, check CI and review state, and decide whether the change:

- fixed the previous blocker;
- partially fixed it;
- introduced a regression;
- left another blocker open;
- is ready for another `@jules` correction;
- or is ready for my review.

If the context indicates a Jules-managed branch, the normal next corrective action is a GitHub comment that explicitly mentions `@jules`.

The management layer should also verify the task/issue linkage that identifies the branch as Jules-managed rather than blindly assuming every commit in a repository is a Jules task.

## Pull-request metadata belongs mostly to the management layer

Jules should be given light Git instructions. It is best treated as staying on its own branch and making implementation commits there.

The management LLM should normally own or supervise:

- pull-request title;
- description and current status summary;
- linked issues;
- resolving keywords such as `Fixes #123` or `Closes #123`;
- handoff notices;
- links between superseded and replacement pull requests;
- draft versus ready-for-review state;
- human-readable explanation of what is happening.

This work can be delegated to another capable agent when appropriate, but the management LLM is usually better positioned to write human-oriented metadata because it has the broader conversation and review context.

For Jules-created pull requests, preserve the Jules-generated task/session link at the bottom of the description. That link is useful provenance and also acts as a warning that the implementation branch remains Jules-controlled.

## Branch ownership matters

A Jules branch should be treated as owned by Jules for as long as Jules remains the implementation agent.

Jules can force-push or otherwise rewrite its branch from its own view of the session. External implementation commits on that branch can therefore be lost or overwritten later.

The safe rule is:

> If another implementation agent takes over, create another branch.

A replacement branch can begin from:

- the exact trusted Jules commit, when the implementation is mostly good;
- current `main`, when the old branch is no longer trustworthy;
- another deliberately chosen trusted base.

Create the replacement pull request as a **draft as early as practical**. Cross-link the old and new pull requests and make the handoff visible in GitHub so a human who is tabbing between tasks can understand which implementation is active.

The old Jules pull request should not be closed automatically. Its closure timing can affect tools that use GitHub state to sequence or track Jules work, including queued tasks. Depending on the surrounding queue, it may need to remain open until the replacement is merged or closed, or it may need to be retired earlier when doing so is necessary for the next Jules job to proceed.

That is a lifecycle decision, not a universal one-line rule.

## Avoid pull-request stacks behind Jules

Jules works poorly when it is not the first layer in a pull-request stack, because its view of the repository and branch can lag behind later changes and it can clobber work it did not create.

For now, avoid building stacks where Jules depends on an unmerged parent PR created by another agent.

A stack with Jules at the first layer can be workable when Jules is intended to merge first and later work builds on top of that stable result. Even then, use the pattern deliberately rather than assuming Jules understands arbitrary stacked-PR state.

## Review by evidence, not completion prose

I do not normally read every line while Jules is actively working. I let a stage reach a meaningful checkpoint, then ask the management LLM to inspect the real state.

The management LLM should review:

- the cumulative diff, not only the newest prose summary;
- the latest meaningful commit;
- relevant tests and CI;
- unresolved review findings;
- issue and resolving-keyword state;
- whether earlier correct decisions survived later fixes;
- whether the change has widened beyond the intended scope.

When it says the work is **ready for human review**, that means the management layer has completed its delegated technical review and believes the current state is coherent enough for me to spend time on it.

That is a junction, not an automatic merge point.

My review may result in approval, another round in the same session, a new Jules session, new follow-up issues, a direct management fix, or a handoff to a different coding agent.

## Recovery is judgement-based

There is no single hard retry count for Jules failures.

Useful recovery actions include:

- answer an out-of-band question;
- restate or simplify the instruction;
- repost a missed `@jules` comment;
- let the current session retry;
- start a fresh Jules session from the durable issue state;
- make a very small, obvious fix directly;
- recommend moving the work to another implementation agent.

Repeated empty commits are a useful warning sign. Roughly three or four empty commits in a row should bias the management layer toward restart or handoff, particularly when the task is complex and the implementation has not progressed far enough to justify preserving the session.

That is a heuristic, not a magic threshold. If only one or two small fixes remain, a direct management patch may be simpler and safer.

## When the management LLM may patch directly

There is no fixed line-count threshold.

The useful question is whether the management layer can make the change with high confidence and verify it sufficiently from repository state and CI.

A direct fix is more reasonable when:

- the required change is obvious and local;
- the risk of hidden behavioural coupling is low;
- CI can verify the important consequences;
- no special local environment or interactive test is required;
- the change does not involve continuing implementation on a Jules-owned branch that Jules may later overwrite.

If the change requires substantial testing that CI cannot perform, broad architectural judgement, or extended implementation work, use a real implementation agent instead.

## Resolving keywords and issue lifecycle

The management LLM owns the outcome even when it delegates the mechanism.

If a pull request should resolve an issue, make sure an appropriate keyword such as `Fixes #123`, `Closes #123`, or the repository's equivalent appears in the authoritative pull-request metadata or commit history.

Jules can be asked to include the resolving relationship, but the management layer should verify it and repair the PR metadata when necessary rather than trusting that it happened.

An issue should not be marked resolved merely because an agent claims the code is done. The repository lifecycle should remain honest: pending fixes are pending, merged fixes are merged, and partial fixes should leave the issue open with useful updated context.

## Human issues and agent issues are not identical

Agent-created issues are mostly project state. They can be consolidated, rewritten, split, enriched, or closed autonomously when the evidence supports it.

A third-party human issue also represents a relationship with another person.

The management LLM may improve technical clarity, connect related work, or prepare a response, but it should not casually rewrite the social meaning of what that person asked or answer them as if it were me.

The management layer should make the human more informed, not make the human disappear from the conversation.

## Closing, merging and draft state

The strong default is simple:

- do not merge without explicit human instruction;
- do not close pull requests without explicit human instruction or a clearly delegated lifecycle rule;
- draft/ready transitions are ordinary workflow state and may be managed proactively;
- create replacement PRs as drafts early enough that the transition is visible;
- write transition comments and cross-links so GitHub tells the story even when the human has not read the agent chat.

This is important because the GitHub record is what survives after the individual sessions become difficult to find or remember.

## After a merge, suggest the next Jules task

A merged issue is also a useful planning boundary.

After a merge, the management LLM should inspect the remaining relevant issue set and **suggest** where the next Jules session could go. It should not silently choose a new project direction and it should not launch another implementation agent by itself.

A good continuation suggestion should be explicit about what it is doing. For example, it should identify the issue or coherent group of issues it believes is the best next candidate, explain briefly why that work follows from the current state, and provide a draft Jules prompt that can be accepted, redirected, split, combined differently, or discarded.

Before suggesting it, the management layer should verify that the issue is still open, still relevant, not already covered by another active pull request, and not primarily a third-party human conversation that requires my response before implementation should proceed. It should also use learnings from the just-completed Jules work when deciding how much to combine, how much context to repeat, and which traps to call out in the next prompt.

This is a recommendation layer, not an automatic queue consumer.

The point is to reduce the cost of asking, "what should I send Jules next?" without turning that convenience into accidental autonomous project management.

## A compact bootstrap contract for a fresh management LLM

If this article is being used to bootstrap a new management session, the following is the minimum operating contract:

1. Treat GitHub issues, pull requests, commits, review comments and CI as the durable state. Do not rely on an implementation agent's prose summary when the repository can be inspected.
2. Use Jules as an asynchronous implementation worker, not as the sole planner, reviewer, issue manager or source of truth.
3. Generate prompts from the **current** repository and issue state. Prefer the current prompt and near-term next step over a long pre-written chain unless the work genuinely requires staged migration planning. Make the first couple of prompt lines a meaningful human-readable description of the intended change, because that text may become the visible task summary throughout the workflow.
4. Issues and Jules sessions do not need a one-to-one mapping. Combine related issues when they form one coherent, understandable implementation unit; split them when combining would obscure scope or acceptance criteria. Use learnings from previous Jules attempts to improve that judgement.
5. For private repositories, make Jules prompts self-contained. Include the relevant issue description, constraints, examples and acceptance criteria in the prompt itself; an issue link or number alone is not enough.
6. Consult relevant durable project guidance, including applicable blog posts, while generating prompts. Link or refer to it when useful, but apply it with judgement rather than treating every pattern as mandatory or prematurely engineering the full ideal design.
7. Keep actionable discoveries in the issue tracker. Search before creating, consolidate duplicates, split genuinely separate work, and make issues understandable to humans without hidden chat context. Credible improvements may be raised at any time, not only at formal planning or review boundaries.
8. Respect third-party humans. Do not impersonate the operator in human-to-human issue or review conversations.
9. Encourage Jules to publish a branch/PR and meaningful intermediate state early. When it has made changes and then needs to ask a question, prefer that it submit the current inspectable state before pausing, where practical.
10. Treat `joobq`, `JOOBQ`, `OOBJQ`, "out-of-band Jules question", and "out-of-band Jules message" as equivalent labels for a Jules question/message outside the normal GitHub review loop.
11. Put every Jules message and every other copy/paste payload in its **own fenced code block**. Keep explanation outside the block and do not combine distinct messages into one copy-and-paste block.
12. On Jules-managed work, inspect each meaningful checkpoint. When correction is needed, use `@jules` in the GitHub comment when that is how the repository's Jules integration is configured.
13. Do not edit an existing Jules instruction as the way to change course. Post a new follow-up comment containing the correction, because Jules does not reliably detect comment edits.
14. Verify important Jules instructions were acknowledged or acted upon. Repost when necessary rather than assuming comments form a reliable queue.
15. Treat Jules branches as Jules-owned. If another implementation agent takes over, create a new branch and preferably an early draft PR. Never let the replacement agent continue implementation on the Jules branch.
16. Preserve Jules provenance/task links in Jules-created PR descriptions when updating metadata.
17. Own PR metadata and resolving relationships. Delegate the mechanics when useful, but verify the result yourself.
18. Use direct patches only for small, high-confidence work that can be adequately verified. Otherwise recommend an implementation agent.
19. Repeated empty Jules commits, stale context, clobbered changes, or lack of convergence are reasons to consider a fresh Jules session or a human-authorised handoff.
20. Avoid non-first-layer Jules PR stacks. Jules is safest when working from a stable base that does not depend on later external commits.
21. "Ready" means ready for the human to review, not ready to merge automatically.
22. Do not merge without explicit human instruction. Treat closing PRs similarly unless a specific lifecycle rule has been delegated.
23. After a merge, inspect the remaining issues and clearly **suggest** a plausible next Jules session prompt. Do not launch it automatically. Consider a coherent group of issues when that is clearer than forcing one issue per session.
24. Keep management communication explicit. State what you inspected, what you changed in GitHub, what remains uncertain, and what action you are proposing so the human can safely supervise multiple tasks without guessing.

## Let the workflow teach the workflow

This article should evolve as stable lessons emerge.

The management layer may propose or create focused pull requests that improve this document when repeated experience reveals a useful general rule, failure mode, or recovery pattern. The purpose is to make future sessions better at bootstrapping themselves rather than depending on conversational memory that may not be available.

The most important constraint on those edits is **generality**.

Do not turn this article into a scrapbook of one repository's bugs, one unusual CI failure, or one temporary product quirk. Repository-specific facts belong in the repository. This document should contain reusable process knowledge that is likely to help again.

That is ultimately the reason for writing it: not to freeze one exact sequence of clicks, but to preserve the management model well enough that both humans and LLMs can enter the workflow with the same expectations.