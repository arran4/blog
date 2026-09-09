---
title: "Canonical GitHub Actions CI/CD Super-Reference"
date: 2026-09-08T06:33:54Z
draft: false
tags: ["github-actions", "ci", "cd", "release", "automation", "goreleaser", "canonical"]
categories: ["devops", "reference", "automation"]
---

<!-- cspell:words GOPATH jurplel mvcommon qmake stefanzweifel todate -->

This is the canonical GitHub Actions CI/CD generation reference.

It supersedes `006`, `011`, `028`, `041` and `042` where they conflict. Agents should normally need THIS article only. Older posts remain useful as historical/rationale material but are no longer the generation specification.

## 1. Purpose and intended use

The purpose of this article is to serve as a complete generation specification for GitHub Actions CI/CD. An agent receiving only this article should have enough guidance to:
1. inspect a repository;
2. inventory its languages, build systems, package/release mechanisms, existing workflows, and repository-specific requirements;
3. determine which standard CI capabilities apply;
4. create one coherent workflow architecture;
5. preserve useful existing behavior;
6. remove obsolete/duplicate CI;
7. implement tests/lint/build/autofix/artifacts/release/maintenance consistently;
8. validate the resulting workflow;
9. explain any justified deviations from the canonical architecture.

The article should strongly reduce agent discretion in areas where we already have preferred patterns. Repository-specific differences should come primarily from capability selection, not from every agent inventing a completely different CI topology.

## 2. Required repository inspection before generation

Before generating or modifying any CI configuration, you must:
- enumerate all `.github/workflows/*`;
- understand each trigger/job;
- inventory useful behavior;
- identify duplicate validation;
- identify every release owner;
- identify obsolete compatibility wrappers;
- inspect repository build/release documentation;
- inspect package/release configuration;
- identify relevant secrets and permissions;
- inspect historical CI failures if necessary.

## 3. Canonical architecture and invariants

The default should be the fewest coherent workflow files necessary, normally one central `.github/workflows/ci.yml` or `.github/workflows/ci.yaml`. Do not preserve multiple workflow files merely because they already exist. A second workflow is acceptable only for a concrete technical or trust-boundary reason.

The canonical orchestration phases must remain consistent:
```text
route
  |
  +-- validation/lint/test
  |
  +-- autofix where applicable
  |
  +-- build/artifacts
  |
  +-- release validation
  |
  +-- release/tag context
  |
  +-- one publisher
  |
  +-- downstream/post-release work
```

Generated workflows must include a short top-of-file pointer back to THIS new article. Do not accumulate pointers to superseded articles.

## 4. Capability-selection matrix

Before generating jobs, classify capabilities as:
- **A. UNIVERSAL DEFAULT:** Baseline routing, basic validation, concurrency logic.
- **B. ENABLED WHEN REPOSITORY CAPABILITY EXISTS:** Language-specific lint/test (Go, Node, Dart, CMake, Dockerfile, Debian/RPM packaging, etc.), artifact building, packaging, GoReleaser.
- **C. OPTIONAL POLICY:** Autofix PR generation, maintenance scheduling, PR constraints.
- **D. EXCEPTION REQUIRING AN EXPLANATION:** Additional workflows, custom semantic version math.

Do not create irrelevant language jobs merely because examples exist. Conversely, do not omit an obvious standard lane if it matches a repository capability. At the same time, do not omit an obvious standard lane merely because the agent decided to produce a minimalist workflow.

## 5. Trigger/event model

The standard event triggers should cover:
```yaml
on:
  push:
    branches: [main, master]
    tags: ['v*', 'v*.*.*', 'v*.*.*-rc*', 'v*.*.*-beta*', 'test-*']
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review, closed]
    branches: [main, master]
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        default: lint-fix
        options: [lint-fix, build, release-major, release-minor, release-patch, release-test, release-rc, release-alpha, monthly-maintenance, publish-tag]
      release_version_override:
        type: string
        default: ''
      allow_prs:
        type: boolean
        default: true
  schedule:
    - cron: '17 3 1 * *'
    - cron: '41 2 * * *'
```

## 6. Routing

