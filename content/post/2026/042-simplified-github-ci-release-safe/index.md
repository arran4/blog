---
title: "Simplified Single GitHub Actions CI/CD File (Release-Safe Update)"
date: 2026-09-03T21:20:00+10:00
draft: false
tags: ["github-actions", "ci", "cd", "go", "node", "dart", "flutter", "qt", "c++", "docker", "goreleaser", "packaging", "release", "agents"]
categories: ["devops", "reference", "automation"]
---

This is the current general-purpose version of my **single GitHub Actions CI/CD workflow** guidance. It supersedes `028-simplified-github-ci-updated` as the default document to give a coding agent when creating or upgrading repository CI.

For the focused explanation of duplicate draft releases, migration checks, and the single-release-owner rule, also see:

- `041-release-safe-single-owner-github-ci`

The resulting workflow must remain bespoke to the repository. This document describes structure, routing, safety rules, and preferred implementation patterns; it is not an instruction to add irrelevant language or packaging lanes.

Most importantly:

> **For one tag, exactly one job or tool owns creation/publication of the GitHub Release.**

A workflow must not create the same release independently from manual dispatch, tag push, `release: published`, GoReleaser, and `softprops/action-gh-release`.

---

## Agent execution assumptions: local repository first

These instructions are deliberately suitable for agents such as Jules that can work effectively on repository files but may have **no GitHub API/UI access and only limited git awareness**.

When following this document, the agent should assume it can usually:

- read and edit files in the checked-out working tree,
- search repository-local files,
- run repository-local commands and tests,
- inspect workflow YAML and release configuration,
- reason about GitHub Actions event flow from the YAML itself.

The agent must **not** assume it can:

- inspect the GitHub Releases page,
- query GitHub Actions runs or logs,
- inspect PRs/issues/comments through GitHub,
- create or update a GitHub PR/issue/release/comment,
- discover repository settings or secrets,
- reliably inspect remote branches/tags/history,
- fetch arbitrary remote information,
- verify the current latest GitHub Action major from the network.

Do not block the repository-file fix on those capabilities.

### Source-of-truth order for a limited agent

Use this order:

1. the user's concrete task/prompt,
2. `AGENTS.md` and other repository-local instructions,
3. the files currently present in the working tree,
4. repository-local tests/configuration/documentation,
5. this guide,
6. remote facts explicitly supplied in the task.

If a fact requires GitHub-side inspection and is not supplied, **do not guess it**. Make the local workflow structurally correct and report the remote check as a human follow-up.

Examples of human follow-ups include:

- whether historical `untagged-*` drafts should be deleted,
- whether a repository secret exists,
- whether a particular GitHub discussion category is enabled,
- whether a workflow has recently succeeded on GitHub,
- whether a newer Action major exists than the one already used/specified.

### Important distinction: generated CI may use git/GitHub even when the agent cannot

The agent's limited git/GitHub awareness does **not** mean the generated GitHub Actions workflow cannot use normal git commands or GitHub Actions features at runtime.

For example, it is valid for the generated workflow to contain:

```bash
git fetch --tags --force
git tag "$TAG"
git push origin "$TAG"
```

The agent only needs to write and statically reason about this workflow. It does not need to perform the release/tag operation itself while implementing the repository change.

Likewise, the workflow may use `GITHUB_TOKEN`, Actions events, artifact actions, GoReleaser, or `softprops/action-gh-release`; those are runtime facilities of GitHub Actions, not capabilities required from the coding agent.

---

## Agent pointer

Generated workflows should identify the guidance used to create them:

```yaml
# Agent rules for generation:
# https://arran4.github.io/blog/post/2026/042-simplified-github-ci-release-safe/
# Release safety details:
# https://arran4.github.io/blog/post/2026/041-release-safe-single-owner-github-ci/
# Built using these posts as reference/guidance.
name: CI/CD
```

