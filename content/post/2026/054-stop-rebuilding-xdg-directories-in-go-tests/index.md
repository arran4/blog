---
title: "Stop Rebuilding XDG Directories in Go Unit Tests"
date: 2026-10-11T02:41:48.640Z
draft: false
guidance: ["go-testing"]
tags: ["go", "testing", "xdg", "dependency-injection", "filesystem", "environment"]
categories: ["Testing", "Software Development"]
---

<!-- cspell:words getenv XDG -->

A test that starts like this makes me ask whether we are testing application behaviour or rehearsing how a desktop session starts:

```go
t.Setenv("XDG_RUNTIME_DIR", runtimeDir)
t.Setenv("XDG_STATE_HOME", filepath.Join(tempDir, "state"))
t.Setenv("XDG_CACHE_HOME", filepath.Join(tempDir, "cache"))
t.Setenv("XDG_DOWNLOAD_DIR", filepath.Join(tempDir, "downloads"))
tokenPath := filepath.Join(tempDir, "torbox.token")
```

None of these lines is automatically wrong. `t.Setenv` is the correct Go tool when a test genuinely needs to change the environment. `filepath.Join` is harmless on its own, and `t.TempDir` is a good tool for real filesystem integration tests.

But five lines of **process and path setup before the action being tested** are a useful design smell. If a download planner needs a fake desktop session, several fake user directories and a token file merely to decide what to download, its dependencies may be hiding in the wrong place.

This is a focused continuation of [treating process state as a dependency](/blog/post/2026/053-go-tests-treat-process-state-time-and-standard-io-as-dependencies/) and [minimising filesystem side effects](/blog/post/2026/048-minimize-filesystem-side-effects-in-tests/), rather than a rule against environmental configuration or temporary files.

## Why I avoid this in ordinary tests

**The environment is shared process state.** Go's `t.Setenv` restores the previous value during cleanup, but does not make the mutation local to the test. It is incompatible with `t.Parallel` in the test or any parallel ancestor. A package-wide assumption that the current environment belongs to one test can also surprise unrelated components.

**Setup obscures the assertion.** A reviewer has to understand which synthetic directory influences which operation, whether the directory exists, and whether a token file has been written, before reaching the actual behaviour under test.

**It tests accidental wiring repeatedly.** Dozens of unit tests that call `os.Getenv` indirectly prove the same environment-reading path over and over. That path needs coverage, but it need not be the entry point for every test of the application.

**It encourages incidental disk I/O.** If the production API insists on pathnames, tests begin creating files even when a byte slice, `io.Reader`, `fs.FS`, or a narrow credential provider would express the case more directly.

**It can hide a false assumption about XDG.** The variables in the example are not all equivalent.

## XDG paths are different contracts

| Setting | Intended source and meaning | Testing consequence |
| --- | --- | --- |
| `XDG_STATE_HOME` | XDG Base Directory variable for persistent user state | Test default/override resolution at the adapter; pass the resulting state directory inward |
| `XDG_CACHE_HOME` | XDG Base Directory variable for disposable user caches | Inject the directory or cache capability for ordinary tests; verify real cache behaviour separately |
| `XDG_RUNTIME_DIR` | A session-scoped runtime directory with ownership, `0700` permissions, lifecycle and local-filesystem requirements | A random temporary folder does not prove runtime-directory compliance |
| `XDG_DOWNLOAD_DIR` | A name used in `xdg-user-dirs` configuration, typically `user-dirs.dirs`, **not** one of the XDG Base Directory variables | Do not assume setting an inherited process environment variable exercises the desktop's download-directory lookup |
| `torbox.token` | An application credential convention, not an XDG location | Inject credential content/provider for logic tests; test secure persistence at its own boundary |

For the Base Directory variables, relative paths are invalid; user state and cache also have documented defaults when unset. Runtime storage has stricter properties and no analogous universally fixed default. The download directory is a separate *user-dirs* convention and may be located through the configuration file or a desktop API. An application may deliberately support `XDG_DOWNLOAD_DIR` as its **own** environment override, but that is a documented application-specific interface, not proof of general XDG compliance.

