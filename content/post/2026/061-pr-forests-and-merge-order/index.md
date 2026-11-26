---
title: "PR Forests: Issue Ownership, Dependency Branches and Merge Order"
date: 2026-11-26T12:44:00+11:00
draft: false
guidance: ["agent-management"]
tags: ["agents", "git", "github", "pull-requests", "workflow", "architecture", "testing"]
categories: ["Software Development", "LLM Instructions", "Automation"]
---

<!-- cspell:words DAG retarget retargeted retargeting worktree worktrees workstream workstreams -->

When I have a substantial repository change to make, I want to review and merge useful pieces independently, without resolving the same conflict several times. I also want coding agents to make progress without waiting for me to merge every prerequisite.

I call this arrangement a **PR forest**. It is a practical application of the dependency tree in my [unified AI-assisted repository development process](/blog/post/2026/059-ai-assisted-repository-process/), not another competing process.

A forest may contain independent roots, stacked branches and an integration branch that depends on several siblings. Strictly speaking, this can be a directed acyclic graph (DAG), not just a collection of trees.

## Issues describe requirements; PRs deliver changes

My general guideline is:

- Each issue has one accountable resolving PR.
- Each PR resolves one or more issues.
- Prefer larger, coherent PRs with little overlap over an artificially fine-grained collection of PRs.

These are guidelines, not hard rules. An issue may require preparatory changes in other PRs. Those PRs can reference it without claiming to resolve it. Assign the eventual closing PR according to where the full acceptance criteria can be verified.

The goal prompt describes the campaign: architecture, boundaries, desired outcome, safety constraints and verification strategy. Issues contain more specific requirements, acceptance criteria and implementation boundaries. Duplicate significant requirements between them as far as practical, with more detail in the issue.

This duplication is intentional. A coding agent should understand what it owns by reading an issue; a coordinating agent should understand how the pieces fit together by reading the goal prompt. Reconcile changed requirements in both places.

## Choosing branches

Start by identifying the providers other changes need. A shared database interface, request runtime or test harness might warrant its own PR. Several related page handlers may belong in one substantial module PR rather than four nearly identical changes.

For example:

```text
main
├── #101 independent build
│   └── #102 shared platform
│       ├── #103 application runtime
│       │   ├── #105 module A
│       │   └── #106 module B
│       └── #104 migration tools
└── #100 backup tooling

#107 integration: based on #103, incorporates #104–#106
#108 deployment: based on #107
```

The PR numbers are illustrative, not references to a real repository.

Branch from the provider when a consumer needs its unmerged changes to build or test. Branch from the default branch when work is genuinely independent. Use separate worktrees so concurrent work does not overwrite another branch's changes. Give shared interfaces, build registration files, migration sequences and test helpers an accountable owner. Changes to a provider belong with that provider rather than being copied into every consumer.

Where appropriate, use component-specific build registration files to reduce contention on central build files. Do not introduce an extension mechanism solely to avoid a trivial conflict. The objective is coherent architecture and reduced overlap, not zero shared files at any cost.

## A merge order is a conditional plan

The graph describes dependencies; a merge table makes them actionable. I ask the management LLM to inspect the actual open PRs, their current base branches, commit IDs and mergeability, rather than relying on an old plan or a coding agent's completion report.

My preferred table has the PR link, its **current base**, purpose, and where to go if merging fails or conflicts. The current base is the actual base at the time of inspection, not the eventual target. Where a base is another PR's head branch, identify that PR. Unless an alternative integration target has been expressly agreed, every PR in the merge plan must ultimately merge directly into `main`. The current base column describes a dependency, not the destination to select when merging.

| Step | PR | Current base | Purpose | If failure or conflict, go to |
| ---: | --- | --- | --- | --- |
| 1 | #100 | main | Independent backup tooling | #101 |
| 2 | #101 | main | Self-contained build | Stop and reassess |
| 3 | #102 | #101 | Shared platform | Stop and reassess |
| 4 | #103 | #102 | Application runtime | #104, then reassess |
| 5 | #104 | #102 | Historical migration | #105, if #103 is merged |
| 6 | #105 | #103 | Module A | #106 |
| 7 | #106 | #103 | Module B | Stop and reassess |
| 8 | #107 | #103 | Integrated verification | Stop and reassess |
| 9 | #108 | #107 | Deployment | Stop and reassess |

Success means go to the next row. Failure means go to an independent, unblocked PR or stop and reassess. A skipped PR does not become optional just because another branch can progress. Return to it before merging a descendant or declaring the campaign complete.

The integration PR must wait for #104, #105 and #106 as well as its current base #103. GitHub's single base does not express every semantic dependency. A sibling with disjoint files may still depend on an agreed interface or data format. Inspect the requirements instead of assuming independence from file names.

Regenerate the table if the live state changes significantly. During merging I find a simple table more useful than a large diagram or a checklist without failure routing.

## Integrating the forest

When a forest has already been verified through ordinary merges of the exact provider commits, I prefer ordinary merge commits throughout that forest. Squashing or rebasing upstream changes can change their identities and make a downstream PR appear to contain work that has already landed.

