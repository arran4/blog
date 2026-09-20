---
title: "Verification Views"
date: 2026-09-20T07:42:01Z
draft: false
tags:
  - testing
  - ui
  - verification
  - architecture
  - llm
categories:
  - Software Architecture
  - Testing
---

Testing the user-visible output of an application is notoriously difficult. Unit tests assert logic but ignore presentation. End-to-end browser tests exercise presentation but are slow, flaky, and require booting massive amounts of infrastructure.

A **verification view** sits between these extremes. It is a cheap, fast way to exercise one real application representation—usually a real template, view, or widget—against a deliberate, known state without booting unrelated infrastructure.

## Three Levels of Verification

Verification views complement rather than replace one another across three distinct levels of isolation.

### 1. Direct Isolated Rendering

At the narrowest level, you render a view directly by supplying explicit view data or narrowly overriding specific dependencies (like template functions). This is surgical template testing. It is perfect for exercising deliberately impossible, incomplete, or component-specific states that are difficult to induce through normal application flow.

### 2. Scenario-Backed Verification

If numerous data-access functions must be replaced to render a view, mock-heavy isolated rendering becomes brittle. Instead, populate an in-memory repository or temporary database using a [scenario]({{< ref "048-scenarios-as-executable-application-state" >}}), and use the normal view-construction path. The real functions query the in-memory implementation. This provides stronger behavioural verification without the overhead of HTTP.

### 3. Disposable Full Server

When HTTP routing, authentication middleware, or session behaviour actually matters for the view being inspected, you boot a disposable full application server populated from the same scenario. The output is inspected, and the server is immediately torn down.

## Keep the Inspected Artifact Real

The core principle of a verification view is that the thing being inspected must remain real.

In a server-rendered application (like Go templates), this means using the real template tree, real partials and layouts, real template functions (where practical), and real view-model construction. Embedded templates should be the default, with external user-provided template directories acting as overlays. Prefer one template-loader architecture shared by the normal application and verification commands instead of divergent compilation paths.

If a rendering API requires a request context, providing a synthetic request or context is entirely acceptable. You do not need a complete HTTP server when HTTP itself is not under test.

## Named Cases as Shared Vocabulary

Verification views thrive on named cases: `empty`, `default`, `dense`, `edit`, `permissions`, `long-text`, `unicode`.

These named states become a powerful shared vocabulary for humans, continuous integration, and coding agents. A developer can quickly ask to see the `dense` state of the dashboard without manually clicking through a UI to generate dozens of records. Both built-in cases (compiled into the tool) and external input (via JSON files or scenario scripts) should be supported.

## Deterministic Output

For a verification view to be useful in automated testing, its output must be completely deterministic. Every run must produce identical bytes given identical input.

This requires controlling:
* **Clocks:** Time must be frozen or deterministically injected.
* **IDs:** Randomly generated IDs (UUIDs) must be replaced with sequential or seeded generators.
* **Sort Order:** Maps and database queries must return results in a guaranteed order.
* **Environment:** Locale, timezone, and volatile request data must be strictly controlled.

## Output Surfaces and Assertions

A verification command should support multiple output surfaces to serve different needs:

1. **Stdout / File Output:** Emitting the raw HTML or text artifact is fast and allows for trivial diffing in CI. HTML artifacts are useful CI outputs even without screenshots.
2. **Tiny Localhost Server:** Serving the view over a local port with static assets enables immediate human inspection and visual debugging.
3. **Headless Browser Screenshots:** Generating screenshots using a headless browser.

Crucially, **screenshots should sit above the verification mechanism** rather than forcing the harness itself to become browser automation. The verification view emits HTML; a separate, optional layer takes a picture of it.

When automating assertions against these outputs, prefer structural or semantic assertions (e.g., "does the DOM contain an element with this ID and text?") over brittle whole-document snapshot tests that fail whenever a CSS class changes.

## Composing Scenarios and Verification

Scenarios and verification views compose beautifully into a powerful pipeline:

`scenario -> domain operations -> memory persistence -> normal query/view construction -> real renderer -> inspectable artifact`

You feed a known, deterministic scenario into the system, execute real application logic, and verify the resulting real view.

## Generalising Beyond the Web

This concept is not limited to server-rendered web applications.
* In a **Flutter or desktop** application, a verification view is a real widget or screen mounted against seeded state in an isolated test harness.
* In a **terminal** application, it is a deterministic text screen dump.
* In a **report generator**, it is a PDF or document output.

The principle remains: expose one real representation of deliberate application state.

## LLM and CI Workflows

This architecture profoundly improves LLM-assisted development.

By documenting these tools in an `AGENTS.md` file or generating a custom skill, you can tell an agent exactly which named scenarios and verification views exist, how to render them, and which commands produce inspectable artifacts. An agent can modify a template, run the verification view command, and immediately read back the HTML or snapshot to confirm the change worked.

However, these exact same commands must be useful to humans. Do not invent an LLM-only parallel application; standardise on tools that benefit everyone.

## The Role of End-to-End Tests

Implementing fast, isolated verification views changes the appropriate role of end-to-end browser tests. E2E tests no longer need to exhaustively assert visual states or render every possible combination of data. Instead, leave HTTP and browser tests responsible for routing, cookies, authentication flows, form submissions, and genuine cross-layer behaviour. Let verification views handle the cheap, rapid rendering of rich states.