A routing job should parse events to determine if the run should execute monthly jobs, manual releases, regular CI tests, auto-fixes, or deployment behaviors.

## 7. Concurrency

Concurrency prevents duplicate manual releases from racing and cleans up outdated PR tests.
```yaml
# Concurrency prevents duplicate manual releases from racing and cleans up outdated PR tests.
# Crucially, release preparation should NOT cancel in progress to avoid aborting a cut tag.
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ !startsWith(github.event.inputs.mode, 'release-') }}
```

## 8. Permissions/security boundaries

Use read-only workflow-level permissions by default, and elevate them per-job. Do not give the whole workflow broad write permissions for convenience.
- normal validation: `contents: read`
- autofix: `contents: write`, `pull-requests: write`
- manual tag + explicit dispatch: `contents: write`, `actions: write`
- release publisher: `contents: write`, `packages: write` (when containers/packages need it)
- security upload: `security-events: write` (only where necessary)

## 9. Common checkout/setup conventions

Every git-mutating job, and every build job, must use actions/checkout. Use `fetch-depth: 0` for release prep jobs or when the history is needed.

## 10. Validation/test/lint architecture

Tests and linters should run concurrently after routing. All release policies require test validation before permanent tags are cut. Public repositories can generally run broader checks by default. Visibility check via `github.event.repository.private`. Private repositories may use a more conservative/cost-aware profile, but do not compromise required release validation.

## 11. Language-specific lanes

Standard modules exist for:
- Go (`golangci-lint`, `go test`, `go vet`, `gofmt`)
- Node (`npm test`, `eslint`, `prettier`)
- Dart / Flutter (`dart analyze`, `flutter test`)
- C / C++ / CMake / Qt
Select modules based on repository capabilities, not generically. Keep these as standard selectable modules within one architecture, with compatible routers and outputs.

Example Go lane:
```yaml
  golangci:
    name: Lint Go Code
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - run: go install github.com/golangci/golangci-lint/v2/cmd/golangci-lint@latest
      - run: golangci-lint run
```

Example Node lane:
```yaml
  node-lint-test:
    name: Node Lint & Test
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint
      - run: npm test
```

Example Dart lane:
```yaml
  dart-analyze-test:
    name: Dart Analyze & Test
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: dart-lang/setup-dart@v1
      - run: dart pub get
      - run: dart analyze --fatal-infos
      - run: dart test
```

Example C/CMake lane:
```yaml
  c-make-build-test:
    name: C CMake Build & Test
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: cmake -B build -S .
      - run: cmake --build build
      - run: ctest --test-dir build --output-on-failure
```

Example Qt/C++ lane:
```yaml
  qt-build-test:
    name: Qt C++ Build & Test
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Install Qt
        uses: jurplel/install-qt-action@v4
      - run: qmake
      - run: make
      - run: make check
```

Example Security/Gitleaks lane:
```yaml
  gitleaks:
    name: Gitleaks
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: gitleaks/gitleaks-action@v3
```

Example Autofix lane:
```yaml
  autofix:
    name: Autofix Formatting
    needs: [route]
    # Only run on pull requests explicitly from the same repository to avoid fork push failures.
    # Fork PRs should run validation only rather than attempt pushback.
    if: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v7
        with:
          ref: ${{ github.head_ref }}
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - run: go fmt ./...
      - name: Commit fixes
        uses: stefanzweifel/git-auto-commit-action@v7
        with:
          commit_message: "style: auto-format code"
```

Example Debian/RPM packaging lane:
```yaml
  packaging:
    name: Linux Packages
    needs: [route, validation]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build Source Debian Package
        run: |
          # Use proper debian source packaging
          sudo apt-get install -y dpkg-dev
          dpkg-source -b .
          mkdir -p dist
          mv ../*.dsc ../*.tar.* dist/
      - name: Build Source RPM Package
        run: |
          # Use proper rpm source packaging
          sudo apt-get install -y rpm
          mkdir -p dist
          rpmbuild -bs --define "_sourcedir $PWD" --define "_srcrpmdir $PWD/dist" package.spec
      - uses: actions/upload-artifact@v7
        with:
          name: packages
          path: dist/*
          if-no-files-found: error
          retention-days: 1
```

