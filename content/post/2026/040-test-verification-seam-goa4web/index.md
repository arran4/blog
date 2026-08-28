---
title: "Testing UI at the Seam: goa4web's Verification Tool"
date: 2026-08-28T11:24:33Z
draft: false
tags: ["go", "testing", "goa4web", "hugo", "ai-agents"]
categories: ["Software Engineering", "Agent Instructions"]
---

When testing server-rendered web applications, there's a common trap: relying on full end-to-end browser automation (like Selenium or Playwright) to verify simple presentation logic. If you want to know how a page renders when a user has no permissions, you often have to spin up a database, migrate it, create a user, navigate to the page, and then assert against the DOM.

This is slow, brittle, and introduces a massive amount of unrelated state (database connections, routing, session management) just to answer a simple question: *Does this HTML template render correctly?*

In `github.com/arran4/goa4web`, we use a dedicated utility to solve this: the `test verification template` command. It is designed to provide a small, programmable verification seam into the application's presentation layer.

## What `test verification template` is for

The `goa4web test verification template` command is not just a template previewer; it makes the application's output directly addressable from the command line. Both humans and automated coding agents can cheaply construct a state, render it, inspect the result, and repeat the process without the overhead of starting the full application stack.

### The Principle: Verify State over Recreating History

When testing presentation, ask yourself: *Do I need to prove the process which creates this state, or do I need to prove how this state is presented?*

If a handler eventually produces `Data{ CanEdit: true }`, you don't need to log in, grant permissions, and navigate through the app just to cause `CanEdit == true`. You can simply inject that state directly into the template and verify the rendering.

This creates a clear hierarchy for UI testing:

1. **Go Unit Tests:** Did the application calculate the state correctly?
2. **`test verification template`:** Does that state render correctly?
3. **Browser Automation:** Does behavior requiring a real browser (clicks, DOM mutations, client-side routing) work correctly?

## How it Works

The command takes a template file and a JSON data fixture as input:

```bash
goa4web test verification template -template forum/threadPage.gohtml -data /tmp/thread.json
```

### JSON Hydration and `Dot`

The JSON fixture allows you to specify the exact environment for the render, specifically the `Dot` field, which maps to the `.` context inside the Go template.

```json
{
  "Dot": {
    "Title": "Hello World",
    "IsAdmin": true
  },
  "Config": {},
  "URL": "http://localhost/...",
  "User": {}
}
```

The tool automatically normalizes types (like converting RFC3339 strings to `time.Time` and JSON numbers to `int32`), making it easy to mock database structures.

### Mock Database and Real Templates

Crucially, the tool isolates the template from the database using a `QuerierStub`. However, it doesn't isolate the template from the rest of the application's presentation logic. It uses the real `CoreData` functions (for things like CSRF tokens and formatting) and compiles *all* `.gohtml` site templates together. This ensures that while the test is targeted, it still catches syntax or definition errors across the broader template set.

## Output Modes

The tool supports three primary output modes, making it incredibly versatile:

1. **Stdout (`stdout`)**: Writes the raw HTML to the console. This is perfect for programmatic assertions (e.g., `grep`-ing for specific IDs or piping to an HTML parser).
2. **File Output (`-output /tmp/result.html`)**: Saves the rendered HTML to a file, useful for snapshot testing, diffs, or manual inspection.
3. **Local Server (`-listen :8080`)**: Starts a lightweight HTTP server serving the rendered template alongside the site's static assets (CSS, JS). This is ideal for visual inspection in a browser.

## Why it's Better for Humans

For developers, this approach drastically reduces iteration time. Instead of rebuilding, restarting, and manually navigating an application, you can create a suite of JSON fixtures representing different edge cases (anonymous user, admin, empty list, very long strings) and render them instantly.

## Why it's Better for AI Agents

Agents thrive on deterministic, fast, and programmable feedback loops. Browser automation introduces flakiness (timing issues, stale selectors, unexpected redirects) that can confuse an agent.

By using `test verification template` and asserting against the output programmatically, agents can verify UI changes locally and reliably. They can generate a JSON fixture, run the tool, assert the output, and iterate—all within a shell script, without touching a browser.

Even when JavaScript is involved, if the script relies on server-rendered data attributes or IDs, this tool can verify those hooks are present, significantly reducing the surface area that actually requires a full browser test.

## Conclusion

By treating templates as functions that take state as input, `goa4web` allows for rapid, isolated, and highly deterministic UI testing. It forces developers and agents alike to think critically about what exactly needs testing, reserving the heavy machinery of browser automation only for genuine client-side interactions.
