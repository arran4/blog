---
title: "GitHub Actions + golangci-lint: Go Version Compatibility Matrix (with Copy/Paste Workflows)"
date: 2026-02-14T00:00:00+00:00
draft: false
tags: ["go", "golangci-lint", "github-actions", "ci", "linting"]
categories: ["reference", "devops"]
---

If you use this in GitHub Actions:

```yaml
- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version: latest
```

you are absolutely right to be cautious: `latest` can move to a new golangci-lint release that adds support for a new Go minor while your workflow, runner, or repo expectations are still pinned to older assumptions.

This guide gives you:

- a practical **version pairing table** (Go ↔ golangci-lint ↔ action),
- **safe version ranges** you can reuse,
- and many **copy/paste workflow examples**.

---

## TL;DR (recommended defaults)

If you want a robust setup today:

1. Pin the action major (`@v9`) and pin a golangci-lint minor line (`v2.6.x`, `v2.8.x`, etc.) instead of `latest`.
2. Use `actions/setup-go@v6` before golangci-lint.
3. Test at least `stable` and `oldstable` Go in CI matrix.
4. Keep in mind golangci-lint policy: supports the **two latest Go minor versions**.

---

## Why `version: latest` can surprise you

`golangci-lint-action` accepts `version: latest`, but that means each CI run can pick newer golangci-lint binaries as they are released. Newer binaries can include parser/toolchain behaviour changes and new Go-version support windows. Great for fast adoption, risky for deterministic CI.

In short:

- `latest` = convenience,
- pinned version/range = reproducibility.

---

## Compatibility facts you should anchor on

### 1) `golangci-lint-action@v9` runtime and action compatibility

From action docs:

- `v9.0.0` requires Node.js runtime `node24`.
- `v8.0.0` works with golangci-lint `>= v2.1.0`.
- `v7.0.0` supports golangci-lint v2 only.
- `v4.0.0+` requires an explicit `actions/setup-go` step.

So for `@v9`, pair it with `setup-go@v6` (also node24 generation).

### 2) `actions/setup-go@v6` runtime note

`setup-go@v6` moved from Node 20 to Node 24 and calls out runner compatibility requirements in its README/release notes.

### 3) golangci-lint Go support policy

golangci-lint FAQ says it tracks Go team policy (the **2 latest minor versions**) and that practical support depends on the Go version used to build golangci-lint and linter ecosystem readiness.

### 4) recent Go support milestones in golangci-lint releases

From changelog/release notes:

- Go 1.22 support: `v1.56.0` line.
- Go 1.23 support: `v1.60.1`.
- Go 1.24 support: `v1.64.2`.
- Go 1.25 support: `v2.4.0`.
- Go 1.26 support: `v2.9.0`.

---

## Practical pairing matrix (recommended)

> Legend:
> - **Minimum known support** = first release explicitly mentioning support.
> - **Recommended today** = practical pin choice for modern CI.
> - Keep `golangci-lint-action` on `@v9` unless you have a legacy constraint.

| Target Go version | Minimum golangci-lint with explicit support | Recommended golangci-lint pin style | Action major | setup-go |
|---|---:|---|---|---|
| Go 1.22 | v1.56.0 | Prefer v2 line if possible (for modern action/docs), otherwise late v1 for legacy repos | v9 | v6 |
| Go 1.23 | v1.60.1 | v2.x pinned (`v2.4+`) | v9 | v6 |
| Go 1.24 | v1.64.2 | v2.x pinned (`v2.4+`) | v9 | v6 |
| Go 1.25 | v2.4.0 | v2.4+ pinned (`v2.4.x` / `v2.5.x` / `v2.6.x`) | v9 | v6 |
| Go 1.26 | v2.9.0 | v2.9+ pinned (`v2.9.x`) | v9 | v6 |

### Version ranges you can adopt

If you like semver-ish policy language in docs/team standards, these are good operational ranges:

- For Go 1.22–1.24 repos: use golangci-lint `>=2.4.0, <3.0.0` and pin exact patch in workflow.
- For Go 1.25 repos: use golangci-lint `>=2.4.0, <3.0.0` (pin exact).
- For Go 1.26 repos: use golangci-lint `>=2.9.0, <3.0.0` (pin exact).

---

## Copy/paste workflow examples

## 1) Most deterministic (single Go, exact lint version)

```yaml
name: lint

on:
  pull_request:
  push:
    branches: [ main ]

jobs:
  golangci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v6
        with:
          go-version: '1.25'

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: v2.6.1
          args: --timeout=5m
```

