---
title: "The Ultimate Single GitHub Actions CI/CD File: Go, Node, Flutter, Dart, Qt/C++, Docker, and Packaging"
date: 2026-03-04T00:00:00+00:00
draft: false
tags: ["github-actions", "ci", "cd", "go", "node", "dart", "flutter", "qt", "c++", "docker", "goreleaser", "packaging"]
categories: ["devops", "reference", "automation"]
---

This is a practical build-up guide for creating **one large `ci.yml`** that is still readable, maintainable, and tailored to real repositories.

The target outcome:

- One workflow file handles **push**, **PR open/update**, **PR close**, **tags**, **release publish**, **manual dispatch**, and **monthly/nightly schedules**.
- It supports mixed repos: **Go**, **Node**, **Dart**, **Flutter**, **Qt/C++**, classic **C/Makefile**, and Dockerized components.
- It can run in **public mode** (broader checks) or **private mode** (cost-controlled), while keeping default test runners Ubuntu unless cross-OS coverage is explicitly needed.
- It includes **autofix PR creation + cleanup**, **security checks**, **artifact fan-out**, and **release lanes**.
- It accounts for packaging outputs beyond standard app bundles, including **source Debian** and **source RPM** pipeline hooks.

The point is not tiny YAML. The point is one intelligent CI/CD platform per repo.

Before the workflow body, add a top-of-file pointer comment so agents and humans know where the generation rules live:

```yaml
# Agent rules for generation:
# https://arran4.com/post/2026/006-Github-CI-and-Deploy/
# Built using this post as a reference/guide.
name: CI/CD
```

---

## Why one file (when multiple files are common)

Multiple files can work, but they drift over time:

- duplicated setup steps,
- inconsistent event triggers,
- fragmented release logic,
- duplicated policy logic for private/public repos.

A single file gives one policy and one dependency graph. You can still keep complexity sane by:

1. sectioned jobs,
2. capability outputs,
3. profile outputs,
4. event routing,
5. reusable local scripts/config files.

---

## Non-negotiable design rules

1. **Event routing first** (avoid accidental duplicate work).
2. **Project-type decisions should mostly be install/template-time** (human comments + toggles), with lightweight runtime detection as a safety net.
3. **Repo visibility is auto-detected** (`github.event.repository.private`) rather than manually toggled.
4. **Public repos run broader checks by default**; private repos are conservative unless manual mode asks for full.
5. **Autofix lanes are language-aware** (go fmt/go fix, dart format, flutter format, prettier, etc).
6. **Release lanes are split** (GoReleaser, container release, source package release).
7. **Monthly maintenance exists by default**.

---

## Step 1: Triggers and modes (copy/paste)

This event model supports normal validation, releases, and cleanup lifecycle.

```yaml
name: CI/CD

on:
  push:
    branches: [main, master]
    # semantic version tags + rc/beta snapshots
    tags:
      - 'v*'
      - 'v*.*.*'
      - 'v*.*.*-rc*'
      - 'v*.*.*-beta*'
      - 'test-*'
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
        description: "Optional explicit release version (for example 2.4.0 or 2.4.0-rc.2)"
        required: false
        default: ""
        type: string
      allow_prs:
        description: "Allow automation to open pull requests"
        required: false
        default: true
        type: boolean
  schedule:
    # preferred heavy monthly run (quota reset strategy)
    - cron: '17 3 1 * *'
    # optional nightly lightweight checks
    - cron: '41 2 * * *'
```

### Why this is better

- It handles PR close cleanup flows.
- It supports semantic tags and release candidates.
- It exposes explicit manual operational modes (`lint-fix`, `build`, and explicit release modes (`release-major`, `release-minor`, `release-patch`, `release-test`, `release-rc`, `release-alpha`)).
- It keeps manual-dispatch states valid by encoding release intent directly into `mode` values.

---

## Step 1.5: Release mode routing (single-input design)

To avoid invalid manual-dispatch state combinations, keep a **single release control surface** in `mode` and one optional `release_version_override`.

```yaml
  prepare-release-tag:
    name: Prepare release tag
    needs: [route]
    if: ${{ github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-') }}
    runs-on: ubuntu-latest
    outputs:
      release_tag: ${{ steps.tag.outputs.release_tag }}
      next_version: ${{ steps.tag.outputs.next_version }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Setup git-tag-inc
        uses: arran4/git-tag-inc-action@v1
        with:
          mode: install
      # Do not also run `go install github.com/arran4/git-tag-inc/...` in this job.
      # Using both is redundant and has caused avoidable CI drift.
      - id: tag
        shell: bash
        run: |
          set -euo pipefail
          git config --global user.name "github-actions[bot]"
          git config --global user.email "41898282+github-actions[bot]@users.noreply.github.com"
          MODE="${{ inputs.mode }}"
          OVERRIDE="${{ inputs.release_version_override }}"

          if [[ -n "$OVERRIDE" ]]; then
            # Accept "1.2.3" or "v1.2.3" override input.
            OVERRIDE="${OVERRIDE#v}"
            next_tag="v$OVERRIDE"
          else
            case "$MODE" in
              release-major) level="major"; suffix="" ;;
              release-minor) level="minor"; suffix="" ;;
              release-patch) level="patch"; suffix="" ;;
              release-test)  level="patch"; suffix="test" ;;
              release-rc)    level="patch"; suffix="rc" ;;
              release-alpha) level="patch"; suffix="alpha" ;;
              *) echo "Unsupported release mode: $MODE"; exit 1 ;;
            esac
            if command -v git-tag-inc >/dev/null 2>&1; then
              # git-tag-inc uses positional commands (patch/major/minor/test/rc...)
              # and NOT flag forms like -patch.
              level="${level#-}"
              args=(-print-version-only "$level")
              [[ -n "$suffix" ]] && args+=("$suffix")
              next_tag=$(git-tag-inc "${args[@]}")
            else
              # Fallback implementation when git-tag-inc is not available.
              git fetch --tags --force
              latest=$(git tag -l 'v*' | sed 's/^v//' | sort -V | tail -n 1)
              [[ -z "$latest" ]] && latest='0.0.0'

              # Prefer npx semver if available (same pattern used in g2 fixes).
              if command -v npx >/dev/null 2>&1; then
                case "$level" in
                  major) bumped=$(npx --yes semver "$latest" -i major) ;;
                  minor) bumped=$(npx --yes semver "$latest" -i minor) ;;
                  *) bumped=$(npx --yes semver "$latest" -i patch) ;;
                esac
                next_tag="v${bumped}"
              else
                base="${latest%%-*}"
                IFS='.' read -r maj min pat <<< "$base"
                case "$level" in
                  major) maj=$((maj+1)); min=0; pat=0 ;;
                  minor) min=$((min+1)); pat=0 ;;
                  *) pat=$((pat+1)) ;;
                esac
                next_tag="v${maj}.${min}.${pat}"
              fi

              if [[ -n "$suffix" ]]; then
                next_tag="${next_tag}-${suffix}.1"
              fi
            fi
          fi

          # Tagging safety guards to avoid duplicate/invalid release states.
          [[ "$next_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.]+)?$ ]] || {
            echo "Invalid tag format: $next_tag" >&2
            exit 1
          }
          git fetch --tags --force
          if git rev-parse "$next_tag" >/dev/null 2>&1; then
            echo "Tag already exists: $next_tag" >&2
            echo "Choose a new mode or set release_version_override." >&2
            exit 1
          fi

          echo "release_tag=$next_tag" >> "$GITHUB_OUTPUT"
          clean_tag="${next_tag#v}"; clean_tag="${clean_tag%%-*}"
          IFS='.' read -r maj min pat <<< "$clean_tag"
          echo "next_version=${maj:-0}.${min:-0}.$(( ${pat:-0} + 1 ))-SNAPSHOT" >> "$GITHUB_OUTPUT"
```

