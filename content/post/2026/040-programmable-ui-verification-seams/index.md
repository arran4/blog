---
title: "Testing UI at the Seam: Programmable Verification Without the Full Stack"
date: 2026-08-28T11:24:25Z
draft: false
tags: ["testing", "ui", "automation", "architecture", "ai-agents"]
categories: ["Software Engineering"]
---

When testing server-rendered web applications, there is a common trap: relying on full end-to-end browser automation (like Selenium or Playwright) to verify simple presentation logic. If you want to know how a page renders when a user has no permissions, you often have to spin up a database, migrate it, insert seed data, authenticate a user, navigate to the page, and then assert against the DOM.

This is slow, brittle, and introduces a massive amount of unrelated state (database connections, routing, session management) just to answer a simple question: *Does this HTML template render correctly?*

The solution is to build a **programmable verification seam** into the application's presentation layer. This turns the problem of UI verification from "recreate a complex history to arrive at a state" into "inject a state and assert the output."

## What is a Verification Seam?

A web application's presentation layer is normally buried behind many unrelated mechanisms:

```text
database → migrations → seed data → authentication → permissions → routing → handler → view model → template → browser
```

If the question being asked is: *Does this state render correctly?* we should ideally have a seam which allows us to enter closer to the end of the pipeline:

```text
view state → template → output
```

This is not claiming the other layers do not need tests. It is about separating the questions:

1. **Did business/handler code calculate the state correctly?** → Unit/handler/integration test
2. **Does that state render correctly?** → Verification seam
3. **Does browser execution behave correctly?** → Browser test

The guiding principle is: **Prefer verification of state over recreation of history when the history itself is not what is under test.**

However, avoid presenting browser automation as a "last resort." The better rule is: **Use the smallest verification surface which genuinely proves the requirement.** If something really requires browser layout, JavaScript execution, focus, keyboard behavior, DOM mutation, or browser APIs, then a browser test is exactly the right tool.

## Concrete CLI Examples

A good verification seam is often exposed as a CLI tool. This makes it addressable, scriptable, and highly useful for both humans and autonomous coding agents. Let's look at a hypothetical CLI, `myapp verify template`, to see how this works in practice.

### Basic Rendering and Assertions

You can render a specific template using a JSON fixture for data:

```bash
myapp verify template \
  --template templates/profile.html \
  --data fixtures/profile.json
```

Stdout might look like this:

```html
<section class="profile">
  <h1>Alice</h1>
  <a class="edit" href="/profile/edit">Edit profile</a>
</section>
```

Because it outputs to stdout, mechanical verification is trivial:

```bash
myapp verify template \
  --template templates/profile.html \
  --data fixtures/editor.json |
  grep -q 'class="edit"'
```

And negative assertions are just as easy:

```bash
if myapp verify template \
    --template templates/profile.html \
    --data fixtures/anonymous.json |
    grep -q 'class="edit"'
then
    echo "anonymous user unexpectedly received edit controls" >&2
    # exit 1
fi
```

*(Note: For complex structural assertions, an HTML parser is preferable to accumulating fragile `grep` checks.)*

### Output to a File (Snapshot Testing)

You can output the result to a file:

```bash
myapp verify template \
  --template templates/profile.html \
  --data fixtures/editor.json \
  --output /tmp/profile.html
```

This enables easy diffing against a "golden" snapshot:

```bash
diff -u testdata/profile.golden.html /tmp/profile.html
```

### HTTP Fixture Server

Sometimes you need to inspect the rendering visually or run a targeted browser script against a known state. The CLI can spin up a local server:

```bash
myapp verify template \
  --template templates/profile.html \
  --data fixtures/editor.json \
  --listen 127.0.0.1:8080
```

```bash
curl -fsS http://127.0.0.1:8080/
```

This server can also expose CSS, JS, and static assets. Crucially: **a fixture HTTP server is not a browser test runner.** It simply serves the static output of the template given a specific state. A browser *may* be pointed at it if browser execution is needed.

### stdin and Ad-Hoc Input

Allowing `-` for input makes the verifier highly scriptable and composable:

```bash
cat <<'JSON' | myapp verify template --template templates/profile.html --data -
{
  "Page": { "Title": "Example" },
  "Permissions": { "CanEdit": true }
}
JSON
```

Or generating input dynamically with tools like `jq`:

