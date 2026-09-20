---
title: "The Scenario-Backed Middle Tier: Bridging Isolated Rendering and Full-Stack Verification"
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

While isolated, direct fixture rendering solves many presentation testing problems (as discussed in [Testing UI at the Seam: Programmable Verification Without the Full Stack]({{< ref "040-programmable-ui-verification-seams" >}})), it can become brittle when templates rely on numerous data-access functions or complex view-model construction logic. If you find yourself mocking dozens of repository methods just to render a template, you've lost the benefit of cheap verification.

On the other hand, booting a full HTTP server, authenticating, and navigating via browser automation is often too heavy.

There is a powerful middle ground: **Scenario-Backed Verification**.

## The Scenario-Backed Middle Tier

This tier introduces an explicit middle step between isolated template rendering and disposable full-server integration. It leverages the deterministic state definition of a scenario (described in [Scenarios as Executable Application State]({{< ref "046-scenarios-as-executable-application-state" >}})) to populate an in-memory repository or temporary database.

Instead of supplying isolated JSON data directly to the view, you:

1.  **Define a Scenario:** Use an executable state definition (e.g., `TXTAR` operations like `user.create`, `forum.post`) to represent domain intent.
2.  **Apply to Ephemeral Storage:** The scenario runner applies these operations to an in-memory repository or a disposable SQLite database.
3.  **Construct the Real View Model:** The real application logic queries this ephemeral storage to construct the complex view model.
4.  **Render the View:** The real template renders the view model.

### When to Choose the Middle Tier

Use this tier when:
*   The view relies heavily on application state that is tedious to construct via raw JSON fixtures.
*   The template executes domain-specific template functions (e.g., `{{ user_has_permission .User .Post }}`) that require a functional persistence layer.
*   You want stronger behavioural verification than isolated rendering, but without the overhead of HTTP routing and authentication middleware.

As established in [Testing UI at the Seam]({{< ref "040-programmable-ui-verification-seams" >}}), the principle is to choose the smallest verification surface that actually proves the requirement. If the view is a pure presentation component (e.g., a simple button or a card displaying literal text), stick to isolated rendering. However, do not imply a browser or HTTP test is inherently unnecessary when layout, JS, routing, cookie, or middleware behaviour is exactly what needs proving. The middle tier handles complex view models; the full server handles the network and browser layer.

## Composing Scenarios and Verification

Scenarios and verification views compose beautifully into a deterministic pipeline:

`scenario -> domain operations -> ephemeral storage -> normal query/view construction -> real renderer -> inspectable artifact`

Because the scenario explicitly defines time and sequential actions without relying on a full network stack, the output is highly deterministic. This allows you to assert against the output structure or use it as a reliable target for headless browser screenshots.

### Example: A Worked Middle-Tier Verification

Imagine verifying a forum topic view that relies on user roles. Creating a complex JSON fixture for the graph is error-prone. Instead, we use a scenario with fixed times to guarantee deterministic output:

```text
-- scenario.meta --
Format: forum-scenario/v1
Name: dense-topic

-- 01-topic.event --
Op: topic.create
Ref: general-discussion
Name: General Discussion
At: 2026-09-01T10:00:00Z

-- 02-user.event --
Op: user.create
Ref: alice
Role: moderator
At: 2026-09-01T10:05:00Z

-- 03-post.event --
Op: post.create
Ref: first-post
Topic: general-discussion
Author: alice
Body: Welcome to the forum.
At: 2026-09-01T10:10:00Z
```

The verification command then loads this scenario, initializes the ephemeral storage, executes the real `GetTopicViewModel` logic, and renders the result:

```go
// Illustrative pseudocode: initializing a scenario runner and rendering a view
func VerifyTopicView(scenarioPath string, topicRef string) ([]byte, error) {
    // 1. Initialize ephemeral storage and scenario runner
    // cspell:disable-next-line
    db := datastore.NewInMem()
    runner := scenario.NewRunner(db)

    // 2. Load and apply the scenario
    sc, err := scenario.ParseFile(scenarioPath)
    if err != nil {
        return nil, fmt.Errorf("parse scenario: %w", err)
    }

    if _, err := runner.Apply(context.Background(), sc); err != nil {
        return nil, fmt.Errorf("apply scenario: %w", err)
    }

    // 3. Resolve the target entity (assuming the API returns an error if missing)
    topicID, err := runner.ResolveRef("topic", topicRef)
    if err != nil {
        return nil, fmt.Errorf("resolve topic ref: %w", err)
    }

    // 4. Use real application logic to build the view model
    viewModel, err := app.GetTopicViewModel(context.Background(), db, topicID)
    if err != nil {
        return nil, fmt.Errorf("get view model: %w", err)
    }

    // 5. Render the real template
    var buf bytes.Buffer
    err = templates.ExecuteTemplate(&buf, "topic_view.html", viewModel)
    if err != nil {
        return nil, fmt.Errorf("execute template: %w", err)
    }

    return buf.Bytes(), nil
}
```

This output can then be asserted structurally in a test:
```go
// Example mechanical assertion
output, err := VerifyTopicView("testdata/dense-topic.txtar", "general-discussion")
if err != nil {
    t.Fatal(err)
}

if !bytes.Contains(output, []byte(`<span class="badge">Moderator</span>`)) {
    t.Error("expected moderator badge to be rendered")
}
```

This provides robust verification without a full HTTP stack.