With this approach, `snapshot/prerelease` is inferred from the selected release mode and tag suffix, not from separate toggles. It also fixes common tagging issues by normalizing override input (`v` prefix optional), validating tag shape, hard-failing on existing tags before publish jobs run, and reminding you to fetch tags before version math. It explicitly installs `git-tag-inc` via `arran4/git-tag-inc-action@v1` (`mode: install`) and includes fallback bump paths (`npx semver`, then pure shell semver math) if the binary is not found. Do not double-install with a separate manual `go install` in the same job. Use `git-tag-inc -print-version-only <major|minor|patch> [test|rc|alpha]` positional arguments to avoid the recurring argument-format mistake. Never use `-patch`/`-major`/`-minor` as flags; those are invalid. Also configure git user/email in the job before running release tag tooling so CI tag operations do not fail on identity checks.

If your repository keeps a version in source files as well as tags (for example `CMakeLists.txt`, `pubspec.yaml`, `package.json`, or similar), compute the next version from the **highest of source version and fetched tag version**. That avoids the recurring failure mode where CI bumps from stale source state, reuses an already-published version, and collides on tag creation.

---

## Step 2: Event routing to reduce duplicate runs


You noted a real issue: push + PR can duplicate work. We fix it with routing-first, state-aware `if:` behavior, but keep an important practical rule: lint/format/vet/test should still appear on PRs so reviewers get direct PR check visibility.

```yaml
concurrency:
  # Keep this as a safety net, not the primary dedupe mechanism.
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
  discussions: write
  pull-requests: write
  checks: write
  packages: write
  security-events: write

jobs:
  route:
    name: Route event
    runs-on: ubuntu-latest
    outputs:
      run_code_checks: ${{ steps.route.outputs.run_code_checks }}
      run_pr_meta_checks: ${{ steps.route.outputs.run_pr_meta_checks }}
      run_cleanup: ${{ steps.route.outputs.run_cleanup }}
      run_release: ${{ steps.route.outputs.run_release }}
      is_monthly: ${{ steps.route.outputs.is_monthly }}
      is_nightly: ${{ steps.route.outputs.is_nightly }}
    steps:
      - id: route
        shell: bash
        run: |
          set -euo pipefail

          run_code_checks=false
          run_pr_meta_checks=false
          run_cleanup=false
          run_release=false
          is_monthly=false
          is_nightly=false

          case "${{ github.event_name }}" in
            push)
              run_code_checks=true
              ;;
            pull_request)
              if [[ "${{ github.event.action }}" == "closed" ]]; then
                run_cleanup=true
              else
                run_pr_meta_checks=true
                # In practice, also run code checks on PRs so lint/fmt/vet/test
                # show up directly in the PR UI. Use concurrency to collapse churn.
                run_code_checks=true
              fi
              ;;
            release)
              run_release=true
              ;;
            workflow_dispatch)
              run_code_checks=true
              if [[ "${{ inputs.mode }}" == release-* ]]; then
                run_release=true
              fi
              if [[ "${{ inputs.mode }}" == "monthly-maintenance" ]]; then
                is_monthly=true
              fi
              if [[ "${{ inputs.mode }}" == "lint-fix" ]]; then
                # Manual lint-fix acts as an on-demand nightly-style maintenance pass.
                is_nightly=true
              fi
              ;;
            schedule)
              run_code_checks=true
              if [[ "${{ github.event.schedule }}" == "17 3 1 * *" ]]; then
                is_monthly=true
              fi
              if [[ "${{ github.event.schedule }}" == "41 2 * * *" ]]; then
                is_nightly=true
              fi
              ;;
          esac

          echo "run_code_checks=$run_code_checks" >> "$GITHUB_OUTPUT"
          echo "run_pr_meta_checks=$run_pr_meta_checks" >> "$GITHUB_OUTPUT"
          echo "run_cleanup=$run_cleanup" >> "$GITHUB_OUTPUT"
          echo "run_release=$run_release" >> "$GITHUB_OUTPUT"
          echo "is_monthly=$is_monthly" >> "$GITHUB_OUTPUT"
          echo "is_nightly=$is_nightly" >> "$GITHUB_OUTPUT"
```

### High-confidence manual-dispatch router baseline

If you want a known-good baseline for manual dispatch semantics, use the same three-route-output shape proven in `arran4/mlocate_explorer` (`run_code_checks`, `run_build`, `run_release`) and then layer project-specific lanes onto it.

```yaml
  route:
    name: Event Router
    runs-on: ubuntu-latest
    outputs:
      run_code_checks: ${{ steps.decide.outputs.run_code_checks }}
      run_build: ${{ steps.decide.outputs.run_build }}
      run_release: ${{ steps.decide.outputs.run_release }}
    steps:
      - id: decide
        shell: bash
        run: |
          set -euo pipefail
          if [[ "${{ github.event_name }}" == "pull_request" && "${{ github.event.action }}" == "closed" ]]; then
            echo "run_code_checks=false" >> "$GITHUB_OUTPUT"
            echo "run_build=false" >> "$GITHUB_OUTPUT"
            echo "run_release=false" >> "$GITHUB_OUTPUT"
            exit 0
          fi

          echo "run_code_checks=true" >> "$GITHUB_OUTPUT"

          if [[ "${{ github.ref }}" == refs/tags/* || ("${{ github.event_name }}" == "workflow_dispatch" && "${{ inputs.mode }}" != "lint-fix") ]]; then
            echo "run_build=true" >> "$GITHUB_OUTPUT"
          else
            echo "run_build=false" >> "$GITHUB_OUTPUT"
          fi

          if [[ "${{ github.ref }}" == refs/tags/v* || ("${{ github.event_name }}" == "workflow_dispatch" && startsWith("${{ inputs.mode }}", "release-")) ]]; then
            echo "run_release=true" >> "$GITHUB_OUTPUT"
          else
            echo "run_release=false" >> "$GITHUB_OUTPUT"
          fi
```

This gives you predictable manual dispatch behavior: `lint-fix` runs checks only, `build` runs build lanes, and `release-*` runs build + release.

This gives explicit behavior control instead of relying only on cancellation.

**Practical rule:** keep code checks on both `push` and `pull_request` when you want lint/format/vet/test results visible in the PR itself. Let concurrency and event routing reduce churn, rather than hiding the checks from reviewers.

### Clarification from a working real-world result (`fork-qip` style)

A practical setup that matches your intent closely uses these additional rules:

1. **Conditional cancellation** for concurrency:
   - cancel in-progress runs on non-main/non-tag refs,
   - avoid cancelling `main`, `master`, and tag builds.
2. **Dedicated `format` job** that always runs for Go repos during code-check events:
   - on manual `lint-fix`, it opens an autofix PR,
   - otherwise it fails with diff output (forcing dev-side formatting).
3. **Separate `go-lint`, `go-test`, and `go-vet` jobs** for cleaner diagnostics and release gating.
4. **Release job guarded with `!failure() && !cancelled()` and `needs` fan-in**.