```bash
jq -n \
  --arg name "Alice" \
  '{User:{Name:$name}, Permissions:{CanEdit:true}}' |
  myapp verify template --template templates/profile.html --data -
```

This dynamic generation is why a CLI interface is especially useful to autonomous coding agents.

## The Input/Data Contract

How does a human or agent know what data the renderer requires? The data contract is one of the most important parts of a verification seam.

### Typed Input Structure

In strongly typed languages like Go, prefer a documented typed boundary:

```go
type VerificationInput struct {
    Page        PageData        `json:"page"`
    User        *UserData       `json:"user,omitempty"`
    Permissions PermissionsData `json:"permissions"`
    Request     RequestData     `json:"request"`
    Config      ConfigData      `json:"config"`
}
```

The alternative is dynamic data (like `map[string]any`). While flexible, it has poorer discoverability and weaker type checking.

### Sane Defaults

A useful verifier should not require a 200-line fixture to render a simple case. An input like `{"Page": {"Title": "Hello"}}` should rely on sane, deterministic defaults: an anonymous user, a `GET /` request, localhost base URL, a fixed timezone, and empty collections.

Expose these defaults so users and agents can inspect them:

```bash
myapp verify template --show-defaults
```

### Machine-Readable Schema

Exposing the contract directly via JSON Schema or similar mechanisms is incredibly helpful, especially for agents:

```bash
myapp verify template --schema
myapp verify template --example-data
```

If your language supports it, generate this schema directly from the canonical types to prevent documentation drift.

### Helpful Errors

Design the verifier for automation. Instead of a generic "template execution failed," provide actionable errors:

```text
input.permissions.canEdit: expected boolean, got string
template profile.html requires .User.Name but User is null
```

## Layered/Merged Fixture Documents

Rather than duplicating complete fixtures for every possible permutation (`anonymous.json`, `admin.json`, `admin-empty.json`), allow composition:

```bash
myapp verify template \
  --data fixtures/base.json \
  --data fixtures/users/alice.json \
  --data fixtures/roles/admin.json \
  --data fixtures/states/empty.json \
  --template templates/list.html
```

Documents are merged left-to-right. For example:

`base.json`:
```json
{
  "Request": { "URL": "http://localhost/" },
  "User": null,
  "Permissions": { "CanEdit": false, "CanDelete": false },
  "Items": []
}
```

`admin.json`:
```json
{
  "User": { "ID": 42, "Name": "Alice" },
  "Permissions": { "CanEdit": true, "CanDelete": true }
}
```

This creates reusable concepts (personas, roles, page states) without combinatorial explosion.

**Crucially, you must precisely define the merge semantics.** Are objects recursively merged? Does `null` mean "set to null" or "remove inherited value"? Using an established representation like JSON Merge Patch or JSON Patch can avoid inventing ambiguous behavior.

You might also support one-off overrides via flags:

```bash
myapp verify template --data fixtures/base.json --set Permissions.CanEdit=true
```

## Implementing the Verifier

To build this, the architectural goal is to construct a renderer that uses enough **real production presentation code** to be meaningful, while replacing unrelated infrastructure.

Conceptually, in Go:

```go
type Renderer interface {
    Render(ctx context.Context, name string, data VerificationInput) ([]byte, error)
}

func runVerify(r Renderer, opts Options) error {
    input, err := loadInput(opts.DataFiles)
    // ...
    output, err := r.Render(context.Background(), opts.Template, input)
    // ...
    _, err = opts.Output.Write(output)
    return err
}
```

This renderer should use the real template loader, real template functions, real URL generation, and real escaping behavior. But it should use a stub database, a synthetic request, a fake authenticated identity, a fixed clock, and make no network calls.

Dependency injection is the key enabling technique:

```go
Dependencies{
    Users: NewStubUserStore(), // Stubbed
    Clock: FixedClock(...),    // Stubbed
    Mail:  DiscardMailer{},    // Stubbed
}
```

A good testing seam often emerges naturally from good dependency boundaries.

## Implementation Architectures

A subcommand on the main binary (`myapp verify template`) isn't the only approach.

*   **Dedicated verification binary (`ui-verify`):** Small, purpose-built, with strict no-production-side-effects guarantees.
*   **Library plus thin CLI (`verification.Render(...)`):** Puts the logic in a reusable package so both Go test suites and the CLI can call it.
*   **Test harness / golden generator:** A Go test helper that renders fixtures directly (`RenderFixture(t, "profile", "fixtures/admin.json")`).
*   **Fixture HTTP server:** A development server that exposes URLs like `/__verify/profile/admin` for manual visual review.

