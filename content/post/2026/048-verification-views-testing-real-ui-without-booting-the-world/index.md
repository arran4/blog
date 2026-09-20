---
title: "Verification Views: Testing Real UI Without Booting the World"
date: 2026-09-17T23:48:36+00:00
draft: false
tags:
  - testing
  - go
  - templates
  - ui
categories:
  - Testing
  - Software Development
---

A surprisingly large amount of user-interface development time is spent not
changing the interface, but getting the application into a state where the
interface can be seen.

A developer wants to inspect a page containing fifty records.

A CI job wants to ensure that an HTML template still renders.

An LLM has changed a CSS class and wants to see the resulting page.

A screenshot test needs a particular permission state.

A reviewer wants to inspect an error panel.

The traditional answer is often to boot the entire application, configure its
dependencies, populate its database, log in, navigate to the correct page and
finally inspect the thing that mattered.

For some tests that is exactly what should happen.

For every test, it is wasteful.

A useful companion to application scenarios is what I call a **verification view**.

A verification view creates one deliberate, inspectable presentation of
application behaviour using the real rendering code but without requiring the
entire production environment.

For a server-rendered Go application that may simply mean:

```text
build known state
    ↓
construct the real template/view model
    ↓
execute the real template
    ↓
write or serve one HTML document
```

That small capability is extraordinarily useful for humans, CI systems and
coding agents.

## The objective is not to mock the page
The most important rule is that the thing under inspection should be real.

If the application uses Go html/template, the verification path should execute
the same template.

If the application has shared template functions, use them.

If it has a view-model builder, use it.

If it has layout templates and partials, include them.

If it uses embedded CSS or other assets, serve the relevant assets with the
output.

The test harness should replace the expensive or irrelevant surroundings, not
the thing being tested.

There is little value in creating a second implementation of the page solely
for verification.

## There are three useful levels of verification
It helps to think of this as a spectrum rather than one testing technique.

|Level|State|Rendering|Best for|
|---|---|---|---|
|Isolated template verification|Explicit supplied data|Real template|Template development, malformed-state checks, LLM inspection|
|Scenario-backed verification|In-memory or temporary scenario state|Real view construction and template|Feature/UI verification|
|Disposable application|Temporary migrated database plus scenario|Normal HTTP application|Routing, auth, integrated behaviour and interactive demos|

The fastest level should be used whenever it answers the question.

Escalate only when the lower level stops exercising something relevant.

This is not an argument against end-to-end testing.

It is an argument against forcing every question to become end-to-end testing.

## The simplest useful command
A template-oriented application can expose something conceptually like:

```bash
application test verification template bookmark-list
```

By default, the rendered HTML can go to stdout.

For agent and CI workflows, writing it to a known file is useful:

```bash
application test verification template bookmark-list \\
--out verification.html
```

For humans and screenshot automation, serving it is even more useful:

```bash
application test verification template bookmark-list \\
--serve 127.0.0.1:8081
```

The tiny verification server should normally serve the generated output and the
static assets required to display it correctly.

It need not pretend to be the whole application.

That distinction keeps the harness small.

## Verification cases should be named
A command that accepts arbitrary JSON is useful, but named cases are even more
useful.

For example:

```text
empty
default
many-items
long-titles
edit
permission-denied
unicode
malformed-import
mobile-density
```

A name gives developers, tests and agents a shared vocabulary.

An issue can say:

```text
The regression is visible in the "long-titles" verification case.
```

CI can render it.

An LLM can reproduce it.

A human can serve it locally.

The name becomes part of the application's test language.

## External data remains important
Named built-ins should not prevent arbitrary input.

A useful verification command should be able to accept a supplied data
document, scenario or template.

For a simple isolated template that might be:

```text
--data-from-json-file case.json
```

For a richer application it may instead be:

```text
--scenario examples/large-library.txtar
```

The distinction is useful.

Raw view data says:

> Render this template with these values.

A scenario says:

> Construct this application state normally, then render the view of it.

Both are legitimate.

The latter provides stronger behavioural coverage.

The former provides faster and more surgical template testing.

## Prefer a fake repository to many fake template functions
An isolated harness often begins by overriding data-returning template
functions.

That is a pragmatic starting point.

Imagine a template calls functions such as:

```text
bookmarks
bookmarkPages
tabName
loggedIn
editingBookmark
```

A verification command can replace those functions with deterministic local
implementations and then execute the normal compiled template set.

This gets real HTML onto the screen quickly and can be extremely valuable.

But there is an architectural threshold at which it becomes cumbersome.

If the harness has to reproduce half of the data-access behaviour expected by
templates, the more maintainable design is usually to provide a small in-memory
implementation of the application's repository or service interfaces.

