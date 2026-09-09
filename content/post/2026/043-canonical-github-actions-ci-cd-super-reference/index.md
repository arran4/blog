---
title: "Canonical GitHub Actions CI/CD Super-Reference"
date: 2026-09-08T06:33:54Z
draft: false
tags: ["github-actions", "ci", "cd", "release", "automation", "goreleaser", "canonical"]
categories: ["devops", "reference", "automation"]
---

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

This article is the authoritative generation input. Working repositories may be used by maintainers or reviewers to validate that this article still reflects deployed practice, but downstream generation MUST NOT require inspecting other repositories to reconstruct the intended design. If an implementation detail is part of the canonical pattern, it belongs here.

Downstream agents must implement `workflow_dispatch` as a migration/improvement process toward a useful manual operator UX. Do not blindly preserve stale or broken structures merely because they exist; instead, update them to the current canonical pattern while retaining genuinely useful repo-specific behavior. Repository-specific prompts should not need to independently request this UX improvement.

## 2. Required repository inspection before generation

Before generating or modifying any CI configuration, you must:
- enumerate all `.github/workflows/*`;
- understand each trigger/job;
- inspect existing manual-dispatch behavior to learn repository-specific requirements, but do not preserve stale/broken/bespoke structure merely because it exists;
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

Explicitly, CI consolidation or simplification MUST NOT remove useful manual-dispatch capability without a documented capability-based exception. A canonical workflow is incomplete if the GitHub Actions UI cannot expose a useful “Run workflow” path after the workflow reaches the default branch. If manual dispatch is absent or broken, create/restore the canonical pattern. If it exists but is stale or awkward, migrate/improve it toward the current pattern while retaining genuinely useful repo-specific behavior.

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

Generated workflows must include a short top-of-file pointer back to THIS article. Do not accumulate pointers to superseded articles.

## 4. Capability-selection matrix

Before generating jobs, classify capabilities as:
- **A. UNIVERSAL DEFAULT:** Baseline routing, basic validation, concurrency logic, practical manual dispatch UX (`workflow_dispatch` where viable).
- **B. ENABLED WHEN REPOSITORY CAPABILITY EXISTS:** Language-specific lint/test (Go, Node, Dart, CMake, Dockerfile, Debian/RPM packaging, etc.), artifact building, packaging, GoReleaser, versioned release controls.
- **C. OPTIONAL POLICY:** Autofix PR generation, maintenance scheduling, PR constraints.
- **D. EXCEPTION REQUIRING AN EXPLANATION:** Additional workflows, custom semantic version math.

Do not create irrelevant language jobs merely because examples exist. Conversely, do not omit an obvious standard lane if it matches a repository capability. At the same time, do not omit an obvious standard lane merely because the agent decided to produce a minimalist workflow.

## 5. Trigger/event model

The standard event triggers should cover the following. `workflow_dispatch` must be implemented to provide a useful manual operator UX where it is practical and viable, rather than being preserved blindly as a meaningless invariant. If manual dispatch genuinely has no practical role, allow a documented capability-based exception rather than requiring meaningless YAML.

Use the canonical `mode` input where applicable. The normal operator-facing modes are:
- `lint-fix`: run the deterministic autofix path and, when allowed, open a focused PR if changes result;
- `build`: run validation/build without publishing a release;
- `release-major`, `release-minor`, `release-patch`: calculate and prepare a semantic-version release using the shared versioning implementation;
- `release-test`, `release-rc`, `release-alpha`: prepare the corresponding prerelease forms where the repository supports them;
- `monthly-maintenance`: run the repository's heavier maintenance path;
- `publish-tag`: an internal/manual recovery publisher entry point that runs in tag context and MUST NOT calculate a new version.

Use `release_version_override` where release workflows support an explicit version and `allow_prs` where autofix/maintenance automation may open pull requests. Do not expose release controls to repositories that do not have corresponding release capabilities.

```yaml
on:
  push:
    branches: [main, master]
    tags: ['v*', 'v*.*.*', 'v*.*.*-rc*', 'v*.*.*-beta*', 'v*.*.*-alpha*', 'test-*']
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
        type: choice
        default: lint-fix
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
          - publish-tag
      release_version_override:
        description: "Optional explicit release version, e.g. 2.4.0 or 2.4.0-rc.2"
        required: false
        type: string
        default: ''
      allow_prs:
        description: "Allow automation to open pull requests"
        required: false
        type: boolean
        default: true
  schedule:
    - cron: '17 3 1 * *'
    - cron: '41 2 * * *'
```

