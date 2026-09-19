---
title: "Jules management: submission is part of the task"
date: 2026-09-19T18:51:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - github
  - workflow
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

This is a clarification to [Managing Jules with a Management LLM](/blog/post/2026/044-jules-management/). For Jules task prompts and out-of-band answers, the submission rule below takes precedence over any earlier wording that makes pull-request creation conditional on the kind of work produced.

## Submission is an outcome, not an optional implementation choice

A Jules task must end in a **submitted, inspectable GitHub pull request** for human review. The management LLM should give one positive, unambiguous instruction: make the relevant changes, commit and push them, and submit or update the PR. Do not undermine that instruction with an alternative ending such as "if no code changes are warranted, don't create a PR", "a PR is unnecessary", or "report the findings instead of creating a PR". Such branches have caused Jules to stop with local output instead of submitting anything, even though submission is essential to this workflow.

This rule applies equally to implementation, audits, documentation, verification, test hardening and issue-reconciliation tasks. A task that finds no production-code defect can still have a reviewable deliverable: checked-in audit evidence, verification notes, acceptance-criteria reconciliation, documentation, or a focused test. Do not invent an unrelated code change merely to make the diff nonempty.

When an existing task PR is available, Jules updates and pushes that PR. When a task does not yet have one, it submits the work in a PR. The management prompt need not speculate about PR creation mechanics or repeatedly contrast "create" versus "do not create". It should state the required end state and leave the ordinary submission mechanics to the agent.

A local report, changed working tree, commit or pushed branch without a PR is **not a completed submission**. If the agent genuinely cannot submit through its available control plane, it must state the concrete failure and return the exact branch, commit and remaining action. The management layer then performs authorised GitHub administration where it has access; this is an exception for an actual capability failure, not a fallback completion route to offer pre-emptively in every prompt.

## Keep submission distinct from approval and closure

Submission does not mean the work is verified, approved, ready for human review or merged. A draft PR is the appropriate inspectable artifact while implementation or management review is still in progress. The management layer reviews the actual diff and checks, requests corrective work on the same PR where appropriate, and marks it ready when delegated review passes. It retains responsibility for consequential lifecycle decisions under the original management guidance.

For audit tasks, maintain a precise distinction between criteria supported by repository evidence, criteria requiring live/manual validation, and criteria that remain incomplete. Map confirmed unresolved problems to durable issues. **Do the audit and submit the audit deliverable**; neither a large follow-up defect nor the absence of a production-code fix cancels the submission requirement.

## Wording for management prompts

> Complete the scoped work, record the evidence and remaining limitations, commit and push the deliverable, and submit the pull request for management review. Return the PR URL and exact head commit. Keep the PR in draft while substantive implementation or review work remains.

Make this the single submission instruction. Do not append conditional alternatives about whether to open a PR or permission to finish with only a local report. If a PR already exists, a direct follow-up can instead say: "Update the existing PR with the completed work, push the changes, and return the PR URL and head commit."