Copy/paste concurrency pattern from that style:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' && github.ref != 'refs/heads/master' && !startsWith(github.ref, 'refs/tags/') }}
```

This is stricter and often better than blanket `cancel-in-progress: true` in busy repos.

---

## Step 3: Project profile decisions (config-time first, minimal runtime checks)

You are right that most tailoring should be done when installing the workflow. Do both:

- template comments/toggles for expected project types,
- runtime detection as guard rails.

```yaml
  discover:
    name: Discover capabilities and cost profile
    needs: route
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
      has_dart_or_flutter_tests: ${{ steps.detect.outputs.has_dart_or_flutter_tests }}
      has_packaging: ${{ steps.detect.outputs.has_packaging }}
    steps:
      - uses: actions/checkout@v4

      # Template-time toggles (set these once for the repo; avoid broad auto-detection)
      # EXPECT_GO=true
      # EXPECT_NODE=false
      # EXPECT_DART=false
      # EXPECT_FLUTTER=false
      # EXPECT_QT_CPP=false
      # EXPECT_MAKE_C=false
      # EXPECT_DOCKER=false
      # EXPECT_GORELEASER=true

      - id: detect
        shell: bash
        run: |
          set -euo pipefail
          # Keep this minimal: most language choices should be decided at workflow install/customization time.
          # Runtime checks stay for optional tests and packaging folders.

          echo "has_go=${EXPECT_GO:-false}" >> "$GITHUB_OUTPUT"
          echo "has_node=${EXPECT_NODE:-false}" >> "$GITHUB_OUTPUT"
          echo "has_dart=${EXPECT_DART:-false}" >> "$GITHUB_OUTPUT"
          echo "has_flutter=${EXPECT_FLUTTER:-false}" >> "$GITHUB_OUTPUT"
          echo "has_qt_cpp=${EXPECT_QT_CPP:-false}" >> "$GITHUB_OUTPUT"
          echo "has_make_c=${EXPECT_MAKE_C:-false}" >> "$GITHUB_OUTPUT"
          echo "has_docker=${EXPECT_DOCKER:-false}" >> "$GITHUB_OUTPUT"
          echo "has_goreleaser=${EXPECT_GORELEASER:-false}" >> "$GITHUB_OUTPUT"

          ([[ -d test ]] || [[ -d tests ]] || [[ -f pubspec.yaml ]]) && echo "has_dart_or_flutter_tests=true" >> "$GITHUB_OUTPUT" || echo "has_dart_or_flutter_tests=false" >> "$GITHUB_OUTPUT"
          ([[ -d packaging ]] || [[ -d pkg ]] || [[ -f debian/control ]]) && echo "has_packaging=true" >> "$GITHUB_OUTPUT" || echo "has_packaging=false" >> "$GITHUB_OUTPUT"

      - id: profile
        shell: bash
        run: |
          set -euo pipefail
          # repo visibility is authoritative
          if [[ "${{ github.event.repository.private }}" == "true" ]]; then
            echo "profile=private" >> "$GITHUB_OUTPUT"
          else
            echo "profile=public" >> "$GITHUB_OUTPUT"
          fi
```

### Why this is not just cost control

Conditional outputs are also for:

- correctness (only run valid lanes),
- readability (clear `if` graph),
- reliability (fewer false failures in unrelated stacks),
- maintainability (easy to extend per language).

---

## Step 4: Lint config and tool config files you should keep in repo

A single CI file works best when lint/build settings are stored in repo config files, not inline shell flags.

Recommended baseline:

- Go: `.golangci.yml`
- Node: `.eslintrc.*`, `.prettierrc*`
- Dart/Flutter: `analysis_options.yaml`
- C/C++: `.clang-format`, `cppcheck` config or suppressions file
- Gitleaks: `.gitleaks.toml`
- GoReleaser: `.goreleaser.yml`
- Packaging: `packaging/` tree (`debian/`, `.spec`, templates)

Example `.gitleaks.toml` starter:

```toml
title = "repo gitleaks config"

[allowlist]
description = "global allowlist"
paths = [
  '''^docs/''',
  '''^testdata/'''
]
```

Example `analysis_options.yaml` starter:

```yaml
include: package:flutter_lints/flutter.yaml

analyzer:
  language:
    strict-casts: true

linter:
  rules:
    - avoid_print
    - prefer_single_quotes
```

Additional copy/paste config starters:

### `.golangci.yml`

```yaml
run:
  timeout: 5m

linters:
  enable:
    - govet
    - staticcheck
    - errcheck
    - ineffassign
    - revive

issues:
  exclude-use-default: false
```

### `.prettierrc.json`

```json
{
  "semi": false,
  "singleQuote": true,
  "printWidth": 100
}
```

### `.clang-format`

```yaml
BasedOnStyle: LLVM
IndentWidth: 2
ColumnLimit: 100
```

### `packaging/rpm/app.spec` (source rpm compatible starter)

```spec
Name:           app
Version:        %{?version}%{!?version:0.0.0}
Release:        1%{?dist}
Summary:        App summary
License:        MIT
Source0:        %{name}-%{version}.tar.gz

%description
App description.

%prep
%autosetup

%build
# build steps here

%install
mkdir -p %{buildroot}/usr/bin