Example non-GoReleaser single owner publication:
```yaml
  publish-generic:
    name: Publish Generic Release
    needs: [route, packaging]
    if: ${{ github.ref_type == 'tag' && github.event_name == 'workflow_dispatch' && inputs.mode == 'publish-tag' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - uses: actions/download-artifact@v8
        with:
          name: packages
          path: release-artifacts
      - uses: softprops/action-gh-release@v3
        with:
          files: release-artifacts/**
```

Example scheduled maintenance cleanup:
```yaml
  maintenance:
    name: Monthly Cleanup
    needs: [route]
    if: ${{ needs.route.outputs.is_maintenance == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write
    steps:
      - name: Cleanup old workflow runs
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          # E.g., delete runs older than 30 days
          gh api repos/${{ github.repository }}/actions/runs --paginate -q '.workflow_runs[] | select(.created_at < (now - 2592000 | todate)) | .id' | xargs -I{} gh api -X DELETE repos/${{ github.repository }}/actions/runs/{} || true
```



## 12. Autofix architecture

Autofix should:
- be opt-in / appropriate to the repository;
- run deterministic mechanical fixes (`gofmt / go fix`, `prettier`, `dart/flutter format`);
- inspect resulting diff and do nothing when clean;
- create a focused PR when allowed;
- not mix unrelated fixes;
- not publish releases;
- have appropriately narrow permissions.

## 13. Build/artifact architecture

Build artifacts should use `actions/upload-artifact@v7`.
**Crucial constraint:** Always set `retention-days: 1` on every `actions/upload-artifact` step to prevent storage overages. Publish/promote jobs should consume artifacts immediately in the same workflow run.

## 14. Release-version planning

`git-tag-inc` MUST BE A FIRST-CLASS DEFAULT.
Do not use shell arithmetic fallbacks for semantic versions. Use `arran4/git-tag-inc` or `arran4/git-tag-inc-action` as the authoritative version logic. Version arithmetic belongs in shared tooling, while repository-specific logic controls the release *policy* and transactional *safety*.

The current `git-tag-inc-action` interpolates inputs directly into shell source and is currently unsuitable for untrusted/user-controlled values. You must use the safe pinned CLI installation approach as the temporary production recommendation until the action is hardened.

## 15. Tagging and release preparation

Manual release validation gates:
- verify request is on main
- checkout full history/tags
- run validation/tests
- fetch current `origin/main`
- verify `$GITHUB_SHA == origin/main`
- calculate next tag using shared tooling
- create/push immutable tag
- explicitly dispatch publisher at that TAG REF using `GITHUB_TOKEN`

The permanent tag MUST come after validation gates. Use concurrency so two manual release requests cannot race.

## 16. GitHub Release ownership

FOR ONE TAG, EXACTLY ONE JOB OR TOOL OWNS CREATION/PUBLICATION OF THE GITHUB RELEASE. Do not surround it with multiple release creators, duplicate draft steps, or `|| true`. `release: published` is downstream/notification state, not another creation path. Never hide duplicate release creation with `|| true`.

## 17. GoReleaser architecture

If GoReleaser is used, GoReleaser is the *sole* release owner. Do not create a separate `softprops/action-gh-release` step.

## 18. Non-GoReleaser release architecture

If not using GoReleaser, one generic publisher job uses `softprops/action-gh-release` or another appropriate single mechanism.

## 19. Containers

Docker build lanes should integrate securely, utilizing `.Env.GITHUB_REPOSITORY | tolower` in GoReleaser templates if dynamically injecting tags.

If building containers outside of GoReleaser, use the standard `docker/build-push-action`.

```yaml
  docker-build:
    name: Docker Build
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4
      - name: Build and push (internal cache, no release)
        uses: docker/build-push-action@v7
        with:
          context: .
          push: false
          load: true
          tags: test-image:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## 20. Package/source-package publication

Native packages (Debian, RPM, etc.) are generated as artifacts and gathered by the single release owner for distribution.

Example artifact consumption:
```yaml
      - name: Collect artifacts
        uses: actions/download-artifact@v8
        with:
          path: dist-release
