---
title: "Managing Jules: Repository-First Continuation After a Merge"
date: 2026-09-19T17:09:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - github
  - issue-management
  - orchestration
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

This is a focused amendment to [Managing Jules with a Management LLM](/blog/post/2026/044-jules-management/). It clarifies that article's post-merge closeout and next-prompt selection rules. For post-merge continuation, use the rules here where the earlier article is less specific; its other ownership, issue-management, review and human-authorisation rules remain in force.

## Start with the repository that just merged

After a human confirms a pull request merged, verify the merge, reconcile issues and superseded pull requests, and review the new state of **that same repository**. The first proposed next task and first complete copy-and-paste Jules prompt must target that repository. Search its current open issues and PRs for an actionable, coherent follow-up. Prefer existing durable issue state over inventing new backlog work. Do not automatically replace that primary prompt with a task in a dependency, generator, tooling or otherwise related repository merely because the completed work exposed a problem there.

An upstream defect with an existing issue is already accounted for. Link it as a dependency or an optional separate task; it is not a reason to displace the consumer repository's next prompt. If the original repository has no suitable unblocked work, say **there is currently no eligible in-repository prompt** rather than silently treating a different repository as its continuation. The human can explicitly redirect the focus.

The report should show the in-repository follow-up first, with its own issue/PR links, scope and executable prompt. Other-repository candidates belong in a separately labelled **Additional unblocked work** section, after the primary result. Give each repository its own distinct prompt and branch/PR lifecycle; never combine implementation instructions for unrelated repositories into one Jules session. Return one copy-and-paste payload per fenced code block.

## Look for work that the merge actually unblocks

Closeout must also inspect existing dependency relationships, blockers and follow-up issues in the same and related repositories. Search issue and PR descriptions, linked dependencies, version pins, review notes and release metadata for tasks whose prerequisites may have changed. Distinguish three states:

- **Ready now:** the exact prerequisite is satisfied, the target issue is still open and accurate, no active PR already covers it, and the implementation can begin from the target repository's current trusted base.
- **Waiting for a release or adoption:** the upstream source change is merged but the target requires a published version, package, image or other release artifact, or still needs an explicit dependency upgrade. Record the candidate and its gate, but do not call it unblocked or start a downstream implementation PR yet.
- **Already accounted for or not yet ready:** the upstream defect itself remains open, another PR already implements the target, the target issue has become obsolete, or prerequisites are unknown. Maintain links and report the blocker rather than fabricating a new task.

For cross-repository consumers, a merged upstream PR is not automatically equivalent to an available dependency. Verify the actual release/tag or published artifact **and** that it contains the fix, is accessible to the consumer, and can be selected by the consumer's version/pin constraints. If the target intentionally consumes unreleased commits, require an explicit documented exception rather than silently treating a merge as a release. Do not infer readiness from a release plan, a green upstream CI run or an issue being closed.

When release readiness is the blocker, the continuation report should identify the upstream issue/PR, required release or version, target repository and downstream issue; state **waiting for upstream release** and present any proposed prompt conditionally, to be revalidated against actual GitHub/release state before use. Publishing a release remains a human-controlled action under the main management policy.

## Turn newly unblocked tasks into separate, reviewable PRs

Once an eligible target is unblocked, search for its existing issue and active PR before creating anything. Update cross-links and the existing issue when appropriate; do not file a duplicate merely because a prerequisite was satisfied. Determine whether the target needs a straightforward dependency bump/regeneration or substantial implementation. For a narrow, high-confidence change within delegated management authority, management may create a separate target-repository branch and draft PR directly, implement the change and verify it with that repository's tests and CI. Do not create an empty placeholder PR or assume green CI alone proves the intended behavior.

For work needing Jules or another implementation agent, provide a **separate, self-contained target-repository prompt** with the verified release/version, prerequisite issue/PR, current target base, exact acceptance criteria, tests and known traps. Establish branch/PR ownership in accordance with the main article. Starting an additional agent session remains a human choice unless explicitly delegated; when authorisation to start the work is given, establish the appropriate draft PR and review it normally. Do not present speculative or blocked prompts as immediately executable.

Opening a downstream draft PR does not authorise merging it. A new PR must pass its own review and CI and remain within its target issue's scope. If a released generator or dependency changes canonical output, regenerate from the authoritative source with the selected released version and keep drift checks strict; do not hand-edit generated output or suppress meaningful differences.

## Required post-merge answer order

1. **Closeout:** verified merge, issue reconciliation, superseded PR cleanup, CI/release state and links.
2. **Primary next prompt — same repository:** select an open, unblocked issue or coherent issue group from the repository just merged; give its own full Jules prompt first. If none exists, state that explicitly.
3. **Additional unblocked work — other repositories:** only include independently verified, ready targets. State the prerequisite release/version and target issue/PR, and supply each optional prompt or authorised draft PR separately. Do not elevate these above the primary prompt.
4. **Waiting on release or another prerequisite:** list relevant linked candidates with the exact gate and no premature implementation claim. Recheck the release and target issue before turning them into prompts or PRs.
5. **Management feedback:** notable changes, uncertainty, agent behavior and any process improvement worth preserving.

The answer should remain useful even when there is no cross-repository work. A recorded upstream issue does not create a standing instruction to work upstream next; the operator's current repository remains the default focus until they choose otherwise.

### A short example

A merged change in a CLI repository makes its documentation and CI current. Its next prompt should come from that CLI repository's outstanding issue set. If the merge also revealed a bug in its code generator, link the already-open generator issue as an additional item, not as the CLI repository's primary continuation. If a later generator PR fixes that bug, first verify that the fixed generator version has actually been released. Only then may a dependent CLI issue to bump the generator and regenerate its output be offered as an additional ready prompt or implemented in a separate CLI pull request. Until then it remains a dependency-tracked, release-gated follow-up.
