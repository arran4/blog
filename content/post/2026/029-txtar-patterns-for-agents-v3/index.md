---
title: "Txtar Test Systems in Practice: Iterating to Scale (v3)"
date: 2026-07-29T10:00:00Z
draft: false
tags: ["go", "testing", "txtar", "embed", "golden-files", "agents", "fs", "fstest"]
categories: ["engineering-process", "reference"]
---

Testing software that relies heavily on filesystem interactions often leads to fragile tests full of boilerplate mock setups or real disk I/O side effects. Over the past few iterations, I've standardized my approach across repositories using `fs.FS` and `txtar`.

This iteration combines past lessons into a comprehensive guide on making maximum use of `fs.FS` for robust, readable, and scalable testing—whether using `txtar` for complex scenarios, `fstest.MapFS` for simple mocks, or `go:embed` for straightforward file pairing.

## Make Maximum Use of `fs.FS`

The `txtar` format (`golang.org/x/tools/txtar`) packs multiple files into a single plain-text blob. This is excellent for defining test fixtures. But the real power comes from converting these `txtar` archives or raw files into an `fs.FS` interface.

By implementing `fs.FS`, `txtar` can be combined with commands like `fs.Sub` (which creates a sub-filesystem scoped to a prefix directory). This enables incredibly clean separation of test inputs and expected outputs.

For instance, rather than manually string matching file prefixes, you can define your archive with `input/` and `expected/` directories:

```go
func SplitInputExpected(ar *txtar.Archive) (input fs.FS, expected fs.FS, err error) {
	// First, convert the archive to a virtual filesystem (e.g., using fstest.MapFS)
	baseFS := ArchiveToMapFS(ar)

	input, err = fs.Sub(baseFS, "input")
	if err != nil {
		// handle missing input directory appropriately
	}

	expected, err = fs.Sub(baseFS, "expected")
	if err != nil {
		// handle missing expected directory
	}

	return input, expected, nil
}
```

This pattern isolates failures and clarifies exactly what files the system under test receives and what it should emit.

### Combining with Variadic Dependency Injection

When your business logic accepts an `fs.FS` via dependency injection, testing becomes trivial. I heavily favor [Optional Dependency Injection via Type-Switched Variadic Args]({{< ref "020-optional-dependency-injection-via-type-switched-variadic-args" >}}).

```go
// Your core function accepts variadic options, injecting the test FS
err := processDirectory("some/path", WithFileSystem(inputFS))
```

This ensures your production code uses `os.DirFS` while tests use your isolated, hermetic virtual filesystems without cluttering the function signature.

## fstest.MapFS is Highly Viable Too

While `txtar` is fantastic for scenarios with multiple files and complex multi-line strings, it isn't always strictly necessary.

If the files you need to mock are all empty (e.g., you're just testing directory structure, file discovery, or parsing package names from paths), `fstest.MapFS` is simpler and more concise. There's no need to invoke `txtar` if there aren't multiline string payloads.

```go
mockFS := fstest.MapFS{
    "app-misc/goreleaser-bin/goreleaser-bin-2.17.0.ebuild":    {},
    "app-misc/goreleaser-bin/goreleaser-bin-2.17.0-r1.ebuild": {},
    "app-misc/goreleaser-bin/goreleaser-bin-2.17.0-r3.ebuild": {},
    "app-misc/goreleaser-bin/goreleaser-bin-2.17.0-r2.ebuild": {},
    "app-misc/goreleaser-bin/goreleaser-bin-1.0.0.ebuild":     {},
    "app-misc/goreleaser-bin/metadata.xml":                    {},
}
```

This immediately provides an `fs.FS` implementation mimicking a complex directory tree with zero boilerplate.

## `go:embed` into `testdata/` is Fine

For very simple tests—such as those where only a single input file and a single output file are tested—don't over-engineer. Under these circumstances, simply using `go:embed` to pull files directly from a `testdata/` directory is perfectly fine.

```go
//go:embed testdata/simple_input.txt
var simpleInput []byte

//go:embed testdata/simple_expected.txt
var simpleExpected []byte
```

Keep your tooling proportional to the complexity of the test. When test scenarios scale to require multiple contextual files, that's when you upgrade to `txtar`.

## Layering is Important for Large Test Suites

If you are writing extensive tests emulating a file system, and a lot of the `txtar` archives share similar files (like standard OS config files, default headers, or baseline setups), repetition wastes space and makes updates tedious.

Layering is an important strategy here. You can create a base `fs.FS` or `txtar` implementation that acts as a fallback.

When your test harness reads a requested file, it first checks the specific test case's filesystem. If the file is absent (yielding `fs.ErrNotExist`), it falls back to querying the base filesystem. This drastically reduces the size of the repository and centralizes updates to common mock files.

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

## Diffs and Comparisons

Writing custom diff logic is important to understand your test failures, but for serious systems, consider using established solutions like `https://github.com/golang-diff` or similar libraries (e.g., `github.com/google/go-cmp/cmp`).

Good diffing libraries provide context, highlighting exactly which line or character failed, which is invaluable when parsing multi-line `txtar` outputs or generated files. Do not reinvent the wheel for standard unified diff outputs.

## Acknowledging `\n` and `\r\n` Differences in Tests

A critical and often overlooked aspect of filesystem testing—especially when comparing expected strings or golden files—is handling line endings.

To prevent cross-platform issues (where a test passes on a Linux CI server but fails on a developer's Windows machine), you must actively acknowledge and normalize `\n` and `\r\n` differences.

When reading expected outputs or test data payloads, normalize the strings before comparison:

```go
func normalizeNewlines(d []byte) []byte {
    // Replace CRLF with LF
    return bytes.ReplaceAll(d, []byte("\r\n"), []byte("\n"))
}
```

Always normalize both the generated output and the expected golden file data before running your diff assertions. This guarantees that your tests remain deterministic regardless of the host operating system's native line endings or git checkout configuration (e.g., `core.autocrlf`).

## Conclusion

By strategically selecting between `fstest.MapFS`, raw `go:embed`, and structured `txtar` archives—and binding them all together with `fs.FS` and smart dependency injection—you create a testing environment that is both hermetic and highly scalable.

Combine these structural patterns with sane fallback layering, robust third-party diffing, and strict line-ending normalization, and your filesystem-heavy tests will become a rock-solid foundation rather than a source of flakiness. Search my public GitHub repository (`github.com/arran4`) for extensive real-world examples and implementations of these patterns.