%files
/usr/bin/*

%changelog
* Thu Mar 04 2026 CI Bot <ci@example.com> - %{version}-1
- Automated source build
```

---

## Step 5: Security jobs (automatic profile behavior)

```yaml
  gitleaks:
    name: Secret scan
    needs: [route, discover]
    if: ${{ needs.route.outputs.run_cleanup != 'true' && (needs.route.outputs.is_nightly == 'true' || needs.route.outputs.is_monthly == 'true') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  dependency-review:
    name: Dependency review (public/full)
    needs: [route, discover]
    if: ${{ needs.discover.outputs.profile == 'public' && github.event_name == 'pull_request' && github.event.action != 'closed' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/dependency-review-action@v4
```

Public repos can afford broader checks by default. Private repos keep monthly/full-mode heavy scans.

Leak check policy: run secret/leak scans as part of nightly/monthly maintenance only (including manual `lint-fix` maintenance dispatch).

---

## Step 5.5: Java/Maven lane (from kagura-style repos)

If a repo has `pom.xml`, add this lane. It is useful for polyglot repos where Java packaging coexists with Go/Node/others.

```yaml
  java-build-test:
    name: Java build/test
    needs: [route, discover]
    if: ${{ needs.route.outputs.run_code_checks == 'true' && hashFiles('pom.xml') != '' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '11'
          distribution: temurin
          cache: maven
      - run: mvn spotless:check
      - run: mvn test -DskipITs=false
```

This mirrors the style in your referenced workflow and can be chained into release fan-in if Java artifacts are part of your release.

---

## Step 5.6: Hugo Pages integration pattern

If the repository includes a Hugo docs/site directory (example: `site/mydocs`), add a Pages lane that builds and deploys docs on `main`/`master`, tag releases, and manual dispatch.

Key ideas from the referenced workflow:

- route-level `run_pages` output (separate from code-check/release output),
- discovery output `has_hugo` for conditional execution,
- workflow permissions include `pages: write` and `id-token: write`,
- split build and deploy jobs (`hugo-build` -> `hugo-deploy`),
- deployment concurrency uses the `pages` group.

### Route/discovery additions (copy/paste)

```yaml
permissions:
  contents: write
  pull-requests: write
  checks: write
  packages: write
  security-events: write
  pages: write
  id-token: write

jobs:
  route:
    outputs:
      run_pages: ${{ steps.route.outputs.run_pages }}
    steps:
      - id: route
        run: |
          run_pages=false
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            run_pages=true
          elif [[ "${{ github.ref }}" == refs/tags/* || "${{ github.ref }}" == "refs/heads/main" || "${{ github.ref }}" == "refs/heads/master" ]]; then
            run_pages=true
          fi
          echo "run_pages=$run_pages" >> "$GITHUB_OUTPUT"

  discover:
    outputs:
      has_hugo: ${{ steps.detect.outputs.has_hugo }}
    steps:
      - id: detect
        run: |
          [[ -d site/mydocs ]] && echo "has_hugo=true" >> "$GITHUB_OUTPUT" || echo "has_hugo=false" >> "$GITHUB_OUTPUT"
```

### Build + deploy jobs (copy/paste)

```yaml
  hugo-build:
    name: Build Hugo site
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_hugo == 'true' && needs.route.outputs.run_pages == 'true' }}
    runs-on: ubuntu-latest
    env:
      HUGO_VERSION: 0.123.7
    steps:
      - name: Install Hugo CLI
        run: |
          wget -O ${{ runner.temp }}/hugo.deb https://github.com/gohugoio/hugo/releases/download/v${HUGO_VERSION}/hugo_extended_${HUGO_VERSION}_linux-amd64.deb
          sudo dpkg -i ${{ runner.temp }}/hugo.deb
      - name: Install Dart Sass
        run: sudo snap install dart-sass
      - uses: actions/checkout@v4
        with:
          submodules: recursive
      - id: pages
        uses: actions/configure-pages@v5
      - name: Install Node dependencies
        working-directory: ./site/mydocs
        run: "[[ -f package-lock.json || -f npm-shrinkwrap.json ]] && npm ci || true"
      - name: Build with Hugo
        working-directory: ./site/mydocs
        env:
          HUGO_ENVIRONMENT: production
          HUGO_ENV: production
        run: |
          hugo --minify --baseURL "${{ steps.pages.outputs.base_url }}/"
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./site/mydocs/public

  hugo-deploy:
    name: Deploy to GitHub Pages
    needs: [route, discover, hugo-build]
    if: ${{ needs.discover.outputs.has_hugo == 'true' && needs.route.outputs.run_pages == 'true' }}
    runs-on: ubuntu-latest
    concurrency:
      group: pages
      cancel-in-progress: false
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

This keeps docs/site deployment first-class without mixing it into language build jobs.

---

## Step 6: Go lane (tests, lint, vet, release prep)

Use `setup-go` built-in caching instead of manual `actions/cache`.

```yaml
  # Requested baseline snippet (modern versions)
  golangci:
    name: lint
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - name: golangci-lint
        uses: golangci/golangci-lint-action@v9
        with:
          version: latest

  go-test:
    name: Go lint/test (${{ matrix.os }})
    needs: [route, discover, golangci]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        # Cost-aware default: Ubuntu only.
        # Add windows-latest/macos-latest only for true platform-specific behavior.
        os: [ubuntu-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
          cache: true
      - name: Test
        run: go test ./... -v

  go-vet:
    name: Go vet
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.route.outputs.run_code_checks == 'true' && needs.discover.outputs.profile == 'public' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
          cache: true
      - run: go vet ./...

  go-fmt-pr:
    name: go fmt -> PR (manual dispatch)
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_go == 'true' && github.event_name == 'workflow_dispatch' && inputs.mode == 'lint-fix' && inputs.allow_prs == true }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - name: Run go fmt
        run: go fmt ./...
      - name: Create PR if go fmt changed files
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          git diff --quiet && { echo "No fmt changes"; exit 0; }
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          BRANCH="ci/gofmt/${{ github.run_id }}"
          git checkout -b "$BRANCH"
          git add -A
          git commit -m "ci: go fmt"
          git push origin "$BRANCH"
          gh pr create --title "ci: go fmt" --body "Automated go fmt from manual dispatch." --base main --head "$BRANCH" --label "ci-autofix"
```

This separates lint, test, and vet while keeping a dedicated manual-dispatch `go fmt -> PR` path.

Recommended behavior (from your working result):

- Keep `format` as a required job in normal CI.
- If `mode == lint-fix`, auto-open PR with fixes.
- Otherwise fail the job and print diff so formatting is corrected in source branches.

Optional cross-OS lane (only when it really matters):

```yaml
  go-cross-os-smoke:
    name: Go cross-OS smoke (${{ matrix.os }})
    needs: [route, discover, golangci]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.route.outputs.run_code_checks == 'true' && (github.event_name == 'workflow_dispatch' && inputs.mode == 'build') }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - run: go build ./...
```

---

## Step 7: Node lane (tests, lint, source package + versioning integration)

```yaml
  node-lint-test:
    name: Node lint/test
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_node == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint --if-present
      - run: npm test --if-present
      - name: Build source npm package
        run: npm pack --json > npm-pack-result.json

      - uses: actions/upload-artifact@v4
        with:
          name: npm-source-package
          retention-days: 1
          path: |
            *.tgz
            npm-pack-result.json
```

Use this baseline with Step 7.5 below as the release/versioning extension for npm publish.

---

## Step 7.5: Node/TS version automation (integrated publish path)

For npm packages, the `tsobjectutils` workflow has strong production ideas worth reusing:

- manual bump levels (`patch|minor|major|prerelease`),
- optional prerelease creation (`-next`),
- compute whether publish is allowed (`-next` can skip public publish),
- idempotent tag/release creation (`actions/github-script` checks if they already exist),
- publish with correct npm dist-tag (`latest` vs `next`),
- create a PR for the next development iteration version.

Copy/paste control snippet:

```yaml
on:
  workflow_dispatch:
    inputs:
      level:
        description: Version Bump Level
        required: true
        default: patch
        type: choice
        options: [patch, minor, major, prerelease]
      create_prerelease:
        description: Create as prerelease (e.g. -next.0)
        required: false
        default: false
        type: boolean

jobs:
  version-and-release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Manual Version Bump
        if: github.event_name == 'workflow_dispatch'
        run: |
          LEVEL="${{ inputs.level }}"
          CREATE_PRE="${{ inputs.create_prerelease }}"
          if [ "$LEVEL" = "prerelease" ]; then
            npm version prerelease --preid=next --no-git-tag-version
          elif [ "$CREATE_PRE" = "true" ]; then
            npm version pre$LEVEL --preid=next --no-git-tag-version
          else
            npm version $LEVEL --no-git-tag-version
          fi

      - name: Determine npm tag and prerelease state
        id: versions
        run: |
          CURRENT_VERSION=$(node -p "require('./package.json').version")
          if [[ "$CURRENT_VERSION" == *-* ]]; then
            echo "npm_tag=next" >> "$GITHUB_OUTPUT"
            echo "is_prerelease=true" >> "$GITHUB_OUTPUT"
          else
            echo "npm_tag=latest" >> "$GITHUB_OUTPUT"
            echo "is_prerelease=false" >> "$GITHUB_OUTPUT"
          fi
```

This pattern reduces accidental duplicate tags/releases and gives predictable npm channel behavior.

## Step 8: Dart + Flutter lanes (including libraries)

You asked to include Dart libs and Flutter libs specifically, with analysis.

```yaml
  dart-analyze-test:
    name: Dart analyze/test
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_dart == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dart-lang/setup-dart@v1
      - run: dart --version
      - run: dart pub get
      - run: dart format --set-exit-if-changed .
      - run: dart analyze
      - run: dart test

  flutter-analyze-test:
    name: Flutter analyze/test (fast path)
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_flutter == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          channel: stable
      - run: flutter --version
      - run: flutter pub get
      - run: dart format --set-exit-if-changed .
      - run: flutter analyze
      - run: flutter test

  flutter-format-pr:
    name: Flutter format -> PR (manual lint-fix)
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_flutter == 'true' && github.event_name == 'workflow_dispatch' && inputs.mode == 'lint-fix' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          channel: stable
      - run: flutter pub get
      - id: format
        run: |
          dart format .
          if [[ -n $(git status --porcelain -- '*.dart') ]]; then
            echo "changes=true" >> "$GITHUB_OUTPUT"
            git status --porcelain -- '*.dart'
          else
            echo "changes=false" >> "$GITHUB_OUTPUT"
          fi
      - name: Open PR with formatting fixes
        if: steps.format.outputs.changes == 'true' && inputs.allow_prs == true
        uses: peter-evans/create-pull-request@v7
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: "style: apply dart format"
          title: "style: apply dart format"
          body: "Automated PR for Flutter/Dart formatting fixes."
          branch: "automated/dart-format-${{ github.ref_name }}"
          base: ${{ github.ref_name }}
          delete-branch: true
      - name: Fail if formatting drift exists
        if: steps.format.outputs.changes == 'true'
        run: |
          echo "Formatting drift detected. Fix directly or merge the generated PR."
          exit 1

  flutter-build-artifacts:
    name: Flutter build artifacts (release/monthly only)
    needs: [route, discover, flutter-analyze-test]
    if: ${{ needs.discover.outputs.has_flutter == 'true' && (needs.route.outputs.run_release == 'true' || needs.route.outputs.is_monthly == 'true' || (github.event_name == 'workflow_dispatch' && inputs.mode == 'build')) }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: subosito/flutter-action@v2
        with:
          channel: stable
      - run: flutter pub get
      - run: flutter build linux --release
      - run: flutter build apk --release || true

      - uses: actions/upload-artifact@v4
        with:
          name: flutter-release-bundles
          retention-days: 1
          path: |
            build/linux/**
            build/app/outputs/flutter-apk/*.apk
```

### Fastforge note

Fastforge is optional. Keep it if you want it; remove it if you don't. The key pattern is to keep release outputs available through independent lanes (flatpak, source packages, container artifacts, GoReleaser outputs) so your pipeline doesn't depend on a single packaging tool.

### Confidence note (tested manual dispatch)

The Flutter manual-dispatch pattern above is based on a working pipeline where `mode=lint-fix` plus `allow_prs` has been tested in practice (`arran4/mlocate_explorer`, commit `9ce9d36`). Treat this as a higher-confidence baseline for Flutter than untested snippets, then add platform build lanes (Linux/Windows/macOS) only when your project actually needs cross-OS deliverables.

When you do add cross-OS Flutter builds, follow this same split:

- keep format/analyze/test as the fast Ubuntu path,
- gate expensive Linux/Windows/macOS artifact lanes behind `run_build` or release,
- upload artifacts per platform and publish only from release-scoped jobs.

### Dart release/version-sync pattern (from dartobjectutils)

For Dart-first repos, one practical pattern is:

1. run `dart analyze` / `dart test`,
2. on manual dispatch, compute the next version (`patch|minor|major|manual`),
3. update `pubspec.yaml`, commit, tag, push,
4. verify tag version matches `pubspec.yaml` and auto-fix with PR fallback when direct push fails.

Copy/paste release prep snippet:

```yaml
  dart-release-prep:
    name: Dart release prep
    if: ${{ github.event_name == 'workflow_dispatch' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: dart-lang/setup-dart@v1
      - name: Compute version and tag
        env:
          INCREMENT: ${{ inputs.increment }}
          MANUAL_VERSION_INPUT: ${{ inputs.manual_version }}
        run: |
          set -euo pipefail
          PUBSPEC_VERSION=$(awk '/^version:/ {print $2}' pubspec.yaml)
          git fetch --tags
          HIGHEST_TAG=$(git tag -l "v*" | sed 's/^v//' | sort -V | tail -n 1)
          [ -z "$HIGHEST_TAG" ] && HIGHEST_TAG="0.0.0"

          CURRENT_VERSION=$(echo -e "$PUBSPEC_VERSION
$HIGHEST_TAG" | sort -V | tail -n 1)

          if [ "$INCREMENT" = "manual" ]; then
            [ -z "$MANUAL_VERSION_INPUT" ] && { echo "manual_version required"; exit 1; }
            NEW_VERSION="$MANUAL_VERSION_INPUT"
          else
            IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
            case "$INCREMENT" in
              major) NEW_VERSION="$((MAJOR+1)).0.0" ;;
              minor) NEW_VERSION="$MAJOR.$((MINOR+1)).0" ;;
              *) NEW_VERSION="$MAJOR.$MINOR.$((PATCH+1))" ;;
            esac
          fi

          sed -i "s/^version: .*/version: $NEW_VERSION/" pubspec.yaml
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git checkout -b "release/v$NEW_VERSION"
          git add pubspec.yaml
          git commit -m "Bump version to $NEW_VERSION"
          git tag "v$NEW_VERSION"
          git push origin "v$NEW_VERSION"
          git push origin "release/v$NEW_VERSION"
