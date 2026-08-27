---
title: "ChatGPT-Orchestrated Jules to Agy or Codex: A Practical Multi-Agent Development Workflow"
date: 2026-08-26T13:04:00+10:00
draft: false
tags:
  - llm
  - agents
  - jules
  - codex
  - antigravity
  - chatgpt
  - github
  - workflow
  - code-review
categories:
  - Software Development
  - LLM Instructions
  - Automation
---

I have increasingly ended up using coding agents as a **pipeline rather than a single worker**. The important part of that pipeline is not only the Jules-to-Agy-or-Codex handoff. There is another agent sitting outside the implementation session: usually **ChatGPT with GitHub integration**, or another system that can inspect the issue, pull request, commits, comments, and CI independently.

In practice my workflow looks more like this:

1. use ChatGPT or another integrated assistant to understand the task and turn it into a focused **Jules** prompt;
2. let Jules do the first codebase exploration and implementation;
3. have the outside assistant review the resulting PR and **each meaningful follow-up commit**, checking Git rather than trusting Jules' completion prose;
4. use that review to write the next Jules PR response, answer a question Jules asks in its web session, or decide that no further prompt is needed;
5. keep implementation changes inside Jules while Jules still owns the branch, because direct non-Jules pushes can be unwound by a later Jules update;
6. when the Jules phase is deliberately over, either make very small, obvious fixes directly through the integrated GitHub tooling or hand substantial remaining work to **Google Antigravity CLI (`agy`)** or **OpenAI Codex**;
7. if handing implementation to another agent, **always create a new branch**: either rebuild from current `main` or fork the last known-good Jules commit into a new branch; never let the replacement agent continue on the original Jules branch;
8. review the Agy/Codex changes with the outside assistant as well;
9. when switching away from Jules, retire the Jules PR: optionally leave an immediate transition comment saying the work is being moved to a new branch and continued by `<agent>`; once the replacement PR exists and is ready to become the canonical work, comment on the Jules PR with the replacement link and close the Jules PR without merging it;
10. throughout the job, keep the PR/work unit narrow but record credible out-of-scope discoveries in the project's durable issue register, normally GitHub Issues, updating an existing issue rather than creating a duplicate when one already exists;
11. at the end of the job, reconcile the open issue register against what actually landed: close issues that are now fully resolved, update partially resolved issues with what was fixed and what remains, and make sure pending fixes are linked accurately when the PR has not yet merged;
12. only merge the replacement when I explicitly decide the work is ready.

This means I am not asking one coding agent to both implement and police itself. The outside assistant acts as **reviewer, prompt writer, state tracker, and traffic controller**. Jules, Agy, and Codex are implementation engines that can be swapped when the state of the work changes.

This is not about one agent being universally better than another. The useful part is the separation of responsibilities and the ability to give a second implementation agent a **different context boundary**. A branch that has accumulated mistaken assumptions, repeated corrective prompts, generated churn, merge conflicts, or empty commits is often easier to finish by treating the old PR as evidence rather than as the workspace that must be preserved.

This post documents the workflow I have converged on, including what information each system actually needs, what is usually redundant, how I review every step, when direct edits are safe, how out-of-scope discoveries are preserved without bloating the current PR, and when a handoff is worth the disruption.

## The missing layer: an outside orchestrator

The most important correction to a simple "Jules -> Agy/Codex" diagram is that I do not normally operate those agents in isolation.

There is a separate conversation, commonly ChatGPT with access to GitHub, that remains outside the implementation agent's context. I use it to:

- inspect the issue and current repository state before writing the initial task;
- turn a rough idea into a self-contained Jules prompt;
- review the initial PR;
- review each subsequent commit or updated cumulative diff;
- inspect CI failures rather than merely relaying the red check name;
- write the next `@jules` PR comment;
- answer questions Jules asks inside the Jules web UI;
- distinguish a real implementation question from something Jules can discover itself;
- keep track of requirements that must survive later corrective passes;
- decide whether the next action should be another Jules prompt, a direct tiny patch, an Agy/Codex handoff, or no change at all;
- make sure credible out-of-scope discoveries are recorded in the project's issue register rather than being silently forgotten or smuggled into the current PR;
- reconcile relevant open issues when the job finishes, closing fully resolved work and updating partially resolved work;
- review replacement PRs and follow-up commits after the Jules phase;
- perform GitHub lifecycle work such as creating or updating PRs and cross-linking superseded work when the connected tools support it.

This outside context is valuable precisely because it is **not the same context as the implementation session**. Jules can become convinced that it changed a file when the commit is empty; the reviewer can simply inspect the commit. Jules can accumulate contradictory instructions over several rounds; the reviewer can reconstruct the currently valid specification from the issue, current `main`, PR discussion, and actual diff.

The orchestrator should not blindly act as a second coder during the Jules phase. Its strongest role is independent observation and concise steering.

## Review every change, not only the final PR

A major part of this workflow is the review cadence.

I do not generally send Jules a task, disappear, and review only when it says it is finished. After the initial PR and after meaningful follow-up commits, I ask the outside assistant to inspect the actual change and answer questions such as:

- Did the requested change actually appear in Git?
- Did the new commit modify the files Jules claimed it modified?
- Does the cumulative PR still preserve earlier correct decisions?
- Did the fix accidentally widen scope?
- Are generated outputs changing because the generator changed, or because a generated file was edited manually?
- Does CI expose a deeper design issue rather than a local typo?
- Did the latest change fix the review blocker without reintroducing an earlier one?
- Did the work reveal another credible problem that belongs in the issue tracker rather than this PR?
- Is the next response a code change request, a question for Jules, or simply approval/no further action?

This review can be extremely lightweight for a small commit. A commit hash and PR URL are often enough for an integrated reviewer to inspect the diff and say whether the previous blocker is gone.

The important rule is:

> **Every implementation agent is reviewed from outside its own completion narrative.**

That applies after Jules too. If Agy or Codex creates a replacement PR, I still review its commits rather than treating the handoff itself as proof that the result is clean.

## Keep scope narrow, but never lose discovered work

A focused PR should not become a grab bag just because an agent notices other problems while exploring nearby code. At the same time, a real problem discovered during the work should not disappear merely because it is outside the current task.

My rule is:

> **Out of scope means record it elsewhere, not ignore it.**

