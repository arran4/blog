---
title: "Management decision forms and Jules failure recovery"
date: 2026-09-25T11:05:00+10:00
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

This is a companion reference for [Managing Jules with a Management LLM](/blog/post/2026/044-jules-management/). The original article remains authoritative for branch ownership, review, recovery, and human approval. These interaction rules apply to **any management question**, not just post-merge and failure recovery.

## One complete decision form, with room for the human

The management LLM must first use the task context and available evidence to do the work it can already do. Ask only about actual decisions requiring the operator's input; do not turn known facts or investigation steps into a questionnaire. Put outstanding human decisions into **one interactive form** when supported. Every question must explain which action a selection authorises, distinguish recommendations from approvals, preselect a reasonable recommendation where safe, include **No action**, and offer **Other with free text**. Independent issue proposals need independent approvals. Do not add irrelevant or impossible options merely to fill out the form.

**Every form must end with an always-visible, unrestricted multiline field titled `Additional details, corrections, or my own instructions`.** This field must not be conditional on selecting Other, must remain available when No action is selected, and must allow an entirely different plan or qualifications to several answers. Read it together with the selected choices before acting; reconcile any conflict rather than silently ignoring either. If an interactive form is unavailable, give a structured text questionnaire with the same choices and an unrestricted final free-text answer area. A form must never trap the operator inside incomplete predefined choices.

Report **ACTION REQUIRED** for decisions, **RECOMMENDATION** for suggested but unauthorised actions, and **INFORMATION** for verified findings and completed actions. Give precise GitHub links and distinguish completed actions from planned ones.

## Post-merge decision coverage

Verify the merge; reconcile issues and pull requests; assess new work and the next release; recommend CONTINUE, HOLD, or CLOSE OUT. The initial response should already contain the full, ready-to-paste **primary Jules prompt** when that is a viable next task. Do not demand a form submission merely to obtain it.

The consolidated form should cover, when relevant:

- Each independent issue proposal: approve the named creation/update/consolidation/closure, defer, no action, or other with free text.
- Continuation: recommended direction, CONTINUE, HOLD, CLOSE OUT, no action, or other with free text.
- Next prompt: recommended task (first), secondary (second), third, a specifically identified later task (Nth), all remaining worthwhile prompts, redo the last prompt with new details, no additional prompt, no action, or other with free text. Offer only tasks actually identified; selecting a prompt does not launch an agent.
- Release: accept the recommended plan **for consideration only**, explicitly create and publish the recommended release, explicitly create and publish a patch/minor/major release where applicable, prepare for review without publishing, defer, no release, no action, or other with free text. Preselect a **non-publishing** choice. A recommendation, issue approval, or prompt choice never authorises publication; verify version and prerequisites before an authorised publication.
- Other consequential review, dependency, or repository-administration decisions that actually require human input.

## A Jules failure report is the starting evidence, not an intake quiz

A recovery request starts with the **outcome the operator has already supplied**, perhaps `JULES OUTCOME: FAILURE — container failed`, `JULES OUTCOME: FAILURE — repeated empty commits`, or a pasted Jules message, logs, session link, PR, or worktree ZIP. The operator may include as much or as little detail as they have. **Do not ask them to select the failure type again or restate the failure, original requirements, or URLs already available.** Ask for genuinely missing, consequential information only when it cannot be recovered from the conversation, GitHub, or artifacts. Do not make the operator select `Investigate` as a recovery strategy: investigating is management's mandatory first step, not a proposed action for approval.

The management LLM is the **manager of the failed implementation**, not the failed Jules worker. Establish where execution stopped, independently check the issue, prior decisions, relevant main commits, session, PR, cumulative diff, review comments, CI, commits, and supplied worktree/patch/ZIP/logs. Report the last trusted implementation state, useful work and remaining requirements. A container failure before checkout is not evidence of coding non-convergence. Repeated empty commits may reflect already-complete work blocked by GitHub administration, or a genuinely stalled implementation; distinguish them. Do not infer a root cause without evidence or discard useful work merely because the session failed.

## Offer bespoke *recovery actions*, not generic investigation options

After establishing the available state, recommend one concrete route and show the **materially viable alternatives for this particular failure**. Each selectable route must say: what work it preserves; which agent(s) do which step; whether the old session or PR is reused or becomes read-only; the exact trusted base; whether a new branch/PR or predecessor merge is needed; prerequisites; and what management will do after approval. Preselect the recommended route and offer No action and Other with free text. Include a genuinely different viable route even when one is recommended; if alternatives are blocked, explain why without offering them as though executable. Do not rank or list agents as interchangeable with recovery methods.

Consider combinations where appropriate, not just one agent per outcome:

