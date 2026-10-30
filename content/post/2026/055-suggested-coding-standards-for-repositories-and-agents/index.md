---
title: "Suggested Coding Standards for My Repositories and Coding Agents"
date: 2026-10-11T02:42:55.065Z
draft: false
guidance: ["coding-standards"]
tags: ["coding-standards", "go", "testing", "architecture", "ai-agents", "review"]
categories: ["Software Development", "LLM Instructions"]
discussion: "https://github.com/arran4/blog/discussions/208"
---

<!-- cspell:words Getenv idempotency lockfiles overengineering workstream XDG -->

I maintain several repositories with different languages, maturity levels and constraints. I do not want them all to adopt a generic architecture or an enormous rules file. I do want repeated decisions to become easier to review, and I want coding agents to stop rediscovering the same standards from scratch.

This is my **suggested** engineering baseline: a catalogue to select from, not a claim that every repository already complies. It collects the ideas in my existing posts and the recurring questions that arise when reviewing changes. The rule is to **adopt only a convention that protects an actual contract in the target project**.

The most important distinction is between a principle, a project rule and a verification method:

- A **principle** explains a trade-off and is appropriate for a blog article.
- A **project rule** says precisely what to do in this repository and belongs in `AGENTS.md`, `CONTRIBUTING.md` or the relevant local design document.
- A **verification method** turns the rule into a reproducible check, test or CI gate when the payoff justifies it.

A long external article is not a replacement for a short actionable project rule.

## The standards I would consider first

| Area | Suggested default | When to make an exception | Existing reference |
| --- | --- | --- | --- |
| Side-effect boundaries | Pass explicit data/capabilities into core logic rather than ambient environment, process globals or incidental files | A test intentionally exercises the real OS or process boundary | [Process state in Go tests](/blog/post/2026/053-go-tests-treat-process-state-time-and-standard-io-as-dependencies/) |
| Filesystem testing | Prefer `fs.FS`, `fstest.MapFS` or readable embedded fixtures for logic; keep OS tests where needed | Permission, rename, symlink, executable or pathname semantics are the subject | [Minimise filesystem side effects](/blog/post/2026/048-minimize-filesystem-side-effects-in-tests/) |
| Fixture representation | Make fixtures small, named, deterministic and understandable without decoding opaque blobs | Exact encoded bytes are the contract, with provenance documented | [Readable test fixtures](/blog/post/2026/050-readable-test-fixtures-prefer-named-data-over-opaque-bytes/) |
| Large tests | Arrange, act and assert should read like a scenario; hide repetitive mechanics, not behaviour | Complex integration scenarios legitimately need explicit steps | [Large tests should read like scenarios](/blog/post/2026/051-large-go-tests-should-read-like-scenarios/) |
| Error contracts | Preserve error identity only when callers need it; add context when it improves diagnosis | Wrapping an error adds nothing, or exposes the wrong API contract | [Go error handling](/blog/post/2026/016-go-error-handling/) |
| Generated output | Make generation deterministic, inspectable and verify committed output is current | Truly transient or deliberately nondeterministic artifacts, with a stated contract | [Golden update conventions](/blog/post/2026/034-golden-test-update-convention/) |
| CI ownership | Keep verification visible, efficient and release-safe with one coherent owner | A real trust, event or reusable-workflow boundary justifies separation | [Canonical CI/CD reference](/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/) |
| Agent PR workflow | Keep changes reviewable, validate the actual diff, and make PR readiness communicate readiness | Emergency or explicitly authorised workflows may differ | [Jules management](/blog/post/2026/044-jules-management/) |

These are defaults with reasons, not automatic lint rules.

## 1. Prefer dependencies that are visible at the point of use

An inner operation should not need to know about `os.Getenv`, the user's home directory, the current working directory, global HTTP clients, process streams, the wall clock, or package-level mutable configuration unless that is the operation's explicit responsibility.

For a pure computation, pass values. For I/O, pass the smallest useful capability: an `io.Reader`, `io.Writer`, `fs.FS`, transport, clock, repository or function. Avoid mirroring the entire platform in an oversized `Dependencies` struct.

For example, a download planner should not require a test to reconstruct a desktop session and create a token file. The focused follow-up, [Prefer Dependency Injection to Environment Overrides in Go Tests](/blog/post/2026/054-stop-rebuilding-xdg-directories-in-go-tests/), explains how to inject resolved configuration, when a real environment test is necessary, and why XDG paths are an instructive special case.

Use the [fixture selection guide](/blog/post/2026/047-choosing-go-filesystem-test-fixtures/) and [Go FSs Everywhere](/blog/post/2026/007-Go-FSs-Everywhere/) to choose the lowest-cost interface. Not every dependency needs an interface; a typed value or a function is often enough.

**Review question:** is this dependency part of the behaviour, or merely the easiest existing route to it?

## 2. Preserve information before making it convenient

When handling formats, protocols, configuration documents or user-owned data, treat **round-trip fidelity** as a separate contract from semantic interpretation.

