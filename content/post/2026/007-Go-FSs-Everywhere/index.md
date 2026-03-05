# Go FSs Everywhere: Treat Side Effects as Dependencies

If your Go code calls `os.Create`, `os.Stat`, `exec.LookPath`, or `net.Dial` directly from business logic, your tests are forced to touch real side effects more often than necessary.

The pattern in this article is simple:

1. Define small interfaces for side effects.
2. Inject real implementations in production.
3. Inject fakes or in-memory versions in tests.

This is why I encourage `myfs.Stat("file.txt")` (or whatever your project names it) over direct `os.Stat("file.txt")` in your core application code.

## Why interfaces matter for switching implementations

The key benefit is **switchability without refactoring call sites**.

If your code is hard-coded to `os.*`, switching behavior later is expensive. If your code depends on an interface, switching is just wiring.

- production: use real OS-backed implementation,
- unit tests: use in-memory fake,
- integration tests: use real disk with temp dirs,
- special tools: use embedded FS, `fstest.MapFS`, or `txtar`.

This gives you speed today and flexibility later.

## Why most (but not all) tests should avoid filesystem operations

You usually want:

- **many unit tests** with no real FS/network/process calls,
- **fewer integration tests** that validate real FS and OS behavior,
- **a small number of end-to-end tests** for full confidence.

This split gives better feedback loops:

- fast local iteration,
- fewer flaky tests,
- better coverage of failure branches,
- still keeping real-world verification where it matters.

So this is not "never touch the file system." It is "use real side effects intentionally, not by default."

## Core pattern: wrap, inject, test

### 1) Define the minimal interface your code needs

```go
package myfs

import (
	"io"
	"io/fs"
	"os"
)

// FS only includes operations this package needs.
type FS interface {
	Create(name string) (io.WriteCloser, error)
	Stat(name string) (fs.FileInfo, error)
	ReadFile(name string) ([]byte, error)
}

// OSFS is the production implementation.
type OSFS struct{}

func (OSFS) Create(name string) (io.WriteCloser, error) { return os.Create(name) }
func (OSFS) Stat(name string) (fs.FileInfo, error)      { return os.Stat(name) }
func (OSFS) ReadFile(name string) ([]byte, error)       { return os.ReadFile(name) }
```

### 2) Inject the interface into business logic

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
	if fs == nil {
		fs = myfs.OSFS{}
	}
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

### 3) Test with fakes in idiomatic table-driven tests

```go
package report_test

import (
	"bytes"
	"errors"
	"io"
	"io/fs"
	"strings"
	"testing"
	"time"

	"example.com/app/report"
)

type nopCloser struct{ io.Writer }

func (nopCloser) Close() error { return nil }

type fakeInfo struct{ name string }

func (f fakeInfo) Name() string       { return f.name }
func (f fakeInfo) Size() int64        { return 0 }
func (f fakeInfo) Mode() fs.FileMode  { return 0 }
func (f fakeInfo) ModTime() time.Time { return time.Time{} }
func (f fakeInfo) IsDir() bool        { return false }
func (f fakeInfo) Sys() any           { return nil }

type mockFS struct {
	files     map[string]*bytes.Buffer
	createErr error
}

func (m *mockFS) Create(name string) (io.WriteCloser, error) {
	if m.createErr != nil {
		return nil, m.createErr
	}
	if m.files == nil {
		m.files = map[string]*bytes.Buffer{}
	}
	buf := new(bytes.Buffer)
	m.files[name] = buf
	return nopCloser{Writer: buf}, nil
}

func (m *mockFS) Stat(name string) (fs.FileInfo, error) {
	if _, ok := m.files[name]; !ok {
		return nil, fs.ErrNotExist
	}
	return fakeInfo{name: name}, nil
}

func (m *mockFS) ReadFile(name string) ([]byte, error) {
	f, ok := m.files[name]
	if !ok {
		return nil, fs.ErrNotExist
	}
	return f.Bytes(), nil
}

func TestGeneratorWrite(t *testing.T) {
	tests := []struct {
		name    string
		path    string
		data    []byte
		fs      *mockFS
		wantErr string
	}{
		{
			name:    "reject parent path",
			path:    "../report.md",
			data:    []byte("x"),
			fs:      &mockFS{},
			wantErr: "security error",
		},
		{
			name:    "reject absolute path",
			path:    "/tmp/report.md",
			data:    []byte("x"),
			fs:      &mockFS{},
			wantErr: "security error",
		},
		{
			name:    "create failure",
			path:    "report.md",
			data:    []byte("x"),
			fs:      &mockFS{createErr: errors.New("permission denied")},
			wantErr: "create output",
		},
		{
			name: "success",
			path: "report.md",
			data: []byte("hello"),
			fs:   &mockFS{},
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			g := report.NewGenerator(tc.fs)
			err := g.Write(tc.path, tc.data)
			if tc.wantErr != "" {
				if err == nil || !strings.Contains(err.Error(), tc.wantErr) {
					t.Fatalf("expected error containing %q, got %v", tc.wantErr, err)
				}
				return
			}
			if err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
			if got := tc.fs.files[tc.path].String(); got != string(tc.data) {
				t.Fatalf("wrote %q, want %q", got, string(tc.data))
			}
		})
	}
}
```

