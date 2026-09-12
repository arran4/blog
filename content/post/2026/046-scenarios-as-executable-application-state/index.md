---
title: "Scenarios as Executable Application State"
date: 2026-09-12T12:52:01+00:00
draft: false
tags:
  - testing
  - architecture
  - scenarios
  - llm
  - development
  - fixtures
categories:
  - Software Architecture
  - Testing
---

There is a recurring problem in application development that tends to acquire a
collection of unrelated solutions.

Tests need data. Developers need a populated application to work against.
Demonstrations need a recognisable set of users and content. Screenshots need a
known visual state. Bug reports need a reproducible situation. Continuous
integration sometimes needs to run the application against something more
interesting than an empty database. An LLM working on a user interface needs to
be able to create exactly the state it is trying to inspect.

The usual answers are fixtures, database dumps, ad-hoc seed scripts,
migration-time inserts, test factories, mocks, API scripts and hand-written
setup code.

All of those can be useful. None of them quite describes the abstraction I
increasingly want.

I call that abstraction a **scenario**.

A scenario describes a meaningful application state in terms of the things that
happened, or the things that need to exist, rather than in terms of the
physical representation chosen by the current database schema.

The distinction is important.

A database fixture says:

```
insert row 42 into users
insert row 107 into permissions
insert row 81 into topics
set topic.user_id = 42
```

A scenario says:

```
create user Alice
enable Alice
give Alice permission to create a private discussion
create a private discussion between Alice and Bob
have Alice start a conversation
have Bob reply
```

The database is an implementation detail of that story.

That apparently small shift changes what the data can be used for.

## The scenario is about application intent

The central rule is:

> A scenario describes what happened. The current application decides how that
> intent is represented.

That means the scenario should not normally contain table names, database
primary keys, SQL fragments, join-table entries or knowledge of the current
schema.

Suppose an application originally stores a permission as a row in a
user_permissions table.

A later release replaces that with role membership.

A still later release derives the permission from membership of a group.

A SQL dump from the first release has become historical baggage.

A scenario that says:

```
grant Alice permission to view private discussions
```

can continue to work.

The scenario runner asks the **current version of the application** to perform
that operation. The current application therefore creates whatever state the
current application requires.

This is one of the most valuable properties of scenarios: they verify present
application behaviour instead of preserving accidental historical storage
behaviour.

Database migration tests are still necessary. They answer a different question:

> Can old persisted state be migrated correctly?

A scenario answers:

> Can the current application construct this meaningful state correctly?

Those concerns should not be confused.

## The layer to call is below the transport and above raw persistence

A scenario should usually avoid HTTP.

It should also usually avoid direct SQL.

The useful layer lies between them.

Consider the ordinary web path:

```
HTTP request
    ↓
routing / authentication / request parsing
    ↓
application or domain operation
    ↓
repository / CoreData / service layer
    ↓
database
```

The scenario path should normally be:

```
scenario operation
    ↓
application or domain operation
    ↓
repository / CoreData / service layer
    ↓
database
```

The HTTP transport is deliberately absent.

That is not cheating. It is the point.

HTTP tests are useful for proving HTTP behaviour: routing, cookies, headers,
authentication middleware, CSRF handling, request decoding and redirects.

A scenario has another responsibility. It needs to create application state
quickly, deterministically and without recreating a web browser merely to reach
the domain operation.

At the same time, bypassing the application layer and inserting rows directly
loses much of the value. A direct insert may forget password hashing, secondary
indexes, permission provisioning, denormalised state, attachment processing,
audit records or other invariants.

A well-wired scenario therefore exercises the same application API that normal
application behaviour ultimately reaches.

When that API changes, both the real handler and the scenario compiler are
forced to follow it.

That coupling is beneficial.

## This is executable documentation

A good scenario simultaneously acts as fixture, demonstration and documentation.

Imagine opening a scenario called private-collaboration.

The first few operations might say that four users are created. Two can access
one private area. Two can access another. A thread exists in each area. Replies
demonstrate who can participate.

Even without running it, a developer can understand what state is being
constructed.

Once it can be executed, much more follows.

The same file can populate a test repository, build a disposable SQLite
database, run behavioural tests, start an interactive demonstration server,
produce screenshots, seed a development database, populate an integration
environment or reproduce a bug.

The scenario becomes a small executable description of a feature.

That is considerably more valuable than a pile of opaque fixture rows.

