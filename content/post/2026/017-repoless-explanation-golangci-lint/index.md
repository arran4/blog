---
title: "Fixing golangci-lint Go Version Mismatch"
date: 2026-07-10T15:57:37+10:00
draft: false
tags:
  - golang
  - golangci-lint
  - github-actions
  - llm
categories:
  - Agent Instructions
  - DevOps
---

When encountering the following `golangci-lint` error in GitHub Actions or locally:

```text
run golangci-lint
  Running [/home/runner/golangci-lint-1.64.8-linux-amd64/golangci-lint config path] in [/home/runner/work/fork-mdtohtml/fork-mdtohtml] ...
  Running [/home/runner/golangci-lint-1.64.8-linux-amd64/golangci-lint run] in [/home/runner/work/fork-mdtohtml/fork-mdtohtml] ...
  Error: can't load config: the Go language version (go1.24) used to build golangci-lint is lower than the targeted Go version (1.25.0)
  Failed executing command with error: can't load config: the Go language version (go1.24) used to build golangci-lint is lower than the targeted Go version (1.25.0)

  Error: golangci-lint exit with code 3
  Ran golangci-lint in 85ms
```

This specific error means you must perform the following steps to properly resolve it:

1. **Delete configuration files:** Delete `golangci-lint.conf` or other old configuration files.
2. **Update dependencies:** Update `golangci-lint` and `golangci-lint-action` to the latest versions. Use external references to find the latest versions, do not default to old versions.
3. **Upgrade Go everywhere:** Upgrade Go across the entire repository to match the required version. Ensure GitHub Actions are using `go-version-file: go.mod` (or similar) to keep versions in sync.
4. **Resolve lint issues in a loop:** Rerun `golangci-lint` ensuring it uses the updated version. **Do not create a new config file.** Instead, attempt to solve all issues iteratively in a loop (resolving a couple of issues each loop) until done.
5. **Format code:** Run `go fmt ./...` on the codebase.
6. **Submit:** Once all steps are complete and the build passes, submit the changes.

### Example Correct GitHub Action Configuration

Ensure your workflow uses the latest action versions and syncs the Go version from `go.mod`:

```yaml
      - uses: actions/checkout@v6
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: latest
```

This procedure ensures that you do not fall back to old and incompatible versions of Go, `golangci-lint`, and `golangci-lint-action`.
