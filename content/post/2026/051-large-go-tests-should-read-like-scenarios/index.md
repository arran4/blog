---
title: "Large Go Tests Should Read Like Scenarios"
date: 2026-10-02T11:47:00+10:00
draft: false
tags:
  - go
  - testing
  - test-design
  - refactoring
categories:
  - Testing
  - Software Development
---

<!-- cspell:words reviewability testdata -->

A long test is not automatically a bad test. End-to-end and integration scenarios sometimes need substantial setup and several assertions.

The problem begins when the test body stops explaining the behaviour and becomes mostly mechanics: temporary files, archive writers, mock HTTP routing, hashes, cleanup, environment restoration, and repeated `if err != nil` blocks.

The standard I want is: **the top level of a test should read like a scenario even when the machinery underneath it is complicated.**

## Length is less important than cognitive surface area

Compare these two shapes.

A mechanically expanded test might read as:

```text
create temp directory
write config file
create zip writer
create archive entry
write bytes
close writer
create temp zip file
copy bytes
close file
calculate hash
start HTTP server
switch across six request paths
set three environment variables
run product
read output file
compare result
```

The actual behaviour can disappear inside that sequence.

A scenario-shaped test can expose the same work as:

```go
func TestGeneration_VerifiesReplacementArtifact(t *testing.T) {
    module := moduleFixture("example/root", "v1.0.0").
        Require("example/dependency", "v1.0.0").
        Replace("example/dependency", "example/fork", "v1.5.0")

    proxy := newModuleProxy(t, module)
    sums := checksumFixture(t, module)
    output := runGenerator(t, proxy, sums)

    assertUsesArtifact(t, output, "example/fork", "v1.5.0")
    assertPackageIdentity(t, output, "example/dependency", "v1.0.0")
}
```

The helpers may still contain careful ZIP, HTTP, hashing, and filesystem code. The scenario no longer has to.

## Extract mechanics when they acquire a domain name

Do not extract code solely because two blocks look similar. Extract it when the repeated mechanics represent the same concept.

Good examples include:

- `mustZip` or `moduleArchive`;
- `newModuleProxy`;
- `configFS`;
- `checksumFixture`;
- `renderTemplate`;
- `assertGeneratedFiles`;
- `mustReadFixture`.

These names reduce cognitive load because they describe *why* the setup exists.

A weak helper such as `setupEverything(t)` hides rather than explains.

## Keep Arrange, Act, and Assert visible

A test does not need ritual comments, but a reviewer should be able to find three things quickly:

1. what world is being arranged;
2. what operation is being exercised;
3. what behaviour is being asserted.

When a scenario is large, short comments can make those boundaries explicit:

```go
// Arrange a proxy where the replacement artifact differs from the original.
...

// Generate using the authoritative checksum set.
...

// The output identity stays original while fetched bytes come from the replacement.
...
```

Comments should explain intent and invariants, not narrate obvious syntax such as `// create a temp file` immediately above `os.CreateTemp`.

## Keep fixture creation out of assertions

A test is easier to debug when setup helpers create data and assertion helpers inspect outcomes.

Avoid a helper that both constructs the system and silently verifies several expectations. That creates invisible assertions and makes reuse dangerous.

Prefer:

```go
fixture := newFixture(t, spec)
got := runOperation(t, fixture)
assertResult(t, got, want)
```

Each helper has one role and failures tell the reviewer which phase failed.

## Use tables for variation, helpers for mechanics

If several tests differ only in inputs and expected behaviour, table-driven cases are a good fit:

```go
tests := []struct {
    name    string
    fixture fixtureSpec
    wantErr error
}{
    {name: "valid replacement", fixture: validReplacement()},
    {name: "missing checksum", fixture: missingChecksum(), wantErr: ErrChecksumMissing},
    {name: "mismatched archive", fixture: mismatchedArchive(), wantErr: ErrChecksumMismatch},
}
```

The fixture builder handles repeated archive/proxy/filesystem mechanics. The table records the behavioural distinction between cases.

Do not force unrelated scenarios into a giant table merely to reduce function count. Independent tests are often clearer when their stories differ substantially.

## Large fixture data should leave the test body

A scenario body is not the right place for:

- large JSON documents;
- binary archive bytes;
- multi-file source trees;
- hundreds of lines of expected generated output;
- many static HTTP responses.

Use embedded `testdata`, `fstest.MapFS`, txtar, golden files, or domain fixture builders according to what the test needs to communicate.

See [Readable Test Fixtures: Prefer Named Data Over Opaque Bytes](/blog/post/2026/050-readable-test-fixtures-prefer-named-data-over-opaque-bytes/) and [Minimize Filesystem Side Effects in Go Tests](/blog/post/2026/048-minimize-filesystem-side-effects-in-tests/).

## Small setup failures should not dominate the story

Repeated setup handling such as:

```go
_, err := writer.Write(data)
if err != nil {
    t.Fatal(err)
}
```

is usually better expressed through a small test helper when no extra diagnostic context is being added.

See [Go Test Setup: Use Small Must Helpers When Errors Add No Meaning](/blog/post/2026/049-go-test-setup-use-small-must-helpers-when-errors-add-no-meaning/).

## Preserve a small number of explicit integration tests

Refactoring a large test should not erase useful integration coverage.

If a behaviour genuinely depends on real file modes, symlinks, HTTP transport, subprocesses, or OS path semantics, keep focused tests that exercise those boundaries. Move only the incidental setup out of the scenario.

A healthy suite often has:

- many small pure/unit tests;
- fixture-driven tests over injected dependencies;
- a smaller set of explicit integration tests;
- a few end-to-end scenarios that prove the whole path.

## A practical refactoring sequence

When a test file has grown difficult to review:

1. Identify repeated mechanical setup blocks.
2. Give each repeated concept a domain-shaped helper.
3. Replace incidental disk access with injected `fs.FS` or narrow writable dependencies.
4. Move large static fixtures to `testdata`, `go:embed`, MapFS, or txtar.
5. Replace large mock-server switches with declarative response fixtures.
6. Collapse uninteresting setup error checks into `must` helpers.
7. Leave the top-level test functions describing behaviour and assertions.
8. Keep dedicated OS/network integration tests where those semantics are the point.

Do this incrementally. The goal is not a test framework rewrite; it is to make each extraction obviously semantics-preserving.

## Standard practice

For large Go tests:

- top-level test functions should read as behavioural scenarios;
- repeated mechanical setup should become small, named, reusable helpers;
- helpers should expose domain concepts and call `t.Helper()` when they can fail;
- large fixture data belongs outside the scenario body;
- comments explain intent and invariants rather than syntax;
- setup, execution, and assertion responsibilities stay separable;
- real integration boundaries remain covered deliberately;
- line count is not the target metric: readability, isolation, and reviewability are.

A large test is acceptable when its size comes from the behaviour being specified, not from plumbing that every reader must mentally execute.