## Symbolic references are more useful than generated IDs

Scenarios should be written using stable symbolic names.

For example:

```
Ref: alice
Ref: engineering-room
Ref: welcome-thread
```

If a later operation needs the user, it refers to alice, not database user ID
7319.

The runner maintains a reference table:

```
alice             → current generated user identifier
engineering-room  → current generated topic identifier
welcome-thread    → current generated thread identifier
```

The application remains responsible for creating identifiers.

This is useful even if the application uses deterministic IDs today. It
prevents persistence details becoming part of the scenario language and allows
the implementation to switch to UUIDs, database sequences, KSUIDs or something
else later.

References should be typed where useful. A reference expected to identify a
user should not silently resolve to a forum or an attachment.

## Ordered events are useful, but not mandatory

Some applications naturally describe state as a sequence.

A forum is an obvious example:

```
09:00 create Alice
09:01 create Bob
09:10 create discussion
09:15 Alice creates thread
09:17 Bob replies
```

Timestamps matter because ordering, age, activity lists and permissions may
depend on them.

An event journal works well for this sort of system.

TXTAR is particularly convenient in Go because a single readable file can
contain metadata, a sequence of event files and auxiliary assets.

A simplified example might look like this:

```
-- scenario.meta --
Format: example-scenario/v1
Name: private-collaboration

-- 010-alice.event --
Op: user.create
Ref: alice
Username: alice
At: 2026-01-01T09:00:00Z

-- 020-bob.event --
Op: user.create
Ref: bob
Username: bob
At: 2026-01-01T09:01:00Z

-- 100-room.event --
Op: room.create
Ref: room
Actor: alice
Participant: bob
Title: Project Room
At: 2026-01-01T09:10:00Z

-- 110-thread.event --
Op: thread.create
Ref: welcome
Actor: alice
Room: room
At: 2026-01-01T09:15:00Z

Welcome to the project.

-- 120-reply.event --
Op: thread.reply
Actor: bob
Thread: welcome
At: 2026-01-01T09:17:00Z

Thanks. I can see it.
```

But an event stream must not become dogma.

An address book may be clearer as structured contacts and relationships.

A bookmark manager may need nothing more complicated than users, bookmarks,
tags and timestamps.

A mail application may already have a perfectly good scenario language: a
directory containing RFC email messages, attachments and perhaps a small
manifest describing mailbox placement, flags and dates.

A filesystem application might use an actual directory tree.

A compiler might use source files.

The principle is more important than the serialization:

**use the most natural representation of application intent.**

Standardise the contract and lifecycle before trying to standardise every
application's syntax.

## Operations should form a small vocabulary

For event-oriented scenarios, it is useful to treat each action as a registered
operation.

Conceptually:

```go
type Operation interface {
    Name() string
    Validate(Event) error
    References(Event) []Reference
    Apply(context.Context, Services, Event, *References) error
}
```

The exact Go interface is not important.

The separation is.

Each operation should know what data it accepts, what references it declares,
what references it consumes and how to apply the intent through current
application services.

For example:

```
user.create
user.enable
user.grant
project.create
thread.create
thread.reply
bookmark.create
bookmark.tag
contact.create
address.add
friend.request
friend.accept
```

This vocabulary effectively becomes a small scenario API.

Once explicit, it can generate documentation. It can expose machine-readable
schemas. It can supply completion. It can generate examples. It can even
contribute material to an agent skill telling an LLM how to construct useful
states.

The implementation and its documentation no longer need to drift independently.

## Validate before changing anything

A scenario engine should have a proper preflight phase.

Parsing successfully is not enough.

Before performing the first mutation it should be possible to detect an unknown
operation, missing required data, duplicate symbolic reference, reference to
something that has never been declared, invalid timestamp, malformed enum,
missing attachment or unsupported format version.

This matters particularly once scenarios can be applied to a real database.

The desirable execution model is:

```
parse
  ↓
validate format
  ↓
validate every operation
  ↓
validate reference graph
  ↓
validate assets
  ↓
confirm target and safety policy
  ↓
apply
```

Where the persistence technology permits it, application should also occur
within an appropriate transaction.

A partially applied demo scenario is inconvenient.

A partially applied administrative seed against a persistent database can be
much worse.

## Time should be explicit

Many fixture systems accidentally depend on time.Now().

That makes scenarios unstable.