## 6. Routing

Routing is not optional glue. It is the canonical place where event semantics become explicit job flags so downstream `if:` conditions stay understandable and manual modes cannot silently become dead routes.

A representative router is:

```yaml
jobs:
  route:
    name: Route event
    runs-on: ubuntu-latest
    outputs:
      run_code_checks: ${{ steps.route.outputs.run_code_checks }}
      run_build: ${{ steps.route.outputs.run_build }}
      run_release: ${{ steps.route.outputs.run_release }}
      run_autofix: ${{ steps.route.outputs.run_autofix }}
      run_cleanup: ${{ steps.route.outputs.run_cleanup }}
      run_post_release: ${{ steps.route.outputs.run_post_release }}
      is_monthly: ${{ steps.route.outputs.is_monthly }}
    steps:
      - id: route
        shell: bash
        run: |
          set -euo pipefail

          run_code_checks=false
          run_build=false
          run_release=false
          run_autofix=false
          run_cleanup=false
          run_post_release=false
          is_monthly=false

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
                [[ "${{ github.event.pull_request.merged }}" == "true" ]] || run_cleanup=true
              else
                run_code_checks=true
              fi
              ;;
            workflow_dispatch)
              case "${{ inputs.mode }}" in
                lint-fix)
                  run_code_checks=true
                  run_autofix=true
                  ;;
                build)
                  run_code_checks=true
                  run_build=true
                  ;;
                release-major|release-minor|release-patch|release-test|release-rc|release-alpha)
                  run_code_checks=true
                  run_build=true
                  run_release=true
                  ;;
                publish-tag)
                  if [[ "${{ github.ref_type }}" != "tag" || ! "${{ github.ref }}" =~ ^refs/tags/v ]]; then
                    echo "publish-tag requires an eligible v* tag ref" >&2
                    exit 1
                  fi
                  run_code_checks=true
                  run_build=true
                  run_release=true
                  ;;
                monthly-maintenance)
                  run_code_checks=true
                  is_monthly=true
                  ;;
                *)
                  echo "Unsupported workflow_dispatch mode: ${{ inputs.mode }}" >&2
                  exit 1
                  ;;
              esac
              ;;
            release)
              run_post_release=true
              ;;
            schedule)
              run_code_checks=true
              is_monthly=true
              ;;
          esac

          echo "run_code_checks=$run_code_checks" >> "$GITHUB_OUTPUT"
          echo "run_build=$run_build" >> "$GITHUB_OUTPUT"
          echo "run_release=$run_release" >> "$GITHUB_OUTPUT"
          echo "run_autofix=$run_autofix" >> "$GITHUB_OUTPUT"
          echo "run_cleanup=$run_cleanup" >> "$GITHUB_OUTPUT"
          echo "run_post_release=$run_post_release" >> "$GITHUB_OUTPUT"
          echo "is_monthly=$is_monthly" >> "$GITHUB_OUTPUT"
```

Repositories may add capability-specific outputs, but should keep event interpretation concentrated in the router instead of scattering incompatible event expressions throughout jobs.

## 7. Concurrency

