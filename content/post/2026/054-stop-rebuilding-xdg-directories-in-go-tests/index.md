---
title: "Prefer Dependency Injection to Environment Overrides in Go Tests"
date: 2026-10-11T02:42:55.064Z
draft: false
guidance: ["go-testing"]
tags: ["go", "testing", "xdg", "dependency-injection", "filesystem", "environment"]
categories: ["Testing", "Software Development"]
discussion: "https://github.com/arran4/blog/discussions/207"
---

<!-- cspell:words getenv goroutines httptest torbox Unsetenv XDG -->

A unit test that starts by rewriting process environment variables may be testing more configuration machinery than the behaviour it claims to protect:

```go
t.Setenv("APP_API_URL", "https://service.example.invalid")
t.Setenv("APP_FEATURE_FLAG", "enabled")
t.Setenv("HOME", t.TempDir())
got := PlanWork(...)
```

None of these calls is inherently wrong. Go's \`t.Setenv\` is useful when **reading the real process environment is the contract under test**. But if \`PlanWork\` only needs a service URL and a feature setting, it should usually accept those values directly rather than reading ambient state.

**Prefer dependency injection (DI) for ordinary behaviour tests; reserve environment overrides for tests of environment integration.** The same principle applies to credentials, filesystem paths, clocks, transports and other hidden dependencies. XDG directories provide a particularly instructive example, but they are not the limit of the rule.

This builds on [treating process state as a dependency](/blog/post/2026/053-go-tests-treat-process-state-time-and-standard-io-as-dependencies/) and [minimising filesystem side effects](/blog/post/2026/048-minimize-filesystem-side-effects-in-tests/). The aim is not to ban \`t.Setenv\`, temporary directories or environment-based configuration; it is to use them only where they prove something.

## The problem is process-wide state, not the spelling of the variable

The environment belongs to the **process**, not an individual function or test. A production function that calls \`os.Getenv\` deep in its implementation makes behaviour depend on whichever environment happens to be active at the moment.

Tests that change it to reach unrelated logic have several costs:

- **Hidden dependencies:** a caller cannot see which settings influence the operation, and a test's setup obscures the assertion.
- **Concurrency constraints:** \`t.Setenv\` restores the previous value during cleanup, but it does not isolate that value from other code in the process. Go prohibits its use in a parallel test or a test with a parallel ancestor; concurrent goroutines can still observe a temporary change.
- **Repeated configuration testing:** dozens of tests implicitly exercise the same \`os.Getenv\` wiring instead of giving the application behaviour direct inputs.
- **Fragile precedence:** defaults, empty variables, CLI flags, configuration files and explicit overrides can be unintentionally mixed when every operation resolves them independently.
- **Artificial side effects:** replacing \`HOME\`, XDG paths or token filenames can force unnecessary directory creation and file I/O.

Replacing \`t.Setenv\` with \`os.Setenv\` and a deferred restore does not solve the design problem; it removes Go's managed test cleanup and leaves the same process-global mutation. Similarly, a mutable package variable for the current configuration merely moves the hidden dependency.

This does **not** mean every use of \`os.Getenv\` is a problem. Reading it at a command, service bootstrap or platform boundary is normal. The question is whether an inner operation should be responsible for reading it.

## Resolve external configuration at the boundary; inject what the operation needs

An outer adapter can read environment variables, validate them and resolve precedence. Inner code then receives typed values or small capabilities. A function does not need a pretend process environment just to build an HTTP request:

```go
type RequestConfig struct {
    APIBaseURL string
}

func newStatusRequest(cfg RequestConfig) (*http.Request, error) {
    return http.NewRequest(http.MethodGet, cfg.APIBaseURL+"/status", nil)
}

