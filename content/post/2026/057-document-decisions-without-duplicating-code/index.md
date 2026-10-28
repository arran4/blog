---
title: "Document Decisions, Not a Second Implementation"
date: 2026-10-28T13:57:02+11:00
draft: false
guidance: ["documentation"]
tags: ["documentation", "architecture", "code-review", "ai-agents", "github", "maintainability"]
categories: ["Software Development", "LLM Instructions"]
---

<!-- cspell:words KLookup -->

A coding agent can finish a feature, write its tests, open a pull request, and then add a Markdown file explaining everything it just did. At first glance that seems thorough. Across a dozen related pull requests, though, those files become another set of things to reconcile, rebase and keep current. They can outlive the context in which they made sense.

I want documentation to preserve information that would otherwise be lost, **not to create a second implementation that competes with the code**.

That does **not** mean stripping detail from issues or pull requests. Quite the opposite: GitHub issues and PRs are where much of the valuable reasoning belongs. Their job is different from that of maintained repository documentation.

## Different records answer different questions

| Place | Question it answers | Does it need to track future implementation changes? |
| --- | --- | --- |
| GitHub issue | What problem were we trying to solve, what did we consider, and what did we decide? | No. It is a historical record of intent and discussion. |
| Pull request | What did this change actually do, why, how was it tested, and what was left unresolved? | No. It describes that particular change. |
| Source code | What does the system do now? | Yes. It is the authoritative implementation. |
| Tests | Which behaviours and edge cases must continue to hold? | Yes. They must remain executable against the current code. |
| Nearby source comment | Why is this non-obvious decision or constraint necessary here? | Yes, while that reasoning remains applicable. |
| Maintained repository documentation | How do I use, extend, operate or understand the *current* system? | Yes, when it describes current behaviour or contracts. |

An issue and a PR may both explain a feature, and the code may make the same feature visible again. **That is useful duplication**, because the three records have different purposes and different lifetimes.

The duplication I want to avoid is two independently maintained versions of an algorithm, state machine, configuration rule or internal architecture: one in source code and one in Markdown. The documentation will eventually drift unless someone keeps editing both.

## Issues are allowed to be detailed

An issue is a good place for requirements, acceptance criteria, design discussions, discarded alternatives, unresolved questions and decisions.

Suppose an application currently destroys a search-provider instance as soon as the first response arrives. An issue proposing pagination should record why that lifecycle is insufficient, what behaviours users need, and what constraints the design must respect.

When implementation later changes, there is no reason to rewrite the issue to pretend its original context never existed. The history helps explain the direction taken.

A terse issue that merely says "add pagination" loses information. A detailed issue is not redundant just because the implementation eventually exists.

## Pull requests are permanent implementation records

A PR should explain the actual change: scope, design choices, compatibility effects, important deviations from the issue, verification performed and remaining limitations. Review discussion is part of that record too.

A PR that says only "Fixes #48" forces a future reader to reconstruct everything from the diff. A PR describing the provider lifetime and cancellation changes, and which tests prove them, gives useful context even years later.

Later code may replace that implementation. **The older PR is not inaccurate**: it truthfully documents what changed *then*. Do not routinely edit or duplicate old PR descriptions to make them portray today's implementation.

This is why I do not apply a simplistic "do not repeat yourself" rule across issues, PRs and code. History is not another copy of the current specification.

## Put local reasoning beside the decision

Source code should contain the implementation. Its names, types and structure should carry as much meaning as possible; tests should express the behaviour that needs to stay true.

Comments are for information the implementation cannot easily convey:

- A surprising invariant, ordering requirement or ownership constraint.
- A security boundary or deliberately restricted fallback.
- A workaround required by an external API or platform.
- Why a seemingly simpler approach is unsafe.
- An intentional limitation that might otherwise be "fixed" incorrectly.

A short comment near the actual constraint is often better than a distant design document. Where an issue or PR has the full rationale, reference it rather than pasting the entire discussion into a comment.

For example, a comment explaining **why** cancellation must happen before a provider is destroyed is useful. A Markdown page reciting every branch of the provider's cancellation function usually is not.

The goal is to keep important decisions discoverable at the point where a future developer is most likely to change them.

## When repository documentation earns its place

A maintained document is justified when its intended audience needs an explanation beyond reading one implementation:

- Installation, configuration and normal user workflows.
- Public APIs, plugin contracts and integration guides.
- Cross-component architecture or operational procedures.
- Security and compatibility constraints spanning several areas.
- Decisions that remain important but have no sensible single source location.

For a plugin interface, a concise contract explaining what a third-party implementer may rely on can be valuable. It should describe the supported boundary and examples, not reproduce the private implementation.

A separate document is less useful when it lists current classes, filenames, constants, default settings or control flow that are already easy to read from code and tests. Those details are likely to change, and the document then becomes a competing source of truth.

The [suggested coding standards](/blog/post/2026/055-suggested-coding-standards-for-repositories-and-agents/) provide the broader principle: adopt only conventions that protect an actual contract. Documentation deserves the same scrutiny.

## The trap of implementation-series documents

One real example is a multi-PR KLookup feature series. The agents created a `docs/implementation-series.md` file recording branches, merge order, test totals, progress and handoff state.

That information matters *during the work*. But branches, checks and merge order change as the work proceeds. Committing the snapshot into the feature stack means each child branch can inherit it, edit it and conflict over it, even though the document will have little value after integration.

Instead:

- Keep issue scope and decisions in the issues.
- Keep each PR's explanation, test evidence and immediate dependencies in its description or discussion.
- Let GitHub show which PRs are open, merged or blocked.
- Keep temporary coordination in the active agent session rather than creating a tracked repository artifact.

There is a legitimate exception. A complex operation may be genuinely blocked and require durable recovery state that cannot practically live in an issue or PR. In that case, record *only* what another worker needs to recover: the blocker, evidence, exact current state, next action and a condition for removing that record.

Do not turn an ordinary merge queue or agent progress report into permanent project documentation.

## How I want agents to apply this

Before adding a documentation file, ask **what would a future user or maintainer lose if this file did not exist?** Then ask whether that information belongs in the issue, PR, tests or a nearby code comment instead.

When documenting a change:

1. Write a meaningful issue and PR narrative; some overlap with code is expected and useful.
2. Express current behaviour in code and executable tests.
3. Keep non-obvious local reasoning close to the relevant implementation.
4. Add maintained documentation only when it serves a genuine current-system audience or contract.
5. Avoid agent diaries, duplicate internal specifications and long-lived implementation-status manifests.
6. Remove obsolete documents when their purpose has ended, but do not indiscriminately delete user guides or public interface contracts.

For an existing stack, make **the smallest safe correction**. Remove an unnecessary document in the PR that introduced it, prevent dependent PRs from reintroducing it, and adjust directly affected references when needed. Do not rewrite every PR, issue, article or source file merely to "apply the policy."

**Keep the code as the source of truth, preserve the history in issues and PRs, and write maintained documentation only when it has a distinct job.**