### Merge into main by default, not into the provider

The order matters because review is work. If I review a platform PR and merge it into another feature branch rather than into `main`, the later PR that brings that feature branch into `main` can include the already-reviewed platform changes again. Repeated branch-to-branch merges can accumulate overlapping diffs, making me review the same implementation several times. A chain of dependencies can make that cost grow substantially.

The normal merge order is therefore a **to-main order**, not a list of instructions to merge each PR into its current base. A stacked base is useful during development and review, but is not permission to merge into that branch. The prerequisite must reach `main` first. The next PR must then target `main` and show its own remaining contribution.

For example, in the table above, merge #101 into `main`, then #102 into `main`, then #103 into `main`. Do not merge #102 into #101 or #103 into #102. This is what allows each review to remain focused on the change it owns.

GitHub automatically retargets open PRs in the same repository that depend on a merged PR's head branch when that head branch is deleted: their new base is the base of the merged PR. See [GitHub's documented merge and branch deletion behaviour](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request). The normal sequence is:

1. Review and merge the prerequisite into `main` using the agreed merge method.
2. Confirm its commits are present in `main`, then delete the merged source branch when it is safe to do so. GitHub may already have done this if automatic branch deletion is enabled.
3. Refresh the dependent PR and confirm GitHub has changed its base to `main`. If the branch must be retained or retargeting did not occur, change the base explicitly.
4. Review the remaining diff and merge the dependent PR into `main` only after its prerequisites are satisfied.

Closing a PR without merging it is not a substitute for this sequence. Nor is a green merge button proof of the correct target. If a PR still targets another feature branch, stop and reassess rather than clicking merge.

### Explicit exception: a deliberate integration or release branch

There are legitimate cases where I intend several changes to reach `main` as one unit: a major feature branch, a coordinated release or an incompatible transition that must not land incrementally. In that case, reviewing individual contributions against the integration branch and then reviewing the combined result can be worthwhile. Some repeated review is the price of checking the complete change at its actual publication boundary.

That is a different merge strategy and must be stated explicitly in the goal prompt, relevant issues, PR descriptions and merge-order table. Name the integration target, explain why incremental merges to `main` are inappropriate, and identify the final PR that brings the complete change into `main`. Do not infer this exception merely because PRs are stacked. In the absence of an expressly agreed exception, the merge plan must be a to-main order.

An integration branch may already contain normal merges of sibling PRs. Once those siblings are merged into the default branch, their exact heads should be ancestors of that branch. Retarget the integration PR and inspect its remaining diff. It should contain integration work, not a second copy of every module. If it does not, stop and investigate.

A successful branch-local test is evidence about that branch, not proof that the combined default branch is correct. Recheck the final merged checkout with the relevant local test matrix and integration or deployment scenarios. Distinguish actual failures from unavailable hosted CI capacity. Record excluded checks rather than claiming they passed.

## Retirement is another dependency gate

Sometimes a forest replaces an old repository or service. Copying its source into a replacement does not make the original disposable.

Add explicit retirement milestones to the merge plan:

| Milestone | Permitted action after verification |
| --- | --- |
| Replacement no longer depends on the original | Stop using the old repository as a build dependency; retain it |
| Required work and issue dispositions are integrated | Freeze further development in the old repository |
| Historical references, metadata, assets and durable backups are verified | Request approval to archive the old repository |
| Archive recovery is tested and remaining consumers are ruled out | Request separate approval for permanent deletion |

Archiving and deleting are different decisions. Neither is an automatic consequence of merging a PR. Consider the effects of pushing historical branches and tags, including workflows defined in old commits. Do not rewrite history merely to suppress those workflows. Record and restore temporary automation settings as part of an explicitly approved preservation operation.

## Instructions for a coordinating agent

When asked to plan or review a PR forest:

1. Inspect current issues, PR heads, actual bases, merge state and repository instructions.
2. Reconcile the goal prompt and issue acceptance criteria. Identify the accountable closing PR for each issue, allowing several issues per PR.
3. Propose cohesive branches with disjoint ownership where practical. Record provider branches and additional dependencies.
4. Reuse existing work rather than creating competing PRs. Confirm exact head commits and distinguish agent-reported tests from independently observed evidence.
5. Present a dependency-aware merge-order table with actual PR links, current bases, purpose and failure/conflict routing to another independent PR or a stop-and-reassess decision.
6. Default to a to-main merge order that avoids reviewing the same changes repeatedly. Identify current bases separately from final merge targets. After merging a provider into main, delete its merged branch when safe and verify dependent PRs were retargeted. Explicitly identify and justify any deliberate feature or release integration branch exception. Stop if the actual destination is wrong.
7. Keep skipped or blocked requirements visible. Include a final integrated verification gate and explicit retirement milestones where applicable.
8. Do not interpret a merge recommendation or successful test report as permission to merge, publish, archive or delete.

The aim is to maintain momentum without making the human reviewer reconstruct the dependency graph every time a PR is blocked. The unit of review should be a coherent change, and the unit of completion should be a verified requirement.