## 2) Stable + oldstable matrix (recommended baseline)

```yaml
name: lint

on:
  pull_request:
  push:
    branches: [ main ]

jobs:
  golangci:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        go-version: [stable, oldstable]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v6
        with:
          go-version: ${{ matrix.go-version }}

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: v2.9.0
          args: --timeout=5m
```

## 3) If you insist on `latest` (guardrails)

```yaml
name: lint

on:
  schedule:
    - cron: '0 3 * * *'
  pull_request:

jobs:
  golangci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-go@v6
        with:
          go-version: 'stable'

      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: latest
          args: --timeout=5m
```

Use this only if your team accepts occasional churn; combine with scheduled runs so breakage appears before business hours.

## 4) Go 1.22 pinned example

```yaml
- uses: actions/setup-go@v6
  with:
    go-version: '1.22'

- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version: v2.4.0
    args: --timeout=5m
```

## 5) Go 1.23 pinned example

```yaml
- uses: actions/setup-go@v6
  with:
    go-version: '1.23'

- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version: v2.4.0
    args: --timeout=5m
```

## 6) Go 1.24 pinned example

```yaml
- uses: actions/setup-go@v6
  with:
    go-version: '1.24'

- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version: v2.6.1
    args: --timeout=5m
```

## 7) Go 1.25 pinned example

```yaml
- uses: actions/setup-go@v6
  with:
    go-version: '1.25'

- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version: v2.6.1
    args: --timeout=5m
```

## 8) Go 1.26 pinned example

```yaml
- uses: actions/setup-go@v6
  with:
    go-version: '1.26'

- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version: v2.9.0
    args: --timeout=5m
```

## 9) Use `.golangci-lint-version` file

`.golangci-lint-version`

```text
v2.9.0
```

Workflow:

```yaml
- name: golangci-lint
  uses: golangci/golangci-lint-action@v9
  with:
    version-file: .golangci-lint-version
    args: --timeout=5m
```

## 10) Reusable workflow pattern for org-wide consistency

```yaml
name: reusable-golangci

on:
  workflow_call:
    inputs:
      go-version:
        required: true
        type: string
      golangci-version:
        required: true
        type: string

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version: ${{ inputs.go-version }}
      - uses: golangci/golangci-lint-action@v9
        with:
          version: ${{ inputs.golangci-version }}
          args: --timeout=5m
```

Caller example:

```yaml
jobs:
  call-lint:
    uses: your-org/your-repo/.github/workflows/reusable-golangci.yml@main
    with:
      go-version: '1.25'
      golangci-version: 'v2.6.1'
```

---

## Migration guidance (if you are currently using `version: latest`)

1. Keep action at `@v9`.
2. Replace `version: latest` with an exact version (`v2.9.0` for Go 1.26, `v2.6.1` for Go 1.24/1.25, etc.).
3. Add a weekly scheduled workflow that temporarily runs `latest` to preview upcoming breaks.
4. Bump pinned version intentionally in PRs.

---

## Common pitfalls

- Forgetting the explicit `setup-go` step (required by modern action versions).
- Using unquoted Go versions (`1.22` parsed as `1.2` by YAML).
- Upgrading action major without runner compatibility checks.
- Using `latest` on critical branches without canary/scheduled workflows.

---

## Source links

- golangci-lint-action README (compatibility + options): https://github.com/golangci/golangci-lint-action/blob/v9.2.0/README.md
- golangci-lint-action v9.0.0 release notes (node24 runtime): https://github.com/golangci/golangci-lint-action/releases/tag/v9.0.0
- actions/setup-go README (v6 Node 24 + examples): https://github.com/actions/setup-go/blob/main/README.md
- golangci-lint FAQ (supported Go versions policy): https://github.com/golangci/golangci-lint/blob/master/docs/src/docs/welcome/faq.mdx
- golangci-lint changelog (Go 1.22/1.23/1.24 support milestones): https://github.com/golangci/golangci-lint/blob/master/CHANGELOG.md
- golangci-lint v2.4.0 release (Go 1.25 support): https://github.com/golangci/golangci-lint/releases/tag/v2.4.0
- golangci-lint v2.9.0 release (Go 1.26 support): https://github.com/golangci/golangci-lint/releases/tag/v2.9.0

---

If you want, you can keep this short policy in your repo:

> We pin `golangci/golangci-lint-action@v9`, use `actions/setup-go@v6`, pin golangci-lint to an exact v2.x tag, and update it intentionally.
