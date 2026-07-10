---
title: "Txtar Test Systems in Practice: Iterating to Scale (v2)"
date: 2026-02-17T00:00:00+00:00
draft: false
tags: ["go", "testing", "txtar", "embed", "golden-files", "agents"]
categories: ["reference", "testing"]
---

I use `txtar` as a practical test and fixture format across multiple repositories.
In a [previous post](/blog/post/2026/004-txtar-patterns-for-agents/), I laid out my reference for how I expect agents (and future me) to structure and evolve txtar-based systems.

Since then, the approach has evolved, specifically when dealing with larger test suites and complex context mocking (like validating `fstab` entries against a mock `/proc/filesystems`). This post covers the iteration of these patterns to scale better, as demonstrated by recent pull requests.

## The Problem: The Monolithic Txtar

Initially, it's tempting to throw all cases into a single `fs.txtar` file:

```txt
-- proc_filesystems --
nodev	sysfs
	ext4
-- valid_fstab --
/dev/sda1 / ext4 defaults 0 1
-- invalid_fstab --
/dev/sda2 / zfs defaults 0 1
```

This works for a while, but as the number of rules and edge cases grows, this monolithic file becomes unreadable. A failure in one scenario requires hunting through a massive file.

## Iteration 1: Granular Files and `fs.WalkDir`

The most significant structural improvement is moving from a single `testdata/fs.txtar` to a directory of scenario-specific archives (`testdata/*.txtar`).

```text
testdata/
  fs_valid.txtar
  fs_invalid.txtar
  swap_valid.txtar
  swap_invalid.txtar
```

Instead of hardcoding a single file read, the test harness walks the directory, creating a distinct `t.Run` subtest for each `.txtar` file:

```go
//go:embed testdata/*.txtar
var testdataFS embed.FS

func TestRules(t *testing.T) {
    var cases []string
    err := fs.WalkDir(testdataFS, "testdata", func(p string, d fs.DirEntry, err error) error {
        if err != nil { return err }
        if d.IsDir() || !strings.HasSuffix(p, ".txtar") { return nil }
        cases = append(cases, p)
        return nil
    })
    // ...
    if err != nil {
        t.Fatalf("failed to walk testdata: %v", err)
    }
    sort.Strings(cases)

    for _, tc := range cases {
        tc := tc
        t.Run(strings.TrimSuffix(filepath.Base(tc), ".txtar"), func(t *testing.T) {
            raw, _ := testdataFS.ReadFile(tc)
            ar := txtar.Parse(raw)
            inputFS, expectedFS := SplitInputExpected(ar)
            // ... run assertions ...
        })
    }
}
```

This isolates failures to specific case files and makes it trivial for agents or humans to add new test cases without touching existing ones.

## Iteration 2: Sane Defaults and Fallbacks

In systems that rely on external context (like reading system configuration files), requiring every `.txtar` file to redefine the exact same mock data creates massive boilerplate.

If 90% of our tests use the same `/proc/filesystems` mock, we shouldn't force the fixture to include it. Instead, the test harness should supply a fallback if the fixture omits it:

```go
// Pre-fill cache (mocking the OS interaction)
c := rules.NewCache()
procData, err := fs.ReadFile(inputFS, "proc/filesystems")
if err != nil {
    // Fallback to a sane default if the test doesn't override it
    procData = []byte("nodev\tsysfs\nnodev\ttmpfs\nnodev\tproc\n\text3\n\text4\n\tsquashfs\n\tvfat\n")
}
```

Now, a standard valid case can be incredibly concise:

```txt
test: valid swap partition entry

Ensures that correctly formatted swap fstab entries pass validation.
-- input/etc/fstab --
UUID=ccd57c54-3caf-47ba none swap defaults 0 0
```

## Iteration 3: Descriptive Assertions and Implicit Success

When adopting the `expected/` tree structure, avoid generic names like `expected/output.txt`. If your tool outputs validation errors, name the expectation `expected/validationerrors.txt`. This makes the intent of the golden file immediately clear without opening it.

Furthermore, we can leverage implicit success assertions. If `expected/validationerrors.txt` is missing from the `.txtar` archive, the test harness should assume *zero* validation errors were expected:

```go
wantOutputBytes, err := fs.ReadFile(expectedFS, "validationerrors.txt")
if err != nil {
    if errors.Is(err, fs.ErrNotExist) {
        // No expected output provided, meaning it should be valid
        if len(allSuggestions) > 0 {
            t.Fatalf("expected valid entry to have no suggestions, got %v for file %s", allSuggestions, tc)
        }
    } else {
        t.Fatalf("unexpected error reading expected output: %v", err)
    }
} else {
    // Expected output provided, assert against it
    // ...
}
```

This drastically reduces the footprint of "happy path" tests, keeping fixtures focused strictly on the unique behavior they are verifying.

## Final Thoughts

The core philosophy remains the same: parse once, convert to an in-memory `fs.FS`, and use `t.Run`. By iterating on the harness to support granular files, default fallbacks, and implicit success, we create a testing system that scales effortlessly as the number of features and agent-authored scenarios grows.