When upgrading an existing repository, inspect the existing **local workflow files** and preserve useful repository-specific behaviour. Do not blindly replace a mature workflow with a generic example.

---

## Non-negotiable design rules

1. **Route events explicitly.** Jobs should not infer release intent independently.
2. **One GitHub Release owner per tag.** This is the release-safety invariant.
3. **Manual release dispatch creates/pushes a tag; the tag-push run owns publication.**
4. **`release: published` is downstream.** It must not route back into the primary publisher.
5. **If GoReleaser publishes the GitHub Release, GoReleaser is the sole release owner.**
6. **Do not create a parallel `draft: true` release merely to collect artifacts.** Actions artifacts can stage files until the release owner publishes them.
7. **If human-reviewed drafts are intentionally required, promote the exact same release.** Never create a second release for the tag.
8. **Do not hide release-creation conflicts with `|| true`.** A duplicate creation attempt is a real pipeline error.
9. **Repository-local evidence decides project type.** Do not invent language/build/package lanes.
10. **Repository visibility can be detected at workflow runtime** using `github.event.repository.private` where cost policy differs.
11. **Keep PR-visible tests on PR events.** Do not deduplicate so aggressively that reviewers lose useful checks.
12. **Autofix lanes are language-aware and deterministic.**
13. **Release artifacts should come from tested build paths where practical.**
14. **Do not invent binary releases for libraries/config-only repositories.**
15. **Scheduled maintenance must not accidentally publish a release.**
16. **Use explicit permissions and reduce them per job where practical.**
17. **Preserve existing Action versions unless the task supplies/authorizes a version update.** Do not require a limited agent to browse GitHub for latest majors.
18. **Preserve intentional prerelease semantics** (`rc`, `alpha`, `beta`, `test`, etc.).
19. **Audit every local workflow file.** Multiple workflow files count as multiple possible release owners.
20. **Do not make GitHub-side observation a prerequisite to fixing an obvious local event-graph bug.**

---

## Step 1: inspect the repository locally

Before editing CI, search the checked-out repository. At minimum inspect:

```text
AGENTS.md
.github/workflows/*.yml
.github/workflows/*.yaml
.goreleaser.yml
.goreleaser.yaml
goreleaser.yml
goreleaser.yaml
package.json
pubspec.yaml
go.mod
CMakeLists.txt
Makefile
Dockerfile
```

Use repository-local search for release creators and routing terms:

```text
softprops/action-gh-release
gh release create
goreleaser/goreleaser-action
release:
types: [published]
publish-draft
promote-release
run_release
draft: true
workflow_dispatch
refs/tags
```

From those files, build a simple event graph:

- which event computes a version,
- which event creates/pushes a tag,
- which jobs build release artifacts,
- which job/tool creates the GitHub Release,
- which jobs only consume an already-published release.

This local graph is sufficient to identify the duplicate-owner class of bug. Do not require access to the GitHub Releases page to prove that two local publisher paths can race.

---

## Step 2: triggers and manual modes

A useful baseline is:

```yaml
name: CI/CD

on:
  push:
    branches: [main, master]
    tags:
      - 'v*'
      - 'v*.*.*'
      - 'v*.*.*-rc*'
      - 'v*.*.*-beta*'
      - 'v*.*.*-alpha*'
      - 'v*.*.*-test*'
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review, closed]
    branches: [main, master]
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      mode:
        description: "Pipeline mode"
        required: true
        default: "lint-fix"
        type: choice
        options:
          - lint-fix
          - build
          - release-major
          - release-minor
          - release-patch
          - release-test
          - release-rc
          - release-alpha
          - monthly-maintenance
      release_version_override:
        description: "Optional explicit release version, for example 2.4.0 or 2.4.0-rc.2"
        required: false
        default: ""
        type: string
      allow_prs:
        description: "Allow CI automation to open pull requests"
        required: false
        default: true
        type: boolean
  schedule:
    - cron: '0 19 1 * *'
    - cron: '41 2 * * *'
```