Then the normal functions can remain normal:

```text
template
    ↓
normal template funcs / view builder
    ↓
normal application service
    ↓
in-memory repository populated by scenario
```

This has an important consequence.

When application querying semantics change, the verification view changes with
them.

A hard-coded bookmarks() replacement might continue returning yesterday's idea
of the data.

A real service backed by an in-memory repository must follow the application's
current contract.

In other words, verification becomes less mock-shaped and more
application-shaped over time.

## Do not add HTTP merely for realism
A verification view does not need an HTTP request merely because the production
page eventually travels over HTTP.

Sometimes rendering code expects request context. Supplying a small synthetic
request is reasonable.

What should be avoided is turning a template verification tool into a browser
automation framework just to claim that it is realistic.

Use HTTP when the behaviour being verified involves HTTP.

That includes routing, cookies, authentication middleware, redirects, headers,
caching behaviour and request-specific security controls.

Do not require it merely to find out whether a table renders the correct labels.

This is the same boundary that makes scenarios useful: reuse the layers that
matter and deliberately leave out the layers that do not.

## Embedded templates should be the default
Go's embedding support makes verification tools particularly convenient.

Production binaries can contain the normal template tree:

```go
//go:embed templates
var templatesFS embed.FS
```

The application compiles those templates and the verification command uses the
same compiled set.

That means the released executable remains self-contained.

A built-in verification case can always render against the templates that were
built with that version.

It also makes CI simple because it does not need to reconstruct an external
template installation before testing.

## Filesystem templates should be an overlay, not a separate world
Embedded defaults should not prevent developers or users from supplying their
own templates.

A useful arrangement is:

```text
embedded templates
        \+
optional filesystem overrides
        ↓
one template loader
        ↓
application and verification commands
```

The application should avoid having one template-loading mechanism for
production and a completely different one for verification.

A filesystem override is particularly valuable when developing templates
because the edit-render-refresh loop does not require rebuilding the binary.

The same mechanism is also valuable when templates are intentionally
user-customisable.

The verification command can therefore answer two questions:

```text
Does the built-in template render this state?
Does my replacement template render this state?
```

That is useful functionality beyond testing.

## Verification output should be deterministic
A verification artifact is much easier to inspect when the output does not
change for irrelevant reasons.

The harness should control the clock where dates are rendered, generated IDs
where they leak into output, random ordering, locale and timezone where
necessary, external URLs, CSRF values if they are not the subject of the test,
and volatile metadata.

This does not mean falsifying the page.

It means distinguishing data that is significant to the case from incidental
nondeterminism.

Deterministic HTML is especially useful to CI and LLM tools because a diff
becomes meaningful.

## HTML is already a valuable CI artifact
Visual testing is often equated with screenshots.

Screenshots are useful, but the generated HTML itself is a powerful artifact.

CI can preserve:

```text
verification/
    bookmark-list.html
    edit-bookmark.html
    permission-denied.html
```

When a job fails, those files can be inspected without rerunning the system.

HTML can also be subjected to structural assertions.

A test can ensure a heading exists, a form contains the expected field, a
forbidden action is absent, an accessibility property is present, or a
generated link points to the expected route.

This is generally less brittle than comparing the entire HTML byte-for-byte.

Snapshots still have a role, but semantic assertions should carry most of the
contract.

## Screenshots belong one layer above
Once a verification view can be served on localhost, screenshot generation
becomes trivial for a headless browser.

That browser does not need to log in, create records or manipulate the
application into shape.

The hard work has already been done by the scenario or verification data.

The browser's responsibility becomes:

```text
open URL
set viewport
wait for stable render
capture screenshot
```

This separation dramatically reduces flaky visual-test setup.

It is also ideal for coding agents. The agent can change a template, run one
verification command, render the page and inspect the screenshot without
discovering the application's entire interactive workflow first.

## Verification views should compose with scenarios
The most useful long-term architecture is:

```text
scenario
    ↓
application/domain services
    ↓
in-memory or temporary persistence
    ↓
normal query/view construction
    ↓
real templates
    ↓
verification HTML
```

This turns scenario construction and verification rendering into two halves of
a single development system.

The scenario answers:

> What application state should exist?

The verification view answers:

> What particular representation of that state should I inspect?

A single scenario can feed several verification views.

For example, a collaboration scenario might render a topic list as Alice, the
same topic list as Bob, a forbidden view as Carol and the thread itself as an
administrator.

The underlying state does not have to be reconstructed four times.

## Sometimes the view does not need a scenario
It is important not to make the scenario system mandatory.

