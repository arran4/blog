---
title: "LLM Compliance: Handling Version Upgrades and golangci-lint with go install"
date: 2026-07-23T02:14:10Z
draft: false
tags:
  - llm
  - instructions
  - golangci-lint
  - go
  - github-actions
  - ci
categories:
  - LLM Instructions
  - DevOps
---

When instructing LLM agents (like coding assistants) to update dependencies such as `golangci-lint`, there are often issues with the models defaulting to older, outdated versions based on their training data. If you try to correct them, they may fall back on what they "know" rather than following your instructions, resulting in version downgrades, overly specific version pinning, and regressions.

This post establishes strict rules and alternative strategies to ensure compliance and prevent these downgrades.

## The Problem: Training Data vs. Current Reality

Older models (such as Gemini 1.5) have old versions built into their knowledge base. Even when instructed to use external references, they often default to pinning specific older patch versions (e.g., "v9.4.3") instead of using generic major tags (like "@v9") or the "latest" keyword, and they might inadvertently downgrade Go to match an older tool version.

## The Solution: Explicit Upgrade Instructions

When resolving `golangci-lint` Go version mismatches, LLM agents must follow these exact directives:

1.  **Delete Config Files:** Delete any existing golangci-lint.conf, .golangci.yml, or .golangci.yaml files to start fresh.
2.  **Update Actions to Latest:** Update `golangci-lint` and `golangci-lint-action` to the latest versions. Rely on external references. Use generic major version tags and the `latest` keyword. Do not over-specify version numbers.
3.  **Upgrade Go (Never Downgrade):** Upgrade Go everywhere to match. Ensure GitHub Actions use "go-version-file: go.mod" (or similar) to keep versions in sync. Update the go.mod file to the appropriate newer version required by the project (e.g., 1.25 or 1.26). **Under no circumstances should you downgrade Go or any other dependency to resolve an issue.** If a downgrade seems necessary, submit a partial fix and let CI fail so the user can intervene.
4.  **Testing on the Agent:** When running `golangci-lint` to test fixes on the agent, do not use the system-provided binary as it might be out of sync. Instead, install the latest version directly using:
    ```bash
    go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest
    ```
5.  **Iterative Resolution:** Rerun `golangci-lint` (ensuring it's the exact same version installed above) in a loop to resolve issues. Do not create a new config file. Attempt to solve all issues iteratively (a couple each loop) until done.
6.  **Format:** Run `go fmt ./...`.
7.  **Submit:** Submit the clean, formatted code.

### Correct Configuration Syntax

To avoid specificity issues, use the "latest" keyword for the tool and the major tag for the action:

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

## Alternative Solutions for Version Compliance

To further enforce compliance and reduce the burden on the LLM to guess versions, consider these alternative solutions:

1.  **Dependabot or Renovate:** Implement automated dependency management tools like Dependabot or Renovate. These tools can automatically create Pull Requests for version updates, meaning the LLM doesn't have to resolve the versions itself; it merely has to fix any breaking code changes introduced by the automated PR.
2.  **CI Minimum Version Checks:** Enforce minimum versions directly in the CI pipeline. A bash script could check the `go.mod` version against the `main` branch or a hardcoded minimum, failing the build if a downgrade is detected.
3.  **Explicit Minimum Bounds in Manifests:** Add instructions to adhere to this in the `agents.md` file as part of this process. The `agents.md` file should explicitly instruct agents to respect minimum version bounds specified in files like `agents.md`, `go.mod`, `package.json`, and `pubspec.yaml`. It should also ensure that agents **never** downgrade Go, or any other dependency, to resolve an issue; instead, they should find better ways or submit a partial fix.