If a scenario represents events, give those events timestamps. If a state is
declarative, give the scenario a stable epoch from which unspecified times can
be derived.

Application APIs that currently call the system clock internally may benefit
from a clock abstraction.

This is not solely for tests. Explicit time makes the scenario comprehensible.
A user joined before a message was posted. A bookmark was edited two weeks
later. An address becomes valid next month. A message is unread because it
arrived after a particular activity.

Time is often part of the domain.

## A scenario should support more than one target

The scenario parser and runner should not be synonymous with a database
implementation.

Ideally the same scenario can be applied to several useful targets.

| Target | Main purpose |
| --- | --- |
| Pure in-memory repository | Fast unit, UI and agent testing |
| In-memory SQLite | Real SQL behaviour without persistent infrastructure |
| Temporary on-disk SQLite | Debuggable disposable environments |
| Normal application database | Development/demo/bootstrap when explicitly requested |
| Domain-native filesystem/archive | Applications whose real persistence format is already portable |

An in-memory implementation is especially attractive when the application
already depends on repository interfaces.

In that architecture, a scenario does not need to mock individual calls made by
a page. It can populate a real in-memory implementation of the same
repositories used by the application.

The UI then asks for data normally.

That produces a much stronger test than teaching every view helper to return a
canned value.

SQLite is also valuable. It is fast enough for disposable instances while still
exercising migrations, constraints and SQL queries.

The two are complementary.

## Embedded scenarios and external scenarios should coexist

Applications should ship with a few useful scenarios.

Go's embed package makes this cheap.

A released binary might contain:

```
scenarios/
    empty
    minimal
    demonstration
    permissions
    complex
```

Those built-ins are important because they are versioned with the code. If the
application changes in a way that invalidates them, CI should notice.

But users, developers and agents also need to supply their own scenarios.

The command-line interface should therefore accept both a built-in scenario
name and an external file or directory.

The same principle applies to templates used by scenarios and verification
tools: ship sane embedded defaults, while allowing a filesystem layer to
override them.

This gives a standalone production binary without taking extensibility away
from developers.

## Applying and serving are different operations

A particularly useful command set is conceptually:

```
scenario list
scenario show NAME
scenario validate SOURCE
scenario apply SOURCE
scenario serve SOURCE
```

validate performs the full preflight but no mutation.

apply writes the scenario into an explicitly selected target.

serve creates a disposable environment, runs normal initialization and
migrations, applies the scenario, and starts the application against it.

The latter is extremely useful.

Instead of:

```
start database
configure account
run migration
create users
set permissions
import data
start application
find relevant page
```

a developer or agent can run:

```
application scenario serve private-collaboration
```

and receive a working application containing precisely the interesting state.

External network side effects should normally be disabled in this mode. Email
should go to a capture sink or nowhere. Uploads and caches should use temporary
directories. Persistent configured databases should be ignored unless the user
explicitly opts in.

A disposable scenario should be genuinely disposable.

## Real database seeding is a first-class use case

Scenarios should not be artificially restricted to test databases.

The same mechanism can be useful to seed a development database, initialise a
demonstration installation or establish optional example content.

What changes is safety.

A real-database apply command should make the target obvious, reject surprising
non-empty targets where appropriate, support dry-run validation, clearly define
whether reapplication is legal, and avoid pretending every scenario is
idempotent.

There is also a distinction between **mandatory bootstrap state** and **optional
scenario state**.

If every valid installation requires a particular invariant for the application
to function, it probably belongs in migrations or a mandatory bootstrap routine.

If it represents a useful policy arrangement, demonstration, tenant
configuration or example content, it may be a scenario.

The two systems can still share application services.

For example, a scenario operation that establishes policy should call the same
policy-provisioning function used by bootstrap code rather than reimplementing
the policy representation.

That is a sensible way to unify overlapping seed systems without making
migrations dependent upon test fixtures.

## Scenarios should be tested as products

A scenario that is never run will rot.

Built-in scenarios should participate in CI.

At minimum, CI should parse and validate every embedded scenario. Important
scenarios should also be applied to the lightest realistic backend.

For an SQL application, a small set should be replayed against migrated
in-memory SQLite.

For particularly important behaviour, the resulting state should be queried
through application APIs and checked semantically.

A private discussion scenario should not merely prove that its inserts
succeeded. It should be able to prove that the intended participants can find
the discussion and an unrelated user cannot.

This turns scenarios into behavioural contracts.

