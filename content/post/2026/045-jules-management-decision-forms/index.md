---
title: "Management decision forms and Jules failure recovery"
date: 2026-09-25T09:50:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - github
  - workflow
  - code-review
  - issue-management
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

<!-- cspell:words handoff handoffs closeout -->

This is a companion reference for [Managing Jules with a Management LLM](/blog/post/2026/044-jules-management/). The original article remains the authority for branch ownership, review, recovery, and human approval. These interaction rules apply to **any management question**, not just post-merge and failure recovery.

## One complete decision form, with room for the human

After investigating the actual task and GitHub state, the management LLM should put outstanding human decisions into **one interactive form** when the interface supports it. Every question must identify what action a selection would authorise, distinguish recommendations from approvals, preselect a reasonable recommendation where safe, include **No action**, and offer **Other with free text**. Independent issue proposals must have independent approvals; accepting a general plan must not silently approve each proposed mutation. Do not add irrelevant questions merely to fill out a form.

**Every form must end with an always-visible, unrestricted multiline field titled `Additional details, corrections, or my own instructions`.** The field must not be conditional on selecting Other, must remain available even when No action is selected, and must allow the human to supply an entirely different plan or qualify several answers. Read it alongside the selected choices before acting. If free text conflicts with a selection, resolve the conflict rather than silently ignoring either. If the interface cannot render such a form, give a structured text questionnaire with the same choices and an unrestricted final free-text answer area. An interactive form must not trap the operator inside incomplete predefined options.

Report **ACTION REQUIRED** for decisions, **RECOMMENDATION** for suggested but unauthorised actions, and **INFORMATION** for verified findings or completed actions. State exactly what was done, what remains pending, and links to the relevant GitHub state. Do not claim that an unavailable control or tool completed an operation.

## Post-merge decision coverage

Verify the merge; reconcile issues and pull requests; assess newly discovered work and the next release; and recommend CONTINUE, HOLD, or CLOSE OUT. The initial response should already contain the full, ready-to-paste **primary Jules prompt** when that is a viable next task. Do not make the operator submit a form simply to obtain the primary prompt.

The consolidated form should cover, when relevant:

- Each independent proposal to create, update, consolidate, or close an issue: approve the named action, defer, no action, or other with free text.
- Continuation: recommended direction, CONTINUE, HOLD, CLOSE OUT, no action, or other with free text.
- Next prompt: recommended task (first), secondary (second), third, a specifically identified later task (Nth), all remaining worthwhile prompts, redo the last prompt using new details, no additional prompt, no action, or other with free text. Offer only tasks actually identified; selecting a prompt does not launch an agent.
- Release: accept the recommended plan **for consideration only**, explicitly create and publish the recommended release, explicitly create and publish a patch/minor/major release where those types apply, prepare for review without publishing, defer, no release, no action, or other with free text. Preselect a **non-publishing** choice. Recommendation, issue approval, and prompt selection never constitute publication authority. Verify the specific version and release prerequisites before any authorised publication.
- Any additional review, dependency, or repository administration decision that actually requires human input.

## Failure intake starts with the Jules outcome

A recovery request should start with an operator-editable line such as:

```text
JULES OUTCOME: FAILURE — [container/setup | clone/authentication | runtime/session | repeated empty commits | implementation/tests | Git/PR submission | wrong repository | other/unknown]
Repository / issue / session / PR: [known links]
Observed error and additional details: [paste text, or leave blank if already available]
```

The management LLM must **act as the manager of the failed implementation**, not as the failed Jules worker. Investigate the issue, original instructions, current main, session, PR, cumulative diff, review comments, CI, available commits, and attached worktree, patch, ZIP, or logs. Find the last independently trusted commit, what work is usable, and what remains. Do not conclude that the code failed because the container failed, and do not treat pre-checkout failures as implementation non-convergence. Attribute service and infrastructure failures narrowly, without inventing a root cause.

Determine whether to complete existing work and GitHub administration, correct a viable Jules session, land a reviewable predecessor slice, restart with fresh Jules from an appropriate base, use a distinct management-owned direct-fix branch and PR, fall back to Codex/Agy/another agent, preserve work for manual recovery, HOLD, or CLOSE OUT. Repeated empty commits require diagnosis: distinguish a stalled implementation from no-op commits produced while already-complete implementation is blocked by GitHub administration. Never demand another empty commit just to acknowledge a status change.

A fallback from a Jules-owned implementation branch requires **management to establish the trusted base, replacement branch, and preferably its draft PR before supplying an executable replacement-agent prompt**. Keep the old Jules branch read-only for the replacement agent; cross-link the old and new PRs and describe the last trusted commit. Do not tell an incoming agent to rebase, switch, or write to the old Jules branch. A new Jules session instead works in its task-managed checkout and submits a new PR. A complete, reviewable draft PR should be marked Ready for review by management; no merge is implied. Human authorisation is required to launch a replacement implementation agent, merge, or publish a release.

The **failure form** must cover every materially available outcome: finish existing implementation/administration; retry the current viable Jules session; salvage a predecessor; fresh Jules; Codex; Agy; another agent; a small direct management fix; manual patch/recovery; HOLD; CLOSE OUT; no action; and Other with free text. Explain and disable inapplicable paths rather than presenting impossible choices as available. Include independent decisions for whether to preserve or retire the old PR, each worthwhile issue change, any review, next prompt, and release only where release is actually relevant. Always show the unrestricted additional-instructions field.

Do not substitute a generic handoff for investigation. If Jules remains viable, include the complete recommended Jules recovery or restart prompt in the initial response. For a handoff requiring a new replacement branch, first obtain the human's handoff decision, create and verify that branch and draft PR, then provide the final executable Agy/Codex prompt directly in a fenced code block in the conversation. If setup fails, identify the blocker rather than inventing a branch or PR URL. GitHub comments should contain only concise findings, decisions, links, and `@jules`-addressed corrections where an active Jules session can use them; full Agy/Codex prompts belong in the conversation.

## Answer submitted decisions together

When the operator submits the form, read **all selections and the always-visible free-text instructions as one decision**. Execute only the actions expressly authorised, observe the original management article's branch ownership and review gates, and report verified completion and remaining blockers. Do not require a fresh approval round for actions already clearly approved; do not infer authorisation for unselected actions. If an instruction is unclear and materially affects a consequential action, resolve only that uncertainty while still completing the independent, unambiguous approved work.
