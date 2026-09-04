---
title: "Simplified Single GitHub Actions CI/CD File (Release-Safe Update)"
date: 2026-09-03T21:20:00+10:00
draft: false
tags: ["github-actions", "ci", "cd", "go", "node", "dart", "flutter", "qt", "c++", "docker", "goreleaser", "packaging", "release"]
categories: ["devops", "reference", "automation"]
---

This is the current general-purpose version of my **single GitHub Actions CI/CD workflow** guidance. It supersedes `028-simplified-github-ci-updated` as the default document to give an agent when creating or upgrading a repository CI workflow.

For the focused explanation of duplicate draft releases, migration checks, and the single-release-owner rule, also see:

- `041-release-safe-single-owner-github-ci`

The resulting workflow should remain bespoke to the repository. This document describes the structure, routing, safety rules, and preferred implementation patterns; it is not an instruction to add irrelevant language or packaging lanes to every project.

The target outcome is one understandable `ci.yml` which can handle:

- push validation,
- pull-request validation,
- semantic-version tags,
- explicit manual build/release modes,
- scheduled maintenance,
- autofix PRs where appropriate,
- language-specific lint/test/build lanes,
- release artifacts,
- GoReleaser where appropriate,
- Docker/container publication where appropriate,
- source package generation where appropriate,
- post-release notification work,
- and cleanup lifecycle.

Most importantly, this revision fixes an unsafe release architecture used by older versions of this guide:

> **For one tag, exactly one job or tool owns creation/publication of the GitHub Release.**

A workflow must not create the same release independently from manual dispatch, tag push, `release: published`, GoReleaser, and `softprops/action-gh-release`.

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

When upgrading an existing repository, inspect the existing workflow and preserve useful repository-specific behaviour. Do not blindly replace a mature workflow with a generic example.

---

## Non-negotiable design rules

1. **Route events explicitly.** Jobs should not infer release intent independently.
2. **One GitHub Release owner per tag.** This is the release-safety invariant.
3. **Manual release dispatch publishes the release in its own run, or uses a specific PAT/App to trigger a downstream release run.**
4. **`release: published` is downstream.** It must not route back into the primary publisher.
5. **If GoReleaser publishes the GitHub Release, GoReleaser is the sole release owner.**
6. **Do not create a parallel `draft: true` release merely to collect artifacts.** Artifact jobs can use Actions artifacts until the release owner publishes them.
7. **If human-reviewed drafts are intentionally required, promote the exact same release ID.** Never create a second release for the tag.
8. **Do not hide release-creation conflicts with `|| true`.** A duplicate creation attempt is a real pipeline error.
9. **Project-type decisions are mostly install/template-time.** Runtime discovery is a safety net, not an excuse to make every job dynamically generic.
10. **Repository visibility is auto-detected** using `github.event.repository.private` where cost policy differs.
11. **Public repositories normally run broader checks.** Private repositories may use a conservative profile.
12. **Keep PR-visible tests on PR events.** Do not deduplicate so aggressively that reviewers lose useful checks.
13. **Autofix lanes are language-aware.** They should make deterministic mechanical changes and create focused PRs.
14. **Release artifacts come only from tested build paths where practical.**
15. **Do not invent binary release lanes for libraries/config-only repositories.**
16. **Scheduled maintenance should not accidentally publish a release.**
17. **Use explicit permissions and reduce them per job where practical.**
18. **Verify current GitHub Action major versions externally before generation.** Examples in this article can age.
19. **Preserve intentional prerelease semantics** (`rc`, `alpha`, `beta`, `test`, etc.).
20. **Keep unrelated release systems from racing.** Multiple workflow files count as multiple possible owners too.

---

## Step 1: triggers and manual modes

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
        description: "Allow automation to open pull requests"
        required: false
        default: true
        type: boolean
  schedule:
    # Preferred heavy monthly run: the 2nd at about 5am AEST, deliberately ignoring DST.
    - cron: '0 19 1 * *'
    # Optional lightweight/nightly maintenance.
    - cron: '41 2 * * *'
