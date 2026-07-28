---
title: "Mastering Go Template Whitespace: The Meaning of the Minus Sign"
date: 2026-07-28T11:50:49Z
draft: false
tags: ["go", "templates", "whitespace", "yaml"]
categories: ["Programming", "Go"]
---

One of the most common pitfalls when working with Go's [`text/template`](https://pkg.go.dev/text/template) and [`html/template`](https://pkg.go.dev/html/template) packages—and a frequent stumbling block for AI agents—is understanding how whitespace manipulation works. Specifically, the `-` (minus sign) in `{{-` and `-}}` is highly meaningful. It is not just decorative syntax or a continuation of the `{{` token; it explicitly clears whitespace.

If you aren't careful with these markers, you can quickly ruin the formatting of output that relies on strict whitespace, such as YAML or cleanly indented HTML.

In this post, we will explore intelligent techniques for managing whitespace in Go templates to ensure your output looks exactly as intended.

## The Meaning of the Minus Sign

When you use `{{-`, you are instructing the template engine to trim all preceding whitespace (spaces, tabs, carriage returns, and newlines) up to the previous non-whitespace character.
Conversely, `-}}` trims all subsequent whitespace up to the next non-whitespace character.

Often, developers mistakenly use `{{-` and `-}}` symmetrically, clearing whitespace in both directions. This frequently leads to text being smushed together across lines.

**Best Practice:** Generally, try to clear whitespace in only one direction. If you only need to clear the newline before a block, use `{{-`. If you only need to clear the newline after, use `-}}`.

## Intelligent Whitespace Techniques

Beyond simply adding `-` to your action tags, here are several advanced techniques for precisely controlling whitespace:

### 1. The Empty Comment Trick

You can use an empty comment combined with whitespace trimming to manipulate spacing without outputting any content.

*   **Clear everything:** Use `{{- /**/ -}}` to completely strip all whitespace surrounding this block.
*   **Stop clearing:** Use `{{ /**/ }}` (without the minus signs) to act as a barrier. The template engine will evaluate it and output nothing, but any whitespace around it will be preserved because there are no `-` markers to trim it.

### 2. Enforcing Exact Whitespace

Sometimes you need to guarantee a specific amount of whitespace, regardless of what surrounds the template tag. You can achieve this by outputting literal string values.

*   **Exact Spaces:** Use `{{- "  " -}}` to clear all surrounding dynamic whitespace and replace it with exactly two spaces. The `-` clears the existing whitespace, and the string literal `"  "` guarantees your desired spacing.
*   **Dynamic Spacing with Printf:** For larger or dynamically sized spacing, you can use the `printf` function. For example, `{{- printf "%20s" "" -}}` will clear surrounding whitespace and insert exactly 20 spaces.

## Best Practices Around `if` Statements

Conditionals in templates (`{{ if .Condition }}`) are notorious for introducing unwanted blank lines. This is particularly destructive when generating formats like YAML, where consistent indentation and spacing are strictly required.

When using `if` statements, pay close attention to which direction you are clearing.

If you blindly apply `{{-` and `-}}` everywhere (e.g., `{{- if .Condition -}}`), you might unintentionally strip the required newline and indentation for the YAML keys, causing invalid syntax.

Instead, it is often best to leave the newline after the condition to preserve the indentation of the inner block, and use `{{-` before the `if` and `end` tags to consume the trailing newlines from the previous blocks:

```yaml
resources:
{{- if .Requests }}
  requests:
    cpu: 100m
{{- end }}
{{- if .Limits }}
  limits:
    memory: 256Mi
{{- end }}
```

In this pattern, the `{{-` on the `if` and `end` lines ensures that if a block is skipped, no empty lines are left behind. At the same time, it preserves the structural indentation and line breaks required by the output format when the condition is met.

Mastering these techniques will make your templates much more robust and ensure your configuration files remain perfectly formatted.
