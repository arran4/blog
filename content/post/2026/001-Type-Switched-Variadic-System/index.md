---
title: "The Type-Switched Variadic System I Keep Reusing in Go"
date: 2026-02-18T15:44:02+11:00
draft: false
tags: ["go", "api-design", "options-pattern", "ergonomics"]
categories: ["notes"]
author: "Arran Ubels"
---

I keep reaching for the same API shape in Go: a variadic argument list (`...any`) processed with a
`type switch`.

I call it my **type-switched variadic system**. It is not the only way to configure behavior in Go,
but for parser/consumer style libraries it has been one of the most productive patterns I use.

If I had to summarize it for future me (or future agents helping me write code), it is this:

> Accept a list of typed option values, iterate once, and interpret each value through a type switch
> into a local config struct.

This post explains the structure, why I like it, where it helps, where it hurts, and what guardrails
make it maintainable.

## The Core Shape

At the call site, the API feels declarative:

```go
result := Parse(input,
    ParserSmartAcronyms(true),
    WithNumberSplitting(true),
    SnakeCasePartitioner,
)
```

Inside, the function does something like this:

```go
func Parse(input string, opts ...any) ([]Word, error) {
    cfg := defaultParserConfig()

    for _, opt := range opts {
        switch o := opt.(type) {
        case Partitioner:
            cfg.Partitioner = o
        case PartitionerConfig:
            cfg.Partitioner = NewPartitioner(o)
        case ParserOption:
            o.Apply(&cfg)
        }
    }

    return runPipeline(input, cfg)
}
```

That loop is the engine.

## Why I Prefer This Pattern

### 1) Ergonomic call sites

You can pass only what matters and ignore everything else. Callers do not have to construct and
thread full config structs just to tweak one behavior.

### 2) Strongly-typed options without giant constructors

Each option type is explicit (`consume.StartOffset`, `consume.CaseInsensitive`, `MaxLines`, etc.), so
behavior is discoverable in docs and completions while still allowing flexible composition.

### 3) Backward-compatible growth

Adding a new option is often additive: define a new type and a new switch case. Existing call sites
keep compiling untouched.

### 4) Locality of behavior

The option parsing logic lives close to the feature. You can read one function and understand how
inputs map to behavior.

## Concrete Examples from My Repos

### `go-pattern`: grid composition via operation values

In `NewGrid(ops ...any)`, each argument can be a row op, column op, positioned cell, size
constraint, or callback. The switch applies these operations in sequence to build the final layout.

That lets the call site read like a mini DSL without introducing a separate parser.

Example sources:
- [grid.go](https://github.com/arran4/go-pattern/blob/main/grid.go#L157)

### `golang-diff`: compact options with typed wrappers

`NewOptions(args ...interface{})` handles different wrappers (`TermMode`, `Interactive`, `MaxLines`,
`LineUpFunc`, etc.) and maps them into an `Options` struct. That gives concise calls while keeping
semantic meaning on each value.

Example sources:
- [options.go](https://github.com/arran4/golang-diff/blob/main/pkg/diff/options.go#L55)

### `strings2`: mixed strategy and option interfaces

`Parse(input string, opts ...any)` accepts both direct strategy values (`Partitioner`), strategy
configs (`PartitionerConfig`), and `ParserOption` interface values. This is a nice middle ground:
functional options and direct typed arguments can coexist.

Example sources:
- [parser.go](https://github.com/arran4/strings2/blob/main/parser.go#L16)

### `go-consume` (strong example): expressive scanning behavior

`UntilConsumer.Consume(from string, ops ...any)` is where this pattern really shines for me. It
supports toggles and configuration values like:

- `consume.Inclusive(true)`
- `consume.StartOffset(n)`
- `consume.Ignore0PositionMatch(true)`
- `consume.CaseInsensitive(true)`
- `consume.ConsumeRemainingIfNotFound(true)`
- `consume.Escape("\\")`
- `consume.Encasing{Start: "(", End: ")"}`
- `consume.EscapeBreaksEncasing(true)`

You can combine these at the call site to describe behavior clearly without exploding function
signatures.

Example sources:
- [until.go](https://github.com/arran4/go-consume/blob/main/strconsume/until.go#L53)

## How I Implement It (Repeatable Recipe)

1. **Start with defaults in local variables or a config struct.**
2. **Loop over `opts ...any` once.**
3. **Use a type switch to map option types to config mutations.**
4. **Run the core algorithm using resolved config.**
5. **Document accepted option types in the function comment.**

A practical variant I like is to support both:
- direct typed values (easy, concise), and
- an `Option` interface with `Apply(*Config)` for richer composition.

## Guardrails That Keep It Healthy

This pattern is easy to abuse. These are the rules I try to keep:

### Keep option types narrow

Avoid overloaded "god options". Prefer small types with one obvious meaning.

### Avoid ambiguous primitive cases

If you add `case int:` or `case bool:`, be careful: ambiguity grows quickly. Named wrapper types
(e.g. `MaxLines`, `StartOffset`) are clearer and safer.

### Last-write-wins should be intentional

If the same option type appears multiple times, the later one usually overwrites earlier values.
That can be useful, but should be documented.

### Panic only for programmer errors

In `go-consume`, empty escape strings panic because they are invalid API usage. For runtime/data
issues, prefer normal return errors.

### Keep the switch in one place

Scattering option interpretation across many helpers makes behavior hard to reason about.

## Trade-offs and Limitations

No pattern is free.

- **Compile-time guarantees are partial**: invalid option combinations are often caught at runtime.
- **Discoverability depends on docs**: users need clear comments listing accepted option types.
- **Large switches can sprawl**: if a function grows too many cases, refactor by option domain.

For very strict APIs, plain config structs or pure functional options may be better.

## Why This Works Well with AI/Agent Collaboration

When I ask an agent to extend one of these libraries, this pattern gives a clear target:

1. Add a new typed option.
2. Add a switch case.
3. Update docs/examples.
4. Add tests for default behavior + option-enabled behavior.

It is explicit and mechanical enough that agents can follow it reliably, while still producing
human-friendly call sites.

## Prompt Template I Can Reuse Later

When I want future agents to produce code in this style, I can be direct:

> Use a type-switched variadic option system.
> Accept `opts ...any`.
> Parse options via one `for` loop with a `type switch` into local config.
> Prefer named wrapper types over raw primitives.
> Keep defaults explicit and document accepted option types.
> Add tests for conflicting options and last-write-wins behavior.

That usually gets me close to what I want.

## Closing

I like this pattern because it balances **ergonomics**, **type-driven clarity**, and **evolution over
time**. In parser/consumer-heavy code, it often reads naturally and adapts well.

It is not mandatory, and I still use plain configs when that is simpler. But when I need a compact,
expressive surface that can grow steadily, the type-switched variadic system keeps proving itself.