A template may need verification specifically against an impossible or
partially constructed state.

Perhaps the goal is to make an error template robust when an optional title is
absent.

Perhaps the page is merely a component demonstration.

Perhaps the template receives a plain data type that is simpler to construct
directly than to derive from domain state.

That should remain easy.

A good hierarchy is:

```text
direct view data when sufficient
scenario-backed state when meaningful
full disposable application when required
external integration only when genuinely under test
```

The cheapest faithful test is usually the best one.

## Verification cases make UI expectations explicit
A conventional test often says:

```text
given this input, expect this string
```

A verification case can say something richer:

```text
this is what an intentionally dense bookmarks page looks like
this is what an empty inbox looks like
this is what a user without edit permission sees
this is what a thread containing forks looks like
```

That makes the intended UX discoverable inside the repository.

It is particularly valuable for states that humans seldom encounter during
ordinary manual development.

Empty states, huge collections, very long strings, unusual Unicode, invalid
imported material and partial permissions are exactly the cases that tend to be
forgotten until a user finds them.

Named verification cases keep them cheap to inspect.

## Use them as an agent interface
LLMs are good at changing code but can be surprisingly expensive to orient
inside a large application.

A repository can make the feedback loop dramatically better by documenting a
small set of commands.

For example:

```bash
application scenario validate demo
application test verification template dashboard --scenario demo --out /tmp/dashboard.html
application test verification template dashboard --scenario demo --serve :8081
```

An agent skill can explain what scenarios exist, how to create an external one,
what verification views exist, how to render them, where artifacts are written
and what constitutes a successful check.

This is much better than a vague instruction to "start the app and test it."

The agent receives an explicit observation mechanism.

Because humans use the same commands, it is not special LLM-only infrastructure
that immediately rots.

## A verification command should itself be tested
The harness is infrastructure and deserves small tests of its own.

A test should establish that a known verification case renders successfully,
required assets can be served, invalid case names fail clearly, user-supplied
data is accepted when enabled, and filesystem template overrides actually
override the embedded default.

If scenario-backed verification exists, at least one test should create state
through the scenario runner and render a real page from it.

This catches an important class of architectural drift.

If a normal template suddenly requires a new function or data field,
verification should fail at the same time as the relevant application change.

That failure is useful.

## Avoid turning the harness into a second application
There is an obvious danger.

A verification tool can grow until it contains a parallel authentication
system, parallel router, parallel data model and parallel implementation of
every view helper.

At that point it is no longer reducing complexity.

The way to avoid this is to keep asking:

> Can this dependency be supplied through an existing application interface
> instead?

If the answer is yes, do that.

Use the normal template compiler.

Use the normal view model.

Use the normal domain service.

Use an in-memory implementation of an existing persistence interface.

Use a controlled clock.

Only fake the boundary that is deliberately outside the verification scope.

## Non-web applications can use the same principle
"Verification view" sounds web-specific, but the idea is broader.

A terminal application can render a screen to a deterministic text buffer.

A mail application can build a widget tree against seeded messages.

A desktop application can launch one screen against an in-memory model.

A report generator can render one document.

A CLI can emit its formatted table for a named state.

The general pattern is:

> Construct a known state and expose one real application representation of it
> with as little unrelated infrastructure as possible.

HTML happens to be an especially convenient representation because it can be
written to a file, inspected as text, served locally, parsed semantically and
rendered visually.

## The relationship with end-to-end tests
Verification views do not eliminate end-to-end tests.

They allow end-to-end tests to concentrate on the things only end-to-end tests
can prove.

A browser test should prove a login flow.

It should prove an actual form can be submitted.

It should prove browser-visible routing and authorization behaviour.

It should not need to spend most of its execution time manufacturing fifty
bookmarks merely so that pagination can be inspected.

Create the fifty-bookmark scenario directly.

Then separately test that the HTTP path for adding a bookmark works.

This produces smaller tests with clearer failure boundaries.

## The larger pattern
Scenarios and verification views fit together naturally.

A scenario is a **state construction interface**.

A verification view is a **state observation interface**.

Together they create a reproducible development loop:

```text
describe state
    ↓
construct state through application semantics
    ↓
render one meaningful view
    ↓
inspect it as HTML, structure or pixels
    ↓
repeat
```

The loop can run entirely in memory.

It can use temporary SQLite.

It can run in CI.

It can run on a developer laptop.

It can be driven by an LLM.

It can become a demo.

And when more realism is necessary, the exact same state can be promoted into a
disposable full application server.

That is the real value of verification views.

They are not an attempt to create a new testing universe.

They are a way to make the **real application easier to observe**.
