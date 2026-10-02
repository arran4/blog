---
title: "Go Tests: Treat Process State, Time, and Standard I/O as Dependencies"
date: 2026-10-02T11:55:00+10:00
draft: false
tags:
  - go
  - testing
  - dependency-injection
  - concurrency
categories:
  - Testing
  - Software Development
---

<!-- cspell:words APIURL Chdir getenv httptest Setenv structs Unsetenv -->

Filesystem access is only one form of hidden test dependency. The same problem appears when a unit test temporarily replaces process-wide state:

```go
old := os.Stdout
os.Stdout = w
defer func() { os.Stdout = old }()
```

or:

```go
oldURL := APIURL
APIURL = server.URL
defer func() { APIURL = oldURL }()
```

or:

```go
oldTimeout := defaultTimeout
defaultTimeout = 10 * time.Millisecond
defer func() { defaultTimeout = oldTimeout }()
```

These tests can work, but they make otherwise local behaviour depend on global mutable state. They are harder to run in parallel, easier to leak across failures, and usually require more plumbing than the behaviour under test deserves.

My default is now: **stdin, stdout, stderr, arguments, environment-derived configuration, HTTP clients, clocks, and similar process state should be injected into application logic when practical. Keep direct process-global manipulation at the outer integration boundary.**

This is the same principle as [minimizing filesystem side effects in tests](/blog/post/2026/048-minimize-filesystem-side-effects-in-tests/): side effects are capabilities, and capabilities should have explicit boundaries.

## Standard input and output are ordinary readers and writers

Core command behaviour should normally accept `io.Reader` and `io.Writer` dependencies:

```go
type IO struct {
    In  io.Reader
    Out io.Writer
    Err io.Writer
}

func Run(args []string, streams IO) error {
    // command behaviour
    return nil
}
```

A unit test then becomes:

```go
func TestRun_FromStdin(t *testing.T) {
    in := strings.NewReader("input\n")
    var out bytes.Buffer
    var stderr bytes.Buffer

    err := Run([]string{"--input", "-"}, IO{
        In:  in,
        Out: &out,
        Err: &stderr,
    })
    if err != nil {
        t.Fatalf("Run() error = %v", err)
    }

    if got := out.String(); got != "expected\n" {
        t.Fatalf("stdout = %q, want %q", got, "expected\n")
    }
}
```

There is no pipe, goroutine, descriptor cleanup, or mutation of `os.Stdin` and `os.Stdout`.

The executable boundary can still wire the real process streams:

```go
err := Run(os.Args[1:], IO{
    In:  os.Stdin,
    Out: os.Stdout,
    Err: os.Stderr,
})
```

Keep one or a few integration tests around that adapter when the real process behaviour itself matters.

## Do not capture process stdout when a writer parameter will do

A common helper creates `os.Pipe()`, replaces `os.Stdout`, drains the pipe concurrently, restores the global, and closes several descriptors.

That is useful when testing an unavoidable process boundary. It is excessive when the function could simply write to an injected `io.Writer`.

A good test helper should remove unavoidable mechanics. It should not compensate indefinitely for a missing production boundary.

If many unit tests need a `captureStdout` helper, treat that as design feedback.

## Arguments belong at the executable boundary too

Temporarily replacing `os.Args` has the same problem:

```go
old := os.Args
os.Args = []string{"tool", "--flag"}
defer func() { os.Args = old }()
```

Prefer:

```go
func Execute(args []string, stdout, stderr io.Writer) int
```

Then `main` supplies `os.Args[1:]`.

Again, a small executable-level test may still exercise the actual global. Most behavioural tests should not need to.

## Environment variables: use `t.Setenv`, then inject parsed configuration where useful

When the code intentionally reads an environment variable, `t.Setenv` is better than manual `os.Setenv` / `os.Unsetenv` bookkeeping:

```go
func TestSourceDateEpoch(t *testing.T) {
    t.Setenv("SOURCE_DATE_EPOCH", "1234567890")
    // ...
}
```

It records cleanup with the test automatically and fails correctly if setup fails.

But `t.Setenv` does not turn process-global environment into a local dependency. A test using it still cannot safely call `t.Parallel()`.

If environment-derived values affect substantial business logic, parse them once at the boundary and pass configuration inward:

```go
type Config struct {
    SourceDateEpoch string
}

func ConfigFromEnv(getenv func(string) string) Config {
    return Config{SourceDateEpoch: getenv("SOURCE_DATE_EPOCH")}
}
```

