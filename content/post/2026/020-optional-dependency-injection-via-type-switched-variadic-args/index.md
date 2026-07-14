---
title: "Go Memory FSs Everywhere in Test: Optional Dependency Injection via Type-Switched Variadic Args"
date: 2026-07-11T13:03:55+10:00
draft: false
tags: ["go", "testing", "architecture", "patterns", "memory-fs", "api-design", "options-pattern"]
categories: ["engineering-process", "reference"]
---

If your Go code calls `os.Create`, `os.Stat`, `exec.LookPath`, or `net.Dial` directly from business logic, your tests are forced to touch real side effects more often than necessary.

The core pattern in this space is simple:

1. Define small interfaces for side effects.
2. Inject real implementations in production.
3. Inject in-memory fakes or standard library memory file systems in tests.

This is why I encourage `myfs.Stat("file.txt")` (or whatever your project names it) over direct `os.Stat("file.txt")` in your core application code. In-memory file systems provide deterministic, fast execution for testing.

However, **there is a trap here when relying on agents to implement this.**

## The Problem: Agents Break Existing Call Sites

When an AI agent is tasked with injecting an `fs.FS` or a custom interface (like `fsys.FS`) into an existing core function, its default instinct is to add it as a required parameter:

```go
// Before
func ReadFile(fType string, fName string) ([]byte, error) { ... }

// After (Agent's typical approach)
func ReadFile(fs fsys.FS, fType string, fName string) ([]byte, error) { ... }
```

When applied across a mature project, this completely shatters backward compatibility. Suddenly, you have to correct dozens of call sites across your production code, injecting `fsys.OSFS{}` manually, rather than just leaving the agent to merge it. The agent solved the testing problem but created a massive refactoring headache.

## The Solution: Optional Dependency Injection via Type-Switched Variadic Args

Instead of forcing a hard dependency change on all callers, we can combine the memory FS pattern with the **type-switched variadic options system** I described in [an earlier post](/blog/post/2026/001-type-switched-variadic-system/).

By leveraging `ops ...any`, we can make the file system injection *optional*. If a custom FS is provided, we use it. If not, we default to the standard OS file system. Call sites remain completely untouched, while test systems can still overwrite the defaults.

### Refactoring to Optional Injection

Let's look at how we adapt the core `ReadFile` function to use this pattern:

```go
package dataformats

import (
	"fmt"
	"os"
	"myapp/fsys" // Your custom FS interface package
)

// ReadFile wrapper with optional FS injection.
func ReadFile[T any](fType string, fName string, next Next[T], ops ...any) (res []T, err error) {
	// 1. Set the default production implementation
	var fs fsys.FS = fsys.OSFS{}

	// 2. Interpret optional overrides
	for _, opt := range ops {
		switch o := opt.(type) {
		case fsys.FS:
			fs = o
		// ... handle other options ...
		}
	}

	// 3. Use the injected (or default) FS
	f, err := fs.OpenFile(fName, os.O_RDONLY, 0644)
	if err != nil {
		return nil, fmt.Errorf("reading %s %s: %w", fType, fName, err)
	}
	defer f.Close()

	return next(f, fType, fName, ops...)
}
```

### Why this is better for humans and agents

1. **Zero changes to existing production code:** `ReadFile("csv", "data.csv", parser)` continues to compile and work exactly as before, defaulting to `fsys.OSFS{}`.
2. **Easy for tests to override:** In your unit tests, you simply pass the mock or memory FS: `ReadFile("csv", "data.csv", parser, myMockFS)`.
3. **Agent friendly:** When you instruct an agent to make a function testable, explicitly telling them to use the type-switched variadic pattern prevents them from breaking the entire call graph.

## Why memory file systems matter for switching implementations

The key benefit is **switchability without refactoring call sites**.

If your code is hard-coded to `os.*`, switching behavior later is expensive. If your code depends on an interface, switching is just wiring. Using an in-memory file system like `fstest.MapFS` makes testing simpler.

- production: use real OS-backed implementation,
- unit tests: use in-memory fake,
- integration tests: use real disk with temp dirs,
- special tools: use embedded FS or `fstest.MapFS`.

This gives you speed today and flexibility later.

## Why most (but not all) tests should use memory file systems

You usually want:

- **many unit tests** with no real FS/network/process calls by using in-memory implementations,
- **fewer integration tests** that validate real FS and OS behavior,
- **a small number of end-to-end tests** for full confidence.

This split gives better feedback loops:

- fast local iteration,
- fewer flaky tests,
- better coverage of failure branches,
- still keeping real-world verification where it matters.

So this is not "never touch the file system." It is "use real side effects intentionally, and memory file systems by default."

## Wrapping Up

If code touches the outside world, make that capability an interface dependency. But when introducing those dependencies into mature codebases, use optional type-switched variadic arguments.

It keeps your production call sites clean, keeps your tests fast and deterministic, and ensures agents don't create unnecessary refactoring busywork for you.
