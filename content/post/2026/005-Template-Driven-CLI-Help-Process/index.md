---
title: "From Patch to Playbook: A Repeatable Process for Refactoring CLI Help Text"
date: 2026-02-27T00:00:00+00:00
draft: false
tags: ["go", "cli", "templates", "process", "agents"]
categories: ["reference", "engineering-process"]
---

A recent patch series for `arran4/git-tag-inc` (PR #54) is a good example of how
to turn a one-off code change into a repeatable method other projects can use.

The technical change was simple:

- move long CLI help text out of Go code and into an embedded template,
- keep dynamic values in code,
- shift conditional rendering into the template,
- and avoid global flag-output side effects.

The process is what matters most, because it is reusable across repos and agent-assisted workflows.

## What changed in the patch (short version)

The patch evolved in three commits:

1. Replace many `fmt.Fprintf` calls in `Usage()` with an embedded `usage.txt`
   rendered by `text/template`.
2. Replace `flag.PrintDefaults()` output-capture hacks with manual
   `flag.VisitAll` formatting to avoid mutating global flag output.
3. Move mode-specific branching fully into the template (`{{if ...}}`) so
   presentation logic lives with presentation text.

That progression is exactly the pattern to replicate.

## Why this pattern is worth reusing

When help text lives inline in code, every wording update becomes risky and noisy.
Templates provide:

- **Review clarity**: prose changes are mostly text-file diffs.
- **Separation of concerns**: code prepares data; template renders docs.
- **Safer evolution**: feature flags/modes can be made explicit in template conditionals.
- **Agent-friendliness**: LLM agents can edit usage copy with lower risk of breaking control flow.

## A repeatable 7-step process for other projects

Use this as a playbook for any CLI project.

### 1) Start with a behavior snapshot

Before refactoring output code, record current behavior.

- Run `tool --help` in at least one default mode.
- Save output fixtures if the repo uses golden tests.
- Note any mode-dependent lines (legacy modes, experimental flags, etc.).

### 2) Extract static prose into a template file

Create something like:

- `cmd/<tool>/usage.txt` (or `.gotmpl`)

Keep placeholders only for truly dynamic values:

- executable name,
- generated flag listing,
- mode booleans,
- version/build metadata.

### 3) Embed template at compile time

In Go:

- `//go:embed usage.txt`
- parse once in `Usage()` or cache if needed.

This keeps distribution simple (no runtime file lookups).

### 4) Build a data struct with minimal fields

Pass a narrow struct to the template, for example:

- `ProgramName string`
- `Flags string`
- `IsLegacyMode bool`

Avoid passing full config objects. Small template contracts are easier to test and review.

### 5) Keep presentation branching in the template

If output differences are textual, put them in template conditionals:

- `{{if .IsLegacyMode}}...{{else}}...{{end}}`

This avoids scattering output branches through Go code.

### 6) Avoid global side effects while collecting flag text

If a codebase currently captures `flag.PrintDefaults()` by mutating shared output,
prefer deterministic manual formatting over global output swapping.

That makes tests and concurrent tooling safer.

### 7) Validate with focused regression checks

For CLI output changes, use a compact check matrix:

- `go test ./...`
- `<tool> --help`
- `<tool> --mode legacy --help` (or equivalent)

If possible, diff previous and new outputs for intentional-only changes.

## Suggested "definition of done" for this class of refactor

You can call the work complete when:

- help text is readable as documentation in a standalone template,
- mode-specific wording is obvious from template conditionals,
- flag output generation is deterministic and side-effect free,
- output parity is confirmed by tests and manual smoke checks,
- future copy edits no longer require touching control-flow-heavy code.

## Agent-ready prompt you can reuse

If you want LLM agents to apply this process in other repositories, use a prompt like:

> Refactor the CLI `Usage()` implementation to a compile-time embedded template.
> Keep dynamic values in a small data struct, move text conditionals into the template,
> avoid global side effects in flag formatting, and preserve current help output semantics.
> Provide tests or smoke checks showing parity.

That gives agents a crisp architectural target instead of just "clean this up".

## Closing thought

The interesting part of PR #54 was not only the template migration. It was the
iterative tightening of boundaries:

- first extract text,
- then remove side effects,
- then move final display logic to the rendering layer.

That sequence is a durable refactoring strategy you can apply to any CLI that has
outgrown `fmt.Fprintf`-driven usage blocks.
