---
title: "Generated Go Is Source Code: Naming, Control Flow, and Reviewable Output"
date: 2026-11-19T14:00:00+11:00
draft: false
guidance: ["generated-go-review"]
tags: ["go", "code-generation", "testing", "readability", "ai-agents"]
categories: ["Software Development", "LLM Instructions"]
discussion: "https://github.com/arran4/blog/discussions/289"
---

A Go generator is not finished when its output compiles. Its output is source code
that people and coding agents will read, debug, diff, and sometimes step through.
If a generator emits correct but incomprehensible code, it shifts development
cost downstream.

I want generators to produce **deterministic, readable Go, with names derived
from the meaning of an operation rather than incidental traversal counters**.
This is a review principle, not a demand to handcraft every line or invent a
general-purpose code-formatting framework.

The existing [coding standards](/blog/post/2026/055-suggested-coding-standards-for-repositories-and-agents/)
cover determinism and test boundaries. This post focuses on the *shape of the
generated Go itself*.

## The output is a product

Consider a generated condition:

```go
condition3 := IsStaff(value1)
condition5 := condition3
if !condition5 {
    condition4 := IsAdmin(value1)
    condition5 = condition4
}
```

The source may implement a correct short-circuit OR, but the reader has to
reconstruct the original intention. The synthetic assignment and reassignment
are scaffolding, not domain meaning. A generator should aim for a representation
that exposes the decision:

```go
if IsStaff(user) || IsAdmin(user) {
    servePrivileged(w, r)
    return
}
```

This shorter version is appropriate **only if** the predicates are ordinary
`bool` functions, provider dependencies are already resolved correctly, and the
original algorithm did not need distinct error handling or deferred evaluation.
Do not replace semantics with prettier source.

## Separate semantic identity from its Go spelling

A useful generator can identify a value before choosing a local variable name.
For example:

| Semantic identity | Candidate Go spelling |
| --- | --- |
| Request-scoped current-user provider | `currentUser` |
| Staff predicate result | `isStaff` |
| Route for `GET /account/profile` | `routeGetAccountProfile` |
| Node responsible for `/account/:id` | `routeAccountByID` |

The semantic identity is the durable part. The spelling must be a valid,
unambiguous Go identifier in the lexical scope where it appears.

For route nodes, model a key such as the module, normalized route path,
method and node role. For provider results, use the provider's fully qualified
identity and the particular scope or route where it is evaluated. **Do not use
only the order in which an unordered map was traversed.**

Identifiers still need a collision policy. Two routes might normalize to the
same spelling; two imported packages may have the same name; a user may define
the name the generator wanted.

A sensible allocation sequence is:

1. Establish a deterministic, source-independent ordering of semantic keys.
2. Propose short domain-derived names, with an explicit vocabulary for
   captures, wildcards, scopes and roles.
3. Reserve Go keywords, predeclared names where relevant, generated helper
   names, imports, and user symbols in each applicable lexical scope.
4. Disambiguate with a meaningful qualifier when possible.
5. If ambiguity remains, add a deterministic, stable suffix tied to semantic
   identity. A hash can be a last resort, not the primary identifier.
6. Check both uniqueness and whether the generated code compiles. An attractive name is useless if
   it shadows an import or conflicts with another declaration.

Inserting a new sibling route should not rename half the generated file merely
because a counter changed. Stability of unaffected names makes diffs more useful.

## Reuse case conversion, not accidental naming policy

