---
title: "Txtar Test Systems in Practice: Data, Scenarios, and Embedded Walkers"
date: 2026-02-16T00:00:00+00:00
draft: false
tags: ["go", "testing", "txtar", "embed", "golden-files", "agents"]
categories: ["reference", "testing"]
---

I use `txtar` as a practical test and fixture format across multiple repositories.
This post is my reference for how I expect agents (and future me) to structure
and evolve txtar-based systems.

Repositories discussed:

- `arran4/golang-rcs` (`testdata/txtar`)
- `arran4/golang-diff` (`pkg/diff/testdata`)
- `arran4/editorconfig-guesser` (`testdata`)
- Related pattern: `arran4/goa4web` templates (`core/templates`)

The core theme is that there is a **range of sophistication**:

1. Simple input/output data pairs
2. Case metadata + descriptions
3. Full scenario definitions with options and assertions

## Why txtar

`txtar` is great when you want fixtures that are:

- Human-readable in reviews
- Easy to compose from multiple files
- Stable enough for golden-style assertions
- Friendly to tooling and directory walking

In practice, this means tests can start tiny and grow naturally without changing
fixture format.

## Pattern 1: simple pairs (minimum viable structure)

At the low end, a txtar can just model pairs:

- one file for input
- one file for expected output

Example shape:

```txt
-- input.txt --
line 1
line 2
-- expected.txt --
line 1
line 2 (normalized)
```

This is ideal for parser normalization, text transforms, or diff behaviour where
you only need deterministic before/after checks.

### When to choose this

- Algorithm is pure and deterministic
- No runtime options are required
- You want quick fixture authoring speed

## Pattern 2: descriptive cases (metadata + intent)

The middle pattern keeps txtar file payloads but adds semantic context:

- `description.txt` or top-level comments for intent
- extra files for knobs (`options.json`, `flags.txt`, etc.)
- explicit failure/success expectation

Example:

```txt
test: trim trailing spaces in mixed indentation

-- input.txt --
a  
\tb\t 
-- options.json --
{"trim_trailing": true, "normalize_tabs": false}
-- expected.txt --
a
\tb
```

This is useful for repositories where fixture meaning matters as much as fixture
content, especially when agents generate or maintain these cases.

## Pattern 3: full scenario tests (options + assertions matrix)

At the high end, txtar becomes a scenario container:

- multi-file source tree inside one archive
- per-case options
- expected outputs and/or expected errors
- optional snapshots of diagnostics

Example:

```txt
test: recursive editorconfig inference with override

-- fs/src/main.go --
package main
-- fs/.editorconfig --
root = true
[*]
indent_style = space
-- fs/sub/.editorconfig --
[*.go]
indent_style = tab
-- request.json --
{"path":"fs/src/main.go"}
-- expected.json --
{"indent_style":"tab"}
```

This style maps well to systems like `editorconfig-guesser`, where behaviour is
contextual and directory-sensitive.

## The important Go harness pieces

The fixture format is only half the system. The harness design decides whether
the tests stay maintainable.

### 1) Use `go:embed` for fixture loading

I prefer embedding test fixtures into the test binary:

- avoids path bugs from different working directories
- avoids accidental I/O differences in CI vs local runs
- keeps tests hermetic and easier for tooling/agents

Typical structure:

```go
package mypkg_test

import (
    "embed"
    "io/fs"
    "path"
    "strings"
    "testing"

    "golang.org/x/tools/txtar"
)

//go:embed testdata/**/*.txtar
var testdataFS embed.FS

func TestCases(t *testing.T) {
    entries, err := fs.Glob(testdataFS, "testdata/**/*.txtar")
    if err != nil {
        t.Fatalf("glob fixtures: %v", err)
    }

    for _, fixture := range entries {
        fixture := fixture
        t.Run(strings.TrimSuffix(path.Base(fixture), ".txtar"), func(t *testing.T) {
            raw, err := testdataFS.ReadFile(fixture)
            if err != nil {
                t.Fatalf("read fixture %s: %v", fixture, err)
            }
            ar := txtar.Parse(raw)
            _ = ar // decode files and assert behaviour
        })
    }
}
```

### 2) Use `t.Run` inside directory walking loops

This is non-negotiable for large fixture sets:

- gives one subtest per fixture
- isolates failures to specific case names
- allows future `t.Parallel()` where safe
- makes generated or agent-authored fixture diffs easier to review

Important implementation detail: shadow loop variables (`fixture := fixture`) so
closures don’t capture the wrong value.

### 3) Keep directory walking explicit and deterministic

Use `fs.Glob` or `fs.WalkDir` with predictable ordering rules.

If ordering matters, sort inputs before execution. Reproducibility matters when
fixture counts grow.

## Bridging to template systems (`goa4web/core/templates`)

While `goa4web/core/templates` is template-driven rather than testdata-driven,
it shares the same operating pattern:

- walk directories
- load file bundles
- transform/render
- compare against expectations or desired outputs

The same harness discipline applies:

- stable directory traversal
- deterministic file naming
- explicit options per case
- clear failure messages tied to relative paths

So even outside strict tests, txtar thinking is still useful: package related
inputs as a single scenario unit, then run predictable transformations.

## Suggested canonical fixture contract for agents

When asking agents to add or update fixtures, I want this contract:

1. Each `.txtar` has a short case identifier and intent.
2. Required file names are documented (`input.*`, `expected.*`, optional
   `options.json`, optional `error.txt`).
3. Harness supports both success and expected-failure scenarios.
4. Fixture discovery is embed-based and path-stable.
5. Tests are `t.Run` subtests by relative fixture path.

This keeps changes scalable from simple pairs to full scenarios without changing
project fundamentals.

## Practical evolution strategy

A pattern that has worked well for me:

- Start new behaviour with Pattern 1 fixture pairs.
- If meaning becomes ambiguous, introduce Pattern 2 description/options files.
- If behaviour becomes contextual or tree-based, move to Pattern 3 scenarios.
- Keep old fixtures valid whenever possible to avoid churn.

That path gives fast feedback early and strong coverage later.

## Copy-paste starter layout

```text
testdata/
  txtar/
    normalize-whitespace.txtar
    parser-error-missing-header.txtar
    nested-resolution-basic.txtar
```

And inside a richer case:

```txt
test: nested resolution basic

-- description.txt --
Ensures nearest config wins over parent defaults.
-- options.json --
{"strict":true}
-- fs/project/.editorconfig --
root = true
[*]
indent_style = space
-- fs/project/pkg/.editorconfig --
[*.go]
indent_style = tab
-- fs/project/pkg/main.go --
package main
-- expected.json --
{"indent_style":"tab"}
```

## Final guidance for agent-authored changes

When I ask for txtar updates, optimize for:

- readability first
- deterministic harness behaviour
- easy case-level debugging with `t.Run`
- no runtime path fragility (`go:embed` preferred)

If there’s a trade-off, choose explicit structure over clever compactness.
That pays off when the fixture corpus gets large.