```

---

## Step 9: Qt/C++ and classic C lane

Include both Qt/CMake and Makefile detection paths.

```yaml
  cpp-qt-build-test:
    name: Qt/C++ build
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_qt_cpp == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update
      - run: sudo apt-get install -y cmake ninja-build build-essential qt6-base-dev qt6-tools-dev clang-format cppcheck
      - name: Lint style and static checks
        run: |
          find . \( -name '*.cpp' -o -name '*.cc' -o -name '*.h' -o -name '*.hpp' \) -print0 | xargs -0 -r clang-format --dry-run --Werror
          cppcheck --enable=warning,style,performance,portability --error-exitcode=1 .
      - run: cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release
      - run: cmake --build build --parallel
      - run: ctest --test-dir build --output-on-failure

  c-make-build-test:
    name: Classic C Makefile build
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_make_c == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: make -j"$(nproc)" all
      - run: make test || true
```

---

## Step 10: Integrated autofix + PR automation lane

You wanted this wired to real formatters and branch-name guessable behavior.

```yaml
  autofix:
    name: Auto-format and open PR
    needs: [route, discover]
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'lint-fix' && inputs.allow_prs == true }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Go (if needed)
        if: ${{ needs.discover.outputs.has_go == 'true' }}
        uses: actions/setup-go@v6
        with:
          go-version-file: go.mod

      - name: Setup Node (if needed)
        if: ${{ needs.discover.outputs.has_node == 'true' }}
        uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: npm

      - name: Setup Dart/Flutter (if needed)
        if: ${{ needs.discover.outputs.has_dart == 'true' || needs.discover.outputs.has_flutter == 'true' }}
        uses: subosito/flutter-action@v2
        with:
          channel: stable

      - name: Run autofix formatters
        shell: bash
        run: |
          set -euo pipefail
          if [[ "${{ needs.discover.outputs.has_go }}" == "true" ]]; then
            go fix ./... || true
            go fmt ./... || true
          fi
          if [[ "${{ needs.discover.outputs.has_node }}" == "true" ]]; then
            npm ci || true
            npx prettier . --write || true
          fi
          if [[ "${{ needs.discover.outputs.has_dart }}" == "true" || "${{ needs.discover.outputs.has_flutter }}" == "true" ]]; then
            dart format . || true
          fi

      - name: Create PR if changes exist
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        shell: bash
        run: |
          set -euo pipefail
          if git diff --quiet; then
            echo "No changes; exiting."
            exit 0
          fi

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          PARENT_PR="${{ github.event.pull_request.number || 'none' }}"
          BRANCH="ci/autofix/${{ github.run_id }}-parent-${PARENT_PR}"

          git checkout -b "$BRANCH"
          git add -A
          git commit -m "ci: automated formatting fixes"
          git push origin "$BRANCH"

          gh pr create \
            --title "ci: automated formatting fixes" \
            --body "Automated formatting pass. Parent-PR: ${PARENT_PR}" \
            --base main \
            --head "$BRANCH" \
            --label "ci-autofix"
