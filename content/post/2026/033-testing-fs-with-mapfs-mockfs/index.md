---
title: "Testing File Systems: How I use MockFS, MapFS, and SimpleFS in Go"
date: 2026-08-14T00:00:58Z
draft: false
tags: ["go", "testing", "fs", "mockfs", "mapfs", "txtar"]
categories: ["engineering", "go-patterns"]
---

When building tools in Go that interact heavily with the file system, having a solid strategy for testing those interactions is critical. Direct coupling to `os` functions like `os.MkdirAll` or `os.WriteFile` makes testing cumbersome and slow.

In this post, I want to detail how I approach this by designing minimal file system interfaces and using in-memory implementations like `MapFS` and `MockFS` for tests.

## The Core Idea: Define Minimal Interfaces

It is okay to use `fs.FS` as a parent interface. However, it is often too limited in its definition for tasks that require writing or manipulating files. We don't want to be typecasting for something we know is rather concrete. Because the interfaces and structs are usually defined close to the source, extreme genericness is unnecessary (especially when we aren't making a public library).

Instead, I define exactly what my code needs. For example, if a function needs to create directories, check if files exist, and write data, I might define a `WritableFS` (or `SimpleFS`):

```go
// WritableFS provides a minimal interface for file system operations needed by overlay init.
type WritableFS interface {
	MkdirAll(path string, perm os.FileMode) error
	Stat(name string) (os.FileInfo, error)
	WriteFile(name string, data []byte, perm os.FileMode) error
}
```

By passing `WritableFS` into the business logic, the production code can use a real OS-backed implementation, while tests can pass an in-memory mock.

## Production Implementation: The OS Wrapper

The production implementation is usually a simple wrapper around the `os` package that implements the required interface. Often, this wrapper is bound to a specific base directory to prevent accidental modifications outside the intended scope.

```go
type OSFS struct {
	baseDir string
}

func NewOSFS(baseDir string) *OSFS {
	return &OSFS{baseDir: baseDir}
}

func (fs *OSFS) MkdirAll(path string, perm os.FileMode) error {
	return os.MkdirAll(filepath.Join(fs.baseDir, path), perm)
}

func (fs *OSFS) Stat(name string) (os.FileInfo, error) {
	return os.Stat(filepath.Join(fs.baseDir, name))
}

func (fs *OSFS) WriteFile(name string, data []byte, perm os.FileMode) error {
	return os.WriteFile(filepath.Join(fs.baseDir, name), data, perm)
}
```

## Testing Implementation: MockFS and MapFS

For testing, I often use a `MockFS` that internally uses a map to store files in memory. This is similar to `testing/fstest.MapFS`, but often augmented to support writes (since `fstest.MapFS` is read-only).

```go
type MockFS struct {
	MapFS map[string]MockFileInfo
}

func NewMockFS() *MockFS {
	return &MockFS{MapFS: make(map[string]MockFileInfo)}
}

func (m *MockFS) MkdirAll(path string, perm os.FileMode) error {
	// For simple tests, we might just ignore directories or record them
	return nil
}

func (m *MockFS) Stat(name string) (os.FileInfo, error) {
	if fi, ok := m.MapFS[name]; ok {
		return fi, nil
	}
	return nil, os.ErrNotExist
}

func (m *MockFS) WriteFile(name string, data []byte, perm os.FileMode) error {
	m.MapFS[name] = MockFileInfo{
		name: name,
		Data: data,
		mode: perm,
	}
	return nil
}
```

And `MockFileInfo` might look like:

```go
type MockFileInfo struct {
	name string
	Data []byte
	mode os.FileMode
}

// ... implement os.FileInfo methods ...
```

### Why this approach?

1.  **Speed**: Tests run entirely in memory.
2.  **Isolation**: No accidental writes to the developer's disk.
3.  **Simplicity**: It's easy to assert on the final state of the file system by simply inspecting the `MapFS` map.

```go
func TestInitOverlay(t *testing.T) {
	fs := NewMockFS()

	// ... call the function under test ...
	InitOverlay(fs, args)

	// ... verify the results ...
	fileInfo, ok := fs.MapFS["profiles/repo_name"]
	if !ok {
		t.Fatalf("Failed to find profiles/repo_name")
	}
	if string(fileInfo.Data) != "expected content\n" {
		t.Errorf("Unexpected content")
	}
}
```

## Integrating with the Variadic Args Pattern

As discussed in [a previous post](/blog/post/2026/020-optional-dependency-injection-via-type-switched-variadic-args/), you can combine this approach with type-switched variadic arguments. This allows you to inject the `MockFS` during testing without changing the required parameters of your production functions, preserving backward compatibility.

```go
func InitOverlay(args OverlayInitArgs, ops ...any) error {
	var targetFs WritableFS = NewOSFS(cwd)

	for _, opt := range ops {
		switch o := opt.(type) {
		case WritableFS:
			targetFs = o
		}
	}

	// ... use targetFs ...
}
```

## Conclusion and Alternatives

Using small, targeted interfaces for file system operations, backed by robust memory implementations like `MockFS` for testing, creates a clean boundary between business logic and side effects.

It's worth mentioning that `txtar` can be a powerful substitute when there are a lot of files for the input and expected states. This is especially true if you use directory prefixes like `input/*.*` and `expected/*.*`, which allow for deep directory comparison. This approach also leaves the rest of the `/` namespace in the txtar file open for configuration, toggles, or metadata. Using two separate `.txtar` files for a single test is also perfectly acceptable, as you might reuse a common `input.txtar` file across multiple scenarios. Because `txtar` adheres to standard interfaces like `fs.FS` and `fs.ReadDirFS`, it integrates smoothly into this pattern.

Whether you are using `txtar` for complex test layouts (see [Txtar Patterns for Agents](/blog/post/2026/004-txtar-patterns-for-agents/)) or simple map-based filesystems for unit testing writes, abstracting the file system is a critical step towards maintaining a testable Go codebase.