```

The `release: published` trigger remains useful, but **not as a release publisher**. Note that events created using `GITHUB_TOKEN` are generally subject to the same workflow-recursion suppression, so do not promise that a GitHub Release created using `GITHUB_TOKEN` will automatically start another `release: published` workflow. For downstream work, prefer jobs in the existing workflow, or explicitly document that an App/PAT is required when a separate event-triggered workflow is genuinely required.

---

## Step 2: concurrency and permissions

Use concurrency to collapse redundant churn, but do not use it as the only event-routing mechanism:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: read
```

Grant write permissions only on jobs that need them. For example:

```yaml
permissions:
  contents: write
```

for a release-publishing job, and:

```yaml
permissions:
  contents: write
  pull-requests: write
```

for an autofix PR job.

---

## Step 3: event router

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
                  # A manual release mode pushes the tag and publishes the release in the same run.
                  # It sets run_release=true to publish immediately.
                  run_build=true
                  run_release=true
                  run_code_checks=true
                  ;;
                monthly-maintenance)
                  run_code_checks=true
                  is_monthly=true
                  ;;
              esac
              ;;

            release)
              # The release already exists and is published.
              # Never route this event back into release creation.
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



---

## Step 4: prepare the next release tag

The unified release path requires one validated tag.

**Recovery semantics:** After a tag is created and pushed, if the subsequent publication fails (e.g. network error), a normal auto-incrementing re-run must not be used as it will silently advance to a completely new version. Recovery must explicitly reuse the exact same tag by providing it via `release_version_override`. The workflow will verify the remote tag correctly points to the validated commit and safely resume publication.

```yaml
  prepare-release-tag:
    name: Prepare release tag
    needs: [route]
    if: ${{ needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    outputs:
      release_tag: ${{ steps.tag.outputs.release_tag }}
      next_version: ${{ steps.tag.outputs.next_version }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Setup git-tag-inc
        if: ${{ github.event_name == 'workflow_dispatch' }}
        uses: arran4/git-tag-inc-action@v1
        with:
          mode: install
      - id: tag
        shell: bash
        run: |
          set -euo pipefail

          if [[ "${{ github.event_name }}" == "push" ]]; then
            echo "release_tag=${{ github.ref_name }}" >> "$GITHUB_OUTPUT"
            echo "next_version=${{ github.ref_name }}" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          MODE="${{ inputs.mode }}"
          OVERRIDE="${{ inputs.release_version_override }}"

          git fetch --tags --force

          if [[ -n "$OVERRIDE" ]]; then
            OVERRIDE="${OVERRIDE#v}"
            next_tag="v$OVERRIDE"
          else
            case "$MODE" in
              release-major) level="major"; suffix="" ;;
              release-minor) level="minor"; suffix="" ;;
              release-patch) level="patch"; suffix="" ;;
              release-rc) level="patch"; suffix="rc" ;;
              release-alpha) level="patch"; suffix="alpha" ;;
              release-test) level="patch"; suffix="test" ;;
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
            # Safe recovery semantics: verify existing tag against remote
            REMOTE_TAG_SHA=$(git ls-remote --tags origin "refs/tags/$next_tag" | awk '{print $1}')
            if [[ "$REMOTE_TAG_SHA" == "${GITHUB_SHA}" ]]; then
              echo "Tag $next_tag exists and points to GITHUB_SHA. Safe to retry."
            else
              echo "Tag already exists and points to $REMOTE_TAG_SHA (expected ${GITHUB_SHA}): $next_tag" >&2
              echo "To retry a failed publication for this exact version, ensure release_version_override is used and GITHUB_SHA matches." >&2
              exit 1
            fi
          fi

          echo "release_tag=$next_tag" >> "$GITHUB_OUTPUT"

          clean_tag="${next_tag#v}"
          clean_tag="${clean_tag%%-*}"
          IFS='.' read -r maj min pat <<< "$clean_tag"
          echo "next_version=${maj:-0}.${min:-0}.$(( ${pat:-0} + 1 ))-SNAPSHOT" >> "$GITHUB_OUTPUT"
```

---

## Step 5: Release Context & Validation Gate

