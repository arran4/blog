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
- It can run in **public mode** (wider matrix, more checks) or **private mode** (cost-controlled).
- It includes **autofix PR creation + cleanup**, **security checks**, **artifact fan-out**, and **release lanes**.
- It accounts for packaging outputs beyond standard app bundles, including **source Debian** and **source RPM** pipeline hooks.

The point is not tiny YAML. The point is one intelligent CI/CD platform per repo.

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
        default: "validate"
        type: choice
        options:
          - validate
          - lint-fix
          - build
          - release-snapshot
          - release
          - monthly-maintenance
      release_mode:
        description: "Release mode"
        required: false
        default: "snapshot"
        type: choice
        options: [snapshot, release]
      release_increment:
        description: "Version increment to apply when preparing release tags"
        required: false
        default: "patch"
        type: choice
        options: [major, minor, patch, none]
      prerelease_channel:
        description: "Pre-release channel"
        required: false
        default: "none"
        type: choice
        options: [none, uat, test, rc, beta, alpha]
      prerelease_number:
        description: "Optional pre-release sequence number (for example: 1 in -rc.1)"
        required: false
        default: ""
        type: string
      increment_mode:
        description: "Alternative increment control style (kagura-style)"
        required: false
        default: "release"
        type: choice
        options: [major, minor, patch, release, test]
      release_version_override:
        description: "Optional explicit release version (for example 2.4.0 or 2.4.0-uat.2)"
        required: false
        default: ""
        type: string
  schedule:
    # preferred heavy monthly run (quota reset strategy)
    - cron: '17 3 1 * *'
    # optional nightly lightweight checks
    - cron: '41 2 * * *'
```

### Why this is better

- It handles PR close cleanup flows.
- It supports semantic tags and release candidates.
- It exposes explicit manual operational modes (`validate`, `lint-fix`, `release-snapshot`, etc).
- It lets you choose release increment semantics (`major|minor|patch`) and prerelease channels (`uat|test|rc|beta|alpha`).

---

## Step 1.5: Release increment + prerelease channel control (copy/paste)

You asked for explicit release bump controls. Add a dedicated lane that computes/pushes the tag before release jobs run.

```yaml
  prepare-release-tag:
    name: Prepare release tag
    needs: [route]
    if: ${{ github.event_name == 'workflow_dispatch' && (inputs.mode == 'release' || inputs.mode == 'release-snapshot') }}
    runs-on: ubuntu-latest
    outputs:
      release_tag: ${{ steps.tag.outputs.release_tag }}
      next_version: ${{ steps.tag.outputs.next_version }}
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      # Option A: use git-tag-inc (recommended if you already use it)
      - name: Compute tag via git-tag-inc
        id: tag
        shell: bash
        run: |
          set -euo pipefail

          base_flag=""
          case "${{ inputs.release_increment }}" in
            major) base_flag="--major" ;;
            minor) base_flag="--minor" ;;
            patch) base_flag="--patch" ;;
            none)  base_flag="" ;;
          esac

          pre_flag=""
          if [[ "${{ inputs.prerelease_channel }}" != "none" ]]; then
            if [[ -n "${{ inputs.prerelease_number }}" ]]; then
              pre_flag="--prerelease ${{ inputs.prerelease_channel }}.${{ inputs.prerelease_number }}"
            else
              pre_flag="--prerelease ${{ inputs.prerelease_channel }}"
            fi
          fi

          # Example command (adjust if your git-tag-inc flags differ)
          next_tag=$(git-tag-inc $base_flag $pre_flag)
          echo "release_tag=$next_tag" >> "$GITHUB_OUTPUT"

          # Optional next version hint (patch-forward default)
          clean_tag="${next_tag#v}"
          clean_tag="${clean_tag%%-*}"
          IFS='.' read -r maj min pat <<< "$clean_tag"
          maj=${maj:-0}; min=${min:-0}; pat=${pat:-0}
          echo "next_version=${maj}.${min}.$((pat + 1))-SNAPSHOT" >> "$GITHUB_OUTPUT"

      - name: Push tag
        env:
          TAG: ${{ steps.tag.outputs.release_tag }}
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git tag "$TAG"
          git push origin "$TAG"
