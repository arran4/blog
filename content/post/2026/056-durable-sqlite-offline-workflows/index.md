---
title: "Durable SQLite Workflows with Files on Disk and Offline Clients"
date: 2026-10-19T22:02:00+11:00
draft: false
guidance: ["go-persistence"]
tags: ["go", "sqlite", "sqlc", "offline-first", "queues", "flutter", "testing"]
categories: ["Software Architecture", "Software Development"]
---

<!-- cspell:words dedupe FTS outbox sqlc -->

A small Go service can be reliable without a distributed job broker or multiple database servers. The difficult part is not choosing SQLite. It is deciding where the **durable truth** lives when a server queue, generated files, a search index, and an offline application must agree after failures.

This guide is a set of defaults for a **single-server SQLite application with offline clients**. It is not a template that every repository must adopt. In particular, a genuinely multi-writer distributed system has different authority and conflict requirements.

It complements [suggested coding standards](/blog/post/2026/055-suggested-coding-standards-for-repositories-and-agents/), [scenarios as executable application state](/blog/post/2026/046-scenarios-as-executable-application-state/), [Go tests and explicit dependencies](/blog/post/2026/053-go-tests-treat-process-state-time-and-standard-io-as-dependencies/), and [asset fingerprinting and caching](/blog/post/2026/039-asset-hashing-in-go/).

## Give each piece of state an owner

| State | Source of truth | May be rebuilt? |
| --- | --- | --- |
| Users, permissions, content identities, subscriptions | SQLite domain tables | No, without a backup |
| Pending, leased, retried, or failed server jobs | SQLite job table | No, until explicitly completed or cancelled |
| Client operations waiting to synchronize | Durable local client outbox | No, until acknowledged |
| Full media bytes | Managed files on disk, with hashes and metadata in SQLite | Only if the upstream guarantees retrieval or regeneration |
| Thumbnail bytes and HTTP caches | Files or a bounded cache table | Yes |
| Full-text search documents | SQLite FTS5 index over authoritative metadata | Yes |
| Current widget tree and in-memory worker state | Memory | Yes |

I want a source-of-truth decision for each item before writing caching or retry logic. A cached value must not quietly become the sole surviving copy. Conversely, a file called "cache" is not disposable if the application cannot fetch it again.

An example application might keep a database and an object directory under the same configurable data root:

```text
data/
  app.sqlite
  objects/ab/cd/<content-hash>.png
  staging/
```

The exact path shape is unimportant; stable content identities, ownership, verification and recovery are not. Avoid persisting an absolute host path as the only way to locate an object.

## Use sqlc as the normal query boundary