Most tests can then construct `Config` directly. A smaller test verifies `ConfigFromEnv(os.Getenv)`.

## Package-level URLs and HTTP clients are test seams, but usually poor ones

This pattern is convenient:

```go
oldURL := APIURL
APIURL = server.URL
defer func() { APIURL = oldURL }()
```

It also serializes otherwise independent tests around a mutable package variable.

Prefer an explicit client:

```go
type Client struct {
    BaseURL string
    HTTP    *http.Client
}

func NewClient(baseURL string, httpClient *http.Client) *Client {
    if httpClient == nil {
        httpClient = http.DefaultClient
    }
    return &Client{BaseURL: baseURL, HTTP: httpClient}
}
```

A test can use:

```go
server := httptest.NewServer(handler)
t.Cleanup(server.Close)

client := NewClient(server.URL, server.Client())
```

The real application still gets production defaults, while tests no longer rewrite global URLs or client timeouts.

The same rule applies to `http.DefaultClient` and `http.DefaultTransport`: prefer an owned/injected client unless testing the process default is specifically the point.

## Time is another dependency

A test that sleeps to make a deadline, expiry, retry, or worker state change can become slow and timing-sensitive:

```go
time.Sleep(100 * time.Millisecond)
if !expired() {
    t.Fatal("expected expiry")
}
```

If the product behaviour is based on "what time is it?", inject the clock:

```go
type Clock interface {
    Now() time.Time
}

type realClock struct{}

func (realClock) Now() time.Time { return time.Now() }
```

Tests can then advance a fake or fixed clock deterministically.

If the test is about concurrency rather than wall-clock time, prefer synchronization over sleeping: channels, wait groups, barriers, callbacks, or observable state transitions.

A timeout around a synchronization wait is still useful as a failure guard. It should not be the mechanism that makes the expected state occur.

## Distinguish timeout integration tests from sleep-based coordination

There are legitimate tests where real elapsed time is part of the boundary. For example, an HTTP integration test may need to prove that a configured client deadline cancels a slow response.

Keep those tests focused and few.

The smell is a broad suite where sleeps are routinely used to "give the goroutine time" or to move application time forward. That usually indicates a missing synchronization or clock seam.

## Working directory is process state too

`os.Chdir` changes the working directory for the whole process. Tests using it are not parallel-safe.

Prefer explicit roots, `fs.FS`, or path arguments where the behaviour allows it. Keep `os.Chdir` for focused integration tests where current-working-directory semantics are genuinely part of the contract.

## A practical dependency boundary

A command-oriented application can gather its side effects into a small environment object:

```go
type Environment struct {
    In     io.Reader
    Out    io.Writer
    Err    io.Writer
    FS     fs.FS
    HTTP   *http.Client
    Now    func() time.Time
    Getenv func(string) string
}
```

This does not mean every project should create one giant dependency container. Often individual constructor parameters or small domain-specific structs are clearer.

The important property is visibility: a reviewer should be able to see which outside-world capabilities a component uses.

## Keep one integration boundary real

Dependency injection should not eliminate confidence that the executable is wired correctly.

A useful layering is:

1. pure/unit tests with explicit readers, writers, clocks, clients, and filesystems;
2. focused integration tests for real files, HTTP transport, process streams, environment parsing, or working-directory behaviour;
3. a small number of end-to-end tests that exercise the actual executable boundary.

The outer tests can be slower and mutate process state because that is what they exist to verify. The inner tests should not inherit those costs accidentally.

## Standard practice

For Go tests I maintain:

- inject `io.Reader`/`io.Writer` rather than replacing `os.Stdin`, `os.Stdout`, or `os.Stderr` in unit tests;
- pass argument slices inward rather than rewriting `os.Args`;
- use `t.Setenv` instead of manual set/unset cleanup when environment access itself is under test;
- parse environment configuration at the boundary and pass typed values inward for substantial logic;
- inject base URLs and owned HTTP clients rather than mutating package globals or default clients;
- inject clocks for expiry/deadline business logic;
- use synchronization rather than sleeps for concurrency coordination;
- avoid `os.Chdir` outside focused current-directory integration tests;
- preserve a deliberately small set of real process-boundary tests.

The question is the same one used for filesystem tests: **is this global side effect the behaviour being tested, or merely the easiest way the test currently knows how to reach the behaviour?**
