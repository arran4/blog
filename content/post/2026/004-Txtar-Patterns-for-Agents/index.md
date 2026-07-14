---
title: "Txtar Test Systems in Practice: Data, Scenarios, and Embedded Walkers"
date: 2026-02-18T19:00:01+11:00
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

For advanced use cases requiring programmatic modification of archives or a writable `fs.FS` interface, you can use the fork [`github.com/arran4/txtar`](https://github.com/arran4/txtar). However, it should only be used when it provides a clear benefit over the standard [`golang.org/x/tools/txtar`](https://pkg.go.dev/golang.org/x/tools/txtar) tooling and library.

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

## Deprojected snippets: txtar to `fs.FS` and deterministic walking

This is the bit I want agents to internalise: parse once, convert to an in-memory
`fs.FS`, then run your product code against that virtual tree.

### Minimal conversion: `txtar` archive to `fstest.MapFS`

```go
package fixturefs

import (
    "path"
    "strings"
    "testing/fstest"

    "golang.org/x/tools/txtar"
)

func ArchiveToMapFS(ar *txtar.Archive) fstest.MapFS {
    out := fstest.MapFS{}
    for _, f := range ar.Files {
        name := path.Clean(strings.TrimPrefix(f.Name, "/"))
        if name == "." {
            continue
        }
        out[name] = &fstest.MapFile{Data: append([]byte(nil), f.Data...)}
    }
    return out
}
```

This lets you remove runtime disk I/O from the test itself while still exercising
code that accepts an `fs.FS`.

### Convention helper: split one txtar into input/expected filesystems

If your archive stores source files under `input/` and expected files under
`expected/`, split them into two independent trees:

```go
func SplitInputExpected(ar *txtar.Archive) (input, expected fstest.MapFS) {
    input = fstest.MapFS{}
    expected = fstest.MapFS{}

    for _, f := range ar.Files {
        switch {
        case strings.HasPrefix(f.Name, "input/"):
            input[strings.TrimPrefix(f.Name, "input/")] = &fstest.MapFile{Data: f.Data}
        case strings.HasPrefix(f.Name, "expected/"):
            expected[strings.TrimPrefix(f.Name, "expected/")] = &fstest.MapFile{Data: f.Data}
        }
    }
    return input, expected
}
```

That pattern is deliberately boring and explicit: easy for humans to read, easy
for agents to generate, easy to validate.

### Deterministic walker over virtual FS

Even with an in-memory filesystem, keep ordering explicit:

```go
func WalkFiles(root fs.FS, dir string) ([]string, error) {
    var files []string
    err := fs.WalkDir(root, dir, func(p string, d fs.DirEntry, err error) error {
        if err != nil {
            return err
        }
        if d.IsDir() {
            return nil
        }
        files = append(files, p)
        return nil
    })
    sort.Strings(files)
    return files, err
}
```

That gives stable case execution and stable diffs.

### End-to-end sketch: parse fixture, construct FS, run assertions

```go
func TestTransform(t *testing.T) {
    raw, _ := fixtures.ReadFile("testdata/cases/basic.txtar")
    ar := txtar.Parse(raw)
    inputFS, expectedFS := SplitInputExpected(ar)

    gotFS, err := transform.Run(inputFS)
    if err != nil {
        t.Fatalf("run transform: %v", err)
    }

    wantFiles, err := WalkFiles(expectedFS, ".")
    if err != nil {
        t.Fatalf("walk expected: %v", err)
    }
    for _, name := range wantFiles {
        want, _ := fs.ReadFile(expectedFS, name)
        got, _ := fs.ReadFile(gotFS, name)
        if string(got) != string(want) {
            t.Fatalf("file %s mismatch\nwant:\n%s\n\ngot:\n%s", name, want, got)
        }
    }
}
```

## Multi-template directory loop (goa4web-style pattern)

For template corpora (for example email templates where each body type has its
own txtar), I want one subtest per template archive discovered by walking a
directory.

```go
//go:embed testdata/templates/**/*.txtar
var templateCases embed.FS

func TestTemplateMatrix(t *testing.T) {
    var cases []string
    err := fs.WalkDir(templateCases, "testdata/templates", func(p string, d fs.DirEntry, err error) error {
        if err != nil {
            return err
        }
        if d.IsDir() || !strings.HasSuffix(p, ".txtar") {
            return nil
        }
        cases = append(cases, p)
        return nil
    })
    if err != nil {
        t.Fatalf("walk template cases: %v", err)
    }
    sort.Strings(cases)

    for _, tc := range cases {
        tc := tc
        t.Run(strings.TrimSuffix(path.Base(tc), ".txtar"), func(t *testing.T) {
            raw, err := templateCases.ReadFile(tc)
            if err != nil {
                t.Fatalf("read %s: %v", tc, err)
            }
            ar := txtar.Parse(raw)
            inputFS, expectedFS := SplitInputExpected(ar)

            gotFS, err := renderTemplates(inputFS)
            if err != nil {
                t.Fatalf("render %s: %v", tc, err)
            }
            assertTreeEqual(t, expectedFS, gotFS)
        })
    }
}
```

This pattern scales from a handful of templates to hundreds while still making
failures obvious and localised.

## Why this helps agents and embedded script runners

Packing all case inputs/expectations into txtar + in-memory `fs.FS` gives two
big practical wins:

- **Single source of case truth**: readers only inspect one fixture blob.
- **Host-independent execution**: fewer path/permission surprises in CI, local,
  and agent sandboxes.

The same structure also ports well to Go-based embedded scripting engines:

- pass a virtual filesystem adapter into the script runtime
- let scripts read `input/...` and write `output/...` in-memory
- compare `output/...` against `expected/...` without touching host disk

So tests, generators, and scripted transforms can all share one fixture model.

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