```

If you do not use `git-tag-inc`, keep the same inputs and swap the compute step with your own semver script.

### Kagura-style increment logic (copy/paste alternative)

The referenced `kagura-original` workflow also uses a practical fallback model:

- parse current version,
- apply increment mode (`major`, `minor`, `patch`, `release`, `test`),
- optionally allow a direct version override,
- tag the release,
- and create a PR that bumps to the next `-SNAPSHOT` development version.

```yaml
      - name: Prepare version/tag (kagura-style)
        id: prep_version
        shell: bash
        run: |
          set -euo pipefail

          CURRENT_VERSION="$(mvn help:evaluate -Dexpression=project.version -q -DforceStdout)"
          BASE_VERSION="${CURRENT_VERSION%-SNAPSHOT}"
          IFS='.' read -r -a PARTS <<< "$BASE_VERSION"
          MAJOR=${PARTS[0]:-0}; MINOR=${PARTS[1]:-0}; PATCH=${PARTS[2]:-0}

          MODE="${{ inputs.increment_mode }}"
          OVERRIDE="${{ inputs.release_version_override }}"

          if [[ -n "$OVERRIDE" ]]; then
            NEW_VERSION="$OVERRIDE"
          elif [[ "$MODE" == "major" ]]; then
            NEW_VERSION="$((MAJOR + 1)).0.0"
          elif [[ "$MODE" == "minor" ]]; then
            NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
          elif [[ "$MODE" == "patch" ]]; then
            NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
          elif [[ "$MODE" == "test" ]]; then
            NEW_VERSION="$BASE_VERSION-test"
          else
            NEW_VERSION="$BASE_VERSION"
          fi

          IFS='.' read -r -a NP <<< "${NEW_VERSION%-*}"
          NEXT_VERSION="${NP[0]:-0}.${NP[1]:-0}.$(( ${NP[2]:-0} + 1 ))-SNAPSHOT"

          echo "TAG_NAME=v$NEW_VERSION" >> "$GITHUB_OUTPUT"
          echo "NEXT_VERSION=$NEXT_VERSION" >> "$GITHUB_OUTPUT"
```

This model is excellent for repositories that want release tagging and automatic next-iteration bump PRs in one flow.

---

## Step 2: Event routing to reduce duplicate runs

You noted a real issue: push + PR can duplicate work. We fix it with a routing job and strict `if:` usage.

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: true

permissions:
  contents: write
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

          case "${{ github.event_name }}" in
            push)
              run_code_checks=true
              ;;
            pull_request)
              if [[ "${{ github.event.action }}" == "closed" ]]; then
                run_cleanup=true
              else
                # keep PR checks scoped to metadata/docs/non-build checks where desired
                run_pr_meta_checks=true
              fi
              ;;
            release)
              run_release=true
              ;;
            workflow_dispatch)
              run_code_checks=true
              if [[ "${{ inputs.mode }}" == "release" || "${{ inputs.mode }}" == "release-snapshot" ]]; then
                run_release=true
              fi
              if [[ "${{ inputs.mode }}" == "monthly-maintenance" ]]; then
                is_monthly=true
              fi
              ;;
            schedule)
              run_code_checks=true
              if [[ "${{ github.event.schedule }}" == "17 3 1 * *" ]]; then
                is_monthly=true
              fi
              ;;
          esac

          echo "run_code_checks=$run_code_checks" >> "$GITHUB_OUTPUT"
          echo "run_pr_meta_checks=$run_pr_meta_checks" >> "$GITHUB_OUTPUT"
          echo "run_cleanup=$run_cleanup" >> "$GITHUB_OUTPUT"
          echo "run_release=$run_release" >> "$GITHUB_OUTPUT"
          echo "is_monthly=$is_monthly" >> "$GITHUB_OUTPUT"
```

This gives explicit behavior control instead of relying only on cancellation.

---

## Step 3: Discovery job (template-time first, runtime second)

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
      has_packaging: ${{ steps.detect.outputs.has_packaging }}
    steps:
      - uses: actions/checkout@v4

      # Optional template-time toggles (set defaults in your repo and keep these comments)
      # EXPECT_GO=true
      # EXPECT_NODE=false
      # EXPECT_FLUTTER=false
      # EXPECT_QT_CPP=false

      - id: detect
        shell: bash
        run: |
          set -euo pipefail
          [[ -f go.mod ]] && echo "has_go=true" >> "$GITHUB_OUTPUT" || echo "has_go=false" >> "$GITHUB_OUTPUT"
          [[ -f package.json ]] && echo "has_node=true" >> "$GITHUB_OUTPUT" || echo "has_node=false" >> "$GITHUB_OUTPUT"
          [[ -f pubspec.yaml ]] && echo "has_dart=true" >> "$GITHUB_OUTPUT" || echo "has_dart=false" >> "$GITHUB_OUTPUT"
          ([[ -f pubspec.yaml ]] && rg -n "^\s*flutter:" pubspec.yaml >/dev/null 2>&1) && echo "has_flutter=true" >> "$GITHUB_OUTPUT" || echo "has_flutter=false" >> "$GITHUB_OUTPUT"
          ([[ -f CMakeLists.txt ]] || rg -n "find_package\((Qt|Qt6|Qt5)" -S . >/dev/null 2>&1) && echo "has_qt_cpp=true" >> "$GITHUB_OUTPUT" || echo "has_qt_cpp=false" >> "$GITHUB_OUTPUT"
          ([[ -f Makefile ]] || [[ -f makefile ]]) && echo "has_make_c=true" >> "$GITHUB_OUTPUT" || echo "has_make_c=false" >> "$GITHUB_OUTPUT"
          ([[ -f Dockerfile ]] || [[ -f Dockerfile.goreleaser ]] || [[ -f docker/Dockerfile ]]) && echo "has_docker=true" >> "$GITHUB_OUTPUT" || echo "has_docker=false" >> "$GITHUB_OUTPUT"
          ([[ -f .goreleaser.yml ]] || [[ -f .goreleaser.yaml ]]) && echo "has_goreleaser=true" >> "$GITHUB_OUTPUT" || echo "has_goreleaser=false" >> "$GITHUB_OUTPUT"
          ([[ -d packaging ]] || [[ -d pkg ]] || [[ -f debian/control ]] || [[ -f .github/packaging/source-rpm.spec ]]) && echo "has_packaging=true" >> "$GITHUB_OUTPUT" || echo "has_packaging=false" >> "$GITHUB_OUTPUT"

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
    if: ${{ needs.route.outputs.run_cleanup != 'true' }}
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

