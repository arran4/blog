---
title: "Choosing Go Filesystem Test Fixtures: embed, MapFS, and txtar"
date: 2026-09-17T12:08:00+10:00
draft: false
tags:
  - go
  - testing
  - txtar
  - embed
  - fs
  - fstest
  - golden-files
categories:
  - Testing
  - Software Development
---

<!-- cspell:words autocrlf proc validationerrors writable -->

I already have broader references for [txtar fixture systems](/blog/post/2026/004-Txtar-Patterns-for-Agents/), [scaling txtar suites](/blog/post/2026/018-txtar-patterns-for-agents-v2/), and [testing filesystem-heavy Go code](/blog/post/2026/033-testing-fs-with-mapfs-mockfs/). The missing piece is a smaller decision guide: **when should a test use a plain embedded file, `fstest.MapFS`, or a txtar scenario?**

The answer is mostly proportionality. Use the least elaborate representation that still makes the case readable, deterministic, and easy to extend.

## A practical selection ladder

A useful default is:

| Test shape | First choice |
| --- | --- |
| One small input/output pair | literal data or `go:embed` |
| Directory structure matters more than file payloads | `fstest.MapFS` |
| Several related files form one readable case | `txtar` |
| Many txtar cases repeat the same environment | txtar plus a shared fallback/layer |
| Product code needs writes | a narrow writable filesystem interface or a writable test implementation |
| Scenario represents application behaviour rather than only filesystem state | the application-level scenario approach |

These are defaults, not type-system rules. The important point is to avoid making every two-file test carry a scenario framework while also avoiding ad-hoc mocks once a case has clearly become a small filesystem.

## `go:embed` is enough for genuinely small pairs

If a test has one input and one expected output, plain embedded files are easy to understand:

```go
//go:embed testdata/simple_input.txt
var simpleInput []byte

//go:embed testdata/simple_expected.txt
var simpleExpected []byte
```

There is little value in converting this into a multi-file archive unless the case is likely to gain more context. Keeping the fixture representation proportional makes the test easier to review.

This also applies to small source/golden pairs where the filenames themselves carry useful meaning.

## `fstest.MapFS` is excellent when shape matters

For tests about discovery, path matching, package layout, walking, or presence/absence, the contents may be nearly irrelevant. `fstest.MapFS` can express a fairly rich tree directly:

```go
mockFS := fstest.MapFS{
    "app-misc/tool/tool-1.2.0.ebuild":    {},
    "app-misc/tool/tool-1.2.0-r1.ebuild": {},
    "app-misc/tool/metadata.xml":         {},
}
```

That is often clearer than a txtar archive full of empty file bodies.

The broader rule is: **do not choose txtar merely because the code accepts `fs.FS`.** Choose txtar when the archive improves the human representation of the case.

## Use txtar when the files form one scenario

Txtar becomes valuable when multiple files are meaningfully related: source plus configuration, input plus expected output, request plus response, templates plus rendered files, or a small virtual project tree.

For those cases I prefer to parse once, expose the archive as an `fs.FS`, and let the product code consume the same filesystem abstraction it would use elsewhere.

A common convention is:

```txt
Case: nested configuration overrides the parent.

-- input/project/.config --
mode = parent
-- input/project/sub/.config --
mode = child
-- input/project/sub/file.txt --
contents
-- expected/result.txt --
child
```

The archive comment before the first file marker is useful human-facing documentation. For full application scenarios, the more extensive guidance in [Scenarios as Executable Application State](/blog/post/2026/046-scenarios-as-executable-application-state/) applies; not every txtar fixture needs to become an application scenario.

## Prefer standard txtar until the fork buys something real

`golang.org/x/tools/txtar` should normally be the first choice.

My `github.com/arran4/txtar` fork is useful when a project genuinely benefits from extra programmatic or writable archive/filesystem behaviour. Do not introduce it merely because it exists. Keeping the standard library-adjacent dependency is simpler when parsing and reading are all the test requires.

This is the same proportionality rule as choosing between `MapFS` and txtar: use the extra abstraction when it removes real complexity rather than because it might be useful later.

## Turn txtar into an ordinary filesystem boundary

A small adapter can convert archive files into `fstest.MapFS`:

```go
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

Once the archive is an `fs.FS`, ordinary Go filesystem tools become available. In particular, `fs.Sub` is a clean way to isolate namespaces such as `input/` and `expected/`:

```go
base := ArchiveToMapFS(ar)

input, err := fs.Sub(base, "input")
if err != nil {
    return err
}
expected, err := fs.Sub(base, "expected")
if err != nil {
    return err
}
```

This is often preferable to teaching the production code about txtar filenames. The fixture format stays at the test boundary while the system under test receives an ordinary filesystem.

## Inject the filesystem, not the fixture format

Product code should generally depend on the filesystem capability it needs, not on txtar itself.

For read-only code, `fs.FS` may be enough. For writes or richer operations, use a narrow interface representing the actual operations. Tests can then supply an in-memory implementation while production uses an OS-backed implementation.

The useful dependency direction is:

```text
txtar / MapFS / embedded files
        |
        v
      fs.FS or narrow filesystem interface
        |
        v
      product code
