---
title: "Go Test Setup: Use Small Must Helpers When Errors Add No Meaning"
date: 2026-10-02T11:55:00+10:00
draft: false
guidance: ["go-testing"]
tags:
  - go
  - testing
  - error-handling
  - test-helpers
categories:
  - Testing
  - Software Development
---

<!-- cspell:words testdata -->

Production error handling should add useful context. Test setup is different.

If a setup operation fails and the test can do nothing meaningful except stop, repeatedly writing this adds noise:

```go
n, err := f.Write(data)
if err != nil {
    t.Fatal(err)
}
_ = n
```

The error is not being classified, wrapped, or asserted. The test is simply saying: **this setup operation must succeed**.

For that case, I prefer a small `must` helper.

## A minimal generic helper

```go
func must[T any](t testing.TB, value T, err error) T {
    t.Helper()
    if err != nil {
        t.Fatal(err)
    }
    return value
}

func mustOK(t testing.TB, err error) {
    t.Helper()
    if err != nil {
        t.Fatal(err)
    }
}
```

Go's multiple-return argument expansion makes this convenient:

```go
f := must(t, os.CreateTemp(t.TempDir(), "fixture-*"))
_ = must(t, f.Write(data))
mustOK(t, f.Close())
```

The important part is not saving lines. It is moving mechanical failure handling out of the scenario so the test body exposes intent.

## Use `t.Helper()` every time

A helper that fails a test should call `t.Helper()` so the reported line points to the caller rather than the helper implementation.

That applies to `must`, fixture builders, comparison helpers, and setup functions:

```go
func mustZip(t testing.TB, files map[string][]byte) []byte {
    t.Helper()
    // build archive or fail the test
}
```

Without `t.Helper()`, abstraction makes failures harder to trace. With it, the helper removes noise without hiding location.

## Do not use `must` when the error is part of the behaviour

This is still useful:

```go
err := service.Save(input)
if !errors.Is(err, fs.ErrPermission) {
    t.Fatalf("Save() error = %v, want permission error", err)
}
```

The error is the assertion. Hiding it behind `must` would destroy the test.

Likewise, keep explicit setup handling when the extra message adds real diagnostic value:

```go
manifest, err := parseManifest(data)
if err != nil {
    t.Fatalf("parse embedded baseline manifest: %v", err)
}
```

The rule is narrower: use `must` when the only information being added is an `if err != nil` branch that immediately calls `t.Fatal(err)`.

## Prefer domain-shaped setup helpers over repeated mechanics

Once the same setup sequence appears several times, do not merely wrap each syscall independently. Extract the meaningful operation.

Instead of:

```go
buf := new(bytes.Buffer)
zw := zip.NewWriter(buf)
f := must(t, zw.Create("example/module@v1.0.0/go.mod"))
_ = must(t, f.Write(modData))
mustOK(t, zw.Close())
```

prefer:

```go
archive := mustModuleZip(t, "example/module", "v1.0.0", map[string][]byte{
    "go.mod": modData,
})
```

The helper name explains why the mechanics exist.

## Helpers should remove plumbing, not hide the test

Good test helpers usually fall into a few categories:

- construct a fixture;
- configure an injected dependency;
- start a deterministic fake service;
- read or compare a result;
- assert one reusable invariant.

A warning sign is a helper named `setupTest`, `doEverything`, or `runCase` that hides most of the scenario and requires reading its implementation to understand the test.

Prefer helpers that expose useful nouns and verbs:

```go
proxy := newModuleProxy(t, modules)
config := configFS(t, "one-project")
got := runGeneration(t, config, proxy)
assertPackage(t, got, "example/module", "v1.0.0")
```

A reviewer can understand that sequence without following every helper.

## Reuse should be low-risk

Test helper reuse is valuable when the helper has a narrow, stable contract.

For example, an archive builder can be safely reused across checksum, parser, HTTP, and extraction tests because its job is only to produce an archive. Changing the product behaviour does not require changing the helper.

By contrast, a helper that constructs a product object, executes it, rewrites globals, reads files, and verifies output is tightly coupled to a specific test path. Reusing it tends to spread assumptions.

The test suite should become drier where repetition is mechanical, not where duplication is carrying meaningful scenario differences.

## Standard practice

For test setup:

- use a small generic `must`/`mustOK` helper for uninteresting setup failures;
- call `t.Helper()` in every helper that can fail the test;
- keep product errors explicit when they are part of the assertion;
- extract repeated mechanical construction into domain-shaped fixture helpers;
- avoid helpers that perform the entire test invisibly;
- prefer reusable helpers whose contract is independent of the behaviour currently being tested.

The result should be fewer error-checking branches and more visible test intent.