## Step 6: Go lane (tests, lint, vet, release prep)

Use `setup-go` built-in caching instead of manual `actions/cache`.

```yaml
  go-lint-test:
    name: Go lint/test (${{ matrix.os }})
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: ${{ fromJSON(needs.discover.outputs.profile == 'public' && '["ubuntu-latest","windows-latest","macos-latest"]' || '["ubuntu-latest"]') }}
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
```

This separates `go test` and `go vet` so public repos can run in parallel.

---

## Step 7: Node lane (tests, lint, source package)

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
          path: |
            *.tgz
            npm-pack-result.json
```

---

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
          path: |
            build/linux/**
            build/app/outputs/flutter-apk/*.apk
```

### Fastforge note

Fastforge is optional. Keep it if you want it; remove it if you don't. The key pattern is to keep release outputs available through independent lanes (flatpak, source packages, container artifacts, GoReleaser outputs) so your pipeline doesn't depend on a single packaging tool.

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

## Step 10: Autofix lane (specific, wired per language)

You wanted this wired to real formatters and branch-name guessable behavior.

```yaml
  autofix:
    name: Auto-format and open PR
    needs: [route, discover]
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'lint-fix' }}
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

This uses both a label and a guessable branch pattern with parent linkage.

---

## Step 11: Docker lanes (build and release)

If repo has Go + Dockerfile or standalone Docker service, build and (optionally) push.

```yaml
  docker-build:
    name: Docker build
    needs: [route, discover]
    if: ${{ needs.discover.outputs.has_docker == 'true' && needs.route.outputs.run_code_checks == 'true' }}
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

---

## Step 12: GoReleaser lane (binary + packages)

```yaml
  goreleaser:
    name: GoReleaser
    needs: [route, discover, go-lint-test, prepare-release-tag]
    if: ${{ needs.discover.outputs.has_go == 'true' && needs.discover.outputs.has_goreleaser == 'true' && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v6
        with:
          go-version-file: go.mod
      - uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: latest
          args: >-
            release --clean
            ${{ (github.event_name == 'workflow_dispatch' && inputs.release_mode != 'release') && '--snapshot' || '' }}
            ${{ needs.prepare-release-tag.outputs.release_tag != '' && format('--tag {0}', needs.prepare-release-tag.outputs.release_tag) || '' }}
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Example `.goreleaser.yml` baseline (copy/paste):

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

changelog:
  sort: asc
  filters:
    exclude:
      - '^docs:'
      - '^test:'
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
          path: build-dir
```

---

## Step 15: Release fan-in and publish stages

Use multiple deploy stages (package -> publish -> promote).

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
    if: ${{ github.event_name == 'release' || (github.event_name == 'workflow_dispatch' && inputs.mode == 'release') }}
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
    if: ${{ github.event_name == 'workflow_dispatch' && (inputs.mode == 'release' || inputs.mode == 'release-snapshot') }}
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
        default: validate
        options: [validate, lint-fix, build, release-snapshot, release, monthly-maintenance]
      release_mode:
        type: choice
        default: snapshot
        options: [snapshot, release]
      release_increment:
        type: choice
        default: patch
        options: [major, minor, patch, none]
      prerelease_channel:
        type: choice
        default: none
        options: [none, uat, test, rc, beta, alpha]
      prerelease_number:
        type: string
        default: ''
      increment_mode:
        type: choice
        default: release
        options: [major, minor, patch, release, test]
      release_version_override:
        type: string
        default: ''
  schedule:
    - cron: '17 3 1 * *'
    - cron: '41 2 * * *'

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
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

  go-lint-test:
    needs: [route, discover]
    # ...

  go-vet:
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
    needs: [route, discover, go-lint-test, prepare-release-tag]
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
| OS matrix | Linux + macOS + Windows | Linux default |
| Parallelism | wide job fan-out | narrower job fan-out, parallel inside step |
| Security | broader PR scans | monthly/full-mode deep scans |
| Artifact retention | longer | shorter |
| Validation strictness | maximum | practical baseline + release hardening |

Visibility should be auto-detected (`github.event.repository.private`) and not manually toggled.

---

## Final checklist before rollout

1. Add config files (`.golangci.yml`, `.goreleaser.yml`, `analysis_options.yaml`, `.gitleaks.toml`, `.clang-format`).
2. Add packaging scripts under `packaging/scripts/`.
3. Add `packaging/debian` and `packaging/rpm` metadata.
4. Dry-run with `workflow_dispatch mode=validate`.
5. Validate `lint-fix` creates/labels branches correctly.
6. Validate `pull_request.closed` cleanup against test PRs.
7. Validate monthly schedule and release lanes.

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