## Why `myfs.Stat` over direct `os.Stat` in app code

Using your own interface boundary means your package owns behavior and can evolve safely.

With a project-local wrapper (`myfs`, `deps`, `platform`, etc.), you can:

- enforce security or path policy centrally,
- add metrics/logging in one place,
- simulate errors in tests,
- migrate storage backends later,
- keep unit tests fast by default.

Direct `os.Stat` spread across the codebase makes all of that harder.

## Standard library test-friendly FS tools (larger examples)

### Example A: `fstest.MapFS` for read-only parser tests

```go
package parser_test

import (
	"io/fs"
	"testing"
	"testing/fstest"
)

func countGoFiles(fsys fs.FS) (int, error) {
	n := 0
	err := fs.WalkDir(fsys, ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if !d.IsDir() && len(path) > 3 && path[len(path)-3:] == ".go" {
			n++
		}
		return nil
	})
	return n, err
}

func TestCountGoFiles_MapFS(t *testing.T) {
	fsys := fstest.MapFS{
		"go.mod":        &fstest.MapFile{Data: []byte("module example.com/test\n")},
		"main.go":       &fstest.MapFile{Data: []byte("package main\n")},
		"pkg/a.go":      &fstest.MapFile{Data: []byte("package pkg\n")},
		"pkg/README.md": &fstest.MapFile{Data: []byte("docs\n")},
	}

	got, err := countGoFiles(fsys)
	if err != nil {
		t.Fatalf("countGoFiles failed: %v", err)
	}
	if got != 2 {
		t.Fatalf("got %d go files, want 2", got)
	}
}
```

### Example B: table-driven path filtering on `fstest.MapFS`

```go
func findMatching(fsys fs.FS, suffix string) ([]string, error) {
	var out []string
	err := fs.WalkDir(fsys, ".", func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			return nil
		}
		if strings.HasSuffix(path, suffix) {
			out = append(out, path)
		}
		return nil
	})
	return out, err
}

func TestFindMatching_MapFS(t *testing.T) {
	base := fstest.MapFS{
		"pkg/a.go":    &fstest.MapFile{Data: []byte("a")},
		"pkg/b_test.go": &fstest.MapFile{Data: []byte("b")},
		"notes.txt":   &fstest.MapFile{Data: []byte("x")},
	}

	tests := []struct {
		name   string
		suffix string
		want   int
	}{
		{name: "go", suffix: ".go", want: 2},
		{name: "test", suffix: "_test.go", want: 1},
		{name: "none", suffix: ".md", want: 0},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			got, err := findMatching(base, tc.suffix)
			if err != nil {
				t.Fatalf("findMatching failed: %v", err)
			}
			if len(got) != tc.want {
				t.Fatalf("len(got)=%d want=%d (%v)", len(got), tc.want, got)
			}
		})
	}
}
```

### Example C: real FS integration test with `t.TempDir`

```go
func TestCountGoFiles_Integration(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "main.go"), []byte("package main\n"), 0o644); err != nil {
		t.Fatalf("write main.go: %v", err)
	}
	if err := os.WriteFile(filepath.Join(dir, "README.md"), []byte("docs\n"), 0o644); err != nil {
		t.Fatalf("write README.md: %v", err)
	}

	got, err := countGoFiles(os.DirFS(dir))
	if err != nil {
		t.Fatalf("countGoFiles failed: %v", err)
	}
	if got != 1 {
		t.Fatalf("got %d, want 1", got)
	}
}
```

Use MapFS for most tests, then keep a smaller integration layer like this.

### Example D: `txtar` for multi-file fixtures

`golang.org/x/tools/txtar` is useful when you want many fixture files in one compact text blob and then expose them as an FS.

```go
ar := txtar.Parse([]byte(`-- go.mod --
module example.com/m
-- cmd/main.go --
package main
`))
// Convert archive to an fs.FS for parser/discovery tests.
```

## Same design for exec, sockets, and HTTP

This pattern is not file-system specific.

### Cleaner `execProxy` with embedded `Discoverer`

