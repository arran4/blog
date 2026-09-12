---
title: "Jules Handoffs Need a Branch-Ownership Gate"
date: 2026-09-12T20:35:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - agy
  - codex
  - github
  - workflow
  - orchestration
  - handoff
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

This is a short operational addendum to [Managing Jules with a Management LLM](/blog/post/2026/044-jules-management/).

The earlier article already says that when work leaves a Jules-owned implementation branch for Agy, Codex, or another implementation agent, the management layer should create a **new branch and draft pull request early**. That rule was correct, but it was still possible for a management session to treat it as guidance rather than as a transition precondition.

That is too weak.

A Jules branch must be treated as an independently writable resource for as long as Jules may still be able to publish to it. A failed VM, expired authentication, apparently terminated session, clean working tree, or a belief that Jules is "done" is not proof that the branch has stopped being Jules-owned. A stale or recovered Jules session may still push later.

If another implementation agent has continued work on that same branch, a later Jules push can overwrite, revert, or otherwise invalidate the new agent's work while still producing a syntactically valid commit and green CI.

## Hard handoff rule

Before issuing instructions to a different implementation agent, the management layer must perform a branch-ownership preflight.

1. Identify the current implementation branch and pull request.
2. Identify which agent owns that branch.
3. Determine the last reviewed good commit that should become the handoff base.
4. If the branch is Jules-owned and the next writer is not Jules, create a replacement branch from that reviewed commit **before the new agent is told to write or push**.
5. Open a replacement draft pull request early so the new branch has a durable review surface.
6. In the new agent's prompt, name the replacement branch and pull request explicitly and prohibit pulls, rebases, merges, or pushes involving the old Jules branch except for read-only comparison.
7. Keep the Jules branch as historical evidence until the replacement is safely established. Do not use it as the integration branch for the new agent.

This is a handoff gate, not a preference.

## Do not rationalise sharing a Jules branch

The following are not sufficient reasons to let Agy, Codex, or another agent continue directly on a Jules-owned branch:

- preserving the existing pull-request number or review history;
- the Jules VM failed;
- the Jules session appears inactive;
- authentication expired;
- the branch is currently clean;
- the next change looks small;
- CI is green;
- creating another pull request feels administratively noisy.

The replacement pull request can link to and supersede the Jules pull request. Review history is less valuable than preserving the implementation state itself.

## If the rule was already violated

If two agents have already written to the same Jules-owned branch, do not immediately reset, merge, or cherry-pick the latest branch wholesale.

Instead:

1. stop additional writes to the contested branch;
2. identify the last independently reviewed good commit;
3. preserve any uncommitted or local work from the replacement agent;
4. create a new replacement branch from the last good commit;
5. move or replay only the replacement agent's work onto that branch;
6. compare later Jules commits against the good checkpoint separately;
7. salvage only changes that remain independently correct and useful;
8. discard broad rollback/recreation work rather than allowing it to become the new baseline;
9. continue review and CI on the replacement pull request.

A later Jules commit can still contain a useful isolated fix. Preserve that fix by reimplementing or cherry-picking the narrow change after review, not by accepting the entire contaminated commit.

## Why the previous wording was not enough

The earlier management article described the correct branch transition, but the rule was embedded in a larger decision flow. That left room for a management session to optimise for continuity of the existing pull request and to treat branch replacement as optional when the old Jules session looked dead.

The missing mechanism was a mandatory preflight question:

> **Who still has write ownership of this branch?**

That question must be answered before choosing whether a new implementation agent may reuse the current branch.

The management layer should therefore treat implementation-agent identity and branch ownership as durable state, not as conversational context that can be inferred later.

## Prompt requirement for replacement agents

A handoff prompt to Agy, Codex, or another agent should state, near the top:

- the exact reviewed base commit;
- the exact replacement branch;
- the replacement draft pull request;
- the old Jules pull request/branch as read-only historical context;
- that the old Jules branch must not be pulled, rebased, merged, force-updated, or pushed to;
- how to preserve current local WIP if the handoff is happening after work has already started.

This turns branch isolation from an architectural idea into an executable handoff instruction.

## General principle

**One writable implementation branch should have one active implementation owner.**

When ownership changes away from Jules, change the branch before changing the writer.