Concurrency prevents duplicate manual releases from racing and cleans up outdated PR tests. Release preparation MUST NOT be cancelled after it has begun.

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ !(github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-')) }}
```

If the expression context used by a repository cannot safely reference `inputs.mode` for all events, compute an equivalent release/non-release value in routing and use that instead. The invariant is that ordinary CI may be superseded, but release preparation must not be cancelled into an ambiguous tag state.

## 8. Permissions/security boundaries

Use read-only workflow-level permissions by default, and elevate them per-job. Do not give the whole workflow broad write permissions for convenience.
- normal validation: `contents: read`
- autofix: `contents: write`, `pull-requests: write`
- manual tag + explicit dispatch: `contents: write`, `actions: write`
- release publisher: `contents: write`, `packages: write` (when containers/packages need it)
- security upload: `security-events: write` (only where necessary)

## 9. Common checkout/setup conventions

Every git-mutating job, and every build job, must use `actions/checkout`. Use `fetch-depth: 0` for release prep jobs or when history/tags are needed.

## 10. Validation/test/lint architecture

Tests and linters should run concurrently after routing. All release policies require test validation before permanent tags are cut. Public repositories can generally run broader checks by default. Visibility check via `github.event.repository.private`. Private repositories may use a more conservative/cost-aware profile, but do not compromise required release validation.

A release-validation gate should make skipped optional jobs explicit rather than accidentally treating a missing job as success. Release preparation must depend on this gate, not merely on whichever build job happens to run first.

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
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - uses: golangci/golangci-lint-action@v9
        with:
          version: latest

  go-test:
    name: Go Test
    needs: [route]
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
          cache: true
      - run: go test ./...
```

Example Node lane:
```yaml
  node-lint-test:
    name: Node Lint & Test
    needs: [route]
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
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
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
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
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
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
    if: ${{ needs.route.outputs.run_code_checks == 'true' }}
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

## 12. Autofix architecture

Autofix is an operator-facing `lint-fix` capability when practical. It should:
- run deterministic mechanical fixes (`go fix`, `gofmt`, `prettier`, `dart/flutter format`, etc.);
- inspect resulting diff and do nothing when clean;
- create a focused PR when `allow_prs` is enabled;
- never mix unrelated fixes;
- never publish releases;
- have appropriately narrow permissions;
- use a fresh automation branch rather than mutating the default branch directly.

Representative implementation:

```yaml
  autofix:
    name: Autofix and open PR
    needs: [route]
    if: ${{ needs.route.outputs.run_autofix == 'true' && inputs.allow_prs == true }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v7
      - name: Apply deterministic fixes
        shell: bash
        run: |
          set -euo pipefail
          if [[ -f go.mod ]]; then
            go fix ./... || true
            go fmt ./...
          fi
          if [[ -f package.json ]]; then
            npm ci
            npm run format --if-present
          fi
      - name: Open focused autofix PR when needed
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        shell: bash
        run: |
          set -euo pipefail
          if git diff --quiet; then
            echo "No autofix changes"
            exit 0
          fi

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          branch="ci/autofix/${{ github.run_id }}"
          git checkout -b "$branch"
          git add -A
          git commit -m "ci: automated formatting fixes"
          git push origin "$branch"
          gh pr create \
            --title "ci: automated formatting fixes" \
            --body "Automated deterministic formatting/fix pass from workflow run ${{ github.run_id }}." \
            --base "${{ github.event.repository.default_branch }}" \
            --head "$branch"
```

If the repository has an established safe same-branch PR autofix path, it may retain that useful behavior, but the canonical manual `lint-fix` path must remain available where autofix is a supported operator capability.

## 13. Build/artifact architecture

Build artifacts should use `actions/upload-artifact@v7`.
**Crucial constraint:** Always set `retention-days: 1` on every `actions/upload-artifact` step to prevent storage overages. Publish/promote jobs should consume artifacts immediately in the same workflow run.

Build lanes must be gated from routing (`run_build`) and must not publish permanent releases by themselves.

## 14. Release-version planning

`git-tag-inc` MUST BE A FIRST-CLASS DEFAULT for semantic version calculation.
Do not use shell arithmetic fallbacks for semantic versions. Use `arran4/git-tag-inc` as the authoritative version logic. Repository-specific workflow logic controls release *policy* and transactional *safety*.

The canonical safe pattern is to use `arran4/git-tag-inc-action@v1` in installation mode, then call the installed `git-tag-inc` CLI with fixed workflow-selected arguments. Do not pass arbitrary untrusted/user-controlled strings through action inputs that are interpolated into shell source.

The manual release modes map to version calculation as follows:

```text
release-major -> git-tag-inc -print-version-only major
release-minor -> git-tag-inc -print-version-only minor
release-patch -> git-tag-inc -print-version-only patch
release-test  -> git-tag-inc -print-version-only patch test
release-rc    -> git-tag-inc -print-version-only patch rc
release-alpha -> git-tag-inc -print-version-only patch alpha
```

`release_version_override`, when non-empty, bypasses increment calculation but MUST still be normalized and validated as a semantic release tag before any tag is created.

## 15. Tagging and release preparation

Manual release preparation is transactional and must be implemented, not inferred. The canonical sequence is:
1. run normal validation/tests;
2. ensure the request is based on the default branch and fetch full history/tags;
3. fetch the remote default branch and verify the release commit is still its tip;
4. install `git-tag-inc` safely;
5. calculate or validate the requested next tag;
6. verify an existing tag, if any, points to the same intended commit before treating the run as retryable;
7. create and push the immutable tag only after all validation gates pass;
8. explicitly dispatch the same canonical workflow at that tag ref with `mode=publish-tag`;
9. let the tag-context publisher be the sole publication owner.

Representative release-preparation job:

```yaml
  prepare-release-tag:
    name: Prepare release tag
    needs: [route, release-validation]
    if: ${{ needs.route.outputs.run_release == 'true' && github.event_name == 'workflow_dispatch' && inputs.mode != 'publish-tag' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0

      - name: Install git-tag-inc
        uses: arran4/git-tag-inc-action@v1
        with:
          mode: install

      - name: Validate branch, calculate tag, push, and dispatch publisher
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          MODE: ${{ inputs.mode }}
          OVERRIDE: ${{ inputs.release_version_override }}
        shell: bash
        run: |
          set -euo pipefail

          default_branch="${{ github.event.repository.default_branch }}"
          git fetch origin "$default_branch" --tags --force
          remote_sha=$(git rev-parse "origin/$default_branch")
          if [[ "$GITHUB_SHA" != "$remote_sha" ]]; then
            echo "Release must run from the current origin/$default_branch tip" >&2
            exit 1
          fi

          if [[ -n "$OVERRIDE" ]]; then
            version="${OVERRIDE#v}"
            next_tag="v$version"
          else
            case "$MODE" in
              release-major) args=(-print-version-only major) ;;
              release-minor) args=(-print-version-only minor) ;;
              release-patch) args=(-print-version-only patch) ;;
              release-test)  args=(-print-version-only patch test) ;;
              release-rc)    args=(-print-version-only patch rc) ;;
              release-alpha) args=(-print-version-only patch alpha) ;;
              *) echo "Unsupported release mode: $MODE" >&2; exit 1 ;;
            esac
            next_tag=$(git-tag-inc "${args[@]}")
          fi

          [[ "$next_tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+([-.][0-9A-Za-z.]+)?$ ]] || {
            echo "Invalid release tag: $next_tag" >&2
            exit 1
          }

          remote_tag_sha=$(git ls-remote --tags origin "refs/tags/$next_tag" | awk '{print $1}')
          if [[ -n "$remote_tag_sha" ]]; then
            if [[ "$remote_tag_sha" == "$GITHUB_SHA" ]]; then
              echo "Tag $next_tag already exists at the intended commit; treating as safe retry"
            else
              echo "Tag $next_tag already exists at another commit" >&2
              exit 1
            fi
          else
            git tag "$next_tag" "$GITHUB_SHA"
            git push origin "refs/tags/$next_tag"
          fi

          gh workflow run "ci.yml" --ref "$next_tag" -f mode=publish-tag
```

If the canonical workflow filename is not `ci.yml`, dispatch its actual filename. The important invariant is explicit dispatch at the new tag ref; do not rely on the tag push alone to recreate hidden release state or to bypass the intended publisher route.

## 16. Publisher/tag-context validation

`publish-tag` is a publisher/recovery mode, not a second version calculator. It must reject branch context and only publish an eligible immutable tag.

```yaml
  publish-gate:
    name: Validate publisher context
    needs: [route]
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'publish-tag' }}
    runs-on: ubuntu-latest
    steps:
      - name: Require v* tag context
        shell: bash
        run: |
          set -euo pipefail
          [[ "${{ github.ref_type }}" == "tag" ]]
          [[ "${{ github.ref_name }}" == v* ]]
