---
title: "Post-Merge Decisions and Safe ChatGPT Finishing for Jules Work"
date: 2026-09-21T22:19:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - chatgpt
  - github
  - workflow
  - issue-management
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

This is an update to [Managing Jules with a Management LLM](/blog/post/2026/044-jules-management/). It adds a decision point after a merge and clarifies that the management LLM can finish bounded work itself before Jules fails. Where the older article requires another Jules prompt merely because an open issue exists, or assumes that implementation must continue with Jules until it fails, **the decision rules here take precedence**. Keep the older article's issue-creation approvals, branch-ownership safeguards, technical review, and human control over merges and releases.

## A merge is a decision point, not an instruction to start another task

After a confirmed merge, the management LLM should verify the merged PR, actual diff, related issue and PR state, CI where applicable, and changes since the last relevant release. It should then give **two independent recommendations**:

- **Release:** release now, use the established scheduled release, defer for a named blocker, or no release applies. Explain the changes since the last release, validation, versioning convention, urgency, and any downstream dependency. Do not equate merged with published. Do not publish a release without the human's authorisation.
- **Development:** **CONTINUE** if a concrete, worthwhile next implementation task is justified now; **HOLD** if valid work remains but can wait; **CLOSE OUT** if the current objective is complete and this workstream needs no more activity. A release and a development hold can both be recommended.

An open issue is a record of potential work, not a standing order to run Jules. Spare agent credits, a green CI run, or the ability to discover another possible test or refactor do not themselves justify extending a workstream. Consider current objectives, correctness and security risks, user-visible benefit, dependencies, existing in-flight work, review and CI burden, maintenance cost, and regression risk. Recognise diminishing returns across the human's other active repositories. Do not demand a zero-issue backlog before recommending a hold or closeout.

Describe a specific resumption trigger for HOLD: for example a reported regression, an approaching release or dependency deadline, an approved new requirement, or a scheduled maintenance review. Preserve legitimate low-urgency issues rather than closing them to make the project appear complete. A CLOSE OUT decision concerns the present objective, not permanent abandonment of the repository.

### Reconcile issues interactively

Search existing issues and PRs before proposing new ones. Close or update resolved items when authorised, check for duplicates or obsolete proposals, and identify credible new defects or improvements discovered during implementation or review. Distinguish work that blocks the current release or objective from work that could wait and ideas whose value remains unproven.

For each worthwhile new issue, present the proposed title, concise problem and acceptance criteria, evidence, urgency, and why an existing issue is not a suitable home. **Ask the human whether to create, modify, combine, defer, or discard it.** Group related decisions into a manageable set of questions. Do not silently create candidate issues, and do not turn every interesting observation into backlog work. When the human approves an issue or group of issues, create them directly when the management layer has permission and return the GitHub URLs. Preserve the existing rules for third-party human conversations and material changes to issue scope.

Do not finalise the next implementation recommendation before incorporating answers that materially affect the issue set or release blockers. The initial report may include provisional release and development advice and the decisions needed from the human; follow up with a reconciled final recommendation after the authorised GitHub administration. If CONTINUE is justified, choose a bounded task in the just-merged repository and provide its full Jules prompt **when the human elects to continue**. If HOLD or CLOSE OUT is justified, do not fabricate a next-task prompt. Report independently actionable downstream work separately rather than automatically moving to another repository.

### Concise post-merge message

The human can paste this into a fresh management conversation after confirming a PR has merged:

> Merged. Follow the post-merge process in https://arran4.github.io/blog/post/2026/052-jules-post-merge-lifecycle/ and the management guidance it updates.
>
> Verify the merge, reconcile existing issues and PRs, and investigate new findings. Propose worthwhile new issues and **ask me** which to create, modify, combine, defer, or discard; create approved issues and return their URLs.
>
> Advise whether to release now, on the normal schedule, or after further work. Recommend CONTINUE, HOLD, or CLOSE OUT, considering remaining value, risk, and activity across my repositories. Ask me about outstanding decisions. Provide the next complete Jules prompt only if I choose to continue; otherwise tell me when to resume.

## ChatGPT may finish work directly, before Jules fails

Jules is a useful first implementation worker, **not a required last worker**. During ordinary management review, actively consider whether a bounded correction, failing final check, small documentation adjustment, GitHub administration, or narrow remaining implementation task is better finished directly by ChatGPT when it has the actual tools and capability. The human may prefer to stop Jules early because it is stalled, becoming confused, repeatedly expanding scope, consuming review attention, or approaching an avoidable failure; a hard Jules failure is not a prerequisite for a handoff. Do not require another Jules attempt merely because the task started there. Likewise, do not imply that ChatGPT can change a repository or stop a Jules session when those controls are unavailable.

Distinguish ordinary **management administration** from implementation. When implementation is already complete and only authorised GitHub bookkeeping remains, perform that bookkeeping directly without sending Jules back for no-op changes. For a narrow implementation fix, inspect the actual PR, diff, reviews, checks, issue requirements, and last independently trusted commit before choosing the handoff. Prefer a direct fix when it has a clear end state and can be verified, not an open-ended rewrite that obscures provenance.

### One writable branch per active implementation owner

Before ChatGPT publishes code or documentation resulting from a Jules-owned implementation branch, establish an **independent non-Jules branch and preferably a draft replacement PR** from a deliberately chosen trusted commit or clean base. The management layer should create that branch/PR before editing when it has the tools to do so. Cross-link both PRs, record the trusted base and the reason for the handoff, and keep the original Jules PR and branch read-only from ChatGPT's perspective. Jules may still be running or may resume unexpectedly; it must not be allowed to overwrite ChatGPT's work, and ChatGPT must not push to Jules's branch. If stopping Jules is available and appropriate, do so, but branch isolation must not depend on stopping it successfully.

The reverse matters too: if ChatGPT's replacement attempt stalls or fails, preserve its independent branch, PR, reviewed commits, and findings. Jules may continue on **its own original branch**, but it must not be instructed to overwrite or adopt the ChatGPT branch as its writable checkout. Choose which line is authoritative after independent review. If the ChatGPT changes need further Jules work, prefer merging the safe replacement PR first and starting a fresh Jules task from the updated base; otherwise deliberately isolate a new task from a trusted base and make any dependency explicit. Do not assume two independently progressing PRs are interchangeable, or merge both without reconciling their diffs.

Do not create a replacement branch solely because the management LLM is reviewing, answering an out-of-band question, adjusting authorised PR metadata, or returning an unpublished local patch. When the current writable branch is already owned by the human or a non-Jules agent and its continuation is safe, normally keep its existing branch and PR. Branch isolation is specifically mandatory when a different implementation owner would otherwise write a Jules-owned branch, or when concurrent or conflicting ownership creates a real overwrite risk.

### Authorisation and review still apply

The human chooses whether to hand implementation to ChatGPT or another worker, and whether to merge or publish. Once a direct finishing task has been authorised, ChatGPT should carry out its bounded edits and validation in the active turn using available tools rather than offering another Jules prompt for work it can complete. Submit an inspectable PR for the finished change, including documentation-only work; report the actual checks run and any missing validation. Do not claim that a draft PR, a passing test, or an agent's completion statement substitutes for the normal management review and human merge decision.

At the post-merge gate, the desired outcome is a reconciled issue tracker and a clear release/development decision, **not a perpetual queue of prompts**.