func TestNewStatusRequest(t *testing.T) {
    req, err := newStatusRequest(RequestConfig{
        APIBaseURL: "https://test.example.invalid",
    })
    if err != nil {
        t.Fatal(err)
    }
    if got, want := req.URL.String(), "https://test.example.invalid/status"; got != want {
        t.Fatalf("URL = %q, want %q", got, want)
    }
}
```

No environment mutation, fake home directory or cleanup is needed. This test is about the request, not the origin of the configuration. If the operation actually sends HTTP requests, inject a transport or client as well, so request behaviour can be tested without contacting a real service.

The environment adapter deserves its **own** tests. Even that adapter can often accept a lookup function instead of touching the actual process:

```go
type LookupEnv func(string) (string, bool)

func resolveRequestConfig(lookup LookupEnv) RequestConfig {
    url := "https://default.example.invalid"
    if value, ok := lookup("APP_API_URL"); ok && value != "" {
        url = value
    }
    return RequestConfig{APIBaseURL: url}
}

func TestResolveRequestConfig(t *testing.T) {
    env := map[string]string{"APP_API_URL": "https://test.example.invalid"}
    lookup := func(key string) (string, bool) {
        value, ok := env[key]
        return value, ok
    }
    if got := resolveRequestConfig(lookup).APIBaseURL; got != env["APP_API_URL"] {
        t.Fatalf("API URL = %q", got)
    }
}

// At application startup: cfg := resolveRequestConfig(os.LookupEnv)
```

This example deliberately treats an unset or empty override as the default. Real adapters should make that policy explicit, validate URLs and other values, and separately test whatever precedence the application promises (for example: CLI option, configuration file, environment variable, default).

Do not pass a generic \`LookupEnv\` through the entire application when only the startup adapter needs it. Prefer the smallest useful dependency: a string or typed options for pure logic; an \`io.Reader\`, \`fs.FS\`, credential provider, clock or HTTP transport for I/O. **DI does not require an interface for every value**, or a giant \`Dependencies\` struct containing every environment variable.

## Three distinct kinds of test

1. **Behaviour test:** inject the exact configuration or capability the operation needs. Exercise normal, failure and edge cases without changing the process environment.
2. **Configuration-resolution test:** provide a controlled lookup, then verify missing, present, empty, invalid and precedence cases. This is where environment interpretation belongs.
3. **Process/OS integration test:** deliberately use \`t.Setenv\`, \`t.TempDir\`, \`httptest\` or a subprocess when the actual environment API, filesystem, permissions, process startup or assembled wiring is the subject.

A small test of the real environment-reading boundary is still worthwhile:

```go
func TestRequestEnvironmentBoundary(t *testing.T) {
    t.Setenv("APP_API_URL", "https://boundary.example.invalid")

    got := resolveRequestConfig(os.LookupEnv)
    if got.APIBaseURL != "https://boundary.example.invalid" {
        t.Fatalf("API URL = %q", got.APIBaseURL)
    }
    // This test and its ancestors must not call t.Parallel.
}
```

Use \`t.Setenv\` rather than manually juggling \`os.Setenv\` and \`os.Unsetenv\` when a focused, serial test genuinely needs process environment overrides. For tests that must run concurrently while changing environment state, isolate the work in subprocesses rather than assuming \`t.Setenv\` is goroutine-local. Do not run the whole suite serially merely to preserve a pattern that could be replaced by injection.

The boundary also matters in production: if configuration is intended to be stable for a service's lifetime, resolve it once at startup. If hot reload or per-request overrides are a requirement, represent those explicitly in the relevant component's API instead of letting arbitrary environment reads decide when values change.

## XDG: a concrete example where the distinction matters

Consider this setup from a download-related test:

```go
t.Setenv("XDG_RUNTIME_DIR", runtimeDir)
t.Setenv("XDG_STATE_HOME", filepath.Join(tempDir, "state"))
t.Setenv("XDG_CACHE_HOME", filepath.Join(tempDir, "cache"))
t.Setenv("XDG_DOWNLOAD_DIR", filepath.Join(tempDir, "downloads"))
tokenPath := filepath.Join(tempDir, "torbox.token")
```

If the test verifies how the real desktop adapter resolves paths, some of this setup may be justified. If it only tests download planning or request construction, it is an elaborate indirect way of providing a destination and a credential.

There is a second problem: these names do **not** all describe the same kind of contract.

| Setting | Intended source and meaning | Testing consequence |
| --- | --- | --- |
| \`XDG_STATE_HOME\` | XDG Base Directory variable for persistent user state | Test default/override resolution at the adapter; pass the resulting state directory inward |
| \`XDG_CACHE_HOME\` | XDG Base Directory variable for disposable user caches | Inject a directory or cache capability for normal tests; verify real cache behaviour separately |
| \`XDG_RUNTIME_DIR\` | Session-scoped runtime directory with ownership, \`0700\` permissions, lifecycle and local-filesystem requirements | A temporary folder alone does not demonstrate runtime-directory compliance |
| \`XDG_DOWNLOAD_DIR\` | Name used in \`xdg-user-dirs\` configuration (usually \`user-dirs.dirs\`), **not** an XDG Base Directory variable | Setting a process variable does not automatically exercise the user's desktop download-directory lookup |
| \`torbox.token\` | Application-specific credential filename, not an XDG directory | Inject credential content or a provider for logic tests; test secure storage at its own boundary |

For the Base Directory variables, relative paths are invalid; state and cache have specified defaults when unset. Runtime storage carries additional requirements and has no equivalent universal fallback. The download directory is a separate *user-dirs* convention and may be obtained through a configuration file or desktop API. An application is free to support \`XDG_DOWNLOAD_DIR\` as its **own documented override**, but that does not make it part of the Base Directory specification.

Sources: [freedesktop.org XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/), [freedesktop.org xdg-user-dirs](https://wiki.freedesktop.org/www/Software/xdg-user-dirs/), and [xdg-user-dir(1)](https://manpages.debian.org/trixie/xdg-user-dirs/xdg-user-dir.1.en.html).

For a download planner, an explicit path is often enough:

```go
type DownloadOptions struct {
    DownloadDir string
}