```

The publisher must consume artifacts/build state appropriate to that tag and must not calculate a new semantic version.

## 17. GitHub Release ownership

FOR ONE TAG, EXACTLY ONE JOB OR TOOL OWNS CREATION/PUBLICATION OF THE GITHUB RELEASE. Do not surround it with multiple release creators, duplicate draft steps, or `|| true`. `release: published` is downstream/notification state, not another creation path. Never hide duplicate release creation with `|| true`.

## 18. GoReleaser architecture

If GoReleaser is used, GoReleaser is the *sole* release owner. Do not create a separate `softprops/action-gh-release` step.

Representative publisher:

```yaml
  goreleaser:
    name: Publish release
    needs: [route, publish-gate, release-validation]
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'publish-tag' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - uses: goreleaser/goreleaser-action@v7
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

Use repository-specific GoReleaser configuration, but do not duplicate release ownership around it.

## 19. Non-GoReleaser release architecture

If not using GoReleaser, one generic publisher job uses `softprops/action-gh-release` or another appropriate single mechanism.

```yaml
  publish-generic:
    name: Publish Generic Release
    needs: [route, publish-gate]
    if: ${{ github.event_name == 'workflow_dispatch' && inputs.mode == 'publish-tag' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      - uses: actions/download-artifact@v8
        with:
          path: release-artifacts
      - uses: softprops/action-gh-release@v3
        with:
          files: release-artifacts/**
```