## Single-Template vs. Template-Set Verification

When implementing, you must decide how to compile templates:

1.  **Parse only the selected template:** Maximally targeted and fast, but may miss broken shared definitions or partials.
2.  **Compile the complete template set:** Detects cross-template parse/definition problems and reflects production composition, but one unrelated broken template can prevent targeted verification.

A sophisticated implementation might offer flags (`--compile target` vs. `--compile all`), or simply choose one and document it clearly.

## Benefits for Humans, CI, and Agents

The benefits go far beyond just saving CPU time:

*   **Tighter Feedback Loop:** Radically faster edit/verify cycles.
*   **Reduced Coordination Complexity:** Less infrastructure startup and fewer unrelated failure modes.
*   **Easier Reproduction:** Explicit and shareable edge states.
*   **Local Diagnosis:** Failures are highly localized.
*   **Parallel Execution:** Agents and CI don't need to compete for application/database/browser state.
*   **Agent Efficiency:** Lower token/tool overhead for agents because outputs are textual, structured, and deterministically generated.

## Limitations and Safety

This pattern does not replace all tests. It has specific limitations:

*   **Synthetic Impossible States:** A fixture can describe a state the real application could never produce. Handler/domain tests are still needed to prove state *construction*.
*   **Mock Drift:** Stubs can diverge from real infrastructure. Keep the seam narrow.
*   **Doesn't Prove Routing:** It doesn't prove a real HTTP request can reach that state.
*   **Doesn't Execute a Browser:** Static output cannot establish JavaScript event behavior, DOM mutations, or real layout.
*   **Fixture Maintenance:** Large JSON fixtures become difficult to maintain without schemas, defaults, and layered composition.

**Safety is paramount.** The verifier should not connect to production services, mutate real databases, send emails, or make arbitrary network calls.

## JavaScript Substitution

JavaScript being present does not automatically require browser automation. If server output is:

```html
<button id="delete-42" data-item-id="42" data-target="#item-42">Delete</button>
```

A verification seam can prove the button exists, the IDs are correct, and the target is correct. A browser test is then *only* needed to prove that clicking it triggers the expected JavaScript event and network behavior. This substantially shrinks the browser test's responsibility.

## Making it Discoverable to Coding Agents

Once a repository has a verification seam, you shouldn't have to prompt an AI agent to use it every time.

### `AGENTS.md`

Put a concise rule in the repository's `AGENTS.md` file:

```markdown
## UI verification

For server-rendered template/UI changes, prefer the verification CLI as the inner development loop:

    myapp verify template --template <name> --data <fixture>

Use it to construct relevant presentation states and make programmatic assertions against the rendered output. Use browser testing when browser execution itself is required.

When reporting verification, state which synthetic states were tested and which output properties were mechanically checked.
```

### Agent Skills

While `AGENTS.md` provides local repository policy, you can also package the workflow into a reusable "Agent Skill" (e.g., `skills/verify-server-rendered-ui/SKILL.md`). A skill provides the actual scripts and procedures for how to use the seam (e.g., how to parse the schema, how to compose fixtures, how to run HTML assertions), allowing the agent to apply the pattern consistently across multiple projects.

## Good Agent Verification Reporting

When agents use these tools, explicit reporting makes the output easy to audit.

**Bad:**
> Verified the UI.

**Better:**
> Rendered profile.html with:
> - anonymous state: edit control absent
> - authenticated viewer: edit control absent
> - editor state: edit control present with /profile/edit href
> - empty biography: empty-state element present
>
> Assertions were made against the generated HTML. The full Go regression suite also passed.

## Design Checklist

When building or evaluating a verification seam, ask yourself:

* Can I construct an interesting presentation state directly?
* Can the renderer run without a production database?
* Can I feed it machine-readable data?
* Are defaults deterministic?
* Can the input contract be discovered by a human or agent?
* Can fixtures be composed instead of copied?
* Can output go to stdout?
* Can failures produce useful exit statuses?
* Can I assert the output mechanically?
* Can I optionally serve it for visual/browser inspection?
* Does the verifier reuse real presentation code?
* Is it clear what this verifier does NOT prove?
* Is the workflow documented in `AGENTS.md`?
* Would a reusable agent skill make the workflow easier to apply consistently?