Sources: [freedesktop.org XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/), [freedesktop.org xdg-user-dirs](https://wiki.freedesktop.org/www/Software/xdg-user-dirs/), and [xdg-user-dir(1)](https://manpages.debian.org/trixie/xdg-user-dirs/xdg-user-dir.1.en.html).

This matters especially for runtime directories: a test can choose an isolated pathname, but it must not pretend that doing so tests session lifecycle, security, or socket support.

## Resolve at the boundary; pass the actual dependency inward

For code that plans where a download goes, I would rather see an explicit input:

```go
type DownloadPlanOptions struct {
    DownloadDir string
    CacheDir    string
}

func PlanDownload(opts DownloadPlanOptions, name string) (string, error) {
    // Validate the destination name before joining it.
    if name == "" || filepath.Base(name) != name || name == "." || name == ".." {
        return "", fmt.Errorf("invalid download name %q", name)
    }
    return filepath.Join(opts.DownloadDir, name), nil
}

func TestPlanDownload(t *testing.T) {
    got, err := PlanDownload(DownloadPlanOptions{
        DownloadDir: "downloads",
        CacheDir:    "cache",
    }, "report.zip")
    if err != nil {
        t.Fatal(err)
    }
    if want := filepath.Join("downloads", "report.zip"); got != want {
        t.Fatalf("destination = %q, want %q", got, want)
    }
}
```

No OS environment, directories, files or cleanup are needed because this test is about destination planning, not filesystem effects.

The important design choice is **not** to make a giant `Dependencies` struct mirroring every possible environment variable. Pass only the locations and capabilities the operation genuinely uses. If a function requires only a cache key and bytes, it may not need a cache path at all.

The outer command, service bootstrap or platform adapter is responsible for taking the real user environment and producing typed configuration. If the application supports CLI flags or explicit configuration, resolve their precedence there, once. Business logic should not be forced to resolve them again.

## Keep credentials separate from their storage

A token's *value* and a token's *filename* are different concerns. A test that is only checking authenticated request construction needs neither a real token file nor a fake home directory.

```go
type TokenSource interface {
    Token(context.Context) (string, error)
}

type staticToken string

func (s staticToken) Token(context.Context) (string, error) {
    return string(s), nil
}

// Unit tests pass staticToken("fake-test-token") to the client.
// Production uses an implementation that loads the credential securely.
```

Use an injectable transport to inspect the outgoing request without contacting a real service. Redact token values from diagnostics. A separate integration test should verify file permissions, failure modes, file lifecycle and the production token loader when those are actual requirements.

Avoid making the token path a globally mutable variable merely to replace it in tests. Prefer a constructor argument or an owned provider. That is a smaller, clearer seam.

## The three tests I actually want

1. **Logic test:** construct typed paths, token providers, fake filesystems and transports directly; assert the intended behaviour. No environment mutation and no temp directory merely for setup.
2. **Configuration boundary test:** call the environment resolver with a controlled lookup function, or use `t.Setenv` in one focused non-parallel test when the actual process environment API matters. Check unset, empty, absolute/relative and override cases as appropriate.
3. **Real integration test:** use `t.TempDir()`, `httptest`, subprocesses or OS facilities when permissions, directory creation, actual download writes, socket behaviour, or credential persistence is what is being proven. Keep the environment mutation local to that deliberately serial boundary.

A pure lookup seam can be small:

```go
type LookupEnv func(string) (string, bool)

func cacheHome(lookup LookupEnv, home string) string {
    if value, ok := lookup("XDG_CACHE_HOME"); ok && filepath.IsAbs(value) {
        return value
    }
    return filepath.Join(home, ".cache")
}

func TestCacheHome(t *testing.T) {
    lookup := func(name string) (string, bool) {
        if name == "XDG_CACHE_HOME" {
            return "/custom-cache", true
        }
        return "", false
    }
    if got := cacheHome(lookup, "/home/test"); got != "/custom-cache" {
        t.Fatalf("cache = %q", got)
    }
}
```

This is illustrative of the *cache* rule only; it is **not** a complete XDG resolver, and a real resolver should keep platform-specific details, missing variables and error policy in their proper adapters. Do not implement the entire desktop specification just to make this unit test possible.

A focused process-boundary test may still be exactly right:

```go
func TestCacheEnvironmentBoundary(t *testing.T) {
    t.Setenv("XDG_CACHE_HOME", t.TempDir())
    // Invoke only the real adapter that intentionally reads os.LookupEnv.
    // Do not call t.Parallel here or from a parallel parent.
}
```

If the integration test requires a real runtime directory, verify relevant permissions and filesystem behaviour; do not equate `t.TempDir()` with a login-managed runtime session.

## How to recognise the right refactor

Ask one question before changing test infrastructure:

> If I replace these five setup lines with explicit values or a small fake, am I still proving the same requirement?

If yes, move the environment lookup and path resolution outward and test the inner operation directly. If not, the test probably *is* about an OS/environment contract; preserve it and name it as such.

Do not rewrite every test as part of one cleanup. Extract one useful seam, retain a boundary test, and stop when the scenario is easier to understand. This follows [choosing proportional filesystem fixtures](/blog/post/2026/047-choosing-go-filesystem-test-fixtures/), [small Go test setup helpers](/blog/post/2026/049-go-test-setup-use-small-must-helpers/), and [writing large tests as scenarios](/blog/post/2026/051-large-go-tests-should-read-like-scenarios/).

## A reusable repository instruction

When this is an actual project convention, put the operative part in the repository's `AGENTS.md` (or its existing agent-instruction file), not only in a remote blog article:

```markdown
### Environment and filesystem tests
- Treat environment variables, XDG paths, credential locations and process globals
  as external dependencies. Resolve them at application boundaries and inject
  only the paths/capabilities the inner operation needs.
- Do not recreate a synthetic XDG session in routine unit tests. Prefer typed
  options, in-memory fixtures, fake token providers and injectable transports.
- Use t.Setenv in focused tests of actual environment parsing/wiring; these
  tests must not run in parallel. Use t.TempDir for genuine OS/path semantics.
- Distinguish XDG Base Directory variables from xdg-user-dirs configuration.
  Do not claim a fake XDG_RUNTIME_DIR verifies session or permission semantics.
- Preserve focused integration coverage when removing incidental test setup.
```

Link the longer article from `docs/testing.md` or `AGENTS.md` as rationale, but keep enough concrete instruction local that the rule still works offline. If the repository has no XDG-specific behaviour, omit those details entirely.

I prefer a **visible dependency over a manufactured desktop**. Tests should explain the behaviour being protected rather than the ceremony needed to reach it.