```


## 21. Scheduled/monthly maintenance

Include maintenance lanes for routine cleanup or deeper monthly scans. Ensure scheduled jobs cannot accidentally route into release publication.

## 22. Cleanup lifecycle

Artifacts should expire quickly. Merge-closed events or scheduled logic should optionally clean up test branches.

## 23. Recovery/idempotency

If publication fails after a tag is created, use explicit recovery input (`release_version_override`). Recovery must:
- verify the tag already exists;
- verify it resolves to the exact validated `$GITHUB_SHA` (annotated tags dereferenced where necessary);
- fail if it does not match exactly or does not exist.
Do not silently move tags or bump to a new version. If it exists at the correct commit, continuing publication should be safe/idempotent.

## 24. Existing-workflow migration procedure

When upgrading CI, inventory existing capabilities, remove duplicated workflows, and consolidate them into the canonical layout. Map existing behavior into the canonical architecture. Delete dead CI files. Do not leave dead/disabled copies behind.

## 25. User Input / Shell Safety

Make this a general rule. Never embed user-controlled workflow input directly into shell source like:

```yaml
    run: something "${{ inputs.foo }}"
```

when the value can contain shell syntax. Pass inputs through `env:` and consume them as properly quoted shell variables. Apply this to release versions, modes, refs, action arguments, filenames, etc. Explain that action authors need the same discipline.

## 26. Action Version Policy

Agents MUST verify current supported GitHub Action versions when generating/upgrading CI. Do not trust remembered major versions from model training. However, distinguish:
- GitHub Action major references where following a supported major is intended;
- release-critical external binaries/actions where a more precise pin is desirable.

Avoid examples that imply stale major versions are forever canonical. Verify current major/version at generation time.

## 27. Testability

Generated release policy should be testable. When repository-specific helper code is necessary, tests should call the SAME helper production calls. Do not let test scripts reimplement the version/recovery algorithm.

For release calculation/recovery tests, cover relevant cases such as:
- normal stable patch/minor/major;
- stable release after an RC;
- RC continuation;
- test continuation;
- RC/test channel isolation;
- malformed tag histories;
- valid recovery;
- missing recovery tag;
- wrong-SHA recovery tag;
- annotated tags where relevant;
- shell-meta-character input;
- dry-run/non-mutating behavior.

Version arithmetic itself should be tested upstream in `git-tag-inc`; repository tests should focus on repository policy and integration.

## 28. Anti-patterns

DO NOT GENERATE:
- multiple GitHub Release owners;
- bespoke repository SemVer parsers when `git-tag-inc` can do the arithmetic;
- fallback shell SemVer implementations;
- tag creation before validation;
- assuming `GITHUB_TOKEN` tag push automatically triggers another workflow;
- `release: published` feeding back into publication;
- broad workflow-global write permissions;
- user-controlled `${{ inputs.* }}` injected directly into shell source;
- blind recreation/movement of an existing release tag;
- independent release logic duplicated between YAML and test scripts;
- tests that reimplement production logic rather than invoking it;
- ignored release errors via `|| true`;
- keeping dead legacy workflow files;
- a generic workflow that runs irrelevant language lanes;
- a minimalist workflow that silently omits obvious repo capabilities;
- dynamic runtime detection being used as an excuse not to tailor the generated YAML to the repository.

## 29. Full coherent reference skeleton

This is a comprehensive skeleton demonstrating the correct relationships. Note: Adjust jobs and steps to match the specific repo capabilities.

```yaml
# Canonical Reference workflow. For generating/updating CI, refer to:
# https://arran4.github.io/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/

name: CI/CD

on:
  push:
    branches: [main, master]
    tags: ['v*', 'v*.*.*', 'v*.*.*-rc*', 'v*.*.*-beta*', 'test-*']
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review, closed]
    branches: [main, master]
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        default: lint-fix
        options: [lint-fix, build, release-major, release-minor, release-patch, release-test, release-rc, release-alpha, monthly-maintenance, publish-tag]
      release_version_override:
        type: string
        default: ''
      allow_prs:
        type: boolean
        default: true
  schedule:
    - cron: '17 3 1 * *'
    - cron: '41 2 * * *'