Keep the manual and external-tag paths mutually exclusive so they cannot create competing releases. We introduce a common `release-context` job that runs for BOTH `push` tags and `workflow_dispatch` manual releases *after* all validation gates successfully pass. It normalizes the tag, safely pushes it if it was a manual request, and exports the tag for downstream publishers.

```yaml
  release-context:
    name: Release Context & Gate
    # Wait for explicit validation gates before allowing ANY release to proceed.
    # Only list jobs here that are REQUIRED and GUARANTEED to run for this repository
    # (or define a unified validation-gate job) so this doesn't skip.
    needs: [route, prepare-release-tag, build-release-artifacts]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    outputs:
      release_tag: ${{ steps.export.outputs.release_tag }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Normalize and push tag
        id: export
        shell: bash
        run: |
          set -euo pipefail

          TAG="${{ needs.prepare-release-tag.outputs.release_tag }}"
          echo "release_tag=$TAG" >> "$GITHUB_OUTPUT"

          if [[ "${{ github.event_name }}" == "push" ]]; then
            exit 0
          fi

          git fetch --tags --force
          REMOTE_TAG_SHA=$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}')

          if [[ -n "$REMOTE_TAG_SHA" ]]; then
            if [[ "$REMOTE_TAG_SHA" == "${GITHUB_SHA}" ]]; then
              echo "Tag $TAG already exists on remote and points to the correct SHA. Continuing safely."
              exit 0
            else
              echo "Tag $TAG already exists on remote but points to a different commit ($REMOTE_TAG_SHA). Failing." >&2
              exit 1
            fi
          fi

          git tag "$TAG" "${GITHUB_SHA}"

          git push origin "$TAG" || (
            VERIFY_SHA=$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}')
            if [[ "$VERIFY_SHA" == "${GITHUB_SHA}" ]]; then
              echo "Tag successfully verified on remote after push error."
            else
              echo "Tag push failed and remote verification failed." >&2
              exit 1
            fi
          )
```

Do NOT expect the manual tag push to start another workflow when using `GITHUB_TOKEN`. This job acts as the unified bridge to the same-run publisher.

### Alternative: strict tag-push-owner model

If the design specifically requires the pushed tag to start a new workflow and that new release run to be the sole publisher, the tag MUST be pushed using a GitHub App installation token or PAT rather than `GITHUB_TOKEN`.

- Use an explicit secret such as `TAG_PUSH_TOKEN`.
- Fail clearly when it is absent.
- Never silently fall back to `GITHUB_TOKEN`, because that produces a tag without the required follow-up workflow.
- Explain this is an operational prerequisite that must be configured for each repository unless the credential is otherwise centrally supplied.

---

## Step 6: capability discovery

Discovery should reflect the actual repository and normally remain lightweight:

```yaml
  discover:
    name: Discover capabilities
    needs: [route]
    runs-on: ubuntu-latest
    outputs:
      profile: ${{ steps.profile.outputs.profile }}
      has_go: ${{ steps.detect.outputs.has_go }}
      has_node: ${{ steps.detect.outputs.has_node }}
      has_dart: ${{ steps.detect.outputs.has_dart }}
      has_flutter: ${{ steps.detect.outputs.has_flutter }}
      has_qt_cpp: ${{ steps.detect.outputs.has_qt_cpp }}
      has_make_c: ${{ steps.detect.outputs.has_make_c }}
      has_docker: ${{ steps.detect.outputs.has_docker }}
      has_goreleaser: ${{ steps.detect.outputs.has_goreleaser }}
    steps:
      - uses: actions/checkout@v7
      - id: detect
        shell: bash
        run: |
          set -euo pipefail
          [[ -f go.mod ]] && echo "has_go=true" || echo "has_go=false"
          [[ -f package.json ]] && echo "has_node=true" || echo "has_node=false"
          [[ -f pubspec.yaml ]] && echo "has_dart=true" || echo "has_dart=false"
          if [[ -f pubspec.yaml ]] && grep -q '^  flutter:' pubspec.yaml; then
            echo "has_flutter=true"
          else
            echo "has_flutter=false"
          fi
          if [[ -f CMakeLists.txt ]] && grep -qiE 'Qt|KF[56]|ECM' CMakeLists.txt; then
            echo "has_qt_cpp=true"
          else
            echo "has_qt_cpp=false"
          fi
          [[ -f Makefile || -f makefile ]] && echo "has_make_c=true" || echo "has_make_c=false"
          [[ -f Dockerfile || -f docker-compose.yml || -f compose.yml ]] && echo "has_docker=true" || echo "has_docker=false"
          if [[ -f .goreleaser.yml || -f .goreleaser.yaml || -f goreleaser.yml || -f goreleaser.yaml ]]; then
            echo "has_goreleaser=true"
          else
            echo "has_goreleaser=false"
          fi
      - id: profile
        shell: bash
        run: |
          if [[ "${{ github.event.repository.private }}" == "true" ]]; then
            echo "profile=private" >> "$GITHUB_OUTPUT"
          else
            echo "profile=public" >> "$GITHUB_OUTPUT"
          fi
```

