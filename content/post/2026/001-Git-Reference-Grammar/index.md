---
title: "Git Refs and Refspecs: Grammar Reference"
date: 2026-01-05T23:59:52+00:00
draft: false
tags: ["git", "refspec", "references"]
categories: ["reference"]
---

Git’s ref system is a tiny language for naming objects and mapping them across
repositories. This post is a grammar reference first, and examples second.

## Grammar reference

### Ref and refname

```
ref          := 'refs/' refpath
refpath      := name ('/' name)*
name         := 1+ valid-char
valid-char   := printable ASCII EXCEPT {space, control, '~', '^', ':', '?', '*', '[', '\\'}
constraints  := not (leading '/', trailing '/', '//', '..', '.lock', '@{')
```

Common namespaces (grammar applies equally):

- `refs/heads/<branch>`
- `refs/tags/<tag>`
- `refs/remotes/<remote>/<branch>`
- `refs/notes/<name>`

### Symrefs (symbolic refs)

```
symref    := 'ref: ' ref LF
examples  := '.git/HEAD', '.git/worktrees/<wt>/HEAD'
```

### Refspec (fetch/push)

```
refspec    := [force] [neg] src [':' dst]
force      := '+'
neg        := '^'                    # fetch-only
src        := pattern | ref | ''     # '' only when ':' present (delete/matching)
dst        := ref | ''               # '' allowed for delete/matching
pattern    := prefix '*' suffix      # exactly one '*'
```

Semantics:

- `+` permits non-fast-forward update.
- `^` removes matches from earlier positive fetch globs.
- `pattern` maps the `*` substring into `dst`.
- `:` with empty `src` deletes `dst` on push.
- Bare `:` (no src/dst) is deprecated matching.

### Revision-ish / `<start-point>`

```
start-point := rev                               # as used by man pages
rev         := ref | objid | rev parent | rev '~' [n] | rev '@{' sel '}' | rev peel
parent      := '^' [n]                           # default n=1
peel        := '^{}' | '^{' type '}'             # type ∈ {commit, tree, blob, tag}
objid       := 40-hex | 64-hex                   # SHA-1 or SHA-256
sel         := integer | date | 'upstream' | 'push'
shorthand   := '@' == HEAD
```

Selectors:

- `rev^` / `rev^n`      parent (n-th for merges)
- `rev~n`               first-parent ancestor
- `rev@{n}`             n-th reflog entry (0 = current)
- `rev@{<date>}`        reflog at time
- `rev^{}`              peel tag to referenced object
- `rev^{tree|commit|blob}` peel to type when ambiguous

### Storage notes (minimal)

- Loose refs: files under `.git/refs/...` (object ID or symref text).
- Packed refs: `.git/packed-refs` with optional peeled lines (`^<object>`).
- Resolution prefers loose, then packed.

## Examples and ready-to-use patterns

- Track all branches: `refs/heads/*:refs/remotes/origin/*`
- Exclude on fetch: `^refs/heads/wip/*`
- Force-push one branch: `+refs/heads/topic:refs/heads/topic`
- Delete remote branch: `:refs/heads/old-feature`
- Rename tag on push: `refs/tags/v1:refs/tags/release-1`
- Parent/ancestor: `feature^`, `feature^2`, `feature~3`
- Reflog selectors: `main@{2}`, `main@{yesterday}`
- Peel annotated tag: `v1.2.3^{}` or `v1.2.3^{commit}`

## Quick checklist

- Only one `*` per refspec glob.
- Avoid control chars, space, `~ ^ : ? * [ \\` in refname components.
- No `//`, `..`, `.lock`, or `@{` substrings; no leading/trailing `/`.
- Provide a destination when globbing on push; fetch often supplies one for
  remote-tracking writes.