## 20. Containers

Docker build lanes should integrate securely, utilizing `.Env.GITHUB_REPOSITORY | tolower` in GoReleaser templates if dynamically injecting tags.

If building containers outside of GoReleaser, use the standard `docker/build-push-action`.

```yaml
  docker-build:
    name: Docker Build
    needs: [route]
    if: ${{ needs.route.outputs.run_build == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v4
      - name: Build (no release publication)
        uses: docker/build-push-action@v7
        with:
          context: .
          push: false
          load: true
          tags: test-image:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

## 21. Package/source-package publication

Native packages (Debian, RPM, etc.) are generated as artifacts and gathered by the single release owner for distribution.

Example artifact consumption:
```yaml
      - name: Collect artifacts
        uses: actions/download-artifact@v8
        with:
          path: dist-release
```

## 22. Scheduled/monthly maintenance

Include maintenance lanes for routine cleanup or deeper monthly scans. Ensure scheduled jobs cannot accidentally route into release publication.

```yaml
  maintenance:
    name: Monthly Cleanup
    needs: [route]
    if: ${{ needs.route.outputs.is_monthly == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: read
      actions: write
    steps:
      - name: Cleanup old workflow runs
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          gh api repos/${{ github.repository }}/actions/runs --paginate \
            -q '.workflow_runs[] | select(.created_at < (now - 2592000 | todate)) | .id' | \
            xargs -r -I{} gh api -X DELETE repos/${{ github.repository }}/actions/runs/{}
```

## 23. Cleanup lifecycle

Artifacts should expire quickly. Merge-closed events or scheduled logic should optionally clean up automation branches/PRs created by CI. Cleanup must identify only branches/PRs owned by the automation; never delete arbitrary contributor branches.

## 24. Validation of generated CI

Before opening a CI PR, ensure:
- the generated workflow is valid YAML and GitHub Actions syntax;
- all action versions and action input names are real/current enough for the intended environment;
- all `needs:` references exist;
- every `needs.*.outputs.*` reference is actually emitted;
- all event/input expressions are valid on the events where the job may evaluate;
- language jobs match repository capabilities;
- all artifact uploads use `retention-days: 1`;
- release preparation cannot race and is not cancelled mid-tagging;
- permanent tags are created only after validation;
- version calculation uses `git-tag-inc`, not local shell semantic-version arithmetic;
- `release_version_override` is normalized/validated before tag creation;
- `publish-tag` runs only in eligible tag context and does not compute another version;
- the newly prepared tag explicitly dispatches the publisher workflow at that tag ref;
- exactly one release owner exists for each tag;
- GoReleaser ownership is not duplicated;
- test/snapshot/prerelease semantics are correct;
- external human-created `v*` tag publication still behaves as intended where supported;
- the actual `Run workflow` UX and routing work, not just the presence of `workflow_dispatch:`;
- if manual dispatch genuinely has no practical role, a documented capability-based exception exists;
- intended manual inputs exist;
- `lint-fix` reaches the deterministic autofix path and opens a PR only when configured/needed;
- ordinary manual `build` reaches useful validation/build jobs;
- applicable `release-major`, `release-minor`, `release-patch` and prerelease modes reach release validation/preparation;
- no `if:` expression makes a manual route dead;
- missing/broken manual dispatch is restored and stale implementations are improved rather than blindly retained;
- scheduled jobs cannot release;
- repository-native tests pass.

## 25. Generation decision procedure

When applying this reference to a repository:

1. Inspect the repository and its existing workflows.
2. Determine capabilities: languages, build systems, release mechanism, packages, containers, autofix viability, maintenance needs.
3. Choose the smallest coherent workflow architecture, normally one canonical CI file.
4. Instantiate the router and only the capability-specific lanes that make sense.
5. If manual dispatch is useful, expose the applicable canonical modes. Restore it if missing/broken; migrate it if stale.
6. For versioned releases, use the canonical `git-tag-inc` release-preparation and tag-context publisher flow.
7. Preserve genuinely useful repository-specific behavior by integrating it into the canonical structure, not by retaining obsolete workflow fragmentation.
8. Validate every manual route and every release ownership boundary.
9. Explain any capability-based deviations in the PR description.

The desired result is not merely fewer workflow files or newer syntax. It is a general improvement in CI operator UX, safety, maintainability, and consistency while retaining repository-specific capabilities that are actually useful.
