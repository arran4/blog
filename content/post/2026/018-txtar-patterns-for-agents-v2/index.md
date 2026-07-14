---
title: "Txtar Test Systems in Practice: Iterating to Scale (v2)"
date: 2026-07-10T19:12:28+10:00
draft: false
tags: ["go", "testing", "txtar", "embed", "golden-files", "agents"]
categories: ["reference", "testing"]
---

I use `txtar` as a practical test and fixture format across multiple repositories.
This post is my updated reference for how I expect agents (and future me) to structure
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

Since then, the approach has evolved, specifically when dealing with larger test suites and complex context mocking (like validating `fstab` entries against a mock `/proc/filesystems`). This post covers the iteration of these patterns to scale better, as demonstrated by recent pull requests.

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
Ensures nearest config wins over parent defaults.

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
Ensures nearest config wins over parent defaults.
-- test-options.json --
{"run_checks": ["indentation"]}

-- input.json --
{"data": true}

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

## The Problem: The Monolithic Txtar

Initially, it's tempting to throw all cases into a single `fs.txtar` file:

```txt
-- proc_filesystems --
nodev	sysfs
	ext4
-- valid_fstab --
/dev/sda1 / ext4 defaults 0 1
-- invalid_fstab --
/dev/sda2 / zfs defaults 0 1
```

This works for a while, but as the number of rules and edge cases grows, this monolithic file becomes unreadable. A failure in one scenario requires hunting through a massive file.

## Iteration 1: Granular Files and `fs.WalkDir`

The most significant structural improvement is moving from a single `testdata/fs.txtar` to a directory of scenario-specific archives (`testdata/*.txtar`).

```text
testdata/
  fs_valid.txtar
  fs_invalid.txtar
  swap_valid.txtar
  swap_invalid.txtar
```

Instead of hardcoding a single file read, the test harness walks the directory, creating a distinct `t.Run` subtest for each `.txtar` file:

```go
//go:embed testdata/*.txtar
var testdataFS embed.FS

func TestRules(t *testing.T) {
    var cases []string
    err := fs.WalkDir(testdataFS, "testdata", func(p string, d fs.DirEntry, err error) error {
        if err != nil { return err }
        if d.IsDir() || !strings.HasSuffix(p, ".txtar") { return nil }
        cases = append(cases, p)
        return nil
    })
    if err != nil {
        t.Fatalf("failed to walk testdata: %v", err)
    }
    sort.Strings(cases)

    for _, tc := range cases {
        raw, err := testdataFS.ReadFile(tc)
        if err != nil {
            t.Fatalf("failed to read testcase %s: %v", tc, err)
        }
        ar := txtar.Parse(raw)
        inputFS, expectedFS := SplitInputExpected(ar)
        // ... run assertions ...
    }
}
```

This isolates failures to specific case files and makes it trivial for agents or humans to add new test cases without touching existing ones.

Important implementation detail: shadow loop variables (`tc := tc`) if running inside `t.Run` concurrently so closures don’t capture the wrong value.

## Iteration 2: Sane Defaults and Fallbacks

In systems that rely on external context (like reading system configuration files), requiring every `.txtar` file to redefine the exact same mock data creates massive boilerplate.

If 90% of our tests use the same `/proc/filesystems` mock, we shouldn't force the fixture to include it. Instead, the test harness should supply a fallback if the fixture omits it:

```go
// Pre-fill cache (mocking the OS interaction)
c := rules.NewCache()
procData, err := fs.ReadFile(inputFS, "proc/filesystems")
if err != nil {
    // Fallback to a sane default if the test doesn't override it
    procData = []byte("nodev\tsysfs\nnodev\ttmpfs\nnodev\tproc\n\text3\n\text4\n\tsquashfs\n\tvfat\n")
}
```

Now, a standard valid case can be incredibly concise:

```txt
test: valid swap partition entry
Ensures that correctly formatted swap fstab entries pass validation.

-- input/etc/fstab --
UUID=ccd57c54-3caf-47ba none swap defaults 0 0
```

## Iteration 3: Descriptive Assertions and Implicit Success

When adopting the `expected/` tree structure, avoid generic names like `expected/output.txt`. If your tool outputs validation errors, name the expectation `expected/validationerrors.txt`. This makes the intent of the golden file immediately clear without opening it.

Furthermore, we can leverage implicit success assertions. If `expected/validationerrors.txt` is missing from the `.txtar` archive, the test harness should assume *zero* validation errors were expected:

```go
wantOutputBytes, err := fs.ReadFile(expectedFS, "validationerrors.txt")
if err != nil {
    if errors.Is(err, fs.ErrNotExist) {
        // No expected output provided, meaning it should be valid
        if len(allSuggestions) > 0 {
            t.Fatalf("expected valid entry to have no suggestions, got %v for file %s", allSuggestions, tc)
        }
    } else {
        t.Fatalf("unexpected error reading expected output: %v", err)
    }
} else {
    // Expected output provided, assert against it
    // ...
}
```

This drastically reduces the footprint of "happy path" tests, keeping fixtures focused strictly on the unique behavior they are verifying.

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
