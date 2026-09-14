---
title: "Recovering from Jules Environment and Session Failures"
date: 2026-09-15T09:30:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - chatgpt
  - github
  - workflow
  - code-review
  - orchestration
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

<!-- cspell:words handoff handoffs inspectable joobq unmerged -->

This is a companion to [Managing Jules with a Management LLM](https://arran4.github.io/blog/post/2026/044-jules-management/). That post describes the overall management model and the important rule that a Jules branch remains Jules-owned even after a failed VM or apparently dead session.

This post makes one narrower part of that workflow more explicit: **what to do when Jules itself fails before the implementation can continue**, especially when a session cannot be resumed immediately.

The important distinction is between an **implementation failure** and an **agent-environment failure**. A VM-preparation failure, repository-clone failure, authentication failure, lost environment, or exhausted agent capacity says very little about the correctness of the code already committed. Treat the repository state and the agent runtime as separate systems.

## First classify the failure

Before deciding what to do, identify where the failure happened.

### Failure before repository access

Examples include:

- VM or container preparation failed;
- repository clone failed;
- repository credentials or proxy access failed;
- the environment terminated before checkout completed.

In this case Jules has not meaningfully evaluated the new task. Do not reinterpret the error as a code review result and do not discard a previously reviewed good commit merely because the new VM could not clone it.

### Failure after checkout but before useful changes

The session may have inspected the repository and then failed, or it may have produced only scratch state that was never pushed.

Treat the last independently inspectable Git commit as authoritative. Unpublished Jules commentary is useful context, not durable implementation state.

### Failure after useful commits exist

This is the most important recovery case. There may already be a nearly-correct Jules PR with one small blocker remaining.

The failed session does not make those commits bad. Preserve the last trusted commit, but also remember that the **Jules branch remains unsafe for external writes** because a recovered or restarted Jules process can still overwrite it later.

## The four practical outcomes

When resume is unavailable or undesirable, I use four outcomes. They are not equal in preference.

| Outcome | Use when | Main risk |
| --- | --- | --- |
| **1. Small manual fix on a new branch/PR** | The remaining correction is narrow, obvious, and independently reviewable | Manual patch may receive less automated exploration |
| **2. Close/retire the failed Jules line and create a replacement Jules prompt** | The implementation still needs substantial agent work and the old session cannot continue | Replacement agent may repeat old questions or rediscover decisions unless the prompt is very explicit |
| **3. Merge the correct current work, then create a new Jules prompt for the remaining follow-up** | The current PR is independently correct and the remaining work is genuinely separable | Temptation to merge known-incomplete work merely to simplify agent state |
| **4. Manually manage a stacked PR** | A true dependency forces the next change to build on unmerged work | The lower Jules branch may be reset or rewritten, destabilising the stack |

The default preference is roughly **1, then 2 or 3 depending on correctness boundaries, with 4 as a last resort**.

## Outcome 1: small manual fix, but do not patch the Jules branch

A management LLM may directly patch a small, high-confidence problem when no capable implementation agent is currently available.

The critical rule is that the patch should normally go onto a **new management-owned branch**, not the Jules-owned branch.

A useful sequence is:

1. identify the last reviewed good Jules commit;
2. create a new branch from that exact commit;
3. make the smallest required correction there;
4. open a replacement PR immediately;
5. cross-link the old and new PRs;
6. retire the old Jules PR when leaving it open would permit CI-fixer or recovered-session automation to interfere with the active work;
7. verify the replacement PR independently before merge.

Creating a new PR is especially preferable when CI takes long enough that Jules automation could wake up during the test window, or when a failing CI job can trigger a Jules CI fixer that might rewrite the original branch.

A direct patch onto the Jules branch can appear faster, but it creates a race against an agent that may later force-push its own remembered state. Avoid that race instead of trying to merge faster than the agent can wake up.

## Outcome 2: replace the Jules session with a new prompt

If the remaining work is too large for a small direct patch, start a new Jules task rather than trying indefinitely to revive a broken environment.

The replacement prompt should **not** look like the original prompt with a new task ID. It should contain the knowledge accumulated during the failed attempt.

A replacement Jules prompt should normally include:

- the durable issue number and full relevant issue content;
- the exact prior PR and last trusted commit for provenance;
- a short statement that the prior session failed for an environment/service reason, not because the implementation was rejected;
- the exact files and symbols that need to change;
- the current observed behaviour and desired behaviour;
- the specific review blockers still outstanding;
- decisions already made in earlier JOOBQ exchanges;
- approaches that were tried and rejected, with the reason;
- snippets or pseudocode for delicate changes when the intended shape is already known;
- exact tests to add or preserve;
- exact validation commands;
- explicit scope boundaries and known non-goals.

The objective is to make the new task **replay-complete**. The new Jules instance should not have to ask the human the same questions simply because the old VM disappeared.

### Be more prescriptive on replacement attempts

The first Jules prompt can often leave ordinary implementation details to the agent. A replacement prompt should become more prescriptive in proportion to the amount already learned.

If review already established that one specific implementation shape is appropriate, say so directly. For example:

```text
In test/views/lifecycle_test.dart, use the repository's existing temporary-Isar
setup pattern. Seed a MathChat, mount ChatPage, allow fireImmediately watchers to
attach, unmount the widget, then mutate the watched chat/message collections and
assert tester.takeException() is null.

Do not make ChatPage silently tolerate a missing Isar instance merely to simplify
the test; preserve the production invariant.
```

If the previous session asked whether to choose between two approaches and management already answered, carry that answer into the new prompt:

```text
Do not ask again whether to use a fake repository abstraction for this fix.
Use the existing temporary-Isar test pattern; broader storage abstraction belongs
to the separate architecture issue.
```

If a small code sketch removes ambiguity, include it:

```dart
final subscription = stream.listen((value) {
  if (!mounted) return;
  setState(() => state = value);
});

@override
void dispose() {
  subscription.cancel();
  controller.dispose();
  super.dispose();
}
```

The snippet is not necessarily a demand for byte-for-byte implementation. It is a way to make the ownership and lifecycle contract explicit.

## Outcome 3: merge correct work, then start a follow-up

Sometimes the existing PR is correct as-is and the remaining concern is genuinely another piece of work. In that case, merging first can produce the cleanest base for a new Jules task.

This option is appropriate only when the current PR independently satisfies its own acceptance criteria. Do **not** merge a known lifecycle bug, failing security property, broken test, or incomplete required behaviour merely because a fresh Jules task is easier to launch from `main`.

Good examples for a post-merge follow-up include:

- a broader refactor that was explicitly out of scope;
- additional non-blocking coverage;
- a performance improvement discovered during review;
- cleanup that is desirable but not required for correctness.

The follow-up prompt should state what just merged and should start from the new `main`, avoiding an unnecessary PR stack.

## Outcome 4: stacked PRs are the least preferred recovery

A stacked PR can be necessary, but it is fragile when the lower branch is Jules-owned.

The danger is straightforward:

```text
main
  |
  +-- Jules PR A
         |
         +-- replacement/manual PR B
```

If Jules later rewrites PR A, PR B can suddenly contain conflicts, disappear from the intended diff, or acquire unrelated changes.

If a stack cannot be avoided:

- freeze the lower dependency at an exact reviewed commit;
- preferably copy that commit to a non-Jules branch before building the upper PR;
- record the dependency explicitly in both PR descriptions;
- never assume the lower Jules branch will remain stable because the session currently appears dead;
- re-check the merge base before every review or merge action.

In most cases it is cleaner either to make a replacement PR from the trusted commit or to merge a complete lower PR before starting the next task.

## CI fixers change the recovery calculation

A failing CI job is not merely passive status when Jules or another automation can react to it.

If a Jules CI fixer is configured, a failing check may wake automation that still considers the original Jules branch authoritative. That creates two independent writers: the manual recovery path and the CI fixer.

When making a direct recovery patch, prefer a new branch/PR if:

- CI will take a meaningful amount of time;
- the existing Jules branch can still receive automated fixes;
- the CI failure itself is unrelated to the code under review;
- it would be difficult to distinguish a useful Jules follow-up from a stale overwrite.

Do not change unrelated CI configuration merely to make the recovery PR green. Record an infrastructure/router failure as such and validate the implementation by another available route when possible.

## When should the old Jules PR be closed?

The management post deliberately avoids a universal rule because open/closed state can interact with queues and automation.

For recovery, use this more concrete test:

**Keep the old PR open** when it is still the active implementation line, when Jules may validly resume it, or when a queue depends on it remaining open.

**Close or retire the old PR early** when all of the following are true:

- a replacement branch/PR has already captured the last trusted state;
- the old branch is no longer intended to receive valid implementation work;
- leaving it open creates a credible risk of CI-fixer, recovered-session, or queue automation overwriting/confusing the replacement;
- the old PR is cross-linked to the replacement so provenance is not lost.

Closing the old PR does not mean deleting history. The replacement should name the superseded PR and trusted commit, and the old PR should point forward to the replacement.

## A replacement-prompt template

When a Jules session has failed and must be replaced, a prompt can use this structure:

```text
<One or two lines describing the intended code change and why.>

This is a replacement for a failed Jules session. The previous session failed
while preparing its environment / cloning the repository. Treat that as an agent
infrastructure failure, not as evidence that the implementation approach was bad.

Repository: <owner/repo>
Issue: #<n> — <title>
Previous PR: #<n>
Last trusted commit: <sha>

Start from <latest main / explicitly selected base>. Do not attempt to resume or
push the old Jules-owned branch.

CURRENT STATE
<What already exists on main or what must be recreated from the trusted diff.>

REQUIRED CHANGES
1. <file/symbol>: <exact change>
2. <file/symbol>: <exact change>
3. <test>: <exact scenario>

KNOWN DECISIONS FROM THE PREVIOUS ATTEMPT
- <question Jules asked>: <answer already decided>
- Do not use <rejected approach>; use <selected approach> because <reason>.

IMPLEMENTATION SHAPE
<Small snippets/pseudocode where this removes ambiguity.>

PRESERVE
- <working behaviour/tests from previous attempt>

DO NOT DO
- <scope boundary>
- <unrelated architecture issue>
- <unrelated CI changes>

VALIDATE
<exact format/lint/test commands>

Create a new PR that links the superseded PR and explains that this task replaces
a Jules environment/session failure.
```

For a private repository, duplicate all task-critical issue and review context into the prompt. Do not rely on the replacement Jules instance being able to read the old PR discussion.

## Management-LLM checklist for Jules errors

When Jules reports a VM, clone, authentication, or environment error, the management layer should:

1. inspect GitHub and identify the last trusted commit rather than trusting the session summary;
2. classify the failure as agent infrastructure versus implementation behaviour;
3. assume the Jules branch remains Jules-owned;
4. determine whether the remaining correction is small enough for a direct management patch;
5. if patching directly, create a new branch first and usually a new PR;
6. otherwise choose between a replacement Jules task and a clean post-merge follow-up;
7. avoid a PR stack unless a real dependency makes it necessary;
8. account for CI-fixer or queue automation that can still write to the old Jules line;
9. make replacement Jules prompts more explicit than first-attempt prompts, carrying forward previous questions, answers, rejected approaches, exact files, tests, and useful snippets;
10. cross-link old and new PRs and preserve the reason for the handoff;
11. never merge known-incomplete work merely to simplify agent recovery;
12. never infer that a dead VM means the Jules branch is safe for external writes.

The durable object is the work item and its Git history, not the individual Jules VM. Recovery becomes much easier once those are treated as separate lifecycles.
