---
title: "Scenarios as Executable Application State"
date: 2026-09-15T17:19:57+10:00
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

<!-- cspell:words debuggable inspectable ksuids -->

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

TXTAR also has a useful feature that is easy to overlook: everything before the
first `-- filename --` marker is the archive comment. That gives a scenario a
natural human-facing description before any machine-readable files begin.

That preamble is an excellent place to explain the **who, what and why** of the
scenario, along with anything else a person or agent should know before running
it: the feature being demonstrated, the actors involved, the state being built,
the behaviour that should be visible, useful entry points, important negative
checks, assumptions and known limitations. The description travels with the
scenario instead of becoming a separate README that can drift away from it.

A simplified example might therefore look like this:

```
Private collaboration scenario.

Who: Alice and Bob are project members; Carol is deliberately outside the room.
What: A private project room with an existing welcome thread and reply.
Why: Demonstrate positive and negative visibility checks and reply permissions.
Useful checks: Alice and Bob can open the room and reply; Carol cannot see it.

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

The runner does not need to interpret that prose as application state. It can
preserve and expose the TXTAR comment as scenario documentation while parsing
the named files normally. A `scenario show` command, test-reporting tool or
scenario picker can surface the preamble directly, making the scenario useful
to someone before they execute it.

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
| Query or repository stub | Fast, controlled unit tests and error-path testing |
| Pure in-memory repository | Stateful unit, UI and agent testing without SQL |
| In-memory SQLite | Real SQL behaviour without persistent infrastructure |
| Temporary on-disk SQLite | Disposable but inspectable SQL environments |
| Normal application database | Development/demo/bootstrap when explicitly requested |
| Domain-native filesystem/archive | Applications whose real persistence format is already portable |

These targets form a **testing ladder**. They should not be treated as synonyms.

A query or repository stub is a programmable test double. It is ideal when a
test needs to say "this lookup returns these two rows" or "this write fails with
this error". It should not pretend to be a small database. It proves how the
caller reacts to an interface contract, not whether SQL, migrations or
constraints are correct.

A genuine in-memory repository is different. It implements the repository or
application storage interface with coherent mutable state. If one operation
creates a user and a later operation queries that user, the result follows from
the state of the fake repository rather than from a separately programmed
expectation. This makes it useful for larger unit tests, UI tests and agent
experiments where SQL semantics are not the thing being tested.

SQLite is different again. It is a real database engine. An in-memory SQLite
scenario should run the application's real migrations, driver-specific seed
data, query adapter and constraints before applying the scenario. That makes it
excellent for disposable application instances and integration tests. It is not
a replacement for testing the production database dialect, but it catches a
large class of problems that a repository fake deliberately cannot.

Temporary on-disk SQLite is worth keeping as a separate mode. It can run the
same migrations and scenario as the in-memory form while leaving a database
file that a developer can inspect after a failure. A useful implementation can
default to memory and offer an explicit "keep" or database-file option for
cases where post-mortem inspection matters.

The cheapest target that proves the behaviour should normally be preferred.
The same scenario being portable across several rungs is what makes the system
particularly useful.

### SQLite should be a supported target, not a shortcut

It is tempting to implement a scenario's SQLite mode with a hand-maintained test
schema. That quickly recreates the fixture problem at another level.

If the main application normally uses another database, SQLite support should
still pass through the ordinary persistence architecture. Driver-specific query
differences can be hidden behind the same query or repository interface used by
the application. Migrations can be filtered or adapted per driver. Mandatory
seed data can have a SQLite representation. The scenario runner should remain
unaware of those details.

There is also a practical trap with SQLite memory databases. A plain `:memory:`
connection may create a separate database for each connection opened by a
pool. A server or integration test that expects several connections can
therefore appear to lose its schema or data. A named shared-memory connection
string is often safer, conceptually:

```
file:scenario-UNIQUE?mode=memory&cache=shared
```

The process should keep the owning database connection alive for as long as the
environment is running and use a unique name for each isolated scenario.

SQLite support may also be optional in a compiled application. That is fine, but
discoverability still matters. It is better for `scenario serve` to remain a
known command and fail clearly with a message explaining that SQLite support is
not present than for the command to silently disappear from help output. A
reviewer, developer or agent should be able to discover both the capability and
how to enable it.

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

## The CLI is part of the scenario feature

A scenario system is much less useful if it can only be reached through test
helpers or package APIs. Humans, CI jobs and automated development agents all
benefit from the same boring, documented command-line entry point.

A useful minimum is:

```
application scenario validate PATH
application scenario apply PATH
application scenario serve PATH
```

Once an application has a catalog of embedded scenarios, `list` and `show`
become useful additions:

```
application scenario list
application scenario show NAME
```

For TXTAR-backed scenarios, `show` should present the archive comment or
preamble prominently before lower-level metadata. That description is the
scenario's natural explanation of who is involved, what state exists, why the
scenario matters and what a reviewer should try.

The important property is that these commands all use the same parser,
validator and operation registry. The CLI should not grow a second scenario
implementation around them.

### Accept both a file and a directory

A small usability choice makes scenarios much easier to work with. Let a command
accept either the scenario file itself or a directory containing a conventional
scenario filename and adjacent assets.

For example, all of these can be reasonable:

```
application scenario validate scenarios/private-collaboration/scenario.txtar
application scenario validate scenarios/private-collaboration
application scenario apply scenarios/private-collaboration
application scenario serve scenarios/private-collaboration
```

The directory form is particularly useful once scenarios have attachments or
other assets. The caller should not need to know how the parser internally
locates those resources.

`validate` should require as little application configuration as possible. It
should parse the scenario, resolve its assets and perform the full preflight
without opening the configured application database.

`apply` is deliberately more consequential. It writes to an explicitly selected
or configured persistent target, so the command should make that target obvious
and perform validation before the first mutation.

`serve` is the accessible demonstration and debugging path. A repository should
be able to document a one-command quick start such as:

```
go run -tags sqlite ./cmd/application scenario serve scenarios/private-collaboration
```

and then tell the reader which local URL to open and which scenario users or
states to inspect. A `--listen` option is useful when the default port is already
occupied:

```
go run -tags sqlite ./cmd/application scenario serve --listen :8090 scenarios/private-collaboration
```

That kind of command is valuable documentation. It gives a new contributor, a
reviewer and an LLM exactly the same reproducible entry point.

### `serve` should be isolated by construction

A disposable scenario server should not merely *intend* to be safe. Its runtime
configuration should be rewritten so that persistent side effects are difficult
to trigger accidentally.

A strong implementation ignores the normal persistent database connection and
opens an ephemeral SQLite database instead. It applies the normal migrations
and mandatory seed data, validates and applies the scenario, derives a local
base URL from the listen address, disables external email delivery, redirects
uploads and caches into a temporary directory, uses process-local signing and
session secrets, and selects an ephemeral dead-letter or background-job target.
On shutdown it closes the server, closes the database and removes the temporary
filesystem state.

That boundary matters because `scenario serve` is precisely the command people
will run casually. It should be safer than the normal application invocation,
not merely shorter.

## Configuration and service doubles can extend the idea

The core scenario idea is about meaningful application state. It does not need
to become a complete deployment-description format.

Still, some useful situations depend on more than persisted data. Behaviour can
change because of feature flags, base URLs, tenant settings or the presence of
an external service such as an OAuth2 or OpenID Connect identity provider,
email service, object store, queue, webhook receiver, payment gateway or search
backend.

One useful extension is to let a scenario environment apply a small,
scenario-specific configuration overlay when configuration materially affects
the state being demonstrated. Another is to let the application substitute
local, in-memory or fake implementations for selected external services. These
are capabilities a scenario runner *can* make available, not requirements every
scenario format must implement.

For example, an interactive authentication scenario might point the
application at a local fake OAuth2/OpenID Connect provider. That provider could
return deterministic users and claims, or model useful outcomes such as consent
denial, an expired token or an account whose groups do not grant access. A mail
scenario might send into a capture provider. An object-store integration might
write into a temporary directory. A queue might be replaced by an in-memory
implementation whose submitted work can be inspected.

The important boundary is still application intent. A scenario might say that
Alice signs in through an external identity with a particular set of claims. It
should not normally need to spell out every HTTP response in an OAuth2 exchange
unless the protocol exchange itself is what is under test. The fake service or
adapter can provide the protocol behaviour while the scenario describes the
meaningful condition.

Provider registries, interfaces and dependency injection make this style easier
because the normal application path can remain intact while the environment
chooses a safer implementation. A disposable `scenario serve` mode might also
rewrite endpoints and credentials so real external services cannot be reached
accidentally. Captured requests can then become useful assertions or debugging
artifacts.

Configuration should stay similarly scoped. The goal is not to copy a
production configuration file into every scenario. It is to record or select
only the configuration that is important to understanding and reproducing that
particular situation, while making the effective scenario configuration visible
to the person or agent running it.

Not every application needs these extensions and not every scenario should use
them. They are additional ways to make a scenario environment faithful when the
interesting application state crosses a process or configuration boundary.

## The command itself should be testable

Command-line accessibility is only durable if the CLI can be tested without
starting a production-shaped process for every case.

The scenario command benefits from the same dependency boundaries as the
application. The loader can accept a filesystem abstraction so tests can use an
in-memory filesystem. `apply` can accept an injected query or repository
interface so unit tests can use a stub or SQL mock. `serve` can accept an
injected database handle so bootstrap and cleanup behaviour can be tested
without depending on a globally configured database.

That makes it cheap to cover details that otherwise become shell-script
assumptions: command dispatch, missing arguments, file versus directory input,
missing scenario files, missing assets, validation failures, expected
application-layer writes and successful cleanup.

It also provides a clean split in the test suite. Small CLI tests can use an
in-memory filesystem and query stubs. SQL-facing tests can use SQLite. A smaller
set of end-to-end tests can run the full disposable server. The user sees one
CLI, while the implementation can test each layer at the cheapest useful level.

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

It should also be operationally accessible. A useful scenario can be validated
from the command line, applied through the same application services against an
appropriate target, or served as a disposable environment without requiring a
reviewer to reverse-engineer the application's test harness first.

Done this way, scenarios provide something database fixtures, mocks and
full-stack browser scripts each struggle to provide on their own:

a common language for saying, precisely, **"put the application into this
situation."**