- **Retry current Jules session:** only when it is viable, can consume a focused `@jules` correction, and the failure is recoverable; avoid repeated no-op commits or retries of inaccessible infrastructure operations.
- **Restart a new Jules session:** start from an appropriate available base with corrected task instructions, preserving recovered requirements and progress. This is different from retrying the failed session; Jules works in its own task-managed checkout and submits a new PR.
- **Recover existing work in a separate branch and PR, then continue with Jules:** management first preserves/reconstructs the trusted work on its own recovery branch and preferably draft PR. If a new Jules task can actually use that recovery base at task creation, specify it there and leave Jules on its assigned checkout; otherwise finish and merge a reviewable recovery predecessor with human approval before starting Jules from the resulting main. Never tell Jules to change branches or push to another agent's checkout. Never present this route as immediately viable when the target repository or base cannot be accessed by Jules.
- **Recover existing work in a separate branch and PR with Agy or Codex:** after human approval, management creates the replacement branch and draft PR from the last trusted base, makes the old Jules branch read-only to the incoming agent, and supplies a complete handoff with the salvaged work and remaining tasks.
- **Split or sequence agents:** for example, management salvages the patch into a reviewable predecessor; Agy or Codex fixes an isolated defect in a separately owned continuation; Jules resumes from the merged predecessor. Assign a clear owner, separate branch/PR lifecycle, validation gate, merge dependency, and handoff point to each phase. Never have Jules and a replacement agent concurrently write the same branch.
- **Complete or salvage the existing PR:** management finishes authorised GitHub administration, or prepares a coherent predecessor for human review without treating unfinished work as merged.
- **Direct management repair or manual recovery:** management repairs a small independently verifiable defect on a separately owned branch and PR, or creates a concrete patch/worktree and explicit manual steps when tool access blocks publication.
- **HOLD, CLOSE OUT, or No action:** preserve the durable record and explain any blockers or superseding work.

A Jules-owned implementation branch is not writable by a different implementation agent or by direct management fixes. A replacement agent normally needs management to create an isolated replacement branch and preferably draft PR before its *executable* prompt is supplied. For the special case of a new Jules task, respect task-managed checkout and base selection at task creation; do not treat a prepared recovery branch as permission to instruct Jules to check it out or to reuse another agent's branch. Human approval is required for a new replacement-agent implementation handoff, merges, and releases. When a draft PR is technically complete, management owns its Ready for review transition; do not ask Jules for empty commits solely to manipulate GitHub state.

## Make the failure decision form reflect the findings

Ask **`Which recovery route would you like me to carry out?`**, not `What happened?` or `Should I investigate?`. Populate it from the actual viable routes found above. A real container failure with no checkout may justify `Retry current Jules`, `New Jules session`, or `Use another agent from main`; a partial, trusted implementation may justify `Salvage to recovery branch/PR -> new Jules`, `Salvage to recovery branch/PR -> Codex`, `Salvage -> Agy -> Jules`, or `Complete current PR`. Do not blindly display all these examples. A path involving a predecessor merge must identify human review as its prerequisite and must not imply automatic merge.

For each proposed recovery route, state whether selecting it authorises management to create the branch/PR and prepare a handoff, merely requests a prompt, or actually launches an agent. A request for a prompt alone must not launch an agent. Include independent, relevant choices for old-PR disposition, each issue proposal, review, next prompt, and release **only if the recovered work has reached a release decision point**. A release question must never be added mechanically to an unfinished failed implementation. Always show the unrestricted additional-instructions field, regardless of the selected route, including No action. Treat free text as able to modify the selected route or describe a custom sequence.

Do not substitute a generic handoff for actual recovery. If Jules remains a viable recommended next step and the prompt is executable without unapproved branch/merge steps, include the complete ready-to-paste Jules retry or restart prompt in the initial response. For an Agy/Codex route needing a new branch, first obtain the human's recovery decision, create and verify the branch and draft PR, then provide the final executable handoff in a fenced code block in the conversation. When prerequisites are blocked, give a conditional/resumption prompt with the exact missing step rather than inventing a branch, PR, or completed merge. GitHub comments contain concise findings and links and `@jules` corrections where an active session can use them, not full Agy/Codex prompts.

## Answer submitted decisions together

Read **all choices and the always-visible free-text instructions as one decision**. Execute the actions expressly authorised; do not demand another approval for the same clear action or infer permission for unselected actions. Observe branch ownership, validation, Ready for review, merge, and release gates. Report what actually succeeded and what remains blocked. If custom text conflicts with a selection in a consequential way, resolve only that ambiguity while proceeding with independent unambiguous authorised work.