The `release: published` trigger can remain, but **not as a release publisher**. It is for downstream work such as site refreshes, notifications, reports, or metadata refreshes.

---

## Step 3: concurrency and permissions

Use concurrency to collapse redundant churn, but not as the only routing mechanism:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: read
```

Grant write permissions only to jobs that need them. For example:

```yaml
permissions:
  contents: write
```

for a tag-pushing/release-publishing job, or:

```yaml
permissions:
  contents: write
  pull-requests: write
```

for CI automation that itself opens an autofix PR.

The coding agent does not need GitHub write access merely to author these permissions in YAML.

---

## Step 4: event router

Use one router as the policy authority:

```yaml
jobs:
  route:
    name: Route event
    runs-on: ubuntu-latest
    outputs:
      run_code_checks: ${{ steps.route.outputs.run_code_checks }}
      run_build: ${{ steps.route.outputs.run_build }}
      run_release: ${{ steps.route.outputs.run_release }}
      run_cleanup: ${{ steps.route.outputs.run_cleanup }}
      run_post_release: ${{ steps.route.outputs.run_post_release }}
      is_monthly: ${{ steps.route.outputs.is_monthly }}
      is_nightly: ${{ steps.route.outputs.is_nightly }}
    steps:
      - id: route
        shell: bash
        run: |
          set -euo pipefail

          run_code_checks=false
          run_build=false
          run_release=false
          run_cleanup=false
          run_post_release=false
          is_monthly=false
          is_nightly=false

          case "${{ github.event_name }}" in
            push)
              run_code_checks=true
              if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
                run_build=true
                run_release=true
              fi
              ;;

            pull_request)
              if [[ "${{ github.event.action }}" == "closed" ]]; then
                if [[ "${{ github.event.pull_request.merged }}" != "true" ]]; then
                  run_cleanup=true
                fi
              else
                run_code_checks=true
              fi
              ;;

            workflow_dispatch)
              case "${{ inputs.mode }}" in
                lint-fix)
                  run_code_checks=true
                  is_nightly=true
                  ;;
                build)
                  run_code_checks=true
                  run_build=true
                  ;;
                release-*)
                  # Manual release dispatch prepares/pushes a tag only.
                  # It MUST NOT publish the GitHub Release in this run.
                  run_code_checks=true
                  ;;
                monthly-maintenance)
                  run_code_checks=true
                  is_monthly=true
                  ;;
              esac
              ;;

            release)
              # This release already exists and is published.
              run_post_release=true
              ;;

            schedule)
              run_code_checks=true
              if [[ "${{ github.event.schedule }}" == "0 19 1 * *" ]]; then
                is_monthly=true
              else
                is_nightly=true
              fi
              ;;
          esac

          echo "run_code_checks=$run_code_checks" >> "$GITHUB_OUTPUT"
          echo "run_build=$run_build" >> "$GITHUB_OUTPUT"
          echo "run_release=$run_release" >> "$GITHUB_OUTPUT"
          echo "run_cleanup=$run_cleanup" >> "$GITHUB_OUTPUT"
          echo "run_post_release=$run_post_release" >> "$GITHUB_OUTPUT"
          echo "is_monthly=$is_monthly" >> "$GITHUB_OUTPUT"
          echo "is_nightly=$is_nightly" >> "$GITHUB_OUTPUT"