```go
type execProxy interface {
	Command(name string, arg ...string) *exec.Cmd
	LookPath(file string) (string, error)
}

type Discoverer struct {
	ExecCommand  func(name string, arg ...string) *exec.Cmd
	ExecLookPath func(file string) (string, error)
}

type realExecProxy struct{ Discoverer }

func newRealExecProxy() realExecProxy {
	return realExecProxy{Discoverer: Discoverer{
		ExecCommand:  exec.Command,
		ExecLookPath: exec.LookPath,
	}}
}

func (r realExecProxy) Command(name string, arg ...string) *exec.Cmd {
	return r.ExecCommand(name, arg...)
}

func (r realExecProxy) LookPath(file string) (string, error) {
	return r.ExecLookPath(file)
}
```

This keeps injection explicit without global mutable variables.

### Table-driven test for exec discovery

```go
type mockExecProxy struct {
	commandFn  func(name string, arg ...string) *exec.Cmd
	lookPathFn func(file string) (string, error)
}

func (m mockExecProxy) Command(name string, arg ...string) *exec.Cmd {
	return m.commandFn(name, arg...)
}

func (m mockExecProxy) LookPath(file string) (string, error) {
	return m.lookPathFn(file)
}

func TestDiscover_PathLookup(t *testing.T) {
	tests := []struct {
		name    string
		proxy   execProxy
		wantErr bool
	}{
		{
			name: "found",
			proxy: mockExecProxy{lookPathFn: func(file string) (string, error) {
				return "/mock/" + file, nil
			}},
		},
		{
			name: "missing",
			proxy: mockExecProxy{lookPathFn: func(file string) (string, error) {
				return "", exec.ErrNotFound
			}},
			wantErr: true,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			_, err := tc.proxy.LookPath("git")
			if tc.wantErr && err == nil {
				t.Fatal("expected error")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}
```

### Sockets and HTTP

Use the same idea for networking:

- inject a `Dialer` interface instead of hard-coding `net.Dialer`,
- use `net.Pipe()` or fake dialers in unit tests,
- use `httptest.NewServer` for controlled HTTP integration tests.

Many teams already do this with `httptest`; this article is about applying that same discipline consistently across all side effects.

## Copy-paste starters

### Starter 1: minimal FS wrapper + constructor injection

```go
package deps

import (
	"io"
	"io/fs"
	"os"
)

type FileSystem interface {
	Create(name string) (io.WriteCloser, error)
	Stat(name string) (fs.FileInfo, error)
}

type OSFS struct{}

func (OSFS) Create(name string) (io.WriteCloser, error) { return os.Create(name) }
func (OSFS) Stat(name string) (fs.FileInfo, error)      { return os.Stat(name) }
```

```go
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

### Starter 2: in-memory fake + table-driven test skeleton

```go
type nopCloser struct{ io.Writer }

func (nopCloser) Close() error { return nil }

type fakeFS struct {
	createErr error
	files     map[string]*bytes.Buffer
}

func (f *fakeFS) Create(name string) (io.WriteCloser, error) {
	if f.createErr != nil {
		return nil, f.createErr
	}
	if f.files == nil {
		f.files = map[string]*bytes.Buffer{}
	}
	buf := new(bytes.Buffer)
	f.files[name] = buf
	return nopCloser{Writer: buf}, nil
}

func TestService(t *testing.T) {
	tests := []struct {
		name    string
		fs      *fakeFS
		wantErr bool
	}{
		{name: "ok", fs: &fakeFS{}},
		{name: "create fails", fs: &fakeFS{createErr: errors.New("boom")}, wantErr: true},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			svc := NewService(tc.fs)
			err := svc.DoWork()
			if tc.wantErr && err == nil {
				t.Fatal("expected error")
			}
			if !tc.wantErr && err != nil {
				t.Fatalf("unexpected error: %v", err)
			}
		})
	}
}
```

### Starter 3: exec wrapper with explicit function injection

```go
type Exec interface {
	Command(name string, arg ...string) *exec.Cmd
	LookPath(file string) (string, error)
}

type RealExec struct {
	CommandFn  func(name string, arg ...string) *exec.Cmd
	LookPathFn func(file string) (string, error)
}

func NewRealExec() RealExec {
	return RealExec{CommandFn: exec.Command, LookPathFn: exec.LookPath}
}

func (r RealExec) Command(name string, arg ...string) *exec.Cmd { return r.CommandFn(name, arg...) }
func (r RealExec) LookPath(file string) (string, error)         { return r.LookPathFn(file) }
```

## Final guideline

If code touches the outside world, make that capability an interface dependency.

- production wires real implementations,
- most tests wire fake/in-memory implementations,
- a smaller integration suite verifies real behavior.

That balance gives fast tests, cleaner architecture, and safer refactoring.