If the repository type is already obvious, hard-coded comments/outputs are often clearer than elaborate runtime discovery.

---

## Step 7: language checks

Each language lane should be explicit enough to understand and debug.

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

Add repository-specific generated-code checks, staticcheck, golangci-lint, integration tests, race tests, or matrices when useful. Avoid multiplying expensive jobs without a reason.

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

Use the project-appropriate setup action and run formatting analysis/tests. Do not add Flutter when the repository is plain Dart.

### Qt/C++ / CMake

Use an environment with the project's actual Qt/KDE dependencies. Typical work includes:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_EXPORT_COMPILE_COMMANDS=ON
cmake --build build -j"$(nproc)"
ctest --test-dir build --output-on-failure
```

Where useful, add `clang-format --dry-run --Werror`, `clang-tidy`, or `cppcheck`, but tune them to the repository rather than generating a noisy theoretical configuration.

### Make/C

Use the project's existing build/test interface. Prefer `make`, `make test`, project scripts, or established targets instead of inventing a second build system.

---

## Step 8: autofix lane

Autofix is for deterministic mechanical fixes. It should be explicit manual/scheduled automation, not surprise commits from ordinary PR validation.

Typical condition:

```yaml
if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'lint-fix' && inputs.allow_prs == true }}
```

Possible fixes include:

- `gofmt` / safe Go fixes,
- Prettier,
- Dart/Flutter formatting,
- clang-format,
- generated-file refreshes with deterministic tooling.

Open a focused PR only when the working tree actually changed. Use a stable branch naming convention and avoid duplicate autofix PRs.

---

## Step 9: build artifacts

Build jobs should be separate from GitHub Release creation. This lets validation/release policy stay clear and prevents builders from becoming accidental competing publishers.

A build lane can upload short-lived Actions artifacts:

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

These Actions artifacts are staging inputs. They are not a reason to create an independent draft GitHub Release.

---

## Step 10: release ownership decision

Before writing publisher jobs, choose one of these paths:

### A. GoReleaser project

GoReleaser owns the GitHub Release.

### B. Non-GoReleaser binary/artifact project

One `github-release` job owns the GitHub Release.

### C. Library/config/non-binary project

The release owner may create a notes-only GitHub Release if releases are desired. Do not invent binary artifacts.

### D. Intentional human-reviewed draft process

One job creates the draft and records the release ID. Promotion modifies that same release. This is an explicit exception, not the default architecture.

Never combine A and B for the same tag.

---

## Step 11A: GoReleaser as sole release owner

Run GoReleaser as the sole publisher in the unified release lane:

```yaml
  goreleaser:
    name: Run GoReleaser
    needs: [route, discover, go-checks, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && needs.discover.outputs.has_goreleaser == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
          fetch-tags: true
      - uses: actions/setup-go@v7
        with:
          go-version: stable
      - uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GORELEASER_CURRENT_TAG: ${{ needs.release-context.outputs.release_tag }}
```

If GoReleaser needs Homebrew, package registries, signing credentials, or another repository token, inject those secrets into this owner job/config as appropriate.

**Do not add another `softprops/action-gh-release` publisher after GoReleaser.**

**Do not add a manual `gh release create` job before GoReleaser.**

---

## Step 11B: non-GoReleaser GitHub Release owner

One job collects tested artifacts and publishes the release:

```yaml
  github-release:
    name: Publish GitHub release
    needs: [route, discover, build-release-artifacts, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && needs.discover.outputs.has_goreleaser != 'true' }}
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
          tag_name: ${{ needs.release-context.outputs.release_tag }}
          prerelease: ${{ contains(needs.release-context.outputs.release_tag, '-rc') || contains(needs.release-context.outputs.release_tag, '-alpha') || contains(needs.release-context.outputs.release_tag, '-beta') || contains(needs.release-context.outputs.release_tag, '-test') }}
          files: dist-release/**
```

For a notes-only project, omit `files:` and the artifact dependency.

The key is not which GitHub release action is used; the key is that **there is one publisher**.

---

## Step 12: what NOT to generate

Older versions of this guidance could produce something like:

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

Do not generate that architecture.

It can leave orphaned `untagged-*` drafts when one path creates a draft and another path publishes the canonical release.

Do not repair it by simply changing `draft: true` to `draft: false`; first determine who should own the release and remove the competing publisher paths.

---

## Step 13: intentional draft releases

A draft process is valid when review before publication is genuinely required. In that case:

1. one job creates the draft,
2. record/resolve its release ID,
3. upload all assets to that exact release,
4. promotion patches that same release to `draft=false`,
5. no other job creates a GitHub Release for the tag.

A placeholder `echo` is not promotion.

If the repository does not need human-reviewed drafts, prefer direct publication from the release owner.

---

## Step 14: `release: published` downstream jobs

Post-publication work can use the release event safely:

```yaml
  post-release:
    name: Post-release work
    needs: [route]
    if: ${{ needs.route.outputs.run_post_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Consume the already-published release here"
```

Examples:

- refresh release pages,
- send notifications,
- update metadata/indexes,
- trigger documentation deployment,
- publish a monthly/reporting entry.

**Note on same-run releases:** If you use the preferred default where `GITHUB_TOKEN` manual tags publish the release in the same run, those events generally will not emit a new `release: published` workflow. Chain the required downstream work immediately after the publisher jobs in that *same* run. Reserve the `release: published` event-driven workflow strictly for externally created releases or explicit PAT-driven architectures.

It must not call `gh release create`, GoReleaser release publication, or a GitHub Release creation API for the same version.

---

## Step 15: Docker/container release

Container publication is separate from GitHub Release ownership. It may consume the same semantic tag without creating another GitHub Release.

A typical container release lane can:

- authenticate to GHCR/another registry,
- build multi-platform images when useful,
- tag the image with the semantic version,
- optionally add `latest` for stable non-prerelease tags.

Keep registry publication idempotent and clearly separate from `gh release create`.

---

## Step 16: source Debian/RPM packages

If the repository genuinely produces source packages, create them as artifact-producing lanes and feed their outputs into the one release owner when GitHub Release attachment is desired.

Do not let a source-package job create another GitHub Release independently.

Package publishing to a distro/package registry is its own distribution action; GitHub Release creation remains single-owner.

---

## Step 17: prerelease semantics

Derive prerelease state from the selected manual mode/tag suffix, not from unrelated toggles.

Examples:

- `v1.2.3` → stable,
- `v1.2.3-rc.1` → prerelease,
- `v1.2.3-alpha.1` → prerelease,
- `v1.2.3-beta.1` → prerelease,
- `v1.2.3-test.1` → prerelease or non-public test lane according to project policy.

If a project deliberately treats `test` tags as artifact-only and not GitHub Releases, encode that in the router/owner condition rather than creating then abandoning drafts.

---

## Step 18: cleanup lifecycle

PR cleanup should be narrowly scoped. For example, if an autofix branch was created for a PR that is later closed without merge, a cleanup job may close/delete the derived autofix branch.

Do not run expensive test/release work on a `pull_request: closed` event just because the workflow was triggered.

---

## Step 19: monthly/nightly maintenance

Scheduled runs may perform:

- dependency freshness checks,
- generated-file consistency,
- lint/fmt drift checks,
- security scans,
- repository reports,
- optional autofix PRs.

They should never accidentally set `run_release=true`.

---

## Step 20: release safety audit when upgrading an existing repo

Before changing an existing workflow, search **all workflow files and release configuration**, not only `ci.yml`, for:

```text
softprops/action-gh-release
gh release create
goreleaser/goreleaser-action
/release
release:
types: [published]
publish-draft
promote-release
run_release=true
draft: true
```

Then answer these questions:

1. What creates the tag?
2. What creates the GitHub Release?
3. What uploads release assets?
4. Can manual dispatch and tag push both publish?
5. Can `release: published` trigger publication again?
6. Does GoReleaser already own publication?
7. Is another workflow file also publishing the same tags?
8. Does any `|| true` hide a creation conflict?
9. Are historical `untagged-*` drafts evidence of an older duplicate path?

Choose one owner and make every other lane either a producer of inputs or a downstream consumer.

---

## Step 21: repository-specific version bumping

Only add version-file mutation if the repository actually keeps a version in source control.

Examples include:

- Node `package.json`,
- Dart/Flutter `pubspec.yaml`,
- CMake project version,
- Java/Gradle/Maven version,
- custom source constants.

When source state and tags can drift, compute the intended version carefully and refuse to reuse an existing tag. A release pipeline should fail safely rather than silently create a second representation of the same version.

---

## Step 22: validation

Before opening/merging a CI change:

- parse/validate the YAML,
- run `actionlint` where available,
- inspect every `needs` dependency and referenced output,
- ensure job conditions are valid for every triggering event,
- ensure manual inputs are not referenced unsafely on unrelated events,
- ensure `release: published` cannot reach the publisher,
- ensure only one GitHub Release creator exists for a semantic tag,
- ensure GoReleaser and `softprops/action-gh-release` are not both owners,
- ensure build artifacts required by the publisher exist on the release run,
- and preserve the repository's existing useful CI semantics.

If CI is unavailable because of account/billing/quota failures, still perform static validation and document what could not be exercised.

---

## Recommended release event flow

The preferred default flow is:

```text
manual workflow_dispatch release-patch
        |
        v
compute/validate vX.Y.Z
        |
        v
lint/test/build artifacts (release gates)
        |
        v
  release-context checks/pushes tag
        |
        v
   ONE release owner only
  (in the SAME manual run)
      /             \
GoReleaser      github-release job
   (one or the other, never both)
        |
        v
GitHub Release published
        |
        +-- (Downstream jobs in SAME run)

(Optional external path: App/PAT triggered release: published event)
```

The old "tag-owner" architecture where manual dispatch pushes a tag to start a release run is not intrinsically wrong; however, it has an external credential prerequisite (e.g. `TAG_PUSH_TOKEN`). Using `GITHUB_TOKEN` to push a tag prevents the `on: push: tags` workflow from triggering. By completing the release publication within the manual workflow run, we avoid the need for external secrets while remaining release-safe.

This separation makes the event graph easier to reason about and prevents the duplicate/orphaned draft releases seen when manual creation, draft creation, and release-event publication are combined.

---

## Migration from `006`, `011`, and `028`

When a repository says it was generated from one of the older CI articles, do not merely update the pointer comment. Audit the existing workflow and migrate its release graph.

In particular:

- replace manual `gh release create` with manual tag push + in-run publication, or ensure `TAG_PUSH_TOKEN` is used,
- remove independent `publish-draft` release creators when another publisher exists,
- remove placeholder `promote-release` jobs,
- stop routing `release: published` into primary `run_release`,
- make GoReleaser sole owner where it already publishes GitHub Releases,
- keep artifact-build jobs but feed their results to the owner,
- preserve intentional prerelease modes,
- and leave historical release cleanup as an explicit separate administrative action.

Use `041-release-safe-single-owner-github-ci` for the focused rationale and migration checklist.

---

## Final agent rule

When an agent is asked to create or upgrade a repository workflow from this article:

- inspect the repository first,
- preserve project-specific behaviour,
- use current Action majors after external verification,
- keep checks visible on PRs,
- keep release/build lanes appropriate to the project,
- and **prove from the event graph that one semantic tag can produce at most one GitHub Release owner path**.

That last condition is part of correctness, not an optional cleanup.