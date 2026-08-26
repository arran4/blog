---
title: "Jules to Agy or Codex: A Practical Agent Handoff Workflow"
date: 2026-08-26T13:04:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - codex
  - antigravity
  - github
  - workflow
  - code-review
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

I have increasingly ended up using coding agents as a **pipeline rather than a single worker**. A pattern that has worked particularly well is:

1. start a task in **Google Jules**;
2. let Jules do the first codebase exploration and implementation;
3. review the resulting pull request rather than trusting the completion summary;
4. continue with Jules while the branch remains healthy;
5. when the session or branch becomes unreliable, hand the work to **Google Antigravity CLI (`agy`)** or **OpenAI Codex**;
6. either rebuild from current `main`, or fork the last known-good commit into a new branch;
7. open a replacement PR, cross-link the old and new PRs, and close the obsolete one.

This is not about one agent being universally better than another. The useful part is that a second agent gets a chance to reason from a **different context boundary**. A branch that has accumulated mistaken assumptions, repeated corrective prompts, generated churn, merge conflicts, or empty commits is often easier to finish by treating the old PR as evidence rather than as the workspace that must be preserved.

This post documents the workflow I have converged on, including what information each system actually needs in a prompt, what is usually redundant, and when a handoff is worth the disruption.

## The core idea: separate implementation state from problem state

A pull request contains at least two kinds of information:

- **problem state**: what behaviour is wanted, the constraints, review findings, tests, issue discussion, and discoveries made while working;
- **implementation state**: the current branch, its commits, generated files, conflict resolutions, partial fixes, and accidental churn.

Those are not equally valuable.

When a PR is healthy, the implementation state is useful context and should normally be preserved. When a PR has become confused, the implementation state can become a liability. The issue, review comments, tests, and selected pieces of the diff may still be excellent specifications even when the branch itself should be discarded.

That leads to the most important handoff question:

> **Do I trust the current branch, or only the knowledge learned while producing it?**

There are three answers.

### 1. Trust the branch: keep using Jules

Stay on the existing PR when:

- the cumulative diff is still small and understandable;
- requested changes are actually appearing in commits;
- the base branch has not moved enough to invalidate assumptions;
- CI failures are ordinary implementation problems;
- Jules is converging rather than oscillating.

Changing agents too early throws away useful working context.

### 2. Trust a specific commit: fork the known-good head

Use this when most of the implementation is correct, but the original Jules PR or session is no longer safe to keep using.

Create a **new branch from the exact trusted commit**, not from whatever the old PR happens to become later. Continue with Agy or Codex there. The old PR becomes a historical record and should be cross-linked and closed after the replacement exists.

This is especially useful when an automated agent can continue reacting to comments or CI and mutate the original branch after I have decided it is no longer trustworthy.

### 3. Do not trust the branch: reconstruct from current `main`

Use a clean rebuild when:

- the base has moved significantly;
- there are substantial merge conflicts;
- the old PR contains unrelated or generated churn;
- later changes on `main` made part of the old implementation obsolete;
- the branch contains too many corrective/revert commits to audit confidently;
- the task's intended semantics are clearer than the branch's history.

In that case the replacement agent should inspect the old PR and its review discussion, but should treat them as a design/reference document. The new branch starts from current `main` and reproduces only the still-valid behaviour.

## Why Jules works well as the first stage

