---
title: "Using gap.md to Guide LLMs in Complex Projects"
date: 2026-08-06T09:57:57Z
draft: false
tags: ["LLM", "AI", "Prompting", "Workflow", "gap.md", "Project Management"]
categories: ["Artificial Intelligence"]
---

Working with Large Language Models (LLMs) on multi-module projects or complex codebases can sometimes feel like a high-wire act. You give the LLM a large set of instructions, and while it might accomplish the immediate tasks, you often find yourself wondering: *Did it actually have all the context it needed? Did it silently skip over something because a dependency wasn't ready?*

To prevent the LLM from trying to stubbornly forge ahead when it lacks prerequisites—or worse, hallucinating a solution—I've developed a prompting pattern that I use regularly. I ask the LLM to generate a `gap.md` file.

## The `gap.md` Strategy

When I'm unsure if the LLM has everything it needs to complete a complex objective, I instruct it to create a `gap.md` file *before* or *instead of* attempting to brute-force a solution. This turns the LLM from a simple executor into an active collaborator in project management.

Here is what I ask the LLM to include in the `gap.md` file:

### 1. Log All the Issues
The LLM must explicitly list any missing dependencies, lack of context, or blockers preventing it from completing the task. This acts as a clear inventory of what is holding up progress.

### 2. Expand with Examples and Context
Simply stating "missing database schema" isn't enough. I require the LLM to explain *why* it's an issue and provide examples. For instance, "I cannot implement the `getUser` function because the `users` table schema in the database module is currently undocumented. I need to know if the primary key is a UUID or an integer."

### 3. Propose Solutions with Examples
The LLM isn't just complaining; it's problem-solving. For each gap identified, it must come up with several potential solutions or workarounds, complete with code examples or architectural suggestions.

### 4. Provide Links to Open Issues or PRs
If the blocker is already a known issue, the LLM should link to any relevant open issues or Pull Requests. This helps consolidate the context and prevents duplicate work.

## Deferring Work and Ticketing

The real power of `gap.md` is that it allows me to explicitly tell the LLM: **Defer doing the work until these gaps are resolved.**

Instead of letting the LLM write broken code, I use the `gap.md` output to create actionable tasks. I ask the LLM to write out the necessary tickets directly into the Pull Request comment to link them properly.

Once those tickets are raised, the workflow shifts:
1. I monitor the tickets until they are all closed.
2. Once the dependencies are met, I return to the LLM.
3. I ask it to reassess the situation based on the closed tickets and proceed with the original task.

This process ensures that work is done in the correct sequence, preventing messy rollbacks or confusing git histories.

## Variations: `featurerequest.md` and `bugs.md`

The `gap.md` pattern is highly adaptable. Depending on the context of the conversation with the LLM, I sometimes ask for variations:

*   **`featurerequest.md`**: When an LLM suggests a good idea that is out of scope for the current sprint or PR, I ask it to draft a `featurerequest.md`. This captures the idea perfectly for the backlog without derailing the current task.
*   **`bugs.md`**: If the LLM notices a pre-existing issue in the codebase while working on something else, I ask it to log it in a `bugs.md` file. This is fantastic for incidental code reviews, ensuring we don't lose track of technical debt.

By formalizing the "I don't know" or "I can't do this yet" response into structured markdown files, you can significantly improve the reliability of LLMs in complex software engineering workflows. It transforms a potential point of failure into a well-documented project roadmap.
