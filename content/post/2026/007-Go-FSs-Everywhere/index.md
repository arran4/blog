# Go FSs Everywhere: Treat Side Effects as Dependencies

If your Go code reaches directly for `os.Create`, `os.Stat`, `os.ReadFile`, `exec.Command`, or `net.Dial`, your tests are paying for real side effects even when they do not need to.

This article explains a practical pattern:

- **wrap side-effectful APIs behind your own small interfaces**,
- **inject real implementations in production**, and
- **inject fakes/in-memory versions in tests**.

The short version:

- Prefer `myfs.Stat("file.txt")` over `os.Stat("file.txt")` in application code.
- Prefer `runner.LookPath("git")` over `exec.LookPath("git")`.
- Prefer `client.Do(req)` over hidden package-level `http.DefaultClient.Do(req)`.

And yes: most tests should avoid file system operations. Not all tests—just **most**.

---

## Why do this?

### 1) Speed
Disk I/O, process spawning, and network calls are slower than memory operations. In-memory tests usually run dramatically faster.

### 2) Stability
Real file systems and OS environments vary:

- path separators,
- file permissions,
- CI container quirks,
- race conditions from shared temp dirs.

Fakes remove those sources of nondeterminism for unit tests.

### 3) Better failure coverage
With wrappers, you can force edge cases easily:

- `permission denied`,
- `file does not exist`,
- `disk full` (simulated),
- executable not found,
- socket timeout.

Those are hard or painful to reproduce consistently on real infrastructure.

### 4) Clear architecture
When code takes dependencies explicitly, boundaries are obvious. You can tell what function actually needs from the outside world.

---

## "Most but not all" tests should avoid filesystem operations

A healthy test pyramid usually looks like this:

- **Unit tests (majority)**: no real file system/network/processes.
- **Integration tests (some)**: use real FS/processes/network where behavior matters.
- **End-to-end tests (few)**: full stack.

So the recommendation is not "never touch the disk." It is:

> Keep side effects out of most tests, and reserve real side effects for the smaller integration/e2e suites.

That gives you both speed and confidence.

---

## Core pattern: wrap, inject, test

## 1) Define the minimum interface your code needs

```go
package myfs

import (
	"io"
	"io/fs"
	"os"
)

// FS defines only what this application actually needs.
type FS interface {
	Create(name string) (io.WriteCloser, error)
	Stat(name string) (fs.FileInfo, error)
	ReadFile(name string) ([]byte, error)
}

// OS is the real production implementation.
type OS struct{}

func (OS) Create(name string) (io.WriteCloser, error) { return os.Create(name) }
func (OS) Stat(name string) (fs.FileInfo, error)      { return os.Stat(name) }
func (OS) ReadFile(name string) ([]byte, error)       { return os.ReadFile(name) }
```

Keep interfaces small and local to your package. Don’t pre-abstract everything.

## 2) Inject it into business logic

```go
package report

import (
	"errors"
	"fmt"
	"path/filepath"

	"example.com/app/myfs"
)

type Generator struct {
	FS myfs.FS
}

func NewGenerator(fs myfs.FS) *Generator {
	return &Generator{FS: fs}
}

func (g *Generator) Write(output string, data []byte) error {
	if filepath.Base(output) != output {
		return errors.New("security error: output file must be in the current directory")
	}

	f, err := g.FS.Create(output)
	if err != nil {
		return fmt.Errorf("create output: %w", err)
	}
	defer f.Close()

	if _, err := f.Write(data); err != nil {
		return fmt.Errorf("write output: %w", err)
	}
	return nil
}
```

Notice there is **no direct `os.Create`** in business logic.

## 3) Test with a fake implementation

```go
package report_test

import (
	"bytes"
	"errors"
	"io"
	"io/fs"
	"testing"
	"time"

	"example.com/app/report"
)

type nopCloser struct{ io.Writer }
func (nopCloser) Close() error { return nil }

type fakeFileInfo struct{ name string }
func (f fakeFileInfo) Name() string       { return f.name }
func (f fakeFileInfo) Size() int64        { return 0 }
func (f fakeFileInfo) Mode() fs.FileMode  { return 0 }
func (f fakeFileInfo) ModTime() time.Time { return time.Time{} }
func (f fakeFileInfo) IsDir() bool        { return false }
func (f fakeFileInfo) Sys() any           { return nil }

type mockFS struct {
	Files map[string]*bytes.Buffer
	Err   error
}

func (m *mockFS) Create(name string) (io.WriteCloser, error) {
	if m.Err != nil {
		return nil, m.Err
	}
	if m.Files == nil {
		m.Files = map[string]*bytes.Buffer{}
	}
	buf := new(bytes.Buffer)
	m.Files[name] = buf
	return nopCloser{buf}, nil
}

func (m *mockFS) Stat(name string) (fs.FileInfo, error) {
	if _, ok := m.Files[name]; !ok {
		return nil, fs.ErrNotExist
	}
	return fakeFileInfo{name: name}, nil
}

func (m *mockFS) ReadFile(name string) ([]byte, error) {
	b, ok := m.Files[name]
	if !ok {
		return nil, fs.ErrNotExist
	}
	return b.Bytes(), nil
}

func TestWrite_Security(t *testing.T) {
	g := report.NewGenerator(&mockFS{})

	invalidPaths := []string{"../report.md", "/tmp/report.md", "subdir/report.md"}
	for _, p := range invalidPaths {
		err := g.Write(p, []byte("x"))
		if err == nil || err.Error() != "security error: output file must be in the current directory" {
			t.Fatalf("path %q: got err=%v", p, err)
		}
	}
}

func TestWrite_CreateError(t *testing.T) {
	g := report.NewGenerator(&mockFS{Err: errors.New("permission denied")})
	if err := g.Write("report.md", []byte("x")); err == nil {
		t.Fatal("expected error")
	}
}
```

