---
title: "Resolving golangci-lint Go Version Conflicts in GitHub Actions"
date: 2026-03-05T00:00:00+00:00
draft: false
tags: ["go", "golangci-lint", "github-actions", "ci", "linting", "automation"]
categories: ["devops", "reference", "go"]
---

If you have encountered a build failure in your Go project's GitHub Actions pipeline, you might see an error output similar to this:

```text
run golangci-lint

  Running [/home/runner/golangci-lint-1.64.8-linux-amd64/golangci-lint config path] in [/home/runner/work/go-pattern/go-pattern] ...

  Running [/home/runner/golangci-lint-1.64.8-linux-amd64/golangci-lint run] in [/home/runner/work/go-pattern/go-pattern] ...

  Error: can't load config: the Go language version (go1.24) used to build golangci-lint is lower than the targeted Go version (1.25.0)

  Failed executing command with error: can't load config: the Go language version (go1.24) used to build golangci-lint is lower than the targeted Go version (1.25.0)

  Error: golangci-lint exit with code 3

  Ran golangci-lint in 90ms
```

This error usually appears when your repository's Go version outpaces the Go version used to compile the `golangci-lint` binary that the action downloaded.

When this happens, here is the six-step process to get everything back in sync and passing:

1. **Delete golangcilint.conf files:** Remove any existing `golangcilint.conf` (or `.golangci.yml`) files to clear the slate.
2. **Update the GitHub Action:** Update the `golangci-lint-action` reference in your workflow to the latest version (use external references to verify the most current version).
3. **Upgrade Go everywhere to match:** Ensure your GitHub Actions workflows are using a `version-file: go.mod` (or similar) strategy to keep the Go version automatically in sync with the codebase.
4. **Resolve issues iteratively:** Rerun `golangci-lint` (ensure it is the same version) in a loop to resolve issues. Do not create a new config file immediately; instead, attempt to solve all issues by fixing a couple of them in each loop until they are all resolved.
5. **Format your code:** Run `go fmt ./...`.
6. **Submit:** Once everything is green and formatted, submit your changes.

Here is an example snippet showing an updated workflow configuration:

```yaml
      - uses: actions/checkout@v6
      - uses: actions/setup-go@v6
        with:
          go-version: stable
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: latest
```

By following this process, you avoid getting stuck maintaining outdated lint configurations and keep your CI workflow aligned with the latest Go tools.