If a parser accepts an input form, a convenience accessor should not silently rewrite its stored representation merely because the accessor wants a canonical or typed view.

```text
original bytes / representation
          |
          +----> preserved source for round-trip output
          |
          +----> parsed semantic view for comparison and validation
```

Good defaults:

- Parse and validate through a typed view; preserve the original representation where lossless output is promised.
- Describe canonical formatting as **canonical**, not byte-for-byte reconstruction.
- Do not drop unknown fields, ordering, repeated properties, whitespace or escaping without an explicit contract allowing that loss.
- Put semantic comparison rules in the comparison layer where possible instead of pre-normalising the stored input.
- Test both semantic equality and preservation with round-trip regressions, including unfamiliar-but-valid inputs.

Sometimes an API intentionally produces only canonical output. That is fine. Document the distinction, and do not invent a lossless-preservation layer when the project never promised one.

**Review question:** has a convenience transformation quietly become a destructive edit?

This is a candidate for a future dedicated article on reversible parsers and canonical output; it should be cross-linked here when written. The existing [scenario guidance](/blog/post/2026/046-scenarios-as-executable-application-state/) also distinguishes meaningful intent from an incidental physical representation.

## 3. Validate boundaries deliberately; fail closed without overengineering

For authentication, permissions, file paths, external identifiers, generated manifests and destructive operations, malformed or unauthorised input should not receive a permissive fallback.

Keep validation at the relevant trust boundary, give callers useful errors, and test both allowed and denied behaviour. It is especially important to prove that a denied operation leaves no partially mutated state.

But “fail closed” is not permission to add redundant layers of validation to every internal helper. Once a trusted type has been validated, repeatedly rechecking it in every pure function can add noise without reducing risk.

**Review question:** can invalid input cross a meaningful boundary, and if rejected, does it leave state unchanged?

## 4. Keep side effects and dry runs honest

A dry run is a **non-mutation promise**, not a mode in which code writes to production locations and plans to delete or restore them afterwards.

For generators, package automation and migration tooling, prefer an explicit separation:

```text
read inputs -> validate -> calculate plan -> render candidate
                                     |
                             inspect / compare
                                     |
                     apply only in explicit write mode
```

Suggested invariants:

- Dry runs must not rewrite tracked files, manifests, lockfiles, application state or destination trees.
- If a tool must materialise candidate output, use isolated temporary storage and clean only the temporary resources it owns.
- Avoid “rewrite then git checkout” restoration: it can lose unrelated user changes.
- An update should be scoped to its declared targets; unexpected deletions or reordered unrelated content are review findings.
- Generated output should be deterministic and preferably idempotent. Re-run generation and compare the tree or artifacts against expectations.

The [canonical CI guide](/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/) covers generated output checks and safe CI wiring. [The golden-update convention](/blog/post/2026/034-golden-test-update-convention/) explains why intentional fixture rewriting must be an explicit mode, not a side effect of ordinary test execution.

**Review question:** what can this command change in the failure path and in dry-run mode?

This also deserves a future standalone article: **Dry Run Means No Mutation**.

## 5. Make tests explain contracts instead of setup machinery

The best test is not always the shortest. Prefer a test whose name, input and assertions expose a meaningful behaviour and regression.

- For setup failures that simply abort the test, use small helpers with `t.Helper()` instead of repeating uninteresting error handling. See [small must helpers](/blog/post/2026/049-go-test-setup-use-small-must-helpers/).
- For small file pairs, use literals or embedded data; for directory shape, use `fstest.MapFS`; for related multi-file scenarios, consider `txtar`. See [fixture selection](/blog/post/2026/047-choosing-go-filesystem-test-fixtures/).
- For substantial scenarios, give events symbolic names and meaningful descriptions instead of coupling the test to incidental database IDs. See [Scenarios as Executable Application State](/blog/post/2026/046-scenarios-as-executable-application-state/).
- Test the observable result, including negative and failure behaviour. Do not treat constructing a fixture, compiling a helper or receiving a non-error as proof of an unrelated end-to-end requirement.
- Include a limited set of real boundary tests (subprocess, filesystem, service, browser) where the assembled behaviour itself matters.

The [programmable UI verification seam](/blog/post/2026/040-programmable-ui-verification-seams/) is the same idea at another layer: use the smallest surface that proves the requirement, not the most theatrical setup.

**Review question:** if this test fails, can someone tell which user-visible or documented contract regressed?

## 6. Make Go errors a deliberate part of the API

I prefer error handling that helps a caller recover or a developer diagnose a failure, without turning every function into a stack of redundant wrappers.

```go
result, err := parseRecord(input)
if err != nil {
    return nil, fmt.Errorf("parse calendar record %q: %w", name, err)
}
```

That additional operation/context may be useful at a boundary. In another context, merely returning `err` may be clearer.