```

### Cleanup on parent PR close (specific)

```yaml
  cleanup-autofix-prs:
    name: Cleanup autofix PRs on parent close
    needs: [route]
    if: ${{ needs.route.outputs.run_cleanup == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          PARENT_PR: ${{ github.event.pull_request.number }}
        run: |
          set -euo pipefail
          gh pr list --state open --search "label:ci-autofix in:title" --json number,headRefName,body | \
            jq -r '.[] | select(.body | contains("Parent-PR: '"$PARENT_PR"'")) | [.number, .headRefName] | @tsv' | \
            while IFS=$'\t' read -r pr branch; do
              gh pr close "$pr" --comment "Closing auto-fix PR because parent PR #$PARENT_PR was closed."
              git push origin --delete "$branch" || true
            done
```

This uses both a label and a guessable branch pattern with parent linkage. Also note the checkout step: if the cleanup job deletes remote branches with `git push origin --delete`, it needs a repository checkout first.

### Repeated gotcha: any `git`-mutating CI job needs checkout first

If a job runs commands like `git push`, `git push origin --delete`, `git commit`, or branch operations, add checkout as the first step.

```yaml
steps:
  - uses: actions/checkout@v4
  - run: git push origin --delete "$BRANCH"
```

Treat this as a hard rule in generated workflows. The same issue repeatedly appears in real repos when cleanup jobs omit checkout.

---

## Step 11: Docker as a release publish step

If repo has Go + Dockerfile or standalone Docker service, build and (optionally) push.

```yaml
  docker-build:
    name: Docker build
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_docker == 'true' && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: ${{ hashFiles('Dockerfile.goreleaser') != '' && 'Dockerfile.goreleaser' || 'Dockerfile' }}
          push: false
          tags: ghcr.io/${{ github.repository }}:ci-${{ github.run_id }}

  docker-release:
    name: Docker release
    needs: [route, discover, docker-build]
    if: ${{ needs.discover.outputs.has_docker == 'true' && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: |
            ghcr.io/${{ github.repository }}:${{ github.ref_name }}
            ghcr.io/${{ github.repository }}:latest
          platforms: linux/amd64,linux/arm64
```

### Dotfiles/Chezmoi/Docker lessons (high-value niche pattern)

For most app repos, the generic Docker section above is enough. For **dotfiles + chezmoi** style repos, a few extra checks from a working pipeline are worth copying:

1. **Shell config validity is a real test target** (bash/zsh parse checks after apply).
2. **Run `chezmoi apply` in CI** to catch template/rendering regressions early.
3. **Use Docker `build-contexts`** when your Dockerfile expects the repo contents as a named context.
4. **Use `docker/metadata-action` tag strategy** so manual override tags and semver tags stay consistent.
5. **Package and publish a dotfiles archive** (`chezmoi archive`) as a first-class release artifact.

Copy/paste pattern:

```yaml
  shell-check-and-chezmoi-apply:
    name: ShellCheck + chezmoi apply
    needs: [route]
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install shellcheck and zsh
        run: sudo apt-get update && sudo apt-get install -y shellcheck zsh
      - name: ShellCheck scripts
        run: |
          shopt -s globstar
          shellcheck **/*.sh
      - name: Apply chezmoi source into CI home
        run: |
          yes "" | sh -c "$(curl -fsLS get.chezmoi.io)" -- init --no-tty --debug --source=$PWD --apply
      - name: Verify rendered shell files parse
        run: |
          for f in ~/.bashrc ~/.bash_profile ~/.bash_login ~/.bash_logout ~/.profile; do
            [[ -f "$f" ]] && bash -n "$f"
          done
          for f in ~/.zshrc ~/.zprofile ~/.zlogin ~/.zlogout ~/.zshenv; do
            [[ -f "$f" ]] && zsh -n "$f"
          done

  docker-release:
    name: Docker release
    needs: [route]
    if: ${{ needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-qemu-action@v3
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - name: Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository_owner }}/dev-dotfiles-debian
          tags: |
            type=ref,event=tag
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=${{ inputs.release_version_override }},enable=${{ inputs.release_version_override != '' }}
            type=raw,value=latest,enable={{is_default_branch}}
      - uses: docker/build-push-action@v6
        with:
          context: .
          build-contexts: dotfiles=.
          file: containers/dev-dotfiles-debian/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}

  package-dotfiles:
    name: Package dotfiles archive
    needs: [route]
    if: ${{ needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build dotfiles archive
        run: |
          yes "" | sh -c "$(curl -fsLS get.chezmoi.io)" -- init --no-tty --debug --source=$PWD --apply
          ./bin/chezmoi archive --source=$PWD --format zip --output dotfiles.zip
      - uses: actions/upload-artifact@v4
        with:
          name: dotfiles-archive
          retention-days: 1
          path: dotfiles.zip
```

Treat this as an opt-in lane: niche, but very effective when your repo is configuration-driven.

---

## Step 12: GoReleaser lane (binary + packages)

Important reliability guard (from real-world PR fixes): avoid running GoReleaser on both tag-push and `release: published` for the same version. If both fire, you can get duplicate upload errors (`422 already_exists`). Keep GoReleaser scoped to:

- tag push events (`push` + `refs/tags/v*`), or
- explicit manual release dispatch modes.

If you publish Homebrew formulas, keep the article generic and parameterized, then provide your real tap as an example. For example, a tap can be `OWNER/homebrew-tap` (your concrete case: `arran4/homebrew-tap`). For cross-repo updates, set `TAP_GITHUB_TOKEN` in secrets and wire it to both the workflow env (`TAP_GITHUB_TOKEN`) and GoReleaser config (`{{ .Env.TAP_GITHUB_TOKEN }}`), with PR updates enabled and non-draft (`draft: false`).

**Confidence note:** the GoReleaser profile used in `arran4/go-playerctl` (commit `53e2a00`) is a strong practical baseline for manual-dispatch releases and should be preferred over purely theoretical snippets when bootstrapping similar Go projects.

Important scope rule: **only add binary build/release lanes when the project actually produces binaries**. If the repo is a library, config repo, API schema repo, or another non-binary project, keep:

- tagging,
- GitHub release creation,
- release notes generation,
- discussions,
- lint/test/vet/fix/security checks,
- package-manager publication steps that make sense (`npm publish`, `dart pub publish`, etc),

and skip binary-specific lanes like GoReleaser `builds`, app bundle packaging, Homebrew formulas for non-binaries, or Docker image publishing unless the repository genuinely ships those deliverables.

```yaml
  goreleaser:
    name: GoReleaser
    # In practice, include all quality gates here (for example: go-test, go-vet, go-lint, format).
    needs: [route, discover, go-test, prepare-release-tag]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.discover.outputs.has_goreleaser == 'true' && (((github.event_name == 'push') && startsWith(github.ref, 'refs/tags/v')) || (github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-'))) }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - name: Run GoReleaser
        uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: '~> v2'
          args: >-
            release --clean
            ${{ (github.event_name == 'workflow_dispatch' && (inputs.mode == 'release-test' || inputs.mode == 'release-rc' || inputs.mode == 'release-alpha')) && '--snapshot' || '' }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TAP_GITHUB_TOKEN: ${{ secrets.TAP_GITHUB_TOKEN }} # inject secrets.TAP_GITHUB_TOKEN
          GORELEASER_CURRENT_TAG: ${{ needs.prepare-release-tag.outputs.release_tag }}
```

For release robustness, use an `if:` guard like this when aggregating many `needs`:

Important GoReleaser v2 note: avoid `--tag` in action args (it can fail with "unknown flag: --tag"). Instead set `GORELEASER_CURRENT_TAG` in `env` when you need to force the tag value from a prepared job output.

Do/Don’t quick check:

```yaml
# ❌ Don't (fails on v2):
# args: release --clean --tag v0.0.1

# ✅ Do:
# args: release --clean
# env:
#   GORELEASER_CURRENT_TAG: v0.0.1
```

```yaml
if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
```

Example `.goreleaser.yml` baseline (copy/paste):

If your repo does **not** emit a binary, do not cargo-cult this whole file. In that case, keep the manual tag/release flow from Step 15 and any relevant package-publish steps, but omit the GoReleaser binary/archive/container sections entirely.

```yaml
project_name: your-project

before:
  hooks:
    - go mod tidy

builds:
  - id: app
    binary: app
    main: ./cmd/app
    env:
      - CGO_ENABLED=0

archives:
  - formats: [tar.gz]
    format_overrides:
      - goos: windows
        formats: [zip]

checksum:
  name_template: checksums.txt

dockers:
  - image_templates:
      - ghcr.io/OWNER/REPO:{{ .Tag }}
      - ghcr.io/OWNER/REPO:latest
    dockerfile: Dockerfile.goreleaser
    use: buildx
    goos: linux
    goarch: [amd64, arm64]

nfpms:
  - id: linux-packages
    package_name: app
    vendor: Your Org
    homepage: https://example.com
    maintainer: You <you@example.com>
    description: App description
    license: MIT
    formats:
      - deb
      - rpm
      - apk
      - archlinux
    section: default
    priority: optional

homebrew_casks:
  -
    repository:
      owner: arran4
      name: homebrew-tap
      branch: "{{.ProjectName}}-{{.Version}}"
      token: "{{ .Env.TAP_GITHUB_TOKEN }}"
      pull_request:
        enabled: true
        draft: false
    commit_author:
      name: goreleaserbot
      email: bot@goreleaser.com

scoops:
  - name: app
    bucket:
      owner: OWNER
      name: scoop-bucket

changelog:
  sort: asc
  filters:
    exclude:
      - '^docs:'
      - '^test:'
```

### Important: avoid archive name templates for binaries

Do **not** set fragile custom archive naming templates for multi-arch binary archives unless you have a very strong reason and a tested collision-proof format.

A proven exception is a template that includes enough uniqueness dimensions (at minimum: project, version, os, arch), like the working `go-playerctl` pattern.

Why:

- New architectures (for example `windows/arm`) can appear over time.
- A hand-rolled name template that seemed unique can start colliding.
- Typical failure is `archive ... already exists` during release.

Recommendation:

- Keep GoReleaser archive names on defaults.
- Keep only `format_overrides` for Windows zip/tar differences.
- If you ever customize names, include enough dimensions (`project`, `version`, `os`, `arch`, and architecture variants) and test against the full matrix before release.

Example of a safer template shape used successfully for manual-dispatch releases:

```yaml
archives:
  - formats: [tar.gz]
    name_template: >-
      {{ .ProjectName }}_{{ .Version }}_{{ .Os }}_{{ .Arch }}
```

---

## Step 13: Source Debian and Source RPM pipelines (separate lane)

You asked for this explicitly: source package generation should be its own lane and file structure.

Recommended repo layout:

```text
packaging/
  debian/
    control
    rules
    changelog
    source/format
  rpm/
    app.spec
  scripts/
    build-source-deb.sh
    build-source-rpm.sh
```

### Source Debian lane

```yaml
  source-deb:
    name: Build source .dsc/.orig.tar.*
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_packaging == 'true' && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update
      - run: sudo apt-get install -y devscripts debhelper build-essential fakeroot
      - name: Build source Debian package
        run: |
          chmod +x packaging/scripts/build-source-deb.sh
          packaging/scripts/build-source-deb.sh
      - uses: actions/upload-artifact@v4
        with:
          name: source-deb
          retention-days: 1
          path: |
            dist/deb-source/*.dsc
            dist/deb-source/*.debian.tar.*
            dist/deb-source/*.orig.tar.*
            dist/deb-source/*.changes
```

Example `packaging/scripts/build-source-deb.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="app"
VERSION="${GITHUB_REF_NAME#v}"
WORKDIR="/tmp/${APP_NAME}-${VERSION}"
OUTDIR="$PWD/dist/deb-source"

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR" "$OUTDIR"

git archive --format=tar.gz --prefix="${APP_NAME}-${VERSION}/" -o "$OUTDIR/${APP_NAME}_${VERSION}.orig.tar.gz" HEAD

tar -xzf "$OUTDIR/${APP_NAME}_${VERSION}.orig.tar.gz" -C /tmp
cp -r packaging/debian "/tmp/${APP_NAME}-${VERSION}/debian"

(
  cd "/tmp/${APP_NAME}-${VERSION}"
  dch --create -v "${VERSION}-1" --package "$APP_NAME" "Automated source release"
  dpkg-buildpackage -S -sa
)

mv /tmp/${APP_NAME}_${VERSION}-1* "$OUTDIR/" || true
```

### Source RPM lane

```yaml
  source-rpm:
    name: Build source .src.rpm
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_packaging == 'true' && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update
      - run: sudo apt-get install -y rpm
      - name: Build source RPM
        run: |
          chmod +x packaging/scripts/build-source-rpm.sh
          packaging/scripts/build-source-rpm.sh
      - uses: actions/upload-artifact@v4
        with:
          name: source-rpm
          retention-days: 1
          path: dist/rpm-source/*.src.rpm
```

Example `packaging/scripts/build-source-rpm.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="app"
VERSION="${GITHUB_REF_NAME#v}"
TOPDIR="$PWD/.rpmbuild"
OUTDIR="$PWD/dist/rpm-source"

mkdir -p "$TOPDIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS} "$OUTDIR"

git archive --format=tar.gz --prefix="${APP_NAME}-${VERSION}/" -o "$TOPDIR/SOURCES/${APP_NAME}-${VERSION}.tar.gz" HEAD
cp packaging/rpm/app.spec "$TOPDIR/SPECS/"

rpmbuild \
  --define "_topdir $TOPDIR" \
  --define "version $VERSION" \
  -bs "$TOPDIR/SPECS/app.spec"

cp "$TOPDIR/SRPMS"/*.src.rpm "$OUTDIR/"
```

This is intentionally independent from fastforge/GoReleaser so source package publishing is never blocked by app-bundle tooling changes.

---

## Step 14: Flatpak and optional app-store packaging lane

For Flutter/Qt desktop apps, keep a manual lane. If Flutter build artifacts were produced earlier, this lane can package those; if not, it can run from source directly.

```yaml
  flatpak-build:
    name: Flatpak package
    needs: [route, discover]
    if: ${{ needs.route.outputs.run_release == 'true' && (needs.discover.outputs.has_flutter == 'true' || needs.discover.outputs.has_qt_cpp == 'true') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: sudo apt-get update
      - run: sudo apt-get install -y flatpak flatpak-builder
      - name: Build Flatpak
        run: |
          flatpak-builder --force-clean build-dir packaging/flatpak/app.yaml
      - uses: actions/upload-artifact@v4
        with:
          name: flatpak-bundle
          retention-days: 1
          path: build-dir
```

---

## Step 15: Release fan-in and publish stages

Use multiple deploy stages (package -> publish -> promote).

### Manual release creation pattern (gh-release script style)

When you manually create releases, the `arran4/dotfiles` `executable_gh-release.sh` flow is a strong pattern, and it closes a common guide gap: generated release notes + discussion creation should be first-class:

- verify default GitHub repo context exists,
- compute version with `git-tag-inc` (`-print-version-only`),
- create and push tags with retry,
- create GitHub release with `--generate-notes`,
- use a default discussion category of `Announcements` (safe for default discussion setups), with graceful fallback when permissions/discussions prevent linking,
- mark prerelease automatically for `test|alpha|beta|rc` increments.
- fetch tags and compare the highest tag version against the source-controlled version before bumping, so release automation never bumps from stale in-repo version text.

You can keep this as a local operator script **and** wire equivalent logic in CI manual-dispatch mode.

Copy/paste CI step style:

```yaml
  manual-gh-release:
    name: Manual release creation
    needs: [prepare-release-tag]
    if: ${{ github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-') }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      discussions: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Sync version source with highest existing tag first
        run: |
          set -euo pipefail
          git fetch --tags --force
          # For repos with a source-controlled version, compare it with the
          # highest fetched tag and bump from whichever is newer.
          # Example: CMAKE_VERSION=$(grep -Po 'project\(app VERSION \K[0-9]+\.[0-9]+\.[0-9]+' CMakeLists.txt)
          # TAG_VERSION=$(git tag -l "v*" | sed 's/^v//' | sort -V | tail -n 1)
          # CURRENT_VERSION=$(echo -e "$CMAKE_VERSION\n$TAG_VERSION" | sort -V | tail -n 1)
      - name: Push prepared tag (retry)
        env:
          TAG: ${{ needs.prepare-release-tag.outputs.release_tag }}
        run: |
          set -euo pipefail
          git push origin "$TAG" || { sleep 2; git push origin "$TAG"; }
      - name: Create release with generated notes + discussion
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          TAG: ${{ needs.prepare-release-tag.outputs.release_tag }}
        run: |
          set -euo pipefail
          prerelease=""
          case "${{ inputs.mode }}" in
            release-test|release-rc|release-alpha) prerelease="--prerelease" ;;
          esac

          discussion_arg="--discussion-category Announcements"

          # Permissions/discussions can block discussion linking in some repos.
          # Fall back to plain release creation if category linking fails.
          if [[ -n "$prerelease" ]]; then
            gh release create "$TAG" --generate-notes $prerelease || true
          else
            gh release create "$TAG" --generate-notes $discussion_arg || \
              gh release create "$TAG" --generate-notes
          fi
```

Guide requirement: if you include a manual release lane, include both generated notes (`--generate-notes`) and discussion-category selection fallback logic so the LLM-generated workflow does not omit release discussions in repositories that use them. Use a fixed default discussion category (`Announcements`) and fall back to plain `gh release create --generate-notes` when permissions or discussions configuration block category linking. When running in Actions, set `permissions.discussions: write` (plus `contents: write`) for this lane.

To avoid duplicate release work, keep artifact publishers scoped by event (for example GoReleaser on tag-push/manual only, not `release: published`).

Integrate language publishers in the same publish stage:

- Go binaries: GoReleaser publish (GitHub releases + packages)
- Node/TS libraries: `npm publish` with `latest`/`next` dist-tags
- Dart/Flutter libraries: `dart pub publish` (or dry-run in non-release modes)
- Docker: release-only buildx push to GHCR, but only if the repo actually ships an image
- Non-binary repos: tag + GitHub release + generated notes + discussion flow, without inventing binary artifacts
- Versioned source repos: fetch tags and bump from the maximum of source version and latest tag, not just the checked-in version text


```yaml
  publish-draft:
    name: Publish draft release assets
    needs:
      - goreleaser
      - source-deb
      - source-rpm
      - docker-release
    if: ${{ needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - name: Collect artifacts
        uses: actions/download-artifact@v4
        with:
          path: dist-release
      - name: Publish draft GitHub release
        uses: softprops/action-gh-release@v2
        with:
          draft: true
          files: dist-release/**
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

  promote-release:
    name: Promote draft to published
    needs: [publish-draft]
    if: ${{ github.event_name == 'release' || (github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-')) }}
    runs-on: ubuntu-latest
    steps:
      - name: Release promoted via upstream process
        run: echo "Promotion step placeholder (gh api patch release draft=false)"
```

---

### Optional: Prepare next development version PR after release

This pattern from the referenced workflow is useful for repos that keep `-SNAPSHOT` / development versions in source control.

```yaml
  prepare-next-version-pr:
    name: Prepare next development iteration PR
    needs: [publish-draft]
    if: ${{ github.event_name == 'workflow_dispatch' && (startsWith(inputs.mode, 'release-') || inputs.mode == 'release-test') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Bump to next version and open PR
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          NEXT_VERSION="${{ needs.prepare-release-tag.outputs.next_version || '' }}"
          [[ -z "$NEXT_VERSION" ]] && { echo "No next version calculated; skipping."; exit 0; }

          BRANCH="bump-version-$NEXT_VERSION"
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git checkout -b "$BRANCH"

          # Replace with repo-specific version bump command(s)
          # mvn versions:set -DnewVersion="$NEXT_VERSION" -DgenerateBackupPoms=false

          git add -A
          git commit -m "Prepare next development iteration $NEXT_VERSION"
          git push -u origin "$BRANCH"
          gh pr create --title "Prepare next development iteration $NEXT_VERSION" --body "Automated PR for next iteration." --base main --head "$BRANCH"
```

---

## Step 16: Full skeleton (compact but wired)


This is the high-level skeleton to start from. Keep this in `.github/workflows/ci.yml` and split script details into `packaging/scripts` and config files.

```yaml
name: CI/CD

on:
  push:
    branches: [main, master]
    tags: ['v*', 'v*.*.*', 'v*.*.*-rc*', 'v*.*.*-beta*', 'test-*']
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review, closed]
    branches: [main, master]
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        default: lint-fix
        options: [lint-fix, build, release-major, release-minor, release-patch, release-test, release-rc, release-alpha, monthly-maintenance]
      release_version_override:
        type: string
        default: ''
      allow_prs:
        type: boolean
        default: true
  schedule:
    - cron: '17 3 1 * *'
    - cron: '41 2 * * *'

concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
  pull-requests: write
  checks: write
  packages: write
  security-events: write

jobs:
  route:
    # ... from section above
  prepare-release-tag:
    needs: [route]
    # ... from section above

  discover:
    needs: route
    # ... from section above

  gitleaks:
    needs: [route, discover]
    # ...

  java-build-test:
    needs: [route, discover]
    # ...

  hugo-build:
    needs: [route, discover]
    # ...

  hugo-deploy:
    needs: [route, discover, hugo-build]
    # ...

  golangci:
    needs: [route, discover]
    # ...

  go-test:
    needs: [route, discover, golangci]
    # ...

  go-vet:
    needs: [route, discover]
    # ...

  go-fmt-pr:
    needs: [route, discover]
    # ...

  node-lint-test:
    needs: [route, discover]
    # ...

  dart-analyze-test:
    needs: [route, discover]
    # ...

  flutter-analyze-test:
    needs: [route, discover]
    # ...

  flutter-build-artifacts:
    needs: [route, discover, flutter-analyze-test]
    # ...

  cpp-qt-build-test:
    needs: [route, discover]
    # ...

  c-make-build-test:
    needs: [route, discover]
    # ...

  docker-build:
    needs: [route, discover]
    # ...

  autofix:
    needs: [route, discover]
    # ...

  cleanup-autofix-prs:
    needs: [route]
    # ...

  goreleaser:
    needs: [route, discover, go-test, prepare-release-tag]
    # ...

  source-deb:
    needs: [route, discover]
    # ...

  source-rpm:
    needs: [route, discover]
    # ...

  docker-release:
    needs: [route, discover, docker-build]
    # ...

  publish-draft:
    needs: [goreleaser, source-deb, source-rpm, docker-release]
    # ...

  promote-release:
    needs: [publish-draft]
    # ...

  prepare-next-version-pr:
    needs: [publish-draft, prepare-release-tag]
    # ...
```

---

## What to decide at install time vs runtime

**Install/template time (prefer this):**

- expected project stacks,
- release channels,
- package targets,
- which jobs are required.

**Runtime (safety):**

- file presence detection,
- public/private profile,
- event-mode routing,
- monthly/nightly schedule behavior.

This gives sane defaults while still protecting mixed repos.

---

## Public vs private behavior recommendations

| Area | Public | Private |
|---|---|---|
| OS matrix | Linux default (add macOS/Windows only when required) | Linux default |
| Parallelism | wide job fan-out | narrower job fan-out, parallel inside step |
| Security | broader PR scans | monthly/full-mode deep scans |
| Artifact retention | longer | shorter |
| Validation strictness | maximum | practical baseline + release hardening |

Visibility should be auto-detected (`github.event.repository.private`) and not manually toggled.

### Storage guardrail: artifact expiry policy (important)

To prevent GitHub Actions storage overages, set `retention-days` on **every** `actions/upload-artifact` step.

Required policy for this template:

- set **`retention-days: 1`** on every `actions/upload-artifact` step.
- publish/promote jobs should consume artifacts immediately in the same workflow run.

Copy/paste baseline:

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: ci-temp-output
    path: dist/**
    retention-days: 1
```

Optional monthly cleanup (especially useful for private repos with low storage quota):

```yaml
  cleanup-old-artifacts:
    name: Cleanup old CI artifacts
    if: ${{ needs.route.outputs.is_monthly == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - name: Delete artifacts older than 1 day
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          cutoff=$(date -u -d '1 day ago' +%s)
          gh api repos/${{ github.repository }}/actions/artifacts --paginate \
            --jq '.artifacts[] | [.id, .created_at] | @tsv' | \
          while IFS=$'	' read -r id created; do
            created_epoch=$(date -u -d "$created" +%s)
            if (( created_epoch < cutoff )); then
              gh api -X DELETE repos/${{ github.repository }}/actions/artifacts/$id || true
            fi
          done
```

---

## Final checklist before rollout

1. Add config files (`.golangci.yml`, `.goreleaser.yml`, `analysis_options.yaml`, `.gitleaks.toml`, `.clang-format`).
2. Add packaging scripts under `packaging/scripts/`.
3. Add `packaging/debian` and `packaging/rpm` metadata.
4. Dry-run with `workflow_dispatch mode=build` or `mode=lint-fix`.
5. Validate `lint-fix` creates/labels branches correctly.
6. Validate `pull_request.closed` cleanup against test PRs.
7. Validate monthly schedule and release lanes.
8. Validate that every `git`-mutating job starts with `actions/checkout@v4`.

### README distribution/install checklist (do not skip)

When you add release lanes, update `README.md` so users know how to install from each release target. Match the README to what the repo actually ships; if there is no binary, do not add fake binary install instructions just because the template has them. At minimum, list:

- **GitHub Releases** (binary/tarball download path),
- **Homebrew** tap install command,
- **Docker** image pull/run command,
- **Go install** command for Go CLIs,
- **native package methods** (`deb`, `rpm`, `apk`, `archlinux`) where available.

Copy/paste template:

```md
## Install

### GitHub Releases
Download binaries from: https://github.com/OWNER/REPO/releases

### Homebrew
brew tap OWNER/homebrew-tap
brew install app

### Docker
docker pull ghcr.io/OWNER/REPO:latest
docker run --rm ghcr.io/OWNER/REPO:latest --help

### Go install
go install github.com/OWNER/REPO/cmd/app@latest

### Native packages
- Debian/Ubuntu (`.deb`): see Releases assets
- RPM (`.rpm`): see Releases assets
- Alpine (`.apk`): see Releases assets
- Arch (`.pkg.tar.zst` or repo): see Releases assets
```

This keeps release automation and user-facing install documentation aligned.

---

## Closing

If your goal is "one CI file that does everything", make it explicit, sectioned, and policy-driven.

The winning pattern is:

- route events,
- detect capabilities,
- branch by profile,
- run language lanes in parallel,
- split release lanes by output type,
- and automate cleanup lifecycle.

That gives you the giant file you wanted, with practical behavior for real repos rather than demo YAML.