```

That keeps test representation replaceable. A test can move from `MapFS` to txtar as it grows without forcing a product API change.

## Layer common context instead of copying it into every case

Large suites often have a baseline environment that almost every case shares: standard configuration, default headers, a mock `/proc/filesystems`, common templates, or other stable data.

Repeating that material inside every txtar makes the cases harder to read. Prefer a deliberate fallback/layering rule:

```go
type layeredFS struct {
    primary  fs.FS
    fallback fs.FS
}

func (l layeredFS) Open(name string) (fs.File, error) {
    f, err := l.primary.Open(name)
    if err == nil {
        return f, nil
    }
    if errors.Is(err, fs.ErrNotExist) {
        return l.fallback.Open(name)
    }
    return nil, err
}
```

The case-specific filesystem wins; the shared baseline supplies only files the case does not override.

Keep this precedence explicit. A fallback filesystem should reduce fixture repetition, not create mysterious last-one-wins behaviour.

## Expectations should say what they mean

A generic `expected/output.txt` works, but more descriptive names make failures and fixtures easier to understand. If the product emits validation errors, `expected/validationerrors.txt` says more than `expected/output.txt`.

For some domains, absence can itself be a useful expectation convention. For example, omitting `expected/validationerrors.txt` can mean “expect no validation errors.” This keeps successful cases compact while still making failure cases explicit.

Use such conventions only when they are documented and unambiguous. Missing fixture data should not accidentally turn a broken expectation into a passing test.

## Use established comparison tools for non-trivial output

Small byte-for-byte checks are fine. Once expected output becomes multi-line or structural, good diffs matter because the failure output becomes part of the developer experience.

Prefer an established comparison library such as `github.com/google/go-cmp/cmp` or an existing project diff helper over repeatedly writing weak ad-hoc diff code. The exact library matters less than producing a failure that makes the difference obvious.

For virtual filesystem outputs, compare the deterministic path set first and then compare the contents of corresponding files. This produces much better diagnostics than flattening an entire tree into one opaque string.

## Be deliberate about line endings

Golden and fixture tests can fail for reasons unrelated to product behaviour when one environment produces LF and another checks out or generates CRLF.

When line endings are **not semantically meaningful**, normalise both sides at the comparison boundary:

```go
func normalizeNewlines(data []byte) []byte {
    return bytes.ReplaceAll(data, []byte("\r\n"), []byte("\n"))
}
```

Do not normalise blindly when the program is specifically meant to preserve or transform line endings; in that case the distinction belongs in the expected behaviour and should be asserted explicitly.

Also remember that Git checkout settings such as `core.autocrlf` can change testdata before the test process sees it. Hermetic embedded fixtures reduce working-directory problems, but they do not remove the need to decide whether CRLF versus LF is part of the contract.

## Keep fixture discovery deterministic

Once there are many cases, use `go:embed` plus `fs.WalkDir` or `fs.Glob`, sort discovered paths when ordering can vary, and give each case its own `t.Run` subtest.

That guidance is already covered in detail in the existing txtar posts, but it is worth retaining as the scaling boundary: once a test has become a corpus, **case-local failures and deterministic discovery are more important than clever fixture compactness**.

### `go:embed` does not make `**` recursive

A subtle trap in fixture examples is writing a shell-style recursive pattern such as:

```go
//go:embed testdata/templates/**/*.txtar
var fixtures embed.FS
```

`go:embed` patterns follow Go `path.Match`-style semantics; `**` is not a special recursive wildcard. For a nested fixture tree, embed the directory and walk/filter it explicitly:

```go
//go:embed testdata/templates
var fixtures embed.FS

err := fs.WalkDir(fixtures, "testdata/templates", func(name string, entry fs.DirEntry, err error) error {
    // select the .txtar files needed by the test
    return err
})
```

This also keeps recursive discovery behaviour explicit and testable.

### Clean and validate projected archive paths

When code manually strips prefixes such as `input/` or `expected/` and creates `fstest.MapFS` keys, do not insert the raw remainder blindly. Clean it and reject empty/root or otherwise invalid paths:

```go
name := path.Clean(strings.TrimPrefix(f.Name, "input/"))
if name == "." || !fs.ValidPath(name) {
    return fmt.Errorf("invalid fixture path %q", f.Name)
}
input[name] = &fstest.MapFile{Data: append([]byte(nil), f.Data...)}
```

This avoids malformed keys such as a bare namespace root and makes manual projection consistent with the filesystem contract. Using `fs.Sub` where possible avoids duplicating much of this namespace handling in the first place.

## A compact decision rule for agents

When adding filesystem-oriented tests:

1. Start with the simplest readable representation.
2. Use `go:embed` or literals for tiny pairs.
3. Use `fstest.MapFS` when path structure is the main fixture.
4. Move to txtar when several related files make one human-readable case.
5. Convert txtar to an ordinary filesystem at the test boundary; use `fs.Sub` for meaningful subtrees.
6. Inject `fs.FS` or a narrow writable interface into product code rather than exposing txtar to the domain layer.
7. Share stable defaults through explicit fallback layering rather than duplicating them in every case.
8. Make expectations descriptive, deterministic, and easy to diff.
9. Normalise line endings only when line-ending differences are intentionally outside the behaviour being tested.
10. Prefer the standard txtar package unless a concrete need justifies a richer implementation.
11. For nested embedded fixture trees, embed the directory rather than relying on `**` recursion.
12. Clean and validate archive-derived paths before projecting them into a virtual filesystem.

The fixture representation should be able to grow with the test without becoming the architecture of the product itself.