```

The critical behaviour is: **manual `release-*` dispatch does not publish a GitHub Release in that same workflow run**.

---

## Step 5: prepare the next release tag

The manual release path calculates one validated tag. Reuse existing repository-local version policy where possible.

```yaml
  prepare-release-tag:
    name: Prepare release tag
    needs: [route]
    if: ${{ github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-') }}
    runs-on: ubuntu-latest
    outputs:
      release_tag: ${{ steps.tag.outputs.release_tag }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Setup git-tag-inc
        uses: arran4/git-tag-inc-action@v1
        with:
          mode: install
      - id: tag
        shell: bash
        run: |
          set -euo pipefail

          MODE="${{ inputs.mode }}"
          OVERRIDE="${{ inputs.release_version_override }}"
          git fetch --tags --force

          if [[ -n "$OVERRIDE" ]]; then
            next_tag="v${OVERRIDE#v}"
          else
            case "$MODE" in
              release-major) level="major"; suffix="" ;;
              release-minor) level="minor"; suffix="" ;;
              release-patch) level="patch"; suffix="" ;;
              release-test)  level="patch"; suffix="test" ;;
              release-rc)    level="patch"; suffix="rc" ;;
              release-alpha) level="patch"; suffix="alpha" ;;
              *) echo "Unsupported release mode: $MODE" >&2; exit 1 ;;
            esac
            args=(-print-version-only "$level")
            [[ -n "$suffix" ]] && args+=("$suffix")
            next_tag=$(git-tag-inc "${args[@]}")
          fi

          [[ "$next_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.]+)?$ ]] || {
            echo "Invalid tag: $next_tag" >&2
            exit 1
          }

          if git rev-parse "$next_tag" >/dev/null 2>&1; then
            echo "Tag already exists: $next_tag" >&2
            exit 1
          fi

          echo "release_tag=$next_tag" >> "$GITHUB_OUTPUT"
```

The coding agent does not need to run `git fetch` itself during implementation. This is runtime logic for the resulting GitHub Actions job.

If the repository stores a source version (`CMakeLists.txt`, `package.json`, `pubspec.yaml`, etc.), inspect that local file and preserve the project's established relationship between source version and tags.

---

## Step 6: manual release dispatch pushes the tag only

```yaml
  manual-release-tag:
    name: Push release tag
    needs: [prepare-release-tag]
    if: ${{ github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-') }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Push prepared tag
        env:
          TAG: ${{ needs.prepare-release-tag.outputs.release_tag }}
        shell: bash
        run: |
          set -euo pipefail
          git fetch --tags --force
          if git rev-parse "$TAG" >/dev/null 2>&1; then
            echo "Tag already exists: $TAG" >&2
            exit 1
          fi
          git tag "$TAG"
          git push origin "$TAG"
```

**Do not call `gh release create` here.** The tag push starts a fresh workflow run. That tag-push run is the publisher.

Do not use `|| true` to mask tag/release collisions.

---

## Step 7: capability discovery from local files

Discovery should reflect the actual repository:

```yaml
  discover:
    name: Discover capabilities
    needs: [route]
    runs-on: ubuntu-latest
    outputs:
      has_go: ${{ steps.detect.outputs.has_go }}
      has_node: ${{ steps.detect.outputs.has_node }}
      has_dart: ${{ steps.detect.outputs.has_dart }}
      has_qt_cpp: ${{ steps.detect.outputs.has_qt_cpp }}
      has_docker: ${{ steps.detect.outputs.has_docker }}
      has_goreleaser: ${{ steps.detect.outputs.has_goreleaser }}
    steps:
      - uses: actions/checkout@v7
      - id: detect
        shell: bash
        run: |
          [[ -f go.mod ]] && echo "has_go=true" || echo "has_go=false"
          [[ -f package.json ]] && echo "has_node=true" || echo "has_node=false"
          [[ -f pubspec.yaml ]] && echo "has_dart=true" || echo "has_dart=false"
          if [[ -f CMakeLists.txt ]] && grep -qiE 'Qt|KF[56]|ECM' CMakeLists.txt; then
            echo "has_qt_cpp=true"
          else
            echo "has_qt_cpp=false"
          fi
          [[ -f Dockerfile ]] && echo "has_docker=true" || echo "has_docker=false"
          if [[ -f .goreleaser.yml || -f .goreleaser.yaml || -f goreleaser.yml || -f goreleaser.yaml ]]; then
            echo "has_goreleaser=true"
          else
            echo "has_goreleaser=false"
          fi
```

If the repository type is obvious, install-time hard-coding can be clearer than elaborate runtime detection.

---

## Step 8: language checks

Use only the lanes justified by repository-local files.

### Go

```yaml
  go-checks:
    needs: [route, discover]
    if: ${{ needs.route.outputs.run_code_checks == 'true' && needs.discover.outputs.has_go == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
          cache: true
      - run: go test ./...
      - run: go vet ./...
```

Add repository-specific generators/static checks only when the local project already establishes them or the task explicitly asks for them.

### Node

```yaml
  node-checks:
    needs: [route, discover]
    if: ${{ needs.route.outputs.run_code_checks == 'true' && needs.discover.outputs.has_node == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: lts/*
          cache: npm
      - run: npm ci
      - run: npm test --if-present
      - run: npm run lint --if-present
```

### Dart / Flutter

Inspect `pubspec.yaml` and existing scripts/workflows. Do not add Flutter setup merely because Dart is present.

### Qt/C++ / CMake

Use the dependencies and build commands already evidenced by `CMakeLists.txt`, README/development docs, package manifests, Dockerfiles, or existing workflow jobs.

Typical shape:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
```

### Make/C

Prefer existing `make`, `make test`, or project scripts instead of inventing a second build system.

---

## Step 9: autofix lane

Autofix is deterministic mechanical maintenance, not ordinary PR validation.

Typical condition:

```yaml
if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'lint-fix' && inputs.allow_prs == true }}
```

The **workflow**, not the coding agent, may use GitHub permissions/actions/`gh` to open an autofix PR at runtime. Jules does not need direct GitHub access to author that behaviour.

Possible fixes include:

- `gofmt`,
- Prettier,
- Dart/Flutter formatting,
- clang-format,
- deterministic generated-file refreshes.

Only create a CI-generated PR when the working tree actually changes.

---

## Step 10: build artifacts

Build jobs are separate from GitHub Release creation:

```yaml
  build-release-artifacts:
    needs: [route, discover]
    if: ${{ needs.route.outputs.run_build == 'true' || needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # ... project-specific build ...
      - uses: actions/upload-artifact@v4
        with:
          name: app-release
          path: dist/
          retention-days: 1
```

Actions artifacts are staging inputs. They are not a reason to pre-create an independent draft GitHub Release.

---

## Step 11: choose one release owner from local configuration

Choose exactly one:

### A. GoReleaser project

If a local GoReleaser config and existing workflow show GoReleaser publishing releases, GoReleaser owns the GitHub Release.

### B. Non-GoReleaser binary/artifact project

One semantic tag-push `github-release` job owns the GitHub Release.

### C. Library/config/non-binary project

The tag-push owner may create a notes-only GitHub Release if releases are desired. Do not invent binary artifacts.

### D. Intentional human-reviewed draft process

Only preserve this if the repository-local workflow clearly implements/needs it. One job creates the draft; promotion modifies that same release. Do not infer a draft-review requirement merely because an old generated workflow happens to contain `draft: true`.

Never combine A and B for the same tag.

---

## Step 12A: GoReleaser as sole release owner

```yaml
  goreleaser:
    name: GoReleaser
    needs: [route, discover, go-checks]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && needs.discover.outputs.has_goreleaser == 'true' && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Preserve any repository-local signing/package/tap environment required by the existing GoReleaser config.

**Do not add another `softprops/action-gh-release` publisher after GoReleaser.**

**Do not add a manual `gh release create` publisher before GoReleaser.**

---

## Step 12B: non-GoReleaser GitHub Release owner

```yaml
  github-release:
    name: Publish GitHub release
    needs: [route, discover, build-release-artifacts]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && needs.discover.outputs.has_goreleaser != 'true' && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v5
        with:
          path: dist-release
          pattern: '*-release'
          merge-multiple: true

      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          draft: false
          generate_release_notes: true
          prerelease: ${{ contains(github.ref_name, '-rc') || contains(github.ref_name, '-alpha') || contains(github.ref_name, '-beta') || contains(github.ref_name, '-test') }}
          files: dist-release/**
```

For a notes-only project, omit the files/artifact dependency.

The key is one publisher, not the particular release action chosen.

---

## Step 13: remove the known duplicate-draft architecture

Do not leave this shape in a generated/upgraded workflow:

```yaml
manual-gh-release:
  run: gh release create "$TAG" --generate-notes || true

publish-draft:
  uses: softprops/action-gh-release@v2
  with:
    draft: true

promote-release:
  run: echo "Promotion step placeholder (gh api patch release draft=false)"
```

Also do not route `release: published` back into the same primary release lane.

Do not 'fix' the problem by merely changing `draft: true` to `draft: false`. First choose the one owner and remove competing creator paths.

A limited agent can make this determination from the workflow YAML alone.

---

## Step 14: intentional draft releases

A draft process is valid only when the repository actually requires review before publication. Then:

1. one job creates the draft,
2. the workflow resolves/records that release,
3. assets go to that exact release,
4. promotion modifies the same release to `draft=false`,
5. no other job creates a release for the tag.

A placeholder `echo` is not promotion.

If the local repository does not evidence an intentional reviewed-draft process, prefer direct tag-push publication.

---

## Step 15: `release: published` is downstream

```yaml
  post-release:
    name: Post-release work
    needs: [route]
    if: ${{ needs.route.outputs.run_post_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Consume the already-published release here"
```

Examples include release-page refreshes, notifications, metadata/index refreshes, or documentation deployment.

It must not call `gh release create`, GoReleaser release publication, or another release-creation API for the same version.

---

## Step 16: containers and source packages

Container registry publication and source-package generation may consume the same semantic tag, but they do not need to create another GitHub Release.

Treat them as either:

- release-adjacent publishers to their own registry, or
- artifact producers feeding the one GitHub Release owner.

Preserve project-local packaging behaviour. Do not add source Debian/RPM/container lanes merely because this guide mentions them.

---

## Step 17: prerelease semantics

Preserve the project's existing tag convention. Common examples:

- `v1.2.3` -> stable,
- `v1.2.3-rc.1` -> prerelease,
- `v1.2.3-alpha.1` -> prerelease,
- `v1.2.3-beta.1` -> prerelease,
- `v1.2.3-test.1` -> project-specific test/prerelease behaviour.

If `test` tags are intentionally artifact-only, encode that in routing rather than creating abandoned drafts.

---

## Step 18: cleanup and scheduled maintenance

PR-close cleanup should be narrow. Do not rerun expensive build/release work on `pull_request: closed` merely because the workflow was triggered.

Scheduled runs may perform repository-local checks such as:

- generated-file consistency,
- lint/fmt drift,
- security tooling already present in the repository,
- reports,
- optional autofix automation.

Schedules must never accidentally set the primary release path.

---

## Step 19: local release-safety audit when upgrading

Answer these questions **from repository files**:

1. Which workflow event can request/compute a version?
2. Which workflow job creates or pushes the tag?
3. Which jobs build release artifacts?
4. Which exact job/tool creates the GitHub Release?
5. Can manual dispatch and tag push both create a release?
6. Can `release: published` re-enter release creation?
7. Does GoReleaser already publish the release?
8. Does another local workflow also publish semantic tags?
9. Does any `|| true` hide release/tag creation conflicts?
10. Is `publish-draft` paired with real promotion, or only a placeholder/second creator?

Choose one release owner and make every other path an input producer or downstream consumer.

Historical `untagged-*` drafts are useful corroborating evidence **when a human or GitHub-capable reviewer supplies them**, but Jules does not need access to them to repair a locally obvious competing-publisher graph.

---

## Step 20: Action versions for a network-limited agent

Do not instruct Jules to browse GitHub to discover latest Action majors.

Use this policy:

1. If the task explicitly supplies desired Action versions, use them.
2. Otherwise preserve existing repository Action majors when they are compatible with the change.
3. For a newly introduced action, use the version specified by this guide/task or match the established repository convention.
4. Do not perform unrelated Action-major churn as part of a release-ownership fix.
5. If latest-major verification is important, list it as a **human/GitHub-capable review item** rather than guessing.

This keeps a focused CI repair from being blocked by unavailable network/GitHub access.

---

## Step 21: local validation

A coding agent should validate everything it can locally:

- parse/check YAML with an available parser,
- run `actionlint` if it is already available or straightforward in the provided environment,
- inspect every `needs` dependency and referenced output,
- ensure job conditions are meaningful for all triggering events,
- ensure manual inputs are not unsafely referenced on unrelated events,
- ensure `release: published` cannot reach the release creator,
- ensure only one GitHub Release creator exists for a semantic tag,
- ensure GoReleaser and `softprops/action-gh-release` are not both owners,
- ensure required artifact jobs are reachable on the tag-push run,
- run relevant repository-local tests/static checks.

Do **not** require the agent to inspect GitHub CI status after implementation.

If a validator/tool is unavailable locally, say so in the handoff rather than installing arbitrary tooling or pretending it passed.

---

## Step 22: handoff from Jules / a limited agent

The implementation handoff should be concise and repository-local. Report:

- files changed,
- old release-owner graph,
- new release-owner graph,
- local checks/tests run and their results,
- any checks not possible in the provided environment,
- any **human/GitHub-side follow-ups** that remain.

Examples of valid human follow-ups:

- inspect/remove obsolete historical draft releases,
- verify a required repository secret exists,
- observe the next release run on GitHub,
- verify latest Action majors if desired,
- create/update PR metadata or issue-closing text if the agent platform does not expose it.

Do not ask Jules to perform those GitHub-side operations if its environment cannot.

---

## Recommended release event flow

```text
manual workflow_dispatch release-patch
        |
        v
compute/validate vX.Y.Z
        |
        v
workflow pushes vX.Y.Z tag
        |
        +------------------------------+
        | fresh tag-push workflow run  |
        +------------------------------+
                |
                v
        lint/test/build artifacts
                |
                v
       ONE release owner only
          /             \
   GoReleaser      github-release job
       (one or the other, never both)
                |
                v
        GitHub Release published
                |
                v
      release: published event
                |
                v
    downstream consumers only
```

The coding agent can prove this structure from YAML without seeing a live GitHub run.

---

## Migration from `006`, `011`, and `028`

When a local workflow says it was generated from an older CI article, do not merely update the pointer comment. Migrate the release graph:

- replace competing manual `gh release create` publication with tag-push ownership,
- remove independent `publish-draft` creators when another publisher exists,
- remove placeholder `promote-release` jobs,
- stop routing `release: published` into primary release creation,
- make GoReleaser sole owner where the local config shows it publishes GitHub Releases,
- keep tested artifact-build jobs as inputs,
- preserve intentional prerelease modes,
- leave historical GitHub Release cleanup to a separate human/GitHub-capable administrative step.

Use `041-release-safe-single-owner-github-ci` for the focused rationale and migration checklist.

---

## Final agent rule

When Jules or another limited coding agent is asked to create/upgrade a workflow from this article:

- read repository-local instructions first,
- inspect repository files rather than GitHub UI/state,
- preserve project-specific behaviour,
- do not browse for Action versions unless the environment explicitly provides that capability,
- do not require the agent to create/manage a PR or issue,
- perform local validation,
- clearly identify remote follow-ups instead of guessing,
- and **prove from the local event graph that one semantic tag can reach at most one GitHub Release owner path**.

That last condition is part of correctness.