A string utility such as
[`github.com/arran4/strings2`](https://github.com/arran4/strings2)
can split route fragments, preserve known acronyms and format meaningful words
into camelCase or PascalCase. It cannot determine whether two different route
nodes are semantically identical, or which identifiers are reserved in a
particular Go scope.

The public
[`go-subcommand` naming allocator](https://github.com/arran4/go-subcommand/blob/main/parsers/sanitize.go)
provides a small example of sanitization, reservation and collision handling.
It is a reference to evaluate, not an instruction to import that entire
generator into another project. The generated-source quality discussion in
[go-subcommand #540](https://github.com/arran4/go-subcommand/issues/540)
covers related structural concerns.

## Prefer clear exits to incidental nesting

In generation, nested source often comes from the structure of an intermediate
representation or template, rather than the problem being modelled. Before
emitting another `if` block, ask whether a guard clause or direct expression
would preserve the contract more clearly.

For a predicate returning `(bool, error)`, evaluation and error propagation
may require separate statements:

```go
isStaff, err := IsStaff(user)
if err != nil {
    return handlePredicateError(err)
}
if isStaff {
    return servePrivileged()
}

isAdmin, err := IsAdmin(user)
if err != nil {
    return handlePredicateError(err)
}
if isAdmin {
    return servePrivileged()
}
return servePublic()
```

This is an *illustrative decision function*, not a universal HTTP handler
signature. The important properties are that `IsAdmin` runs only when needed,
errors do not silently become `false`, and the action is obvious at the point
of execution.

Flatter is not automatically better. Nesting can encode a genuinely scoped
dependency or a subtle lifetime rule. Likewise, extracting a closure solely to
remove one indent level may introduce allocations or hide evaluation order.
Choose the smallest structure that makes control flow and ownership clear.

A good working rule for coding agents is **avoid unnecessary nesting, not
nesting at any cost**.

## Route-node comments should locate the reader

A generated function named `node17` says little about what it owns.
A path-derived name helps, but generated route trees also contain shared
prefixes, wildcard captures, fallbacks and overlapping method candidates.

A concise Go comment can identify the route or subtree:

```go
// routeAccountByID matches the /account/:id subtree.
// It dispatches the remaining path after the account identifier.
func routeAccountByID(/* generated parameters */) {
    // ...
}
```

This makes the current parsing position discoverable while debugging.
Comments should describe actual generated contracts and important surprises,
not restate every `switch` or create a second maintained routing
specification. The source and tests remain authoritative; see
[Document Decisions, Not a Second Implementation](/blog/post/2026/057-document-decisions-without-duplicating-code/).

## Test the behavior and the generated source separately

I want three complementary kinds of evidence:

- **Planning and naming tests** establish canonical semantic keys,
  deterministic allocation, collisions, valid identifiers, and no accidental
  shadowing. These tests can often run entirely in memory.
- **Inspectable generated-source fixtures** show small and complex examples
  with readable formatting and useful comments. Exact golden output is
  appropriate where the emitted bytes are themselves an accepted contract;
  otherwise test meaningful AST or semantic properties.
- **Compiled and behavioural tests** prove real output compiles and operates
  correctly: short-circuiting, terminal `(bool,error)` handling, dependency
  evaluation, resource cleanup, HTTP outcomes and command behavior where
  relevant.

Perturb inputs deliberately: reorder declarations, change map insertion order,
add an unrelated sibling node, introduce conflicting import aliases, exercise
Unicode and punctuation in path components, and generate twice. Run the
compiled output rather than relying only on string searches for a particular
helper name. A variable rename should not break a behavioural test; changing
which provider runs should.

Use readable `txtar` scenarios where several source and expected files belong
to one case. Embed fixtures and use in-memory filesystems for logic; reserve
real temporary modules, compilers and subprocess execution for the integration
boundary that actually needs them. See
[Choosing Go Filesystem Test Fixtures](/blog/post/2026/047-choosing-go-filesystem-test-fixtures/),
[Minimize Filesystem Side Effects](/blog/post/2026/048-minimize-filesystem-side-effects-in-tests/)
and [Large Go Tests Should Read Like Scenarios](/blog/post/2026/051-large-go-tests-should-read-like-scenarios/).

Do not postprocess generated source with regular expressions to make a poor
intermediate model appear elegant. If `gofmt` repairs the output, that is
acceptable as a formatting boundary; it does not repair semantic naming,
unnecessary assignments or excess scaffolding.

## A short review checklist for agents

When a generated Go change is ready for review, answer:

- Can a reader identify the purpose of a local variable and routing node without
  reverse-engineering numeric counters?
- Are names valid, collision-free and stable under irrelevant input changes?
- Are values assigned once where possible, with no gratuitous copy/reassign
  chain?
- Can the control flow be followed without unnecessary nesting or hidden
  evaluation?
- Do errors, provider scopes and short-circuit behavior remain intact?
- Do generated comments locate paths and meaningful constraints without
  duplicating the implementation?
- Are golden examples, compiled output and behavioural tests all covered where
  they add distinct evidence?
- Has the generator, rather than only its checked-in example, been fixed?

A generated file should look like Go written with intention. Not every identifier
will be perfect, and some machinery is unavoidable, but unnecessary obscurity
should not be accepted merely because the generated code is correct.