# Concurrency prevents duplicate manual releases from racing and cleans up outdated PR tests.
# Crucially, release preparation should NOT cancel in progress to avoid aborting a cut tag.
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ !startsWith(github.event.inputs.mode, 'release-') }}

permissions:
  contents: read

jobs:
  route:
    name: Route Event
    runs-on: ubuntu-latest
    outputs:
      is_pull_request: ${{ steps.route.outputs.is_pull_request }}
      is_manual: ${{ steps.route.outputs.is_manual }}
      is_release: ${{ steps.route.outputs.is_release }}
      is_maintenance: ${{ steps.route.outputs.is_maintenance }}
    steps:
      - id: route
        env:
          EVENT_NAME: ${{ github.event_name }}
          INPUT_MODE: ${{ github.event.inputs.mode }}
        run: |
          set -euo pipefail
          is_pull_request=false
          is_manual=false
          is_release=false
          is_maintenance=false
          if [[ "$EVENT_NAME" == "pull_request" ]]; then
            is_pull_request=true
          elif [[ "$EVENT_NAME" == "workflow_dispatch" ]]; then
            is_manual=true
            if [[ "$INPUT_MODE" == "publish-tag" ]]; then
                is_release=true
            fi
          elif [[ "$EVENT_NAME" == "schedule" ]]; then
            is_maintenance=true
          fi
          echo "is_pull_request=$is_pull_request" >> "$GITHUB_OUTPUT"
          echo "is_manual=$is_manual" >> "$GITHUB_OUTPUT"
          echo "is_release=$is_release" >> "$GITHUB_OUTPUT"
          echo "is_maintenance=$is_maintenance" >> "$GITHUB_OUTPUT"

  validation:
    name: Validation & Tests
    needs: [route]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - run: go test ./...

  release-ready:
    name: Release Quality Gates Passed
    needs: [route, validation]
    if: always() && !contains(needs.*.result, 'failure') && !contains(needs.*.result, 'cancelled')
    runs-on: ubuntu-latest
    steps:
      - run: echo "All release quality gates passed."

  prepare-release-tag:
    name: Prepare Release Tag
    needs: [route, release-ready]
    if: ${{ github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-') }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
          # If no go.mod exists, specify a current major version instead
      - name: Verify Exact Origin/Main
        env:
          GITHUB_REF_NAME: ${{ github.ref }}
          GITHUB_SHA: ${{ github.sha }}
        run: |
          set -euo pipefail
          if [[ "$GITHUB_REF_NAME" != "refs/heads/main" ]]; then
            echo "Error: Manual release preparation must run on refs/heads/main, got $GITHUB_REF_NAME"
            sh -c "exit 1"
          fi
          git fetch origin main
          MAIN_SHA=$(git rev-parse origin/main)
          if [[ "$MAIN_SHA" != "$GITHUB_SHA" ]]; then
            echo "Error: Requested release against $GITHUB_SHA but origin/main is at $MAIN_SHA"
            sh -c "exit 1"
          fi
      - name: Calculate or recover version
        env:
          RELEASE_MODE: ${{ inputs.mode }}
          RELEASE_VERSION_OVERRIDE: ${{ inputs.release_version_override }}
        run: |
          set -euo pipefail
          export PATH="$(go env GOPATH)/bin:$PATH"
          if [[ -n "$RELEASE_VERSION_OVERRIDE" ]]; then
             echo "Recovering version $RELEASE_VERSION_OVERRIDE"
             # Validate shape and ensure it's a remote tag, then dereference
             if ! [[ "$RELEASE_VERSION_OVERRIDE" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?$ ]]; then
                echo "Error: Override $RELEASE_VERSION_OVERRIDE is not a valid release tag shape."
                sh -c "exit 1"
             fi
             TAG_SHA=$(git ls-remote --tags origin "refs/tags/$RELEASE_VERSION_OVERRIDE" | grep -v '{}$' | awk '{print $1}')
             if [[ -z "$TAG_SHA" ]]; then
                echo "Recovery failed: Tag $RELEASE_VERSION_OVERRIDE does not exist on origin."
                sh -c "exit 1"
             fi
             # Dereference if it's an annotated tag by checking for the peeled ^{} ref
             PEELED_SHA=$(git ls-remote --tags origin "refs/tags/$RELEASE_VERSION_OVERRIDE^{}" | awk '{print $1}')
             if [[ -n "$PEELED_SHA" ]]; then
                 TAG_SHA="$PEELED_SHA"
             fi
             if [[ "$TAG_SHA" != "$GITHUB_SHA" ]]; then
                echo "Recovery failed: Tag $RELEASE_VERSION_OVERRIDE points to $TAG_SHA, not $GITHUB_SHA"
                sh -c "exit 1"
             fi
             TAG="$RELEASE_VERSION_OVERRIDE"
          else
             # Use git-tag-inc safe version calculation
             echo "Installing pinned git-tag-inc..."
             go install github.com/arran4/git-tag-inc/cmd/git-tag-inc@90266586fefee6ffcb9fb02b00543b5959cd6c13
             # Usage composing primitives. See semver_calc wrapper from mvcommon#20 for real world policy mapping
             TAG="$(git-tag-inc --print-version-only --skip-forwards "${RELEASE_MODE#release-}")"

             # Final race guard: verify origin/main is STILL exactly GITHUB_SHA right before tagging
             git fetch origin main
             CURRENT_MAIN_SHA=$(git rev-parse origin/main)
             if [[ "$CURRENT_MAIN_SHA" != "$GITHUB_SHA" ]]; then
                echo "Race condition: origin/main advanced to $CURRENT_MAIN_SHA before tagging"
                sh -c "exit 1"
             fi

             # Create and push the tag since it was calculated and verified
             git tag "$TAG"
             git push origin "$TAG" || {
                # Race safe remote verification
                REMOTE_SHA=$(git ls-remote --tags origin "$TAG" | awk '{print $1}')
                if [[ "$REMOTE_SHA" != "$GITHUB_SHA" ]]; then
                   echo "Race condition: tag pushed remotely with different SHA"
                   sh -c "exit 1"
                fi
             }
          fi
          echo "TAG=$TAG" >> "$GITHUB_ENV"
      - name: Dispatch Publisher
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh workflow run ci.yml --ref "$TAG" -f mode=publish-tag

  publisher:
    name: Release Publisher
    needs: [route]
    # Runs when explicitly dispatched from a tag
    if: ${{ github.ref_type == 'tag' && github.event_name == 'workflow_dispatch' && inputs.mode == 'publish-tag' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - name: Run GoReleaser (Sole Release Owner)
        uses: goreleaser/goreleaser-action@v7
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
```

## 30. Generation acceptance checklist

Before opening a CI PR, ensure:
- repository inspected before generation;
- selected capability matrix documented;
- obsolete workflows removed;
- event routes mutually coherent;
- PR checks visible;
- no accidental duplicate push/PR work beyond intended behavior;
- permissions minimized;
- user inputs safely passed via environment variables;
- tests/lint/build selected correctly;
- release validation happens before permanent tag;
- manual release only operates against current main;
- release concurrency protects tag calculation;
- shared `git-tag-inc` used rather than local SemVer arithmetic;
- recovery is exact-tag/exact-SHA;
- exactly one release publisher exists;
- GoReleaser ownership is not duplicated;
- test/snapshot/prerelease semantics are correct;
- external human-created `v*` tag publication still behaves as intended where supported;
- scheduled jobs cannot release;
- CI syntax validated;
- repository-native tests pass;
- generated workflow carries the canonical article pointer;
- PR description explains any deviations/exceptions.

## 31. Migration notes from the superseded posts

- **028 (Breadth):** The comprehensive capability lane structures were recovered from 028 to prevent agents from creating underspecified CI.
- **041/042 (Release Safety):** The exact tag recovery, exact-SHA matching, manual explicit dispatch at tag ref, and single-owner release rules were carried forward unchanged.
- **git-tag-inc:** Semantic versioning must reside in `arran4/git-tag-inc` or `arran4/git-tag-inc-action` rather than fallback inline awk/sed scripts.
