---
title: "The `go test -update` Convention for Golden Files"
date: 2026-08-14T02:27:49Z
draft: false
tags: ["go", "testing", "golden-files", "txtar", "fs", "agentic-coding"]
categories: ["engineering", "go-patterns"]
---

`go test ./... -update` is a common **golden-test update convention**, but `-update` is **not built into `go test`**. The repository's test code defines that flag and uses it to decide whether to compare against or overwrite `.golden` files.

A typical implementation looks like:

```go
var update = flag.Bool("update", false, "update golden files")

func TestSomething(t *testing.T) {
    got := generateOutput()

    golden := "testdata/example.golden"

    if *update {
        if err := os.WriteFile(golden, got, 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(golden)
    if err != nil {
        t.Fatal(err)
    }

    if !bytes.Equal(got, want) {
        t.Errorf("output differs from golden file")
    }
}
```

So normally:

```bash
go test ./...
```

does approximately:

```text
generate current output
        │
        ▼
read testdata/foo.golden
        │
        ▼
compare expected ↔ actual
        │
        ├── same → PASS
        └── different → FAIL
```

Whereas:

```bash
go test ./... -update
```

does:

```text
generate current output
        │
        ▼
write output → testdata/foo.golden
        │
        ▼
golden file now represents the new expected output
```

### Why `-update` reaches the tests

Go's test binary accepts flags registered by the test package. For example:

```go
var update = flag.Bool("update", false, "update golden files")
```

When you run:

```bash
go test ./... -update
```

`go test` builds each package's test binary and effectively invokes it with the relevant test arguments. The registered `update` flag is then available as:

```go
*update
```

inside the tests.

Sometimes you'll instead see:

```bash
go test ./... -args -update
```

`-args` explicitly says "everything after this goes to the generated test binary." For a flag that `go test` doesn't itself consume, the shorter:

```bash
go test ./... -update
```

often works as well.

### More realistic golden-test pattern

Many projects have a helper along these lines:

```go
func golden(t *testing.T, name string, got []byte) {
    t.Helper()

    filename := filepath.Join("testdata", name+".golden")

    if *update {
        if err := os.WriteFile(filename, got, 0644); err != nil {
            t.Fatal(err)
        }
    }

    want, err := os.ReadFile(filename)
    if err != nil {
        t.Fatal(err)
    }

    if diff := cmp.Diff(string(want), string(got)); diff != "" {
        t.Errorf("golden mismatch (-want +got):\n%s", diff)
    }
}
```

Then tests simply do:

```go
func TestRender(t *testing.T) {
    got := renderSomething()
    golden(t, "render_something", []byte(got))
}
```

Running:

```bash
go test ./... -update
```

regenerates:

```text
testdata/render_something.golden
```

from `renderSomething()`.

The important implication is that **the test implementation itself is the generator**. There usually isn't a separate `.golden` generation program. `-update` just switches the assertion helper from roughly:

> "compare this result with the checked-in expected result"

to:

> "make this result the new checked-in expected result."

If you're asking about one of your particular GitHub repos, I can trace the exact `-update` implementation and show precisely which code generates each `.golden` file.

### Integrating with `fs.FS` and `txtar`

When working with more complex testing scenarios—especially involving file system abstractions (`fs.FS`) and the `txtar` format for multi-file fixtures—the `-update` convention remains powerful.

Instead of reading and writing individual `.golden` files from disk, you can use `-update` to rewrite the actual `.txtar` archives that serve as your test inputs and expected outputs.

For instance, if your tests use `fs.WalkDir` over a structured directory of `txtar` test cases, and inject an in-memory `MapFS` or `MockFS` for the code under test to operate on, you can capture the resulting virtual filesystem state. If `-update` is true, you can bundle that in-memory state back into the `txtar` archive format and write it back out to the real `testdata/` directory, updating the expected files inline.

This aligns perfectly with agentic coding practices by ensuring complex inputs and expected outputs are clearly defined and easily regenerated, while the actual testing logic remains isolated through `fs.FS` interfaces rather than coupled to `os` functions.