You can test behavior precisely with no disk access.

---

## Why wrap your own usage (`myfs.Stat`) instead of calling `os.Stat` directly?

Because **you own the seam**.

If code uses `os.Stat` everywhere, you cannot replace behavior without invasive refactors or global hacks.

If code uses `myfs.Stat` (or a local `FS` interface), you can:

- run fast in-memory unit tests,
- simulate failures on demand,
- swap implementation (local disk, embedded files, txtar, remote-backed virtual FS),
- enforce organization-wide behavior (logging, metrics, path rules, audit).

Also, avoid global mutable indirection like:

```go
var osExec execProxy = realExecProxy{} // avoid this
```

Global state leaks between tests and encourages hidden coupling. Prefer explicit fields/parameters:

```go
type Discoverer struct {
	Exec execProxy
}

func NewDiscoverer() *Discoverer {
	return &Discoverer{Exec: realExecProxy{}}
}
```

---

## Using standard library test-friendly FS tools

Go already gives you good building blocks.

### `testing/fstest.MapFS`

For read-oriented scenarios:

```go
fsys := fstest.MapFS{
	"go.mod":      &fstest.MapFile{Data: []byte("module example.com/test\n\ngo 1.22\n")},
	"pkg1/cmd.go": &fstest.MapFile{Data: []byte("package pkg1\n")},
}
```

Great for parser/discovery logic where you only need an `fs.FS`.

### `golang.org/x/tools/txtar` FS

If you like archive-like fixtures in a single text block, `txtar` can represent multi-file test layouts and expose them as an FS.

Useful for concise, copyable, fixture-heavy tests.

---

## Example: command execution wrapper (same concept, not FS)

```go
type execProxy interface {
	Command(name string, arg ...string) *exec.Cmd
	LookPath(file string) (string, error)
}

type realExecProxy struct{}

var ExecCommand = exec.Command

func (realExecProxy) Command(name string, arg ...string) *exec.Cmd {
	return ExecCommand(name, arg...)
}

func (realExecProxy) LookPath(file string) (string, error) {
	return exec.LookPath(file)
}

type Discoverer struct {
	Exec execProxy
}

func NewDiscoverer() *Discoverer {
	return &Discoverer{Exec: realExecProxy{}}
}
```

In tests, inject a mock `execProxy` that returns deterministic values.

---

## Example: network/socket wrapper (same concept again)

```go
type Dialer interface {
	DialContext(ctx context.Context, network, addr string) (net.Conn, error)
}

type NetDialer struct{ d net.Dialer }

func (n NetDialer) DialContext(ctx context.Context, network, addr string) (net.Conn, error) {
	return n.d.DialContext(ctx, network, addr)
}

type Client struct {
	Dialer Dialer
}
```

In tests, use `net.Pipe()` or a fake dialer to avoid real sockets.

---

## You already do this with HTTP (often without noticing)

`httptest.NewServer` is exactly this philosophy:

- replace external network dependency with controlled in-process test server,
- run fast,
- assert exact requests/responses,
- avoid flaky external dependencies.

You can extend that same mindset to file systems, command execution, sockets, cloud SDKs, and databases.

---

## When to use real filesystem tests anyway

Use real FS integration tests when validating things fakes cannot guarantee well:

- file permissions and ownership behavior,
- symlink behavior,
- long path / platform specifics,
- atomic rename semantics,
- interaction with real tools consuming generated files.

Keep these tests focused and fewer. Mark them clearly as integration tests.

---

## Practical adoption strategy for existing codebases

1. **Pick one hot path** (where tests are slow/flaky).
2. **Introduce a tiny interface** that covers only current needs.
3. **Add constructor injection** with a real default implementation.
4. **Migrate direct `os.*` calls** inside that path to the injected dependency.
5. **Write fast unit tests** with fakes.
6. **Retain/add a few integration tests** using real `os` behavior.

You don’t need a big-bang rewrite.

---

## Copy-paste starter template

```go
// package deps
package deps

import (
	"io"
	"os"
)

type FileSystem interface {
	Create(name string) (io.WriteCloser, error)
	Stat(name string) (os.FileInfo, error)
}

type OSFS struct{}

func (OSFS) Create(name string) (io.WriteCloser, error) { return os.Create(name) }
func (OSFS) Stat(name string) (os.FileInfo, error)      { return os.Stat(name) }
```

```go
// package app
package app

type Service struct {
	FS deps.FileSystem
}

func NewService(fs deps.FileSystem) *Service {
	if fs == nil {
		fs = deps.OSFS{}
	}
	return &Service{FS: fs}
}
```

This keeps production simple and tests fast.

---

## Final guideline

If a function touches the outside world, treat that capability as a dependency and inject it.

- Use real implementations in production.
- Use in-memory/fake implementations for most tests.
- Keep a smaller set of integration tests for real-world behavior.

That’s how you get **fast feedback**, **stable tests**, and **clear boundaries**—without giving up confidence.
