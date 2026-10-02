---
title: "Minimize Filesystem Side Effects in Go Tests"
date: 2026-10-02T11:42:00+10:00
draft: false
tags:
  - go
  - testing
  - filesystem
  - dependency-injection
  - fs
categories:
  - Testing
  - Software Development
---

<!-- cspell:words fstest testdata txtar -->

A test that creates directories, writes configuration files, closes temporary archives, reopens them, and removes them afterwards may still be hermetic, but it is doing more work than the behaviour under test usually requires.

My default for Go tests is now stronger: **unit tests should avoid the operating-system filesystem unless filesystem semantics are part of the behaviour being tested.**

This tightens the guidance in [Go FSs Everywhere](/blog/post/2026/007-Go-FSs-Everywhere/), [Memory FS for Testing](/blog/post/2026/008-Memory-FS-for-Testing/), [Testing `fs.FS` with MapFS and MockFS](/blog/post/2026/033-testing-fs-with-mapfs-mockfs/), and [Choosing Go Filesystem Test Fixtures](/blog/post/2026/047-choosing-go-filesystem-test-fixtures/).

## Filesystem interfaces can make a useful test boundary

When code naturally operates over a filesystem abstraction, `fs.FS` or another small standard interface can provide a useful boundary without introducing a project-specific filesystem framework:

```go
func LoadConfig(fsys fs.FS, name string) (Config, error) {
    data, err := fs.ReadFile(fsys, name)
    if err != nil {
        return Config{}, fmt.Errorf("read config %q: %w", name, err)
    }
    return ParseConfig(data)
}
```

The unit test can then use `fstest.MapFS`:

```go
func TestLoadConfig(t *testing.T) {
    fsys := fstest.MapFS{
        "config.toml": &fstest.MapFile{Data: []byte("mode = \"safe\"\n")},
    }

    got, err := LoadConfig(fsys, "config.toml")
    if err != nil {
        t.Fatal(err)
    }
    if got.Mode != "safe" {
        t.Fatalf("mode = %q, want safe", got.Mode)
    }
}
```

No temporary directory is required because the test is about parsing and lookup, not kernel filesystem behaviour.

## Prefer standard interfaces before custom filesystem frameworks

A project should not invent a large mock filesystem just because production code performs file operations.

Use the smallest useful abstraction, in roughly this order:

1. `fs.FS`, `fs.ReadFileFS`, `fs.ReadDirFS`, and related standard interfaces for reads.
2. `fstest.MapFS` for small in-memory trees.
3. `txtar` or embedded fixtures when several related files form one scenario.
4. A narrow writable interface when the product genuinely needs writes, renames, removals, or metadata changes.
5. A real OS-backed filesystem in the smaller integration layer that verifies OS-specific semantics.

A writable interface should describe what the application needs rather than attempt to reproduce all of `os`:

```go
type OutputFS interface {
    WriteFile(name string, data []byte, perm fs.FileMode) error
    Rename(oldName, newName string) error
    Remove(name string) error
}
```

This keeps the dependency small enough to fake without building another filesystem implementation.

## `t.TempDir()` is an integration tool, not the default fixture format

`t.TempDir()` is excellent when a test needs to prove behaviour involving:

- permissions and modes,
- symlinks,
- atomic rename semantics,
- executable bits,
- path behaviour that differs by operating system,
- subprocesses that require pathnames,
- compatibility with APIs that are intentionally path-based.

Those tests should exist. They should simply be recognisable as the integration layer rather than being the easiest way to create every fixture.

A useful smell is a unit test whose setup contains several of these before the product call appears:

```go
dir := t.TempDir()
os.WriteFile(...)
os.WriteFile(...)
os.CreateTemp(...)
filepath.Join(...)
```

When that happens, ask whether the product API is missing an injectable filesystem boundary.

## Do not write an archive to disk merely to read or hash it again

Archive tests often accidentally turn an in-memory value into a filesystem workflow:

```go
buf := new(bytes.Buffer)
zw := zip.NewWriter(buf)
// populate archive

f, err := os.CreateTemp("", "fixture-*.zip")
// write buf to f, close it, hash/read it, clean it up
```

If the operation under test accepts an `io.Reader`, `io.ReaderAt`, `[]byte`, or `fs.FS`, keep the archive in memory.

If a dependency only accepts a pathname, isolate that pathname requirement behind a small adapter where practical. Then most tests can exercise the logic without disk, while one integration test verifies the adapter.

## Separate pure transformation from side effects

A common reason tests need disk is that parsing, planning, and writing are fused together.

Prefer this shape:

```text
filesystem input
      |
      v
   parse/load
      |
      v
 pure model / plan
      |
      v
   render bytes
      |
      v
filesystem output
```

The middle stages can be tested without the OS. Only the input/output adapters need integration coverage.

This also makes error injection much easier. A fake filesystem can return `fs.ErrPermission` or `fs.ErrNotExist` directly instead of requiring permissions tricks on a temporary directory.

## Avoid global mutable seams when dependency injection will do

Changing a package global for a test is another form of hidden side effect:

```go
old := defaultPath
oldTimeout := defaultTimeout
defer func() {
    defaultPath = old
    defaultTimeout = oldTimeout
}()
```

Prefer an object or function parameter carrying those dependencies. Tests become independently runnable, parallel-safe, and easier to understand.

The same principle applies to HTTP clients, clocks, environment readers, and process execution.

## A migration rule that keeps changes low risk

Do not convert an entire package to a virtual filesystem in one rewrite.

A safer sequence is:

1. Identify one cluster of tests whose disk setup is incidental.
2. Extract the product's filesystem dependency behind the smallest interface that covers that cluster.
3. Keep the existing OS-backed implementation as the production default.
4. Convert those tests to `fstest.MapFS`, `txtar`, or a small writable fake.
5. Retain one focused integration test for the OS behaviour that matters.
6. Repeat only when another cluster benefits.

This keeps the refactor behavioural rather than architectural for its own sake.

## Standard practice

For Go code I maintain, the working standard is:

- unit tests use in-memory data and injected capabilities by default;
- when abstracting read-only filesystem access, standard `fs` interfaces are a useful starting point;
- custom writable interfaces stay narrow and application-shaped;
- `fstest.MapFS`, embedded data, and `txtar` are preferred over ad-hoc temporary directory setup when OS semantics are irrelevant;
- real filesystem tests are retained for permissions, symlinks, atomic operations, subprocess/path compatibility, and other genuine OS contracts;
- repeated test-side filesystem plumbing is treated as feedback about the production API, not merely as test boilerplate to tolerate.

The goal is not zero filesystem tests. The goal is to make every real filesystem access earn its place.