[Jules](https://jules.google/docs/) is naturally repository and pull-request oriented. A task runs in its own VM, it clones the selected repository and branch, produces a plan, implements the change, and can create a branch/PR. Jules can also respond to pull-request feedback, and in Reactive Mode it only acts when explicitly mentioned with `@jules`.

That makes Jules a good first-stage agent because I usually **do not need to spend prompt space describing GitHub mechanics**. The repository and base branch are already selected in the UI.

For an initial Jules task I normally need to describe:

- the problem or desired behaviour;
- important architectural constraints;
- behaviour that must be preserved;
- acceptance criteria;
- relevant tests or verification expectations;
- an issue number if the resulting PR should use a resolving keyword such as `Fixes #123`.

I normally do **not** need to tell Jules:

- to clone the repository;
- how to name a branch;
- how to commit;
- how to push;
- how to create the initial PR;
- the repository URL when I have already selected the repository;
- a long sequence of Git commands.

Those details are usually noise in the initial task. The useful prompt is the locally actionable software task.

Jules also supports repository instructions such as `AGENTS.md`, so stable repository conventions are better stored there than repeatedly copied into every task.

### Jules limitations I plan around

The repository-oriented workflow is also why I avoid treating a Jules task as an indefinitely reliable workspace:

- the task executes in a remote VM, so host-specific, hardware-specific, desktop, packaging, or credential-dependent behaviour may not be reproducible there;
- plan and completion messages are useful explanations, but they are not proof that the branch contains the described changes;
- PR feedback automation can keep acting on the original PR, which is convenient while I trust the session and a reason to fork away from it when I do not;
- usage and concurrency limits exist and change by plan, so I do not make the workflow depend on unlimited retries;
- a long feedback chain can accumulate stale assumptions even when each individual instruction was reasonable at the time.

These are reasons to add verification and an escape hatch, not reasons to avoid Jules.

### The important Jules limitation: completion prose is not the diff

The strongest lesson from repeated use is that I must review **what GitHub says changed**, not what the agent says it changed.

I have had Jules report that a fix was completed and pushed while the resulting commit was empty. In one Quickshell update, two consecutive follow-up commits (`0211ce7` and `08e5950`) contained **zero additions, zero deletions, and no changed files**, even though Jules' replies described the requested file changes as completed. In another `goa4web` PR, commit `7a17b99` similarly claimed a comprehensive repair but was empty.

That does not make the whole session useless. It is a signal that the current agent loop has stopped reliably connecting intent to repository state.

My rule is now:

> **After a suspicious completion, inspect the commit or cumulative diff immediately. After repeated empty/no-op commits, stop spending corrective prompts on the same session.**

A prompt saying "do not make another empty commit" is useful once because it confirms the failure mode. Repeating it indefinitely is not.

## The PR review loop: what effective feedback looks like

When Jules is still converging, pull-request comments work well when they contain **specific behavioural blockers** rather than a general request to "fix the PR".

A useful corrective comment has this structure:

```text
@jules
Please correct this PR without broadening its scope.

1. <observable incorrect behaviour>
   - why it is wrong
   - the invariant that must hold
   - a concrete reference if one exists

2. <second blocker>
   - expected behaviour
   - what must not be changed to obtain it

Verification:
- run the focused tests
- run the normal repository checks
- inspect the resulting diff

Preserve:
- <known-good behaviour A>
- <known-good behaviour B>
```

The `Preserve:` section has turned out to be particularly valuable. Corrective agents otherwise have a tendency to repair one problem by undoing a previous correct decision.

For generated systems, I also explicitly distinguish **source-of-truth files** from generated output. If a generated Go file, workflow, manifest, or fixture is wrong, the prompt should normally say to fix the generator/input and regenerate rather than hand-editing generated output.

## When to stop the Jules loop

I hand off when one or more of these starts happening repeatedly.

### Repeated empty commits

This is the clearest failure mode. The agent's natural-language reply says work is complete, but `git show --stat`, GitHub's commit view, or the PR diff shows no change.

At that point, the important prompt is no longer another detailed implementation request. The important action is to establish a clean branch boundary.

### Oscillation or reverts

A follow-up fixes A but breaks B; the next restores B but reintroduces A. This often indicates that the session's accumulated context is working against the current specification.

### The branch is being mutated by automation I no longer trust

If the agent is still attached to the PR and automatically responding to comments or CI, preserving the current PR can be risky even after I have found a good commit. Fork the known-good commit to a new branch before further work.

### The base moved and changed the truth

This is more serious than an ordinary merge conflict. Sometimes `main` has gained a fix or migration that makes part of the old PR conceptually obsolete. Rebasing the old implementation can preserve code that should now disappear.

A clean rebuild forces the replacement agent to ask: **what remains necessary today?**

### The cumulative diff contains too much historical noise

A PR can eventually contain the right final files and still be difficult to trust because of generated churn, unrelated edits, or a long series of repair commits. If reconstructing the desired change from current `main` is cheaper than auditing the branch, reconstruction wins.

## Agy and Codex as second-stage agents

I use [Google Antigravity CLI](https://antigravity.google/docs/cli/overview/) (`agy`) and [OpenAI Codex](https://openai.com/codex/) for roughly the same second-stage role: give an independent agent a cleanly defined repository state and a compact record of what was learned from the first attempt.

The exact product interfaces differ, but the handoff principles are the same.

### Agy

Agy is a local terminal agent. It operates in the project workspace, supports planning, file editing, command execution, and approval modes. Google's own best-practice guidance emphasises exploration, planning, verification loops, and providing runnable tests.

That makes it well suited to a handoff where I want the agent to inspect Git state directly and perform branch surgery in a local checkout.

The important practical requirements are:

- start from a clean workspace or worktree;
- make the trusted base explicit (`main` or an exact commit);
- ensure Git/GitHub authentication is available if I expect it to push and open/close PRs;
- state the PR lifecycle operations explicitly, because they are part of the task rather than implicit output of a Jules task.

What Agy does **not** need is a tutorial on Git. If the repository is already checked out, it does not need the repository URL repeated in every prompt. If it can inspect the old PR/diff through GitHub tooling, I do not need to paste the complete patch into the prompt.

Agy's main limitation in this workflow is that **its environment is my environment**. That is a major advantage when the bug depends on local tooling, but it means a missing compiler, container runtime, credential, repository checkout, or GitHub permission is a real capability boundary. Unlike the initial Jules task flow, a replacement-PR lifecycle is not something I assume from the interface: if I want a new branch, PR, cross-link, and closure of the old PR, I say so. Approval/sandbox mode is also a deliberate trade-off: `plan` is useful for a safe audit, while broader edit/command approval is useful only once the starting state is clear.

### Codex

Codex can operate in terminal, editor, and cloud environments, and can use repository `AGENTS.md` instructions. I use it similarly as an independent implementation/review pass, particularly when I want a clean reconstruction or a more deliberate audit of what should be preserved from a problematic PR.

For Codex, the highest-value context is again not a giant transcript. It is:

- the target repository and issue/PR identity;
- the trusted starting point;
- the behavioural requirements;
- the review findings that matter;
- what to preserve;
- what to deliberately discard;
- how to verify the result;
- what GitHub lifecycle result I expect.

A configured development environment and reliable test commands are much more valuable than verbose implementation instructions. OpenAI's Codex guidance similarly recommends prompts that look like good GitHub issues: scoped problem descriptions, relevant files/components, examples, and verification.

Codex has a similar environment boundary to Agy, but it can show up in more than one form: local CLI/editor work and cloud/worktree-style tasks do not necessarily have the same tools, credentials, network access, or services. I therefore avoid prompts that silently assume access to a private dependency or a running local service. I also do not assume that "continue PR #123" means "preserve this exact branch history": the trust boundary and desired GitHub lifecycle need to be explicit. A clean context can still broaden scope, so the preserve/drop lists and cumulative-diff review remain necessary.

### Which second-stage agent?

The roles overlap heavily. I tend to favour Agy when the most valuable thing is the **existing local environment and direct branch/worktree manipulation**, and Codex when I want a **fresh independent audit or a clean agent workspace**. Availability, plan limits, and the state of the local toolchain can decide the choice just as legitimately as model preference. The workflow should survive either agent being temporarily unavailable.

### Shared limitation: a fresh agent can still faithfully implement the wrong specification

Switching agents is not magic. If the handoff says "copy PR #123 exactly", a second agent can reproduce the same mistake perfectly.

The handoff must therefore explain **why the old PR is being replaced** and identify which parts are authoritative:

- current `main`;
- the issue/acceptance criteria;
- selected review findings;
- a specific known-good commit or file blob;
- tests that express the intended behaviour.

The old branch is evidence, not automatically truth.

## Two handoff templates

These are intentionally different. Choosing the wrong one is a common source of wasted work.

### Template A: rebuild from current main

Use this for stale, conflicted, polluted, or conceptually obsolete PRs.

```text
Work on <repo> and replace PR #<old> with a clean implementation.

The old PR is untrusted as an implementation branch. Do not rebase, merge, or
wholesale cherry-pick it. Start a new branch from current main and use the old
PR, its review discussion, and its diff only as reference material.

Goal:
- <behavioural outcome>

Preserve from the old work:
- <requirement/invariant A>
- <requirement/invariant B>

Re-evaluate or discard:
- <obsolete implementation A>
- <unrelated/generated churn B>

Acceptance criteria:
- <observable behaviour>
- <tests>
- <scope boundary>

Verification:
- run <focused tests>
- run <normal repository checks>
- review the cumulative diff against current main for unrelated changes

GitHub lifecycle:
1. create a new branch and replacement PR;
2. make the new PR body say it supersedes #<old>;
3. retain any resolving reference to the underlying issue, e.g. `Fixes #<issue>`;
4. after the replacement PR exists, comment on #<old> with the new PR link;
5. close #<old> without merging it.
```

The critical line is: **"the old PR is untrusted as an implementation branch"**. Without that, an agent may "helpfully" rebase or merge the exact history I am trying to escape.

### Template B: fork the last trusted commit

Use this when the branch is good up to a specific point but the attached Jules session must no longer be allowed to control it.

```text
Replace PR #<old> with a new PR that continues from the last trusted state.

The trusted source is commit <sha> (currently the known-good head/state of the
old PR). Create a new branch starting exactly from that commit. Do not continue
working on the original Jules branch after the fork.

Remaining work:
- <fix A>
- <fix B>

Preserve exactly:
- <known-good semantic decision>
- <file/blob/hash if byte identity matters>

Verification:
- confirm the new branch starts from <sha>;
- confirm the requested change creates a real diff;
- run <tests/checks>;
- inspect the cumulative PR diff for unintended changes.

GitHub lifecycle:
1. open the replacement PR;
2. say `Supersedes #<old>` in its body;
3. retain `Fixes/Closes/Resolves #<issue>` if applicable;
4. cross-link the replacement from #<old>;
5. close #<old> only after the replacement PR exists.
```

This pattern protects a good implementation from a bad *session* without needlessly reconstructing everything.

## What is actually required in a handoff prompt

The most effective Agy/Codex handoff prompts I have used contain seven things.

### 1. The object being replaced

Give the old PR number or URL and, if relevant, the issue it is meant to resolve. The second agent should be able to inspect the original discussion rather than relying on my memory of it.

### 2. The trust boundary

State one of these explicitly:

- **start from current `main`; old branch is untrusted**, or
- **start from exact commit `<sha>`; that state is trusted**.

Do not leave the branch strategy implicit.

### 3. The reason for replacement

One sentence is often enough: repeated empty commits; merge conflicts and a moved base; automatic revert commits; generated churn; or obsolete assumptions after new changes landed on `main`.

This tells the replacement agent what failure it must avoid reproducing.

### 4. Preserve/drop lists

A handoff should say both what is known-good and what should be reconsidered. This is more useful than asking for a generic "clean up" because it establishes invariants.

### 5. Behavioural acceptance criteria

Prefer observable outcomes and tests over micro-managing the implementation.

Good:

```text
Two concurrent append attempts must not overwrite one another; the database
mutation must be authoritative and the regression test must fail under the old
read/replace implementation.
```

Less useful:

```text
Edit lines 210-240 and add a mutex.
```

The first gives the agent room to discover the correct repository-native solution.

### 6. Verification

Name the focused tests and the normal repository checks. Also require an inspection of the **cumulative diff against the intended base**.

A test suite can pass while the PR contains unrelated changes.

### 7. The GitHub lifecycle

This is required when the handoff is meant to replace a PR. The code agent should not have to infer that "fix this" also means:

- create a different branch;
- open a different PR;
- cross-link it;
- preserve resolving keywords;
- close the old PR.

These are workflow semantics, not code semantics.

## What is usually not required

Several things make prompts longer without improving the result.

### A full transcript of the previous agent session

The useful information should already be distilled into review findings, the old PR, tests, and a preserve/drop list. A full chat history adds contradictory intermediate ideas.

### The entire old diff pasted into the prompt

If the agent can inspect the PR or commit, point it there. Paste only small fragments that are themselves the specification, such as an exact error message, SQL shape, expected output, or known-good hash.

### A branch name chosen in advance

Usually I only care that the replacement branch is distinct and starts from the correct base. Naming it is low-value unless repository automation depends on a naming convention.

### Generic instructions such as "write good code"

Repository conventions belong in `AGENTS.md`, tests, linters, and existing code patterns.

### Every Git command

Describe the desired Git state. Let the coding agent choose the safe commands unless a precise operation is itself important, such as "branch exactly from commit `<sha>`" or "do not rebase the old branch".

### Repeating requirements the repository can state authoritatively

If `AGENTS.md` defines generated-file policy, test commands, formatting, or architectural rules, the prompt can refer to it. Duplicating those rules increases the chance that the prompt and repository instructions drift apart.

## Case studies from my PR history

The pattern is easier to see in real replacements.

### `g2` #420 -> #520: discard the contaminated branch

[`g2` #420](https://github.com/arran4/g2/pull/420) accumulated **12 commits** around a small three-file change. The replacement, [#520](https://github.com/arran4/g2/pull/520), explicitly said it superseded #420 with a clean diff against current `main`, retained the reviewed `fs.FS` compatibility behaviour, removed unrelated churn, and was merged with a **single commit**.

The lesson is not "one commit good, twelve commits bad". The lesson is that once the branch was no longer trusted, preserving its history had no value. The specification was smaller and cleaner than the implementation history.

### `goa4web` #3074 -> #3075: current main invalidated part of the old solution

[`goa4web` #3074](https://github.com/arran4/goa4web/pull/3074) mixed several fixes, including database work for long external URLs. By the time it needed repair, the base had moved and migration `0096` on `main` had already solved the URL-storage problem differently.

The replacement [#3075](https://github.com/arran4/goa4web/pull/3075) rebuilt against current `main`, explicitly documented that the old migration work was obsolete, implemented only the remaining forum filter and quote-selection fixes, added stronger tests, and merged.

This is the strongest argument against blindly rebasing a stale agent PR: a conflict is sometimes telling me that the world has changed, not merely that Git needs help choosing lines.

### `g2` #453 -> #528: keep the architectural intent, narrow the scope

[`g2` #453](https://github.com/arran4/g2/pull/453) established RuleSet groundwork but review uncovered subtle behaviour around metadata-aware rules and severity ownership. The replacement [#528](https://github.com/arran4/g2/pull/528) retained the core architecture, added an explicit opt-in interface for RuleSet-managed rules, and deliberately left broader auto-detection/CLI selection to a separate issue.

The useful handoff information here was not "copy these five files". It was the architectural invariant: **legacy and metadata-aware rules must not silently stop running merely because RuleSets were introduced**.

### `arrans_overlay` #854 -> #859: escape an automation-controlled history

[`arrans_overlay` #854](https://github.com/arran4/arrans_overlay/pull/854) contained a substantial Caelestia stack implementation. The replacement [#859](https://github.com/arran4/arrans_overlay/pull/859) explicitly existed to keep a clean history and avoid automatic revert commits from automated sessions during CI failures. It preserved the large known-good package payload while fixing the revision/source and update-workflow problems, then merged.

This is an example where "start over" did **not** mean "forget everything". The replacement PR body acted as a compact inventory of what was being carried forward.

### `arrans_overlay` #871 -> #874: fork a good state away from a bad session

[`arrans_overlay` #871](https://github.com/arran4/arrans_overlay/pull/871) is the clearest example of the trusted-commit pattern. Follow-up repair prompts were specific: restore a strict-aliasing patch, preserve unconditional Qt Gui dependencies, keep the version bump, and fix line-length lint without inventing a USE flag.

Jules replied as though it had applied the fixes, but successive commits were empty while the malformed patch remained. The replacement [#874](https://github.com/arran4/arrans_overlay/pull/874) carried forward the Quickshell update to a clean replacement branch and restored the patch from a known-good blob.

When an exact artefact matters, a **hash is an excellent acceptance criterion**. "Make this patch equivalent" leaves room for accidental whitespace damage. "The resulting file must hash to `1d3e149f9856e410c191fbb69801f3bb89a9db5a`" is machine-verifiable.

### `goa4web` #3076: a completion summary can be completely disconnected from the commit

In [`goa4web` #3076](https://github.com/arran4/goa4web/pull/3076), a large review request covered race-safe SQL append semantics, image handling, activity metadata, grants, read markers, search indexing, generated-code hygiene, and regression tests. Jules replied that these had been completed; the corresponding commit `7a17b99` was empty.

The practical lesson is to verify **immediately after large claimed completions**. The more comprehensive the prose summary, the more expensive it is to assume it reflects repository state without checking.

## Tips that have made the workflow more reliable

### Use cumulative-diff review, not only last-commit review

A corrective commit can look perfect while the PR still contains an earlier unrelated change. Always inspect the final diff against the intended base.

### Record exact known-good artefacts when possible

Useful anchors include:

- commit SHA;
- blob SHA;
- generated output checksum;
- fixture output;
- SQL query shape;
- exact error text;
- a passing/failing regression test.

These reduce ambiguity during a cross-agent handoff.

### Separate "must preserve" from "must fix"

This prevents a common repair pattern where an agent solves the latest review comment by undoing the previous correct change.

### Prefer one coherent review request over many tiny contradictory comments

Once I have enough evidence to understand the real bug, a consolidated review comment is usually better than a chain of incremental guesses. If later evidence changes the diagnosis, write a new coherent specification rather than asking the agent to mentally subtract old instructions.

### Do not keep paying the same failure mode

One mistaken commit is ordinary. A second empty commit after an explicit warning is evidence that the session itself may be the problem. Switching agents or branches is then a debugging technique, not a judgement about the model.

### Keep old PRs as history

I prefer replacing and cross-linking rather than deleting evidence. The old PR often contains useful review discussion explaining why the replacement was necessary.

A replacement body should say something like:

```text
Supersedes #123.

Recreated from current main because the original branch had <reason>.
The old PR is retained for review history/context.

Fixes #45
```

The `Supersedes` relationship explains PR history; the resolving keyword still connects the replacement to the underlying issue.

### Close in the right order

Create the replacement PR first. Then add its link to the old PR and close the old PR. That avoids a period where the work exists only in an unreferenced branch.

### Use the second agent as a reviewer before using it as an editor

For difficult changes, I often get a better result if the handoff first asks the new agent to inspect current `main`, the old PR, and review findings and state what is still required. Then the implementation follows that fresh model of the problem.

Both Agy and Codex support planning/exploration workflows, so there is little reason to force them directly into editing when the main problem is uncertainty about the previous implementation.

## A compact decision checklist

Before I send another corrective prompt to Jules, I ask:

- Is the last claimed change actually present in Git?
- Is the cumulative diff still understandable?
- Is the old base still semantically current?
- Are generated changes coming from the correct source files?
- Am I fixing a code problem, or am I now fighting the agent/session state?

If the code problem is clear and the branch is healthy, continue Jules.

If the branch is good at a known commit but the session is not, fork that exact commit and continue with Agy/Codex.

If the branch or its assumptions are no longer trustworthy, start from current `main`, use the old PR as reference, and rebuild only the validated intent.

## Final principle

The most effective part of a multi-agent workflow is not "agent A writes code, agent B writes better code". It is the ability to **reset the implementation context without resetting the engineering knowledge**.

Jules can cheaply establish a first implementation, reveal codebase constraints, produce tests, and expose hidden requirements during review. Agy or Codex can then take a deliberately chosen clean state and finish the task without inheriting every mistake made along the path.

The handoff prompt should therefore be shorter than the history it replaces. It should say:

- what problem remains;
- what is known to be correct;
- what state is trusted;
- what must be discarded;
- how success will be measured;
- what the replacement PR lifecycle should be.

Everything else is implementation detail that the next agent can rediscover from the repository.