func PlanDownload(opts DownloadOptions, name string) (string, error) {
    if name == "" || filepath.Base(name) != name || name == "." || name == ".." {
        return "", fmt.Errorf("invalid download name %q", name)
    }
    return filepath.Join(opts.DownloadDir, name), nil
}

func TestPlanDownload(t *testing.T) {
    got, err := PlanDownload(DownloadOptions{DownloadDir: "downloads"}, "report.zip")
    if err != nil {
        t.Fatal(err)
    }
    if want := filepath.Join("downloads", "report.zip"); got != want {
        t.Fatalf("destination = %q, want %q", got, want)
    }
}
```

There is no reason to manufacture an XDG session merely to verify that plan. A test of actual writes, secure credential persistence or a runtime socket is different: use the OS facilities required by that contract. In particular, \`t.TempDir()\` does not recreate the ownership, lifetime or security guarantees of a login-managed \`XDG_RUNTIME_DIR\`.

A credential's value is also distinct from its filename. For authenticated request tests, prefer an injected token source (or a plain token value when sufficient) rather than writing a fake token file:

```go
type TokenSource interface {
    Token(context.Context) (string, error)
}

type staticToken string

func (s staticToken) Token(context.Context) (string, error) {
    return string(s), nil
}
```

Use a separate integration test for the real loader's permissions, error handling and lifecycle. Do not log real token values.

## Interfaces select what changes; optional arguments select how

The examples above show a plain typed configuration value and a small `TokenSource` interface. There is another decision to make in an **existing** Go codebase: how do I add those dependencies without making every old caller supply them?

I have an established pattern for this. [The type-switched variadic system](/blog/post/2026/001-Type-Switched-Variadic-System/) describes `opts ...any` as a set of *typed option values* interpreted by a single type switch. [Optional Dependency Injection via Type-Switched Variadic Args](/blog/post/2026/020-optional-dependency-injection-via-type-switched-variadic-args/) specifically applies that pattern to filesystem and other side-effect dependencies.

The two ideas complement each other:

- An **interface** states the capability to replace: a token source, a read-only filesystem, a writer, a transport, or a clock. Prefer `fs.FS` and other established small interfaces where they fit; use a project-specific one only for a capability that does not fit.
- An **optional argument** specifies how an old public entry point accepts a replacement without forcing every caller to change.
- A **named option type** distinguishes values that share the same underlying type, such as a state directory and a cache directory. Do not interpret arbitrary `string` options as paths by position or accident.
- A **typed internal configuration** gives the implementation an ordinary, explicit set of dependencies after the options have been resolved. Internal functions need not repeatedly parse `...any`.

### An additive seam for an existing constructor

Suppose the existing API is `NewDownloader(downloadDir string) (*Downloader, error)`. Changing it to require an extra filesystem, token provider and HTTP client would ripple through existing callers. An additive type-switched option list can preserve ordinary calls:

```go
type DownloadDir string // a named override, not an arbitrary string option