- Use `errors.Is` / `errors.As` when callers need reliable classification.
- Introduce stable sentinels or types only for distinctions callers can meaningfully act on.
- Wrap with `%w` when preserving identity is part of the contract; do not accidentally export implementation details as permanent API semantics.
- Do not wrap mechanically at every stack frame or replace structured error identity with string comparisons.
- Keep test setup error shortcuts separate from product error assertions.

The full discussion is in [Effective Error Handling in Go](/blog/post/2026/016-go-error-handling/).

**Review question:** does this error layer contribute context, classification, or recovery behaviour?

## 7. Prefer small compatibility-preserving changes over fashionable rewrites

Use existing patterns and standard-library interfaces where they fit. Before adding a generic helper, new interface or wrapper, ask whether the project already has an appropriate seam.

Do not add abstractions purely because an agent finds them easier to mock. Do not reduce a repository's supported Go version, compiler level, or dependency constraints merely to get a CI job passing. Test changes against the project's declared compatibility promise.

Useful companion material includes [optional dependency injection](/blog/post/2026/020-optional-dependency-injection-via-type-switched-variadic-args/), [compile-time type assurance](/blog/post/2026/025-compile-time-type-assurance-in-go/), and [LLM compliance with version upgrades](/blog/post/2026/019-llm-compliance-version-upgrades/). These posts describe options, not instructions to copy a technique into unrelated code.

**Review question:** has this PR solved its requirement with the smallest coherent change, preserving the callers and behaviours it claims to support?

## 8. Treat a passing CI result as evidence, not the entire review

A PR should identify the changed contracts, their tests, and what was **not** verified. Do not substitute agent prose for a diff review.

A good review packet contains the changed paths, meaningful assertions, verification commands/results and exceptions. Separate failures in source/tests from infrastructure failures that prevented tests from starting.

For a stacked PR series, verify each diff against its actual parent. One PR can resolve multiple closely related issues; an issue can be split when a meaningful independently reviewable slice exists. Avoid stacks that force reviewers to reconstruct enormous unrelated diffs.

A ready PR should be marked **Ready for review**; draft means meaningful implementation or validation is still outstanding. Do not merge without the requested authorisation. After merge, reconcile issue states, check follow-up value and decide whether the workstream should continue.

See [Jules management](/blog/post/2026/044-jules-management/) for the operational process and [canonical CI/CD](/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/) for the actual verification graph.

**Review question:** what did we prove about this exact change, and what remains uncertain?

## How I would adopt these in repositories

I would **not** paste this entire article into every repository's `AGENTS.md`. That duplicates prose, creates conflicts and makes local exceptions impossible to find.

Instead:

1. Keep a short, stable `AGENTS.md` (or the repository's already established equivalent) with the applicable imperative rules and links to the longer rationale.
2. Use `CONTRIBUTING.md` or `docs/engineering.md` for human workflow and examples that are too detailed for agent bootstrap instructions.
3. Place subsystem-specific invariants near the subsystem—package docs, tests, design notes or nested instructions where the tooling supports them.
4. Prefer CI and regression tests for mechanically verifiable claims. Policy prose should not be the only defence against destructive behaviour.
5. State explicit exceptions rather than introducing global rules that silently contradict existing architecture.

Here is a deliberately short **suggested** starting point, to trim for each project:

```markdown
## Engineering defaults
- Follow this repository's actual public API, compatibility, data-preservation
  and security contracts. Do not impose unrelated architectural conventions.
- Resolve environment, time, I/O and filesystem dependencies at boundaries.
  Prefer explicit values and narrow capabilities in inner logic and unit tests.
- Preserve the original representation when a format promises lossless round
  trips. Do not confuse canonical output with byte-for-byte reversibility.
- Reject malformed or unauthorised external input at trust boundaries; check
  denied operations for unintended side effects.
- A dry run must not mutate user/repository state. Generate and verify
  candidates in isolated storage before explicit application.
- Keep tests scenario-readable, deterministic and focused on observable results;
  retain real integration coverage for behaviour that genuinely needs it.
- Wrap errors when it adds context or preserves a caller-relevant identity,
  not merely because an error passed through another function.
- Report the exact verification performed. Keep PR diffs coherent and
  signal review readiness accurately; do not merge without authorisation.

Further rationale: https://arran4.github.io/blog/guidance/coding-standards/
```

That final URL is the stable guidance collection for this article once published. The individual linked articles remain the detailed rationale and may evolve separately. An agent must still inspect local instructions rather than assuming that an external guideline supersedes them.

### Suggested adoption order

First choose one or two persistent sources of review friction in the repository. Write a concrete local rule, add a regression if possible, and apply it in the next relevant PR. Do not open a repository-wide cleanup solely to make it resemble this catalogue.

For smaller utilities, **explicit dependencies, trustworthy dry runs and reproducible tests** may cover almost everything. For parsers, **reversibility and error contracts** may matter most. For user-facing applications, **permissions, state transitions, scenarios and boundary integration** deserve more attention.

The purpose of a standard is to **remove recurring ambiguity without removing valid design choices**.