The project's normal issue register is the preferred durable location. For these repositories that usually means GitHub Issues. When an agent or reviewer finds a credible defect, missing test, architectural debt, follow-up improvement, or other actionable problem outside the current work unit, the workflow is:

1. search the existing issue register for the same underlying problem before creating anything new;
2. if an appropriate issue already exists, update it rather than opening a duplicate;
3. if no suitable issue exists, create a focused new issue;
4. record enough evidence that a later agent can reproduce or locate the problem without reconstructing the whole discovery session;
5. keep the current PR scoped unless the newly discovered problem is actually required to make its stated behaviour correct.

Useful evidence can include:

- the PR or commit where the problem was discovered;
- a file path, function, symbol, or specific line reference when that is stable and useful;
- a failing test, CI job, error message, log excerpt, or reproduction;
- the observed behaviour and the expected behaviour;
- why the finding is outside the current PR's scope;
- any dependency on or relationship to the current work.

Line references are especially useful when the problem is local to a concrete piece of code, but they should not replace the semantic description: line numbers move, while the underlying behaviour is what the future issue needs to preserve.

The issue should distinguish confirmed findings from speculation. I do not want agents generating a backlog from every thought they have while reading code. The threshold is a **credible, actionable project concern** with enough evidence to be useful later.

This responsibility is capability-aware. Agy, Codex, ChatGPT with GitHub integration, or another tool with issue access can search, create, and update the issue directly. If an implementation agent cannot reliably administer the project's issue tracker, it should still surface an issue-ready finding with the evidence above, and the outside orchestrator should make sure the durable record is actually created or updated. The responsibility is to ensure the finding is recorded, not necessarily to force every agent through an interface it does not have.

If a project uses something other than GitHub Issues as its authoritative issue register, use that instead. The important property is that the finding lands in the project's normal durable work queue, not only in an ephemeral agent response or PR conversation.

## Reconcile the issue register before declaring the job done

Issue hygiene also runs in the other direction. A completed job can make existing open issues stale even when those issues were not the original reason for the PR.

Before declaring the work finished, I want a deliberate pass over the project's open issue register, with particular attention to issues touching the changed components, behaviour, tests, or architecture. The goal is to compare the issues against the **actual final repository/PR state**, not against the agent's summary.

For each relevant open issue:

- if the completed work fully resolves the issue, close it once the fix is actually authoritative according to the project's lifecycle, and reference the resolving PR/commit where useful;
- if the work resolves only part of the issue, keep it open and update it with what is now complete, what remains, and links or code references that make the new state clear;
- if the work changes the diagnosis or invalidates part of the issue description, update the issue so a future agent is not sent down an obsolete path;
- if an existing issue covers a newly discovered out-of-scope finding, enrich that issue instead of opening another one;
- if the issue is still valid and untouched, leave it alone rather than manufacturing an update.

The merge boundary matters here. If a fix exists only in an open PR and has not landed on the authoritative branch, I do not want to falsely claim that the repository is already fixed. In that case the issue should be linked to the pending PR, and a resolving keyword can be used where appropriate so GitHub closes it on merge. Once the change has landed, fully resolved issues should not remain open merely because nobody revisited the issue list.

A partially resolved issue should be more useful after the job than before it. A good update says which acceptance criteria or sub-problems are now done and identifies the exact residual work. This prevents the next agent from repeating already-completed investigation or accidentally reopening settled design decisions.

This end-of-job reconciliation is part of the work product, alongside tests, the cumulative diff, PR metadata, and handoff state.

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

While I am in this state, I also avoid casually pushing my own fixes onto the Jules-controlled branch. Those edits may be correct and still be a bad workflow choice because Jules can later update from its own view of the task and **undo or overwrite a non-Jules push**.

There is one hard boundary here: **if I decide to switch implementation agents, I stop using the Jules branch for implementation immediately**. Even when the branch is healthy and the handoff is voluntary, Agy, Codex, or any other replacement implementation agent gets a new branch. If the Jules head is trusted, the new branch can start at that exact commit; if it is not, the new branch starts from current `main` or another deliberately chosen trusted base.

The Jules PR is also retired as part of that switch. It remains useful history, but it is no longer the active implementation PR. Once the replacement PR exists and is ready to take over, I link to it from the Jules PR and close the Jules PR without merging it.

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

The distinction between states 2 and 3 is therefore **which commit the new branch starts from**, not whether a new branch exists. A Jules-to-other-agent handoff always creates one.

## Why Jules works well as the first implementation stage