type Downloader struct {
    dir       string
    templates fs.FS
    tokens    TokenSource
}

// The production adapter is intentionally OS-backed.
type fileToken string

func (p fileToken) Token(context.Context) (string, error) {
    data, err := os.ReadFile(string(p))
    if err != nil {
        return "", err
    }
    return strings.TrimSpace(string(data)), nil
}

// Before: NewDownloader(downloadDir string) (*Downloader, error)
// After:  old direct calls still compile without passing dependencies.
func NewDownloader(downloadDir string, opts ...any) (*Downloader, error) {
    cfg := Downloader{dir: downloadDir}

    for _, raw := range opts {
        switch opt := raw.(type) {
        case DownloadDir:
            cfg.dir = string(opt)
        case fs.FS:
            cfg.templates = opt
        case TokenSource:
            cfg.tokens = opt
        default:
            return nil, fmt.Errorf("unsupported downloader option %T", raw)
        }
    }

    if cfg.dir == "" {
        return nil, errors.New("download directory is required")
    }
    if cfg.templates == nil {
        cfg.templates = os.DirFS(cfg.dir)
    }
    if cfg.tokens == nil {
        cfg.tokens = fileToken(filepath.Join(cfg.dir, "torbox.token"))
    }
    return &cfg, nil
}
```

The example uses `fs.FS` for **reading templates or metadata**. It is not a writable filesystem: if this downloader writes files, represent that separately through the smallest output capability that actually supports writes. The sample's filename is an application convention, not an XDG rule.

With those optional dependencies, a unit test can construct the downloader without mutating environment variables or creating a fake home:

```go
d, err := NewDownloader("unused-on-disk",
    DownloadDir("virtual-downloads"),
    fstest.MapFS{
        "settings.json": &fstest.MapFile{
            Data: []byte(`{"enabled":true}`),
        },
    },
    staticToken("fixture-only-token"),
)
if err != nil {
    t.Fatal(err)
}
// Exercise d's real operation and assert its output and failure paths.
```

An actual unit test should assert the operation's observable behaviour, not merely that construction succeeded. A smaller integration test still proves that the default `fileToken` adapter reads a real credential and that the OS-backed filesystem is wired correctly.

This is a **constructor boundary**, not an invitation to pass a bag of `any` arguments into every helper. Resolve once, then pass `cfg.templates`, `cfg.tokens` and the selected directory to internal functions as ordinary typed dependencies.

### Compatibility and validation are still requirements

The variadic approach preserves direct invocation such as `NewDownloader(path)`, but it does **not** preserve every aspect of the function's type. For example, assigning the new function to a variable of type `func(string) (*Downloader, error)`, or implementing an interface that requires the old method signature, may no longer compile. If those contracts exist, retain the exact old entry point and add a separately named options-aware constructor, then delegate both to the same private implementation.

Do not change an existing return signature solely to report an unsupported option. Where the public API already returns `error`, reject unsupported options explicitly rather than silently ignoring them. When it does not, choose a compatible API shape or follow the project's documented programmer-error policy.

Other guardrails matter:

- **Defaults stay real and lazy.** Normal callers should continue to get the documented production adapters; a unit test that supplies a fake should not have to perform OS setup merely to construct the object.
- **Name ambiguous values.** A raw `string` cannot tell the state path from the download directory. Prefer named wrappers, or a typed options struct when many related values belong together.
- **Document repeated options.** If later options override earlier ones, say so and test the precedence. Likewise, choose explicit semantics for combinations of interfaces or wrapper types that could overlap.
- **Validate injected values.** A typed nil pointer can satisfy a non-nil interface; an unchecked fake can still panic. Validate important contracts at construction without creating a reflection-heavy generic framework.
- **Keep accepted types discoverable.** Include them in constructor documentation, examples and tests. The single type switch should not become a hidden global configuration language.
- **Do not turn every function into `...any`.** For new, small internal code, an explicit argument, plain struct or typed constructor is often simpler and offers stronger compile-time checking.

A useful decision rule is: **prefer a direct dependency when designing a new internal function; consider optional type-switched arguments when evolving an existing public call surface that already fits this style**. Interfaces express the interchangeable capability regardless of which entry-point style is selected.

## Recognising the right refactor

Ask: **If I replace these environment overrides with explicit inputs or a small fake, am I still proving the same requirement?**

If yes, resolve the external state outside the operation and inject the useful values or capabilities. If not, the test is probably about an environment or OS contract: keep the real boundary test, name it clearly and constrain its scope.

Do not refactor every test or introduce a universal configuration framework. Extract one useful seam, retain essential integration coverage and stop when the test makes the intended behaviour clearer. The same proportional approach is described in [choosing filesystem fixtures](/blog/post/2026/047-choosing-go-filesystem-test-fixtures/), [small Go test setup helpers](/blog/post/2026/049-go-test-setup-use-small-must-helpers/) and [writing large tests as scenarios](/blog/post/2026/051-large-go-tests-should-read-like-scenarios/).

## A reusable repository instruction

Where this fits a project's real conventions, put an actionable version in \`AGENTS.md\` or the repository's existing agent-instruction file:

```markdown
### Process environment in tests
- Treat environment variables and other process globals as external inputs.
  Resolve configuration at application boundaries and inject the typed values
  or small capabilities required by inner operations.
- Do not override the process environment merely to configure ordinary unit
  tests. Prefer explicit options, readers, fake providers or transports.
- Test environment defaults, empty/unset values, validation and precedence in
  focused configuration-adapter tests using an injected lookup where practical.
- Use t.Setenv for tests that intentionally read the real process environment;
  keep such tests and their ancestors non-parallel. Use subprocess isolation
  when independent concurrent environment mutation is required.
- Use t.TempDir when actual filesystem behaviour matters, not just as setup.
- Preserve focused integration coverage when removing incidental test setup.
```

For repositories that actually integrate with XDG, add a separate XDG-specific rule:

```markdown
- Distinguish XDG Base Directory variables from xdg-user-dirs configuration.
  Inject resolved paths for ordinary tests; do not claim that a temporary
  XDG_RUNTIME_DIR demonstrates session lifecycle or permission compliance.
```

Link the article from local documentation for rationale, but keep enough instruction within the repository for an agent to apply the rule offline. If the project does not use XDG, it should not inherit XDG-specific testing ceremony.

**Prefer visible inputs over rewriting the process around a test.** The goal is to prove application behaviour without repeatedly reconstructing its runtime environment.