## They are exceptionally useful for LLM-assisted development

It is reasonable to ask whether all this machinery is excessive merely to
construct test data.

In an LLM-assisted development workflow, I think the economics have changed.

The expensive part is increasingly not writing fifty lines of fixture code. It
is giving an automated developer an environment in which it can reliably
understand what it changed.

An agent that has only an empty database faces a large setup problem for almost
every UI task.

An agent given a scenario can instead be told:

```
Run the "large-bookmark-library" scenario.
Open the bookmark search verification view.
Confirm that title matches rank before URL-only matches.
```

That instruction is reproducible by another agent, by CI and by a human.

The same scenario can become part of an issue report.

The resulting debugging loop is far shorter.

The abstraction is therefore not complexity for complexity's sake. It is
infrastructure that reduces repeated context construction.

The test is whether scenarios remain simpler than the setup they replace.

If every scenario requires its own bespoke runner code, the abstraction has
failed.

If adding a new operation makes dozens of ordinary states easy to express, it
is paying for itself.

## Scenarios can become an application capability

Once the operation vocabulary is structured, it can support tooling beyond
tests.

A program can expose a catalog of built-in scenarios.

Documentation can be generated from the operation registry.

A schema can describe accepted fields.

An LLM skill can explain available scenario operations and include concise
examples.

A development environment can offer a scenario picker.

A bug-report tool could optionally export a sanitised scenario representing a
reproducible state.

A documentation build could render examples from scenarios and know that the
examples are still executable.

This is where scenarios stop being "fixture files" and start becoming a small
application capability.

## DSLs remain a valid alternative

Not every useful scenario has to be an external declarative file.

A typed Go builder can be exceptionally expressive:

```go
Scenario(
    User("alice",
        CreatedAt(t0),
        Identity("Alice"),
    ),
    Forum("Project",
        Thread("Build failure",
            Post("alice", "I can reproduce this."),
            Reply("bob", "Same here."),
        ),
    ),
)
```

A builder DSL has compile-time integration with domain types and can represent
sophisticated relationships elegantly.

Its disadvantages are that it normally needs recompilation, is harder for
non-Go tooling to produce, and is less naturally supplied as user data.

There is no reason to insist on one mechanism.

A good application may have an internal typed DSL for complex test construction
and an external scenario format for portable states.

They can even compile into the same intermediate representation.

That subject deserves treatment of its own because fixture DSL design has
different trade-offs from portable scenario design.

## Domain-native formats are sometimes the best scenario format

Email is a useful counterexample to excessive abstraction.

If the application exists to consume email, an .eml file already describes a
very large amount of meaningful state.

A scenario directory might therefore look like:

```
scenario.yaml
inbox/
    001-welcome.eml
    002-calendar-invite.eml
    003-html-newsletter.eml
attachments/
    example.pdf
```

The manifest only needs to describe information that is not naturally carried
by the message itself: mailbox placement, local flags, profile ownership, read
status or an artificial import timestamp.

Inventing a second language that restates From, To, Subject, MIME parts and
attachments would make the scenario system worse.

The same reasoning applies to other domains.

Prefer native, standard representations when they already express the intent.

## Maintenance rules

A scenario system remains useful when its maintenance incentives are aligned
with the application.

The operation implementation should call current application services. Built-in
scenarios should run in CI. Generated identifiers should stay out of the source
format. External side effects should be replaceable. Time should be
controllable. Validation should precede mutation. The format should be
versioned. Important application features should have representative scenarios.
Obsolete operations should fail clearly rather than silently becoming no-ops.

Most importantly, when a feature changes, its scenario should be considered
part of the feature.

If adding a new mandatory field to CreateUser breaks user.create, that breakage
is useful information. The scenario was another caller of the application API
and has identified that its description of creating a user also needs to evolve.

That is exactly the maintenance coupling we want.

## The result

The useful mental model is not "seed data."

It is:

> **A scenario is a portable, executable description of meaningful application
> state.**

It should know as little as practical about storage and as much as necessary
about application intent.

It should be cheap enough to use for tests, deterministic enough for CI,
understandable enough for humans, structured enough for LLMs, portable enough
for demos and faithful enough to exercise the real application pathways beneath
the transport layer.

Done this way, scenarios provide something database fixtures, mocks and
full-stack browser scripts each struggle to provide on their own:

a common language for saying, precisely, **"put the application into this
situation."**