[Jules](https://jules.google/docs/) is naturally repository and pull-request oriented. A task runs in its own VM, it clones the selected repository and branch, produces a plan, implements the change, and can create a branch/PR. Jules can also respond to pull-request feedback, and in Reactive Mode it only acts when explicitly mentioned with `@jules`.

That makes Jules a good first-stage implementation agent because I usually **do not need to spend prompt space describing GitHub mechanics**. The repository and base branch are already selected in the UI.

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
- a long sequence of Git commands;
- to explain ordinary repository facts it can inspect itself.

Those details are usually noise in the initial task. The useful prompt is the locally actionable software task.

Jules also supports repository instructions such as `AGENTS.md`, so stable repository conventions are better stored there than repeatedly copied into every task.

## ChatGPT writes most of the Jules steering text

During the Jules phase I commonly use ChatGPT or another outside integrated assistant to write the text I send back to Jules.

Whenever I ask the outside assistant to produce a prompt, Jules response, Agy/Codex handoff, or other text that I am expected to paste somewhere else, I want the **ready-to-paste payload in a fenced `text` code block**. Explanations, review findings, and recommendations can stay outside the block. This keeps the actionable text unambiguous and makes it easy to copy without accidentally including the surrounding analysis.

Drafting that text and **acting on it are different operations**. Unless I explicitly ask the outside assistant to post the comment/review, update the PR, push a change, or merge, it should return the draft to me and stop there. In particular, "review this PR and give me a Jules response" is not permission to post that response to the PR, and a conclusion that a PR is ready is not permission to merge it.

A request to **switch implementation away from Jules** is different from a request to merely draft a review response. In this workflow, the switch itself implies the branch/PR retirement lifecycle: create the replacement branch, move the implementation to the named agent, create the replacement PR, link the old Jules PR to it, and close the Jules PR once the replacement is ready to take over. It still does **not** imply permission to merge the replacement.

Issue-register maintenance is another deliberate workflow responsibility rather than an accidental PR comment. When I ask an agent to perform a coding/review job under this workflow, credible out-of-scope findings should be durably registered and the relevant open issues should be reconciled at completion. That does not authorize unrelated code changes; it is how the workflow preserves work while keeping the PR scoped.

There are three common forms.

### 1. The initial Jules task

I describe the feature, bug, issue, or goal in the outside conversation. The reviewer can inspect the repository and issue, remove assumptions that are already false, and produce a prompt that is self-contained for a fresh Jules session.

This is particularly useful when Jules will have **no context from an earlier PR or chat**. The prompt should include the current problem and constraints, not references such as "do what we discussed earlier".

### 2. PR review responses

After Jules pushes a commit, I give the reviewer the PR or commit. It inspects the actual state and writes the next response for the PR, usually as a focused `@jules` comment.

The response should normally be returned to me in a fenced code block so I can inspect and copy it. The outside assistant should **not post the review response directly to the PR unless I explicitly ask it to do so**. Review, drafting, posting, and merging are separate levels of authority.

A useful response does not merely repeat a failing check. It explains:

- the remaining blocker;
- why it is a blocker;
- what invariant must be preserved;
- which parts of the previous implementation are already correct;
- any credible out-of-scope finding that must be put into the issue register rather than folded into this PR;
- the focused verification expected after the fix.

This lets the outside reviewer accumulate engineering knowledge while Jules remains the branch author.

### 3. Questions Jules asks inside its own web session

Jules sometimes stops and asks an architectural or scope question before continuing. I often copy that question into the outside conversation and ask for help answering it.

The outside assistant can inspect the issue, PR, repository, current base, and previous review findings and then give me:

- a short summary of why Jules is asking;
- the current technical situation;
- a recommended decision;
- a ready-to-paste answer for Jules.

The ready-to-paste answer should be in a fenced code block, separate from the explanation, so I can copy exactly the part intended for Jules.

The answer should resolve the decision Jules genuinely needs. It should **not** over-specify mechanics Jules can discover itself.

For example, if Jules has correctly discovered that a requested condition already exists in generated examples but not in the source template, the useful answer is about **which file is authoritative and what regression should be added**, not a list of shell commands telling Jules how to open the files.

This pattern also works after the Jules phase: I can use ChatGPT to write an Agy or Codex handoff prompt, review its result, and write follow-up instructions for that agent.

### Jules is not a general GitHub or PR administration agent

A major prompt-design rule is to separate **implementation work** from **repository administration**. Jules can work on the selected repository, create its task branch/PR, and respond to implementation feedback, but I do not treat it as a general-purpose GitHub client or as the independent reviewer of the work it just produced.

In this workflow, I treat the following as outside Jules' practical capabilities and do **not** spend prompt space asking Jules to do them:

- independently review a landed GitHub commit or cumulative PR diff as an outside reviewer;
- update an existing PR title, body, or summary after the PR has been created;
- merge the PR or make the final merge decision;
- force-push, reset, rebase, or otherwise rewrite branch history to an arbitrary trusted state;
- perform branch surgery such as moving a branch back to an exact known-good commit;
- create and administer a replacement-PR lifecycle: supersede the old PR, cross-link the two, preserve resolving keywords, and close the obsolete PR;
- safely arbitrate a branch containing non-Jules pushes while Jules still has its own task/session state for that branch;
- perform general GitHub administration such as labels, reviewer management, draft/ready state, closing/reopening, or other metadata operations unless that capability is explicitly exposed by the product.

The commit-review point is particularly important. Jules can inspect files in its own task workspace, but that is **not the same thing as independently reviewing the GitHub commit that actually landed**. I want that check to happen from another context using the commit SHA, PR diff, and CI as external evidence.

Similarly, "please update the PR summary" or "please merge this when done" is usually wasted or misleading Jules prompt content. Those are control-plane operations, not implementation requirements. I reserve them for ChatGPT with connected GitHub tools, Agy or Codex when they have appropriate Git/GitHub access, another similarly capable orchestration tool, or an explicit human action.

Issue hygiene is slightly different: Jules should not be asked to pretend it has a general GitHub issue-management capability that it does not have, but it **must not silently discard an out-of-scope finding**. It should report the finding in issue-ready form, including evidence and relevant code locations, so the outside orchestrator can search for an existing issue and create or update the durable record. Where the agent actually has issue-tracker access, it can perform that registration itself.

For Git history manipulation, Agy/Codex or another terminal-capable agent is normally a better fit because it can be told exactly which commit is trusted and can perform the required branch/worktree operations. For PR metadata and independent review, ChatGPT with GitHub integration is usually the better fit. For merging, a capable tool may execute the operation, but **the decision to merge remains separate and explicit** in this workflow.

This division also makes Jules prompts better. The Jules prompt should concentrate on behaviour, source-of-truth files, tests, invariants, and what must be preserved. GitHub administration belongs to the orchestration layer.

### Jules limitations I plan around

The repository-oriented workflow is also why I avoid treating a Jules task as an indefinitely reliable workspace:

- the task executes in a remote VM, so host-specific, hardware-specific, desktop, packaging, or credential-dependent behaviour may not be reproducible there;
- plan and completion messages are useful explanations, but they are not proof that the branch contains the described changes;
- PR feedback automation can keep acting on the original PR, which is convenient while I trust the session and a reason to fork away from it when I do not;
- usage and concurrency limits exist and change by plan, so I do not make the workflow depend on unlimited retries;
- a long feedback chain can accumulate stale assumptions even when each individual instruction was reasonable at the time;
- a later Jules action can unwind a manual/non-Jules branch edit if Jules still considers itself authoritative for that branch.

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

Out-of-scope findings:
- do not expand this PR for unrelated work;
- report any credible newly discovered issue with enough evidence for it to be
  added to or matched against the project issue register.

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

## Do not mix Jules ownership with casual direct pushes

This deserves its own rule because it changes how I use connected GitHub tools.

While Jules is actively working a PR, I generally treat its branch as **Jules-owned**. The outside reviewer can read everything and can write PR comments, but it should be conservative about pushing code to that branch.

The reason is practical rather than philosophical: Jules may later apply a plan based on its own task state and restore the version it believes should exist. A perfectly correct manual or ChatGPT-generated fix can therefore disappear in the next Jules commit.

During the active Jules phase the normal loop is:

```text
Jules changes code
        ↓
outside assistant reviews actual commit/diff
        ↓
outside assistant writes the next Jules response
        ↓
Jules makes the next code change
```

I break that rule only deliberately.

### After the Jules phase, small direct fixes are efficient

Once I have decided that Jules is finished and will no longer be allowed to mutate the branch, the trade-off changes.

If review finds a **small, mechanically obvious change**, it can be faster and safer for ChatGPT or another integrated GitHub tool to patch it directly rather than starting another coding-agent cycle. Examples include:

- correcting a typo or documentation sentence;
- fixing a small workflow condition whose intended form is already established;
- restoring a known-good one-line configuration value;
- adjusting a PR-owned test expectation when the semantics are already settled;
- adding a missing dictionary entry or similarly bounded repository metadata;
- making a tiny follow-up requested by CI where no architectural decision remains.

The threshold is not a line count. The question is whether there is any **meaningful implementation uncertainty** left.

If there is uncertainty, code generation, architecture, broad refactoring, generated-file regeneration, or substantial testing involved, I prefer Agy/Codex rather than turning the outside reviewer into an ad-hoc implementation agent.

A small direct post-Jules patch by the outside orchestrator is not the same thing as handing ownership to another implementation agent. **If Agy, Codex, or another implementation agent takes over, a new branch is mandatory**, even if the only intended difference at the moment of handoff is the branch name.

Before a direct post-Jules push, I want the branch ownership transition to be explicit:

- Jules is no longer expected to modify this branch;
- the current head has been reviewed and is the state being continued;
- the direct change is narrow and inspectable;
- the resulting commit is reviewed again;
- CI is checked afterwards.

This prevents the worst hybrid state: two agents both believing they own the same branch.

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

### Switching agents always means switching branches and retiring the Jules PR

This is true even when none of the failure modes above applies. A handoff can happen because a different environment is more useful, because local tooling is required, because I want an independent context, or simply because I choose to use another implementation agent.

The rules are still the same:

> **Never hand the original Jules branch to the replacement implementation agent. Create a new branch first.**
>
> **Once the replacement PR is ready to take over, point the old Jules PR to it and close the Jules PR without merging it.**

The new branch has only two meaningful starting strategies in this workflow:

- branch from the exact trusted Jules commit when that implementation state is worth preserving; or
- branch from current `main` when the Jules implementation state should be reconstructed or re-evaluated.

As soon as I decide to switch, an optional transition comment on the Jules PR can make the state clear before the replacement PR exists:

```text
This work is being moved to a new branch and will be continued by <agent name>.
A replacement PR will be linked here once it is ready.
```

Once the replacement PR exists and is ready to become canonical, I leave a final pointer on the Jules PR, for example:

```text
This work has moved to #<new> and is now being continued by <agent name>.
Closing this Jules PR without merging it; please follow #<new> for the active work.
```

Then I close the Jules PR. This makes the ownership transition visible in both Git and GitHub, preserves the Jules discussion as history, and prevents a later Jules action from colliding with the new agent's work.

## Agy and Codex as second-stage implementation agents

I use [Google Antigravity CLI](https://antigravity.google/docs/cli/overview/) (`agy`) and [OpenAI Codex](https://openai.com/codex/) for roughly the same second-stage role: give an independent agent a cleanly defined repository state and a compact record of what was learned from the first attempt.

The exact product interfaces differ, but the handoff principles are the same.

### Agy

Agy is a local terminal agent. It operates in the project workspace, supports planning, file editing, command execution, and approval modes. Google's own best-practice guidance emphasises exploration, planning, verification loops, and providing runnable tests.

That makes it well suited to a handoff where I want the agent to inspect Git state directly and perform branch surgery in a local checkout.

The important practical requirements are:

- **always create a new branch before Agy takes over from Jules**;
- choose that new branch's base explicitly: current `main` or an exact trusted Jules commit;
- start from a clean workspace or worktree for the new branch;
- ensure Git/GitHub authentication is available if I expect it to push and open/close PRs or maintain the issue register;
- state the PR lifecycle operations explicitly, because they are part of the task rather than implicit output of a Jules task;
- record credible out-of-scope discoveries in the project issue register rather than broadening the current PR;
- reconcile relevant open issues at the end of the job.

What Agy does **not** need is a tutorial on Git. If the repository is already checked out, it does not need the repository URL repeated in every prompt. If it can inspect the old PR/diff through GitHub tooling, I do not need to paste the complete patch into the prompt.

Agy's main limitation in this workflow is that **its environment is my environment**. That is a major advantage when the bug depends on local tooling, but it means a missing compiler, container runtime, credential, repository checkout, or GitHub permission is a real capability boundary. Unlike the initial Jules task flow, a replacement-PR lifecycle is not something I assume from the interface: if I want a new branch, PR, cross-link, closure of the old PR, or issue-register mutation, I say so. Approval/sandbox mode is also a deliberate trade-off: `plan` is useful for a safe audit, while broader edit/command approval is useful only once the starting state is clear.

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
- how to handle out-of-scope issue discoveries and end-of-job issue reconciliation;
- what GitHub lifecycle result I expect.

When Codex takes over from Jules, it also **always works on a new branch**. The handoff must say whether that branch starts from current `main` or from an exact trusted Jules commit; continuing directly on the Jules branch is not an option in this workflow.

A configured development environment and reliable test commands are much more valuable than verbose implementation instructions. OpenAI's Codex guidance similarly recommends prompts that look like good GitHub issues: scoped problem descriptions, relevant files/components, examples, and verification.

Codex has a similar environment boundary to Agy, but it can show up in more than one form: local CLI/editor work and cloud/worktree-style tasks do not necessarily have the same tools, credentials, network access, or services. I therefore avoid prompts that silently assume access to a private dependency or a running local service. I also do not assume that "continue PR #123" means "preserve this exact branch history": the trust boundary and desired GitHub lifecycle need to be explicit. A clean context can still broaden scope, so the preserve/drop lists, issue-register spillover, and cumulative-diff review remain necessary.

### Which second-stage agent?

The roles overlap heavily. I tend to favour Agy when the most valuable thing is the **existing local environment and direct branch/worktree manipulation**, and Codex when I want a **fresh independent audit or a clean agent workspace**. Availability, plan limits, and the state of the local toolchain can decide the choice just as legitimately as model preference. The workflow should survive either agent being temporarily unavailable.

Whichever implementation agent I choose, switching away from Jules first creates the branch boundary and retires the Jules PR. Agent choice comes after those invariants, not instead of them.

### Shared limitation: a fresh agent can still faithfully implement the wrong specification

Switching agents is not magic. If the handoff says "copy PR #123 exactly", a second agent can reproduce the same mistake perfectly.

The handoff must therefore explain **why the old PR is being replaced** and identify which parts are authoritative:

- current `main`;
- the issue/acceptance criteria;
- selected review findings;
- a specific known-good commit or file blob;
- tests that express the intended behaviour.

The old branch is evidence, not automatically truth.

## Rules for each system

The workflow is easier to reason about when each system has an explicit job and explicit limits.

### ChatGPT or another integrated outside assistant

**Primary role:** orchestrator, independent reviewer, prompt writer, and small post-agent fixer.

Rules I use:

- inspect the actual issue, PR, commit, diff, and CI before giving implementation advice when those are available;
- review each meaningful change rather than relying on an agent's completion summary;
- keep a running distinction between what is fixed, what remains, and what must be preserved;
- write the initial Jules prompt, follow-up PR comments, and answers to Jules' in-web questions;
- put prompts, PR-review responses, Jules answers, and agent-handoff text in **fenced `text` code blocks** so the exact actionable payload can be copied without the surrounding analysis;
- default to **drafting, not acting**: do not post a PR comment/review, update PR metadata, push a change, or merge merely because the user asked for a review or a prompt; perform those actions only when explicitly instructed;
- treat issue hygiene as part of the assigned engineering workflow: search for an existing issue before creating a duplicate, record credible out-of-scope discoveries durably, and reconcile relevant open issues when the job completes;
- when updating an issue, include useful evidence such as the discovering PR/commit, affected symbol/path/line when warranted, tests or errors, and the remaining work;
- treat an explicit request to **switch away from Jules** as an instruction to perform the standard handoff lifecycle, not merely draft it: create the new branch, arrange the replacement PR, cross-link it from the Jules PR when ready, and close the Jules PR without merging it;
- an optional early lifecycle comment may state that the work is moving to a new branch and being continued by the named agent; this is distinct from posting a drafted code-review response;
- ask the implementation agent for behaviour, not unnecessary Git command choreography;
- during the active Jules phase, prefer **comments/prompts over direct code pushes** to the Jules-owned branch;
- after the Jules phase, direct-edit only narrow, low-uncertainty changes; hand substantial work to Agy/Codex;
- whenever implementation ownership moves from Jules to Agy, Codex, or another coding agent, require a **new branch** before that agent changes code; start it from current `main` or an exact trusted Jules commit;
- never tell a replacement agent to continue directly on the original Jules branch;
- once the replacement PR is ready to take over, comment on the old Jules PR with the replacement link and agent name, then close the Jules PR without merging it;
- perform other PR metadata/lifecycle operations such as updating summaries or labels when the connected tools support them **and when I have explicitly requested those actions**;
- reserve branch-history surgery and force-push/rewrite work for a tool that actually has the required Git capabilities rather than trying to express it as a Jules implementation prompt;
- if a branch or PR is being replaced, make the trusted starting point and lifecycle explicit;
- re-review direct patches and agent patches after they land;
- do not merge merely because checks are green or because an agent says it is done; merging is a separate explicit decision.

The outside assistant should be willing to say **"no further prompt is needed"** when the change is correct. Continually inventing work is as harmful as missing a defect.

### Jules

**Primary role:** first implementation pass and iterative implementation while its PR remains healthy.

Rules I use:

- give Jules the software problem, constraints, invariants, acceptance criteria, and issue-resolution requirement;
- let Jules inspect repository mechanics it can discover itself;
- keep follow-up requests focused on observable blockers;
- explicitly say what previous behaviour must be preserved;
- answer genuine scope/design questions when Jules asks them;
- verify every claimed completion externally;
- do not broaden the PR for credible but unrelated discoveries; instead report them in issue-ready form with concrete evidence so the orchestrator can place them in the project's issue register;
- do not ask Jules to update PR summaries/bodies, independently review landed commits, merge PRs, force-push/rewrite history, or administer superseding/replacement PRs;
- route those GitHub control-plane tasks to ChatGPT, Agy, Codex, another suitably integrated tool, or an explicit human action;
- do not mix casual non-Jules pushes into a branch Jules is still expected to update;
- when another implementation agent takes over, retire the Jules branch from further implementation work, fork a new branch from the chosen trusted base, and retire the Jules PR once the replacement PR is ready;
- stop the loop when commits become empty, changes oscillate, the base invalidates the implementation, or the session is otherwise no longer trustworthy.

Jules is allowed to be the **author**, but not the sole reviewer, Git historian, PR administrator, issue-register administrator, or merge authority for its work.

### Agy

**Primary role:** local second-stage implementation, especially when direct access to my checked-out environment or branch surgery is useful.

Rules I use:

- **never continue directly on the original Jules branch**;
- create a new branch before making implementation changes;
- tell Agy exactly which Git state that new branch starts from;
- say whether it must start from current `main` or an exact trusted Jules commit;
- explain why the previous PR/session is being replaced;
- give preserve/drop lists rather than a full conversation transcript;
- keep unrelated discoveries out of the current PR and record them in the project issue register, updating an existing issue when possible;
- at completion, inspect relevant open issues, close those fully resolved by authoritative landed work, and update partially resolved ones with the residual scope;
- state branch/PR/cross-link/closure requirements when those operations are expected;
- let it inspect the repository rather than pasting everything into the prompt;
- use the outside reviewer again after Agy changes the branch.

Agy becomes the implementation owner only after the Jules ownership boundary is clear and the new branch exists.

### Codex

**Primary role:** independent second-stage implementation/reconstruction, particularly when a fresh context is more valuable than preserving the original session.

Rules I use:

- **never continue directly on the original Jules branch**;
- create a new branch before making implementation changes;
- provide the same explicit trust boundary as for Agy: current `main` or an exact trusted Jules commit;
- prefer issue-like prompts: problem, constraints, relevant components, examples, acceptance criteria, and verification;
- say what old implementation evidence is informative but not authoritative;
- keep unrelated discoveries out of the current PR and record them in the project issue register, updating an existing issue when possible;
- at completion, inspect relevant open issues, close those fully resolved by authoritative landed work, and update partially resolved ones with the residual scope;
- do not assume its environment has every local service, credential, or dependency;
- require the expected GitHub lifecycle when the task is to replace a PR rather than merely edit files;
- review its output independently after it lands.

Codex is not a magical cleanup step. A bad handoff specification can cause a clean agent to recreate the same wrong behaviour.

### GitHub/CI and the issue register

There is also a non-agent participant: the repository and its durable project records.

I treat GitHub, tests, generators, linters, CI, and the issue register as **evidence and state**, not just gates. A failed check can tell the reviewer what assumption is wrong. A green check does not prove that the cumulative diff has no unrelated change. An open issue can also become stale when a different PR happens to resolve some or all of it.

The repository therefore has its own rules:

- current `main` outranks stale assumptions from an old agent conversation;
- source-of-truth files outrank generated output;
- a commit hash or blob hash can be a stronger acceptance criterion than prose when exact identity matters;
- the cumulative PR diff matters more than the apparent neatness of the latest commit;
- resolving keywords and superseding links are part of the work product when issue/PR lifecycle matters;
- the issue register should reflect the current known project state, not merely the state at the time an issue was opened;
- fully resolved issues should be closed once the fix is authoritative;
- partially resolved issues should stay open but be updated so completed and remaining work are explicit;
- credible out-of-scope findings should be registered rather than left only in an agent transcript.

## Two handoff templates

These are intentionally different. Choosing the wrong one is a common source of wasted work. Both templates share two invariants: **the replacement implementation agent gets a new branch**, and **the old Jules PR is cross-linked and closed once the replacement is ready**.

### Template A: rebuild from current main

Use this for stale, conflicted, polluted, or conceptually obsolete PRs.

```text
Work on <repo> and replace PR #<old> with a clean implementation using <agent name>.

The old PR is a Jules PR and is untrusted as an implementation branch. Do not
rebase, merge, or wholesale cherry-pick it. Create a new branch from current
main and use the old PR, its review discussion, and its diff only as reference
material. Do not make implementation changes on the original Jules branch.

If useful before the replacement PR exists, leave a short comment on #<old>
stating that the work is moving to a new branch and being continued by
<agent name>.

Goal:
- <behavioural outcome>

Preserve from the old work:
- <requirement/invariant A>
- <requirement/invariant B>

Re-evaluate or discard:
- <obsolete implementation A>
- <unrelated/generated churn B>

Scope/issue hygiene:
- do not broaden this PR for unrelated problems discovered while working;
- search the project issue register for each credible out-of-scope finding;
- update an existing issue when it already covers the problem, otherwise create
  a focused issue with useful PR/commit/code/test references;
- at the end of the job, reconcile relevant open issues: close those fully
  resolved by authoritative landed work and update partially resolved issues
  with what remains. If this PR is still unmerged, link pending fixes rather
  than claiming they are already resolved on main.

Acceptance criteria:
- <observable behaviour>
- <tests>
- <scope boundary>

Verification:
- confirm work is occurring on the new branch created from current main;
- run <focused tests>
- run <normal repository checks>
- review the cumulative diff against current main for unrelated changes

GitHub lifecycle:
1. create a replacement PR from the new branch;
2. make the new PR body say it supersedes #<old>;
3. retain any resolving reference to the underlying issue, e.g. `Fixes #<issue>`;
4. once the replacement PR is ready to take over, comment on #<old> with the new PR link and say the work is being continued by <agent name>;
5. close #<old> without merging it;
6. do not merge the replacement PR unless explicitly instructed.
```

The critical line is: **"the old PR is untrusted as an implementation branch"**. Without that, an agent may "helpfully" rebase or merge the exact history I am trying to escape.

### Template B: fork the last trusted commit

Use this when the branch is good up to a specific point but the attached Jules session must no longer be allowed to control it.

```text
Replace PR #<old> with a new PR that continues from the last trusted state using
<agent name>.

The trusted source is commit <sha> (currently the known-good head/state of the
old Jules PR). Create a new branch starting exactly from that commit. Do not
continue working on the original Jules branch after the fork, even though the
starting content is intentionally identical.

If useful before the replacement PR exists, leave a short comment on #<old>
stating that the work is moving to a new branch and being continued by
<agent name>.

Remaining work:
- <fix A>
- <fix B>

Preserve exactly:
- <known-good semantic decision>
- <file/blob/hash if byte identity matters>

Scope/issue hygiene:
- do not broaden this PR for unrelated problems discovered while working;
- search the project issue register for each credible out-of-scope finding;
- update an existing issue when it already covers the problem, otherwise create
  a focused issue with useful PR/commit/code/test references;
- at the end of the job, reconcile relevant open issues: close those fully
  resolved by authoritative landed work and update partially resolved issues
  with what remains. If this PR is still unmerged, link pending fixes rather
  than claiming they are already resolved on main.

Verification:
- confirm the new branch starts from <sha>;
- confirm implementation work is occurring on the new branch, not the Jules branch;
- confirm the requested change creates a real diff;
- run <tests/checks>;
- inspect the cumulative PR diff for unintended changes.

GitHub lifecycle:
1. open the replacement PR from the new branch;
2. say `Supersedes #<old>` in its body;
3. retain `Fixes/Closes/Resolves #<issue>` if applicable;
4. once the replacement PR is ready to take over, comment on #<old> with the new PR link and say the work is being continued by <agent name>;
5. close #<old> without merging it;
6. do not merge the replacement PR unless explicitly instructed.
```

This pattern protects a good implementation from a bad *session* without needlessly reconstructing everything. The branch fork is still required even when the trusted commit itself is perfect.

## What is actually required in a handoff prompt

The most effective Agy/Codex handoff prompts I have used contain eight things.

### 1. The object being replaced

Give the old PR number or URL and, if relevant, the issue it is meant to resolve. The second agent should be able to inspect the original discussion rather than relying on my memory of it.

### 2. The trust boundary and new branch

State both of these explicitly:

- **create a new branch; do not continue on the Jules branch**, and
- choose its base: **current `main`; old branch is untrusted**, or **exact commit `<sha>`; that state is trusted**.

Do not leave either the branch transition or the base strategy implicit. The replacement agent always gets a new branch; the only question is what state that branch begins from.

### 3. The reason for replacement

One sentence is often enough: repeated empty commits; merge conflicts and a moved base; automatic revert commits; generated churn; obsolete assumptions after new changes landed on `main`; a need for local tooling; or simply a deliberate switch of implementation agent.

This tells the replacement agent what failure it must avoid reproducing and why the ownership boundary exists.

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

### 6. Scope and issue hygiene

Tell the replacement agent what to do when it discovers something real but unrelated to the current PR:

- do not silently ignore it;
- do not automatically broaden the PR;
- search the project's issue register first;
- enrich an existing issue if one already tracks the problem;
- otherwise create a focused issue;
- include useful evidence such as PR/commit references, code paths or lines when warranted, errors/tests, and the observed/expected behaviour;
- before declaring the job complete, reconcile relevant open issues with the final state, closing fully resolved issues only when the fix is authoritative and updating partially resolved ones with the residual work.

This turns scope control into durable project memory rather than lost context.

### 7. Verification

Name the focused tests and the normal repository checks. Also require an inspection of the **cumulative diff against the intended base** and confirmation that the implementation is happening on the new branch rather than the original Jules branch.

A test suite can pass while the PR contains unrelated changes.

### 8. The GitHub lifecycle

This is required when the handoff is meant to replace a Jules PR. The lifecycle is not optional or something the replacement agent should infer:

- create a different branch;
- optionally annotate the old Jules PR immediately that work is moving to `<agent name>` on a new branch;
- open a different replacement PR;
- preserve resolving keywords;
- once the replacement is ready to take over, comment on the Jules PR with the replacement link and the new agent name;
- close the Jules PR without merging it;
- leave merging the replacement as a separate explicit decision.

These are workflow semantics, not code semantics.

## What is usually not required

Several things make prompts longer without improving the result.

### A full transcript of the previous agent session

The useful information should already be distilled into review findings, the old PR, tests, the issue register, and a preserve/drop list. A full chat history adds contradictory intermediate ideas.

### The entire old diff pasted into the prompt

If the agent can inspect the PR or commit, point it there. Paste only small fragments that are themselves the specification, such as an exact error message, SQL shape, expected output, or known-good hash.

### A branch name chosen in advance

A **new branch is mandatory**, but its exact name usually is not important. I care that it is distinct from the Jules branch and starts from the correct base. Naming it in advance is low-value unless repository automation depends on a naming convention.

### Generic instructions such as "write good code"

Repository conventions belong in `AGENTS.md`, tests, linters, and existing code patterns.

### Every Git command

Describe the desired Git state. Let the coding agent choose the safe commands unless a precise operation is itself important, such as "create a new branch exactly from commit `<sha>`", "do not continue on the Jules branch", or "do not rebase the old branch".

### Repeating requirements the repository can state authoritatively

If `AGENTS.md` defines generated-file policy, test commands, formatting, architectural rules, or issue-workflow conventions, the prompt can refer to it. Duplicating those rules increases the chance that the prompt and repository instructions drift apart.

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

### `arrans_overlay` #871 -> #874: review every commit and fork away from a bad session

[`arrans_overlay` #871](https://github.com/arran4/arrans_overlay/pull/871) is the clearest example of the trusted-commit pattern and the outside-review loop. Follow-up commits were inspected as they appeared. Repair prompts were then rewritten around the actual remaining state: restore a strict-aliasing patch, preserve unconditional Qt Gui dependencies, keep the version bump, and fix line-length lint without inventing a USE flag.

Jules replied as though it had applied the fixes, but successive commits were empty while the malformed patch remained. The outside review caught the mismatch between completion prose and Git. The replacement [#874](https://github.com/arran4/arrans_overlay/pull/874) carried forward the Quickshell update to a clean replacement branch and restored the patch from a known-good blob.

When an exact artefact matters, a **hash is an excellent acceptance criterion**. "Make this patch equivalent" leaves room for accidental whitespace damage. "The resulting file must hash to `1d3e149f9856e410c191fbb69801f3bb89a9db5a`" is machine-verifiable.

### `goa4web` #3076: the outside reviewer catches a disconnected completion summary

In [`goa4web` #3076](https://github.com/arran4/goa4web/pull/3076), a large review request covered race-safe SQL append semantics, image handling, activity metadata, grants, read markers, search indexing, generated-code hygiene, and regression tests. Jules replied that these had been completed; the corresponding commit `7a17b99` was empty.

That is exactly where an independent integrated reviewer is useful. The next decision should be based on the commit and PR state, not on the apparent confidence or detail of the Jules response.

The practical lesson is to verify **immediately after large claimed completions**. The more comprehensive the prose summary, the more expensive it is to assume it reflects repository state without checking.

## Tips that have made the workflow more reliable

### Use cumulative-diff review, not only last-commit review

A corrective commit can look perfect while the PR still contains an earlier unrelated change. Always inspect the final diff against the intended base.

### Make the outside review cheap enough to do repeatedly

A review does not need to be a ceremonial full audit every time. For a small follow-up, I can provide the commit hash and ask whether the previous blocker was actually fixed and whether anything regressed. Keeping this loop cheap is what makes "review every change" practical.

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

### Use the issue register as the spillway for scope

An agent should not choose between scope discipline and preserving a useful discovery. Keep the current PR focused, then put the unrelated finding where the project normally keeps future work.

Search before creating. If an existing issue already describes the same root problem, add the new evidence there: the discovering PR or commit, a relevant code location or line reference, the test or error that exposed it, and any new understanding of the remaining work. Only open a new issue when the existing register does not already have a suitable home.

This makes "out of scope" a routing decision rather than a synonym for "forgotten".

### Reconcile issues after the implementation is finished

The issue tracker should not be write-only. Once the job is complete, look back through the open issues that the work may have affected.

If the landed change completely resolves one, close it or make sure the resolving PR will close it when merged. If it only resolves part, update the issue so the finished and unfinished portions are explicit. This is particularly important when the work solved a problem incidentally rather than through the issue that originally described it.

### Separate "must preserve" from "must fix"

This prevents a common repair pattern where an agent solves the latest review comment by undoing the previous correct change.

### Prefer one coherent review request over many tiny contradictory comments

Once I have enough evidence to understand the real bug, a consolidated review comment is usually better than a chain of incremental guesses. If later evidence changes the diagnosis, write a new coherent specification rather than asking the agent to mentally subtract old instructions.

### Answer questions; do not make the agent rediscover decisions I have already made

When Jules explicitly asks for a scope or design decision, the answer should be direct. Asking it to "investigate and decide" again wastes a useful pause in the workflow. The outside reviewer can do the investigation, explain the trade-off to me, and produce a concise answer that lets Jules continue.

Conversely, if Jules asks something that is plainly discoverable from the repository and does not require a product/design decision, I do not need to manufacture policy. I can tell it to follow the repository's source of truth and tests.

### Do not keep paying the same failure mode

One mistaken commit is ordinary. A second empty commit after an explicit warning is evidence that the session itself may be the problem. Switching agents or branches is then a debugging technique, not a judgement about the model.

### Never reuse the Jules branch for a replacement agent

This is worth repeating because it is easy for an agent to interpret "continue from this PR" as "keep working on this branch".

When the implementation agent changes, the branch changes too. If the Jules head is trusted, create a new branch at that exact commit. If the Jules implementation should be discarded, create a new branch from current `main`. In neither case should Agy, Codex, or another replacement implementation agent write to the original Jules branch.

### Retire the Jules PR when implementation moves

A new branch alone is not enough; leaving the old Jules PR open makes it look like there are two active implementations and leaves Jules attached to an apparently live piece of work.

When I commit to the handoff, I may first leave a short transition comment saying that the work is moving to a new branch and naming the replacement agent. Once the replacement PR exists and is ready to become the active work, I add a second comment linking to it and close the Jules PR without merging it.

The old PR remains valuable as review and implementation history. Closing it declares that it is no longer authoritative.

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

Once I have decided to switch, an optional early comment can mark the old Jules PR as being moved to `<agent name>` on a new branch. Then create the replacement branch and PR. Once that PR is ready to take over, add its link to the old Jules PR and close the old PR. Do not merge the Jules PR.

This avoids both failure states: closing the old PR before there is anywhere useful to point readers, and leaving two PRs looking simultaneously active after the replacement is established.

### Use the second agent as a reviewer before using it as an editor when appropriate

For difficult changes, I often get a better result if the handoff first asks the new agent to inspect current `main`, the old PR, and review findings and state what is still required. Then the implementation follows that fresh model of the problem.

Both Agy and Codex support planning/exploration workflows, so there is little reason to force them directly into editing when the main problem is uncertainty about the previous implementation.

### Keep merge authority separate from coding authority

An agent opening a PR, fixing all review comments, or making CI green does not imply permission to merge. The orchestrator can recommend that the work is ready, but the merge is a separate explicit action.

This separation is particularly useful in automated workflows because it prevents "the agent finished" from silently becoming "the change shipped".

## A compact decision checklist

After every meaningful implementation change I ask:

- Is the change Jules/Agy/Codex claimed actually present in Git?
- Did it fix the previous blocker?
- Is the cumulative diff still understandable?
- Is the old base still semantically current?
- Are generated changes coming from the correct source files?
- Did the change preserve earlier known-good behaviour?
- Did the work reveal any credible out-of-scope issue, and if so has it been matched to or recorded in the project issue register?
- Does the next step require implementation, or only a question/answer/review response?
- Am I fixing a code problem, or am I now fighting the agent/session state?

If the code problem is clear and the Jules branch is healthy, continue Jules and send the next externally reviewed prompt.

If Jules is deliberately finished and only a tiny, low-uncertainty correction remains, make the direct fix and review it.

If another implementation agent is taking over, **create a new branch first**. If the Jules branch is good at a known commit, branch from that exact commit and continue with Agy/Codex there. If the Jules branch or its assumptions are no longer trustworthy, create the new branch from current `main`, use the old PR as reference, and rebuild only the validated intent. Once the replacement PR is ready to take over, link it from the old Jules PR and close the Jules PR without merging it.

Before the job is declared complete, do the issue-register pass: inspect the open issues affected by the work, close those now fully resolved when the fix is authoritative, update those only partially resolved, and ensure any pending unmerged fixes are linked rather than misreported as already landed.

After Agy/Codex or a direct patch, return to the outside-review step again. The pipeline ends because the change, project issue state, and handoff state are reviewed and ready, not merely because the last implementation agent stopped talking.

## Final principle

The most effective part of this multi-agent workflow is not "agent A writes code, agent B writes better code". It is a separation of **implementation, review, control, and durable project memory**.

Jules can cheaply establish a first implementation, reveal codebase constraints, produce tests, and expose hidden requirements during review. ChatGPT or another integrated outside assistant can inspect what actually landed, maintain the current engineering specification, write the next question or response, ensure out-of-scope discoveries reach the issue register, reconcile issues after the work, and decide when the Jules phase has ended. Small, obvious changes can then be made directly once branch ownership is safe, while Agy or Codex can take over substantial remaining work from a deliberately chosen **new branch** based on either the trusted Jules commit or current `main`. The old Jules PR is then cross-linked and closed rather than left as a competing active implementation.

The important handoff is therefore not only Jules -> Agy/Codex. There are several repeated transitions:

```text
human intent
    ↓
outside assistant: inspect + formulate
    ↓
implementation agent: change code
    ↓
outside assistant: review actual Git state
    ↓
record out-of-scope findings in the issue register
    ↓
question / next prompt / approval / direct tiny fix / agent handoff
    ↓
new branch before replacement implementation agent edits
    ↓
replacement PR linked from old Jules PR; old PR closed
    ↓
reconcile open issues: close resolved, update partial
    ↓
review again
```

A good prompt should be shorter than the history it replaces. A good reviewer should know which parts of that history still matter. A good issue register should preserve the useful work that does not belong in the current PR. And no implementation agent should be required to be the final authority on whether its own work is correct.