For Go code, keep ordinary schema and query definitions in SQL, and generate typed bindings with [sqlc](https://sqlc.dev/). A simple single-engine configuration is:

```yaml
version: "2"
sql:
  - engine: sqlite
    schema: sql/schema
    queries: sql/queries
    gen:
      go:
        package: storedb
        out: internal/storedb
        emit_interface: true
```

The generated `Querier` interface is a useful narrow dependency for application services and tests. Prefer its typed queries to ad hoc SQL scattered through HTTP handlers. Keep transaction construction and commit/rollback under an explicit unit-of-work or store boundary. The underlying `*sql.DB` should not leak into domain code merely to make one query convenient.

This is consistent with the existing `sqlc` and repository-interface practices in projects such as `goa4web` and `address`. It is **not** a requirement to wrap every generated method mechanically or to mock all database tests. Migrations, FTS5 virtual tables and pragmas may require explicitly justified SQL paths; do not hide that exception. Pin the generator version, check in generated files where repository conventions require it, and verify regeneration yields no diff.

Enable SQLite foreign keys, choose a busy timeout and WAL policy deliberately, use prepared/bounded statements, and test actual transactions against temporary SQLite databases. Multi-step writes that must succeed together belong in one transaction.

## Design server jobs as a durable state machine

Do not call an in-memory channel a reliable queue. Use a persisted job row with enough state to survive a process restart:

```text
pending -> leased -> succeeded
                 \-> retry-wait -> leased
                 \-> permanently-failed
```

Typical fields are a stable job ID, kind, normalized payload or reference, idempotency key, state, attempt count, next eligible time, lease owner and expiration, last error, and creation/update times.

A worker should:

1. Atomically claim an eligible job, or safely fail to claim it when another worker wins.
2. Perform bounded work using an injected HTTP client and clock where useful.
3. Persist success only after required output is durably available.
4. On transient failure, persist an eligible retry time with bounded exponential backoff and jitter.
5. Let an expired lease become reclaimable after a crash, without assuming the previous attempt had no side effects.

There is no exactly-once execution guarantee merely because a job row exists. Aim for **at-least-once execution with idempotent effects**. Give each operation a stable deduplication key, and enforce uniqueness in SQLite for requests that must not create duplicate work. Do not make the success state absorb an earlier interrupted write without verifying the output.

Use a small worker count until profiling and contention evidence justify more. Keep completed, pending and permanently failed jobs inspectable, with a specific operator retry path. Avoid infinite retries of permanent validation or authorization errors.

## Crossing the boundary between SQLite and files

A relational transaction does not atomically commit an unrelated filesystem rename. Design for the gap instead of pretending it cannot occur.

For generated or downloaded media:

1. Resolve a canonical key (for example source ID plus immutable upstream media ID) and ensure only one logical content record can own it.
2. Write to a private staging path while enforcing byte limits, content-type checks and hash verification.
3. Flush/close as required by the durability contract, then rename within the same filesystem to a content-addressed location. When power-loss guarantees matter, include file and directory synchronization appropriate to the platform.
4. Mark the media record ready only after the expected file exists and passes validation.
5. At startup or through a repair command, detect and reconcile incomplete metadata, staged files and orphaned objects.

If the process dies after a rename but before the SQLite state update, a retry should discover and verify the existing immutable file instead of downloading or generating it again. If it dies before the rename, the incomplete staging file should be safely disposable.

A database row saying "ready" must not make a missing disk file appear usable. Conversely, deletion and garbage collection must respect all live references, not just a single entry. Full media can be kept outside SQLite, while bounded thumbnails and search metadata can live inside it when that is a conscious trade-off.

Content addresses do not automatically grant authorization. An authenticated media endpoint must still check whether the caller may access the referenced entry. Defend storage paths against traversal and symlink escapes.

## Treat FTS5 and thumbnails as derived projections

SQLite FTS5 is appropriate when searching a local catalogue. Store the authoritative title, description, dates, author and source identity in normal tables, with FTS5 as a **rebuildable index**. Decide whether updates use triggers or one transactional indexing path; test insert/update/delete consistency and provide a rebuild command.

Do not search arbitrary unbounded user-controlled query strings directly without correct FTS query escaping/validation. Search must also apply user-visible catalogue and access restrictions. A globally indexed document is not globally readable.

Keep thumb generation idempotent and avoid duplicate work for the same media hash plus representation parameters. A size limit or eviction rule should make "bounded" meaningful.

## Keep client work durable until the server acknowledges it

Offline applications need a *local* outbox, not just an HTTP retry loop. Each user action is stored before optimistic UI success is treated as durable:

```text
local operation persisted
  -> available for replay
  -> sent with stable operation ID
  -> acknowledged by server
  -> removed/compacted locally
```

The server records operation IDs with a uniqueness constraint scoped to the authenticated user (and, if appropriate, the device). A repeated batch must produce the same outcome rather than a second mutation.

After pushing pending changes, the client pulls server changes from a durable monotonic cursor and advances its checkpoint **only after** applying the received data locally. A crash at any step should cause a harmless replay, not a lost update. Handle partial batch acknowledgements explicitly.

Conflict resolution is a product policy, not something SQLite decides. For a single authoritative server, "last server-accepted operation wins" can be an acceptable first contract, but an old offline change might overwrite a newer online change. If that is unacceptable, add version preconditions or per-field conflict semantics and tests. Never silently switch policies.

A read flag, current chapter, intra-image position and reading-time history are different facts. Decide which require cross-device synchronization rather than conflating them in one boolean. Store stable content identifiers, not only viewport offsets or transient row positions.

Pending image downloads and unread/read mutations have different loss and eviction rules. A user operation should not be discarded like a disposable image fetch.

## Source fetchers should advertise capabilities

A comic source may support `FetchLatest`, `FetchArchive`, `FetchArchiveYear`, or a subset. Prefer optional capability interfaces instead of requiring every source to pretend it offers everything. An RSS adapter is one way to implement `FetchLatest`, not a guarantee of archive discovery.

Keep source inspection separate from durable content materialization: fetching metadata can enqueue bounded image download/generation jobs, which then update immutable media and derived indexes. Use stable upstream identities and cursors, bounded pages, and explicit end-of-history behavior.

A remote source needs timeouts, response limits, redirect policy, MIME checks, and server-side request-forgery defenses. For developer-controlled private hosts, use an explicit trusted-source policy rather than silently permitting reserved addresses.

## Make the failure path executable

A useful integration scenario should be able to create meaningful state without hand-editing SQL:

```text
create user Alice
register example comic One
fetch latest entries
generate image for entry One/12
mark entry One/12 read on client A
disconnect client A
mark entry One/13 read while offline
restart server
reconnect client A; replay operation
connect client B; pull changes
verify both clients agree
```

Use deterministic generated images and fixture-backed RSS data, not live network access, to test the core path. Prove both cached and uncached media behavior. Include restart points between file rename/DB update, job claim/job completion, client send/ack, and server change/client checkpoint.

Use a fake clock for retry timing where possible, and a real filesystem plus SQLite for a few bounded integration tests. This follows [scenario testing](/blog/post/2026/046-scenarios-as-executable-application-state/) and [explicit dependency boundaries in Go tests](/blog/post/2026/053-go-tests-treat-process-state-time-and-standard-io-as-dependencies/). The important assertion is the final observable state after recovery, not just that functions returned nil.

## Implementation and review standards

For agent-assisted work, record the desired observable goal and independently closable acceptance criteria in GitHub. A sequence of development phases is a plan, not an obligation to create one tiny PR per phase. Prefer coherent issue-complete PRs, linked dependencies only when real, a durable issue-to-PR ledger, and tests that prove what is claimed. See [Jules management](/blog/post/2026/044-jules-management/) and [the canonical CI guide](/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/).

Before declaring a local-content/offline-sync goal complete, I would require:

- a fresh database migration and a repeatable migration on existing state;
- reproducible `sqlc generate` with generated interfaces present;
- cross-user read isolation, unauthorized media denial, and no plaintext passwords or bearer tokens in logs;
- repeatable media generation and no duplicate materialization after restart;
- queue claim, retry, lease expiry, and permanent failure tests;
- offline outbox replay, idempotent receipts, cursor recovery and cross-device conflict tests;
- bounded archive traversal and FTS5 consistency/rebuild tests;
- a real end-to-end demonstration that survives server/client restarts.

This is deliberately not an automatic request for Docker, Redis, a new ORM, separate search infrastructure, or distributed consensus. Adopt the least complicated durable design that satisfies the demonstrated contract.
