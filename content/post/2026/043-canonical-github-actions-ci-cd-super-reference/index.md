---
title: "Canonical GitHub Actions CI/CD Super-Reference"
date: 2026-09-08T06:33:54Z
draft: false
tags: ["github-actions", "ci", "cd", "release", "automation", "goreleaser", "canonical"]
categories: ["devops", "reference", "automation"]
---

<!-- cspell:words actionlint AppImage Buildx DBUILD Dockerfiles GOPATH GoReleaser jurplel mvcommon myapp nFPM prerelease qmake semver stefanzweifel todate TXTAR typecheck zizmor -->

This is the canonical GitHub Actions CI/CD generation reference.

It supersedes `006`, `011`, `028`, `041` and `042` where they conflict. Older posts remain useful as rationale, but an agent should normally need only this article plus the target repository to create or modernise its CI.

The goal is consistency without generic bloat: the agent discovers what the repository actually contains, selects the applicable capabilities here, and writes a bespoke workflow that already knows what it is responsible for. The checked-in workflow should not rediscover the project on every run.

The examples in this article are not merely illustrative. Where a repository selects a capability described by a canonical module, the generated workflow should normally preserve that module's dependency shape, safety properties, permissions and event semantics while substituting repository-specific commands and names. This is how different agents should arrive at recognisably consistent workflows without copying irrelevant jobs into every repository.

## 1. Purpose and design objective

A generated workflow should be:

- **single-owner:** one coherent CI/CD dependency graph and exactly one GitHub Release publisher per tag;
- **single-file by default:** normally one `.github/workflows/ci.yml` or `.github/workflows/ci.yaml`;
- **event-efficient:** run when new information needs validation, and cheaply avoid work that an event cannot require;
- **repository-specific:** include only languages, platforms, generators, services, packaging and release mechanisms that exist in the repository;
- **release-safe:** validation precedes permanent tagging and publication;
- **self-verifying:** generated files, examples, workflows and built release artifacts are checked when those capabilities exist;
- **maintainable:** avoid unnecessary helper files and duplicated policy;
- **predictable:** selected capabilities use the canonical module shapes below unless the repository has a concrete reason to differ.

The canonical shape is a specification for generation, not a universal workflow to paste unchanged into every project.

## 2. Discovery happens when the workflow is generated

Before editing CI, the agent must inspect the repository and make the design decisions once.

Inventory:

- every `.github/workflows/*` file and every trigger/job;
- repository instructions such as `AGENTS.md`, README files and build/release documentation;
- languages and build systems;
- tests, linters, formatters and static-analysis tools;
- committed generated source;
- generated documentation, man pages, fixtures and compatibility matrices;
- generated examples and generated workflow/configuration examples;
- runnable examples and demos;
- integration tests and their filesystem/process/network/database/service boundaries;
- any end-to-end or system tests;
- Dockerfiles and Compose environments;
- declared supported operating systems and architectures;
- minimum supported language/toolchain versions;
- packaging/installers and GoReleaser or equivalent release configuration;
- release binaries whose version/commit/date metadata is injected at build time;
- existing schedules, manual modes, autofix automation and cleanup;
- every current release owner;
- secrets, token permissions and trust boundaries;
- historical CI failures where they explain an existing workaround.

Also classify the repository itself. Archived forks and upstream-tracking forks normally should not be rewritten merely to impose this architecture unless they are intentionally maintained as independent projects.

The checked-in workflow should be bespoke to that repository. The canonical document describes selectable modules; the generated repository workflow contains only the modules that apply.

The result of discovery is a tailored checked-in workflow. Runtime capability discovery is a fallback only for facts that genuinely vary during a run. Do not build a giant `discover` job which re-detects known project structure on every invocation.

## 3. One self-contained workflow is the normative target

The normal target is explicitly `.github/workflows/ci.yml` or `.github/workflows/ci.yaml` containing the repository's complete coherent CI/CD graph.

When upgrading an existing repository, actively attempt to fold these into that workflow:

- lint;
- unit tests;
- integration tests;
- generated-file verification;
- example verification;
- workflow validation;
- compatibility matrices;
- builds;
- artifact generation;
- release gates;
- tagging;
- publication;
- scheduled verification;
- ordinary maintenance.

Use native `needs:` edges so the dependency graph is visible in one place. Delete superseded workflow files after consolidation. Do not use the weaker idea that keeping several existing workflow files is acceptable merely because they are already separated.

A second workflow needs a concrete reason. Valid exceptions include:

- a genuine reusable `workflow_call` interface;
- a materially different secrets/trust boundary;
- a GitHub event/platform limitation that prevents coherent consolidation;
- genuinely independent administrative automation;
- a large family of independently scheduled generated maintenance workflows where forcing every schedule into one monolithic file would materially reduce readability or maintainability.

Historical structure by itself is not an exception. If more than one workflow remains, the PR should explain why each additional workflow cannot reasonably be a job in the central graph.

Support files follow the same principle:

- keep small CI routing and shell logic inline;
- do not create helper scripts merely to make the YAML look smaller;
- preserve or introduce helper code only when it is substantial, naturally belongs to the repository's implementation language, is shared with production logic, or materially improves direct testing.

## 4. Capability selection

Classify discovered capabilities before writing jobs:

- **Universal baseline:** event routing, ordinary validation, minimal permissions, useful manual dispatch where applicable, and periodic verification for maintained repositories.
- **Enable when present:** language-specific lint/test, generation checks, examples, integration/services, E2E/system smoke, platform/toolchain matrices, packaging, containers, release artifacts, GoReleaser.
- **Optional policy:** autofix PRs, dependency-update PRs, expensive scheduled checks.
- **Exception requiring explanation:** additional workflow files, bespoke version arithmetic, unusual release ownership, or unusually broad permissions.

Do not add a lane merely because this article contains an example. Do not omit an obvious lane merely to keep YAML short.

After capability selection, use the canonical modules in this article as the default implementation vocabulary. A repository may change commands, matrices and package names, but should not casually invent a different routing/release topology for a capability that already has a canonical shape here.

## 5. Trigger model: run when information changes, avoid duplicate runs

The trigger set should cover every state transition that needs validation without running the same logical validation twice.

The standard baseline is:

```yaml
on:
  push:
    branches: [main, master]
    tags: ['v*']

  pull_request:
    types: [opened, synchronize]
    branches: [main, master]

  workflow_dispatch:
    # repository-specific useful modes

  schedule:
    - cron: '0 19 1 * *'
```

The intent is deliberate:

- **Every push to the authoritative branch runs CI.** The default branch is deployed/shared state and must remain continuously verified.
- **Opening a pull request runs CI.** The initial PR state must be checked even if the branch commit already existed before the PR.
- **Updating an open pull request runs CI through `pull_request:synchronize`.** Do not also subscribe to ordinary pushes for every feature branch; that creates duplicate branch-push + PR runs for the same commit.
- **Eligible version tags run the publication/release path.**
- **Scheduled runs prove a quiet repository still works.**
- **Manual dispatch exposes only useful operator actions.**

Do not subscribe to PR state-only events such as `reopened`, `ready_for_review` or `closed` for ordinary validation by default. They do not change the commit being validated. Add one only when the repository has a concrete state-dependent lifecycle job, and route that event only to the cheap job that requires it.

A merge already produces the authoritative-branch push that needs normal CI, so `pull_request: closed` must not rerun the normal test/build graph.

Likewise, do not add `push` for all branches when pull-request events already provide the review validation you need.

Path filters may reduce cost for clearly isolated areas, but only when it is safe for required checks and cross-cutting changes. Prefer job-level capability conditions over a clever filter that can silently suppress required validation.

## 6. Route cheaply and exit early

A small router may convert GitHub events and manual inputs into explicit policy outputs, but the event triggers themselves should already eliminate obvious duplicate runs.

The router should be cheap: no full checkout or dependency installation unless routing genuinely needs repository state.

A useful policy model is:

```text
event
  |
  +-- default-branch push ------> normal validation/build
  |
  +-- PR opened/updated --------> PR validation
  |
  +-- v* tag -------------------> tag-context validation/publisher
  |
  +-- manual build -------------> requested validation/build
  |
  +-- manual release -----------> validation -> tag preparation
  |
  +-- monthly schedule ---------> health/freshness validation
```

Jobs should use `if:` conditions to leave the run as early as possible when they cannot apply. An irrelevant event should not install a toolchain merely to discover that there is nothing to do.

Every exposed `workflow_dispatch` mode must demonstrably reach useful work. Do not keep decorative inputs or dead router outputs.

## 7. Concurrency is selective, not a substitute for correct routing

Correct triggers and routing come first. Concurrency should address real races or superseded work, not hide duplicate-event design.

Good default uses:

- **PR validation:** newer commits may cancel older validation for the same PR, because the older result is superseded.
- **Default-branch pushes:** normally let every authoritative-branch run complete; do not silently cancel required verification.
- **Tag publication:** do not cancel an in-progress publication.
- **Manual release/tag preparation:** serialize the release-critical section when concurrent version calculations could race.
- **Independent maintenance jobs:** use repository-specific groups only where concurrent mutation would conflict, for example package-update automation in a large overlay.

Avoid one broad workflow-level concurrency group that accidentally cancels tag publication, main-branch validation or manual release work.

If the repository wants PR supersession cancellation, the canonical workflow-level form is:

```yaml
concurrency:
  group: ${{ github.event_name == 'pull_request' && format('{0}-pr-{1}', github.workflow, github.event.pull_request.number) || format('{0}-run-{1}', github.workflow, github.run_id) }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
```

This deliberately gives every non-PR run a unique group while grouping all attempts for one PR together.

Release preparation uses its own non-cancelling serialization module later in this article.

## 8. Permissions, dependencies and security posture

Use read-only workflow-level permissions by default and elevate per job where practical:

- ordinary validation: `contents: read`;
- autofix/maintenance PR: `contents: write`, `pull-requests: write`;
- tag preparation: `contents: write`, and `actions: write` only if explicit dispatch is needed;
- release publication: `contents: write`, plus `packages: write` only when publishing packages/containers;
- security uploads: only the specific permission required by the selected scanner.

Security hardening should match the repository's stated risk. Do not turn every small personal repository into a heavyweight high-assurance pipeline.

### Action/dependency provenance

When adding CI dependencies, classify them:

1. GitHub-maintained actions such as `actions/checkout`, `actions/setup-*`, `actions/upload-artifact` and `actions/download-artifact`;
2. actions/tools owned by the repository owner, such as `arran4/*`;
3. established external dependencies already used by the project;
4. a new external dependency introduced only for this CI change.

Owner-controlled actions are not a third-party supply-chain concern in the same way as a newly introduced external action. That does **not** make a known implementation defect harmless: unsafe shell/input handling still needs to be avoided or fixed.

For every newly introduced external CI dependency, prefer existing repository-native tooling when it is equally clear, and list the new dependency in the PR description with:

- what it does;
- why an existing tool or simple native command is not sufficient;
- the selected version/reference;
- whether it receives a token, secrets, write permission or untrusted input.

Where a repository explicitly declares CI/security to be high assurance, strengthen this baseline: consider commit-SHA pinning, `zizmor`, dependency review, secret scanning, provenance/attestation and stricter token boundaries. These are capability/risk-driven additions, not universal boilerplate.

When generating or upgrading CI, verify that referenced Action majors and release-tool versions are currently supported. Do not treat version numbers in this article as permanently current. Release-critical tools should use the repository's normal pinning policy; newly introduced external dependencies should be documented as above.

## 9. Shell and GitHub context safety

Never attempt to override GitHub's reserved `GITHUB_*` default environment variables.

Use the variables GitHub already exports in shell steps:

- `GITHUB_REF` is the full ref, such as `refs/heads/main` or `refs/tags/v1.2.3`;
- `GITHUB_REF_NAME` is the short ref name;
- `GITHUB_SHA` is the commit selected for the run.

If a transformed value is needed, copy it to a differently named variable:

```bash
AUTHORITATIVE_BRANCH="${GITHUB_REF#refs/heads/}"
```

Do not write:

```yaml
env:
  GITHUB_REF: ${{ github.ref }}
```

User-controlled values should also cross into shell via `env:` and then be consumed as quoted shell variables. Avoid embedding `${{ inputs.* }}` directly into shell source when it may contain shell syntax.

## 10. Canonical verification graph

Capabilities that do not exist disappear from the graph:

```text
route
  |
  +-- workflow/security validation
  |
  +-- generated-output/example verification
  |
  +-- lint/static analysis
  |
  +-- unit/component tests
  |
  +-- compatibility/integration tests
  |
  +-- selective E2E/system smoke
  |
  +-- build/package artifacts
  |
  +-- built-artifact smoke verification
  |
  +-- release-validation gate
  |
  +-- immutable release/tag context
  |
  +-- exactly one publisher
  |
  +-- post-release work
```

Independent checks should run in parallel when they can. Unsupported or non-applicable capabilities disappear from the graph.

A single release-validation aggregate job provides the publisher with one clear gate, rather than each repository inventing complex `always()`/`skipped` logic.

## 11. Testing hierarchy

The canonical testing model follows this hierarchy, using the cheapest useful test at each layer:

- many unit/component tests with controlled dependencies;
- fewer integration tests exercising real boundaries;
- a small number of end-to-end/system tests where they materially improve confidence.

Real boundaries include:

- filesystem;
- subprocess;
- network;
- database;
- local service;
- container;
- browser/UI where genuinely necessary.

Do not require E2E tests merely because the repository is an application. Prefer a cheaper programmable seam when it proves the same behavior.

Use E2E/system tests when the actual assembled system matters, for example:

- invoke the built CLI as a subprocess;
- start a disposable server and make HTTP requests;
- start a real temporary database/service;
- bring up a Compose environment;
- launch a built container and probe it;
- exercise browser-level behavior that genuinely depends on the browser;
- install a package and run a smoke command.

Expensive integration, E2E, conformance, or fuzz work may be scheduled or manually triggered when it is not required for release confidence. Anything required to claim that a release is valid must gate publication.

## 12. Generated outputs are a first-class capability

Repositories with generated content must verify it as a first-class capability. Distinguish between:

1. **Committed generated output** — must remain synchronized with its source;
2. **Generated examples/documentation/fixtures** — must remain synchronized and should be validated as artifacts;
3. **Ephemeral build/test output** — should normally remain uncommitted.

For committed generated output, the standard CI validation pattern is:

```text
run the authoritative generator
        |
        v
compare the working tree
        |
        +-- clean -> continue
        |
        +-- changed -> fail and show the diff
```

For Go, `go generate ./...` followed by a clean-tree check is a common implementation, but do not make the rule Go-specific. Use the repository's authoritative deterministic generator where `go generate ./...` is too broad or inappropriate.

Normal validation must not silently accept and commit regenerated output. An optional automation lane may regenerate and open a focused PR, but that does not replace the drift check.

Canonical Go generation job:

```yaml
  generated-go:
    name: Generated Go Is Current
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - name: Regenerate
        run: go generate ./...
      - name: Require clean generated output
        run: |
          set -euo pipefail
          git status --short
          git diff --exit-code
```

If the repository has a narrower deterministic generator, replace only the `Regenerate` command; keep the clean-tree assertion.

## 13. Validate generated artifacts, not only drift

Proving that generated output is up to date is not the same as proving that generated output is valid.

After regeneration and drift checking, validate generated artifacts using the normal validator/compiler/parser for that artifact. This validation forms an explicit selectable CI lane.

Canonical validation examples include:

- generated GitHub Actions YAML: regenerate -> diff check -> `actionlint`;
- generated Go code: regenerate -> diff check -> compile/test;
- generated configuration: regenerate -> parse/load using the production parser;
- generated examples: regenerate -> compile/run representative examples where practical;
- generated documentation/man pages: regenerate and perform appropriate structural/build validation where practical.

Generated workflow examples are particularly important: a generator can deterministically reproduce invalid YAML. Drift checking alone will not detect that.

Canonical generated-workflow job shape:

```yaml
  generated-workflows:
    name: Generated Workflows Are Current And Valid
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Add the repository-specific toolchain/setup required by the generator.
      - name: Regenerate workflow examples
        run: ./path/to/repository-generator
      - name: Require clean generated examples
        run: |
          set -euo pipefail
          git status --short
          git diff --exit-code -- examples/
      - name: Validate generated workflows
        run: go run github.com/rhysd/actionlint/cmd/actionlint@latest examples/.github/workflows/*
```

`actionlint` is an external dependency. If it is newly introduced to a repository, list and justify it in the CI PR as required by the dependency-provenance rule.

## 14. Runnable examples and documentation smoke tests

Repositories often contain `examples/`, sample configs, demos, or documentation snippets which ordinary package tests do not necessarily exercise.

CI pipelines must inspect these assets. Where practical:

- compile examples;
- execute cheap examples;
- parse example configurations;
- smoke-test documented commands;
- test CLI `--help` and `--version`;
- verify example-generated output where appropriate.

Do not execute examples with destructive or external side effects merely for coverage.

A normal example job should be explicit rather than discovering example types at runtime:

```yaml
  examples:
    name: Examples
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Add only the setup the checked-in examples actually require.
      - name: Build examples
        run: ./repository-specific-example-build
      - name: Smoke representative example
        run: ./repository-specific-example-smoke
```

## 15. Language and ecosystem modules

These are selectable modules, not mandatory blocks. Prefer full jobs with stable names and dependency edges rather than scattering language setup across unrelated jobs.

### Go

Canonical baseline:

```yaml
  go-test:
    name: Go Test
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - run: go test ./...
      - run: go vet ./...
```

Use `gofmt`/`golangci-lint` where the repository already uses them or where adding them is justified. Test minimum supported Go versions when the project makes such a compatibility claim.

A cross-platform compatibility job should remain separate from the fast ordinary Go validation job:

```yaml
  go-compat:
    name: Go Compatibility (${{ matrix.os }})
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-go@v7
        with:
          go-version-file: go.mod
      - run: go test ./...
```

Only select this matrix when cross-platform support is actually claimed.

### Node / JavaScript / TypeScript

Canonical baseline:

```yaml
  node-test:
    name: Node Test
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        with:
          node-version: '20'
          cache: npm
      - run: npm ci
      - run: npm test
```

Add the repository's actual lint/typecheck/build commands (`eslint`, `prettier`, `tsc`, bundling) rather than assuming names.

### Dart / Flutter

Canonical validation shape:

```yaml
  flutter-test:
    name: Flutter Test
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Use the repository's established Flutter setup action/tooling.
      - run: flutter pub get
      - run: dart analyze
      - run: flutter test
```

Desktop applications may require platform-specific Linux/Windows/macOS build jobs. Only add those platforms when the project claims or releases support for them.

### C / C++ / CMake / Qt / KDE

Canonical CMake shape:

```yaml
  cmake-test:
    name: CMake Build And Test
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: cmake -S . -B build -DBUILD_TESTING=ON
      - run: cmake --build build --parallel
      - run: ctest --test-dir build --output-on-failure
```

Qt/KDE projects may require additional package installation or an existing project bootstrap/container. Preserve those project-native environment contracts rather than replacing them with a generic Qt action if that loses necessary dependencies.

### Containers

Build containers when the repository actually ships or relies on them. Prefer a build-and-smoke path before publication. If GoReleaser owns the image, do not add a second image publisher for the same tags.

A dependency-light container smoke module is:

```yaml
  container-smoke:
    name: Container Build And Smoke
    needs: [route]
    if: ${{ needs.route.outputs.build == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build image
        run: docker build -t ci-image:local .
      - name: Smoke image
        run: docker run --rm ci-image:local --version
```

Replace `--version` with the repository's cheapest meaningful container smoke command.

### Native/package-manager packaging

Debian, RPM, Flatpak, AppImage, Gentoo metadata or other packaging is selected only when the project supports it. Package builds should be treated as artifacts that can themselves need smoke/install validation.

Use a stable artifact handoff shape:

```yaml
  package:
    name: Package
    needs: [route, validation]
    if: ${{ needs.route.outputs.build == 'true' && needs.validation.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - name: Build repository packages
        run: ./repository-specific-package-command
      - uses: actions/upload-artifact@v7
        with:
          name: packages
          path: dist/**
          if-no-files-found: error
          retention-days: 1
```

## 16. Compatibility matrices are evidence-driven

Compatibility matrices must be evidence-driven. Do not add Windows/macOS/old toolchain versions because a generic template happens to contain them.

Use matrix entries to validate an actual support claim. For example:

- if a library claims a minimum supported language version, test that minimum where practical;
- if released binaries claim Windows/macOS/Linux support, ensure those platform builds are appropriately tested or smoke-tested;
- architecture-specific release builds;
- database engine/version compatibility;
- GUI/headless variants where the project genuinely supports them.

Do not repeat expensive static analysis on every matrix entry unless doing so provides actual value.

Distinguish between:

- compatibility matrix;
- fast normal PR testing;
- release artifact matrix.

## 17. Integration and service compatibility

Projects depending on databases, queues, or local services should normally keep compatibility and integration jobs inside the central workflow.

Prefer these local isolation mechanisms inside `ci.yml`:

- GitHub Actions service containers;
- disposable local processes;
- temporary databases;
- deterministic fixtures;
- repository-provided Compose environments.

Database-engine/version compatibility should normally be a matrix/job inside the central workflow rather than automatically justifying another workflow file.

Keep CI credentials ephemeral and local where possible. Respect PR/fork trust boundaries and do not expose production secrets merely to make integration tests work.

Canonical service-container shape, using PostgreSQL only as a structural example:

```yaml
  integration-db:
    name: Database Integration
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:18
        env:
          POSTGRES_DB: test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U test -d test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    env:
      DATABASE_URL: postgres://test:test@127.0.0.1:5432/test
    steps:
      - uses: actions/checkout@v7
      # Add only the repository's language/toolchain setup.
      - run: ./repository-specific-integration-test-command
```

Use the repository's actual supported engine/version rather than copying PostgreSQL into unrelated projects. When multiple supported engines or versions matter, convert the image/version into a matrix rather than cloning the job into separate workflow files.

## 18. Workflow validation

GitHub Actions workflow validation is a first-class concern. Where viable, repositories containing Actions workflows should run `actionlint`. Generated workflows must also be validated after generation.

Canonical job:

```yaml
  workflow-validation:
    name: Validate GitHub Actions
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - run: go run github.com/rhysd/actionlint/cmd/actionlint@latest
```

If `actionlint` is newly introduced, document it as an external CI dependency.

When the repository's security posture warrants it, additional tools should be considered as capability/risk-based additions, rather than mandatory jobs for every repository:

- `zizmor`;
- dependency review;
- secret scanning;
- ecosystem vulnerability scanners.

Agents authoring CI must reason through the logic for:

- every `needs:` edge;
- referenced outputs;
- skipped jobs;
- event-specific contexts;
- permissions;
- concurrency;
- release recursion limitations;
- manual-dispatch paths.

Successful YAML parsing alone is insufficient.

## 19. Autofix and maintenance

Autofix is optional and should:

- perform deterministic mechanical changes only;
- produce no PR when the tree remains clean;
- create a focused automation PR when allowed;
- avoid mixing unrelated dependency or semantic changes;
- never publish a release.

Maintained repositories should normally have periodic verification even when quiet. The baseline private-repository cadence is the second day of each month around 05:00 AEST, represented as:

```yaml
schedule:
  - cron: '0 19 1 * *'
```

Scheduled verification should run meaningful normal validation and optionally repository-appropriate dependency-freshness checks. A schedule must not publish a release.

Do not add a nightly job merely because an old template had one.

Canonical autofix shape:

```yaml
  autofix:
    name: Autofix
    needs: [route]
    if: ${{ needs.route.outputs.autofix == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v7
      # Add repository-specific setup.
      - name: Apply deterministic fixes
        run: ./repository-specific-autofix-command
      - name: Detect changes
        id: changes
        run: |
          if git diff --quiet; then
            echo "changed=false" >> "$GITHUB_OUTPUT"
          else
            echo "changed=true" >> "$GITHUB_OUTPUT"
            git diff --check
          fi
      - name: Open focused autofix PR
        if: ${{ steps.changes.outputs.changed == 'true' && (github.event_name != 'workflow_dispatch' || inputs.allow_prs) }}
        uses: peter-evans/create-pull-request@v7
        with:
          commit-message: "style: automated fixes"
          title: "style: automated fixes"
          branch: automation/autofix
          delete-branch: true
```

`allow_prs: false` therefore permits a manually requested fix/check run without creating a PR. `peter-evans/create-pull-request` is an external action. Reuse it where already established; if newly introduced, list and justify it in the PR. A repository that deliberately avoids this dependency may implement the same focused-PR contract with its existing repository-native automation.

Canonical monthly-maintenance shape:

```yaml
  maintenance:
    name: Monthly Maintenance
    needs: [route]
    if: ${{ needs.route.outputs.maintenance == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Run the repository's normal validation/freshness checks here.
      - run: ./repository-specific-freshness-check
```

Do not give maintenance write permissions unless it actually creates or mutates repository state.

## 20. Build artifacts and smoke verification

A release/build verification stage must execute between artifact construction and publication.

Source tests alone do not prove that release artifacts work, especially where packaging, linking, or embedding version data occurs during release builds. Build jobs must produce the artifacts that the project promises.

Where applicable, test the actual candidate artifact before publication by:

- executing the candidate CLI with `--version`;
- checking expected version, commit, and/or build-date metadata;
- exercising one representative command;
- checking that expected binaries/files exist;
- inspecting archive/package contents;
- installing and smoke-testing native packages where practical;
- starting built container images and testing a command or health endpoint.

Use short Actions-artifact retention for transient handoff artifacts; one day is a good default when publication consumes them immediately.

Publication must explicitly depend on successful candidate-artifact verification where this capability applies.

Canonical build/artifact/smoke chain:

```yaml
  build:
    name: Build Artifacts
    needs: [route, validation]
    if: ${{ needs.route.outputs.build == 'true' && needs.validation.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Add repository-specific setup.
      - name: Build candidate artifacts
        run: ./repository-specific-build-command
      - uses: actions/upload-artifact@v7
        with:
          name: release-candidates
          path: dist/**
          if-no-files-found: error
          retention-days: 1

  artifact-smoke:
    name: Smoke Candidate Artifacts
    needs: [route, build]
    if: ${{ needs.route.outputs.build == 'true' && needs.build.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/download-artifact@v8
        with:
          name: release-candidates
          path: release-candidates
      - name: Smoke candidate artifacts
        run: ./repository-specific-artifact-smoke-command release-candidates
```

The smoke command must test the built artifact, not rebuild the project from source.

## 21. Release version planning

`arran4/git-tag-inc` is the default shared semantic-version tool for repositories using this release model. Do not duplicate SemVer arithmetic in shell.

Owner-controlled tooling may be used directly. Choose the interface according to its actual safety characteristics:

- fixed trusted inputs to an owner-controlled action can be acceptable;
- user-controlled strings must not be interpolated unsafely into shell;
- where an action interface cannot safely carry the required input, install/use the CLI and pass values through environment variables.

For example:

```yaml
- name: Install git-tag-inc
  run: go install github.com/arran4/git-tag-inc/cmd/git-tag-inc@v1.0.0
```

Use the current appropriate version when generating/upgrading the repository. Do not treat the example version as forever canonical.

## 22. Manual release preparation and immutable tags

Manual release preparation must:

1. run the repository's required release-validation gate;
2. operate only against the authoritative release branch;
3. checkout/fetch enough history and tags;
4. verify the selected commit still equals current `origin/<authoritative-branch>`;
5. calculate or explicitly select the intended tag;
6. if the tag already exists, verify it resolves to the exact validated commit;
7. create/push the immutable tag only after validation;
8. route publication using the tag as immutable context.

Use GitHub's existing shell environment variables directly:

```bash
set -euo pipefail

AUTHORITATIVE_BRANCH="${GITHUB_REF#refs/heads/}"

case "$AUTHORITATIVE_BRANCH" in
  main|master) ;;
  *)
    echo "Release preparation must run on main or master" >&2
    exit 1
    ;;
esac

git fetch origin "$AUTHORITATIVE_BRANCH"
ORIGIN_SHA="$(git rev-parse "origin/$AUTHORITATIVE_BRANCH")"

if [[ "$ORIGIN_SHA" != "$GITHUB_SHA" ]]; then
  echo "origin/$AUTHORITATIVE_BRANCH advanced; refusing to tag" >&2
  exit 1
fi
```

Repeat the origin check immediately before creating a new tag to close the race window.

Never silently move an existing release tag.

## 23. Recovery and manual version overrides

`release_version_override` may explicitly choose a version instead of calculating a new one.

Normalize an optional leading `v`, validate the resulting shape, and pass it through the same idempotent tag verification.

A failed publication after a tag has already been pushed must recover the **same** intended tag. Do not rerun auto-increment logic and silently advance to another release version.

`publish-tag` is the immutable tag-context publication/recovery path. It must not calculate or move a version.

Annotated tags must be dereferenced appropriately when verifying the commit.

## 24. Exactly one release owner

For one tag, exactly one job or tool owns creation/publication of the GitHub Release.

- If GoReleaser publishes the GitHub Release, GoReleaser is the sole owner.
- Otherwise one generic publisher owns it.
- `release: published` is downstream state, not another release creator.
- Do not create a second draft release merely to collect artifacts.
- Do not hide duplicate release creation with `|| true`.

The publisher consumes artifacts only after the release-validation aggregate succeeds.

## 25. External tags and manual dispatch

Repositories may support human/external `v*` tag pushes as a direct publication path.

That tag-context run should validate whatever is required for publication and should not try to recalculate or move the tag.

For workflow-created tags, remember that events produced using ordinary `GITHUB_TOKEN` are subject to recursion suppression. Do not assume pushing a tag with `GITHUB_TOKEN` will start another workflow automatically. Either keep publication in the same workflow run or explicitly dispatch the tag-context publisher when the repository's design requires a separate run.

## 26. Generic orchestration skeleton

The skeleton is intentionally ecosystem-neutral. The generation agent replaces the comments with only the modules that the repository actually needs. It is a wiring template; the canonical modules in the next section provide the implementation details that should be composed into it.

```yaml
# Generated using:
# https://arran4.github.io/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/

name: CI/CD

on:
  push:
    branches: [main, master]
    tags: ['v*']
  pull_request:
    types: [opened, synchronize]
    branches: [main, master]
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        required: true
        default: build
        options: [build]
  schedule:
    - cron: '0 19 1 * *'

permissions:
  contents: read

jobs:
  route:
    runs-on: ubuntu-latest
    outputs:
      validation: ${{ steps.route.outputs.validation }}
      build: ${{ steps.route.outputs.build }}
      release: ${{ steps.route.outputs.release }}
      publisher: ${{ steps.route.outputs.publisher }}
      autofix: ${{ steps.route.outputs.autofix }}
      maintenance: ${{ steps.route.outputs.maintenance }}
    steps:
      - id: route
        shell: bash
        env:
          EVENT_NAME: ${{ github.event_name }}
          REF_TYPE: ${{ github.ref_type }}
          INPUT_MODE: ${{ inputs.mode }}
        run: |
          set -euo pipefail

          validation=false
          build=false
          release=false
          publisher=false
          autofix=false
          maintenance=false

          case "$EVENT_NAME" in
            pull_request)
              validation=true
              build=true
              ;;
            push)
              validation=true
              build=true
              if [[ "$REF_TYPE" == "tag" ]]; then
                publisher=true
              fi
              ;;
            schedule)
              validation=true
              build=true
              maintenance=true
              ;;
            workflow_dispatch)
              case "$INPUT_MODE" in
                build)
                  validation=true
                  build=true
                  ;;
                *)
                  echo "Unsupported manual mode: $INPUT_MODE" >&2
                  exit 1
                  ;;
              esac
              ;;
          esac

          echo "validation=$validation" >> "$GITHUB_OUTPUT"
          echo "build=$build" >> "$GITHUB_OUTPUT"
          echo "release=$release" >> "$GITHUB_OUTPUT"
          echo "publisher=$publisher" >> "$GITHUB_OUTPUT"
          echo "autofix=$autofix" >> "$GITHUB_OUTPUT"
          echo "maintenance=$maintenance" >> "$GITHUB_OUTPUT"

  validation:
    name: Validation Aggregate
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Replace this aggregate with the selected validation modules and their needs edges."

  build:
    name: Build Aggregate
    needs: [route, validation]
    if: ${{ needs.route.outputs.build == 'true' && needs.validation.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Replace this aggregate with the selected build/artifact modules."
```

Do not ship placeholder aggregate jobs in a generated repository. Replace them with the selected modules below and make aggregate `needs:` lists explicit.

## 27. Canonical selectable modules

The modules below restore the concrete implementation constraints which would otherwise be lost by using only an ecosystem-neutral skeleton. Select only the modules the repository needs, but once selected preserve their important semantics.

### 27.1 Versioned repository dispatch and routing

For a versioned repository using manual release preparation, replace the baseline `workflow_dispatch` inputs and router with this shape, deleting unsupported prerelease modes rather than leaving dead options:

```yaml
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        required: true
        default: build
        options:
          - build
          - lint-fix
          - monthly-maintenance
          - release-major
          - release-minor
          - release-patch
          - release-test
          - release-rc
          - release-alpha
          - publish-tag
      release_version_override:
        type: string
        required: false
        default: ''
      allow_prs:
        type: boolean
        required: false
        default: true
```

Router:

```yaml
  route:
    name: Route Event
    runs-on: ubuntu-latest
    outputs:
      validation: ${{ steps.route.outputs.validation }}
      build: ${{ steps.route.outputs.build }}
      release: ${{ steps.route.outputs.release }}
      publisher: ${{ steps.route.outputs.publisher }}
      autofix: ${{ steps.route.outputs.autofix }}
      maintenance: ${{ steps.route.outputs.maintenance }}
    steps:
      - id: route
        shell: bash
        env:
          EVENT_NAME: ${{ github.event_name }}
          REF_TYPE: ${{ github.ref_type }}
          INPUT_MODE: ${{ inputs.mode }}
        run: |
          set -euo pipefail

          validation=false
          build=false
          release=false
          publisher=false
          autofix=false
          maintenance=false

          case "$EVENT_NAME" in
            pull_request)
              validation=true
              build=true
              ;;
            push)
              validation=true
              build=true
              if [[ "$REF_TYPE" == "tag" ]]; then
                publisher=true
              fi
              ;;
            schedule)
              validation=true
              build=true
              maintenance=true
              ;;
            workflow_dispatch)
              case "$INPUT_MODE" in
                build)
                  validation=true
                  build=true
                  ;;
                lint-fix)
                  autofix=true
                  ;;
                monthly-maintenance)
                  validation=true
                  build=true
                  maintenance=true
                  ;;
                release-major|release-minor|release-patch|release-test|release-rc|release-alpha)
                  validation=true
                  build=true
                  release=true
                  ;;
                publish-tag)
                  if [[ "$REF_TYPE" != "tag" || "$GITHUB_REF" != refs/tags/v* ]]; then
                    echo "publish-tag requires a v* tag ref; got $GITHUB_REF" >&2
                    exit 1
                  fi
                  validation=true
                  build=true
                  publisher=true
                  ;;
                *)
                  echo "Unsupported manual mode: $INPUT_MODE" >&2
                  exit 1
                  ;;
              esac
              ;;
            *)
              echo "Unsupported event: $EVENT_NAME" >&2
              exit 1
              ;;
          esac

          echo "validation=$validation" >> "$GITHUB_OUTPUT"
          echo "build=$build" >> "$GITHUB_OUTPUT"
          echo "release=$release" >> "$GITHUB_OUTPUT"
          echo "publisher=$publisher" >> "$GITHUB_OUTPUT"
          echo "autofix=$autofix" >> "$GITHUB_OUTPUT"
          echo "maintenance=$maintenance" >> "$GITHUB_OUTPUT"
```

Do not copy a release/prerelease mode the repository does not actually support.

### 27.2 Validation aggregate

Run selected validation jobs in parallel after `route`, then add one explicit aggregate. The generation agent must list the selected jobs; do not create runtime optional job discovery.

Example with three selected checks:

```yaml
  validation:
    name: Validation Aggregate
    needs: [route, workflow-validation, go-test, generated-go]
    if: ${{ always() && needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - name: Require selected validation jobs
        env:
          WORKFLOW_RESULT: ${{ needs.workflow-validation.result }}
          TEST_RESULT: ${{ needs.go-test.result }}
          GENERATED_RESULT: ${{ needs.generated-go.result }}
        run: |
          set -euo pipefail
          [[ "$WORKFLOW_RESULT" == "success" ]]
          [[ "$TEST_RESULT" == "success" ]]
          [[ "$GENERATED_RESULT" == "success" ]]
```

If a selected capability is release-critical, include it here or in the release aggregate below. Do not accept `skipped` for a job that should have run for the current route.

### 27.3 Build and artifact-smoke aggregate

The build job should consume successful validation and produce artifacts once. The smoke job consumes those exact artifacts. The generation agent may have multiple platform build jobs, but publication must consume the already-tested candidates rather than silently rebuilding different binaries.

The canonical two-stage shape is the `build` + `artifact-smoke` module in section 20.

### 27.4 Release-validation aggregate

For a repository with release preparation or publication, define one explicit release gate containing every required release-critical selected job:

```yaml
  release-ready:
    name: Release Quality Gates Passed
    needs: [route, validation, build, artifact-smoke]
    if: ${{ always() && (needs.route.outputs.release == 'true' || needs.route.outputs.publisher == 'true') }}
    runs-on: ubuntu-latest
    steps:
      - name: Require release gates
        env:
          VALIDATION_RESULT: ${{ needs.validation.result }}
          BUILD_RESULT: ${{ needs.build.result }}
          SMOKE_RESULT: ${{ needs.artifact-smoke.result }}
        run: |
          set -euo pipefail
          [[ "$VALIDATION_RESULT" == "success" ]]
          [[ "$BUILD_RESULT" == "success" ]]
          [[ "$SMOKE_RESULT" == "success" ]]
```

If integration, compatibility, generated-output or package-install verification is part of the release promise, add it explicitly to `needs` and the result assertions. The gate should make the repository's release contract obvious by inspection.

### 27.5 Manual release/tag preparation

Use non-cancelling serialization for the release-critical mutation path:

```yaml
  prepare-release-tag:
    name: Prepare Release Tag
    needs: [route, release-ready]
    if: ${{ needs.route.outputs.release == 'true' && needs.release-ready.result == 'success' }}
    runs-on: ubuntu-latest
    concurrency:
      group: ${{ github.workflow }}-release-preparation
      cancel-in-progress: false
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
      - name: Install git-tag-inc
        run: go install github.com/arran4/git-tag-inc/cmd/git-tag-inc@v1.0.0
      - name: Verify exact authoritative branch
        run: |
          set -euo pipefail

          AUTHORITATIVE_BRANCH="${GITHUB_REF#refs/heads/}"
          case "$AUTHORITATIVE_BRANCH" in
            main|master) ;;
            *)
              echo "Release preparation must run on main or master; got $AUTHORITATIVE_BRANCH" >&2
              exit 1
              ;;
          esac

          echo "AUTHORITATIVE_BRANCH=$AUTHORITATIVE_BRANCH" >> "$GITHUB_ENV"
          git fetch origin "$AUTHORITATIVE_BRANCH"
          ORIGIN_SHA="$(git rev-parse "origin/$AUTHORITATIVE_BRANCH")"

          if [[ "$ORIGIN_SHA" != "$GITHUB_SHA" ]]; then
            echo "Requested release at $GITHUB_SHA but origin/$AUTHORITATIVE_BRANCH is $ORIGIN_SHA" >&2
            exit 1
          fi
      - name: Calculate or select release tag
        env:
          RELEASE_MODE: ${{ inputs.mode }}
          RELEASE_VERSION_OVERRIDE: ${{ inputs.release_version_override }}
        run: |
          set -euo pipefail
          export PATH="$(go env GOPATH)/bin:$PATH"

          if [[ -n "$RELEASE_VERSION_OVERRIDE" ]]; then
            TAG="v${RELEASE_VERSION_OVERRIDE#v}"
            if ! [[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.]+)?$ ]]; then
              echo "Invalid release tag: $TAG" >&2
              exit 1
            fi
          else
            case "$RELEASE_MODE" in
              release-major) level="major"; suffix="" ;;
              release-minor) level="minor"; suffix="" ;;
              release-patch) level="patch"; suffix="" ;;
              release-test)  level="patch"; suffix="test" ;;
              release-rc)    level="patch"; suffix="rc" ;;
              release-alpha) level="patch"; suffix="alpha" ;;
              *)
                echo "Unsupported release mode: $RELEASE_MODE" >&2
                exit 1
                ;;
            esac

            args=(--print-version-only "$level")
            [[ -n "$suffix" ]] && args+=("$suffix")
            TAG="$(git-tag-inc "${args[@]}")"
          fi

          echo "TAG=$TAG" >> "$GITHUB_ENV"
      - name: Create tag idempotently
        run: |
          set -euo pipefail

          REMOTE_SHA="$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}' || true)"
          PEELED_SHA="$(git ls-remote --tags origin "refs/tags/$TAG^{}" | awk '{print $1}' || true)"
          [[ -n "$PEELED_SHA" ]] && REMOTE_SHA="$PEELED_SHA"

          if [[ -n "$REMOTE_SHA" ]]; then
            if [[ "$REMOTE_SHA" != "$GITHUB_SHA" ]]; then
              echo "Tag $TAG exists at $REMOTE_SHA, expected $GITHUB_SHA" >&2
              exit 1
            fi
            echo "Tag $TAG already points to the validated commit; continuing recovery."
            exit 0
          fi

          git fetch origin "$AUTHORITATIVE_BRANCH"
          CURRENT_ORIGIN_SHA="$(git rev-parse "origin/$AUTHORITATIVE_BRANCH")"
          if [[ "$CURRENT_ORIGIN_SHA" != "$GITHUB_SHA" ]]; then
            echo "origin/$AUTHORITATIVE_BRANCH advanced to $CURRENT_ORIGIN_SHA before tagging" >&2
            exit 1
          fi

          git tag -d "$TAG" 2>/dev/null || true
          git tag "$TAG"
          if ! git push origin "$TAG"; then
            REMOTE_SHA="$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}' || true)"
            PEELED_SHA="$(git ls-remote --tags origin "refs/tags/$TAG^{}" | awk '{print $1}' || true)"
            [[ -n "$PEELED_SHA" ]] && REMOTE_SHA="$PEELED_SHA"
            if [[ "$REMOTE_SHA" != "$GITHUB_SHA" ]]; then
              echo "Concurrent tag creation did not resolve to $GITHUB_SHA" >&2
              exit 1
            fi
          fi
      - name: Dispatch immutable tag publisher
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: gh workflow run ci.yml --ref "$TAG" -f mode=publish-tag
```

If the repository uses `.github/workflows/ci.yaml`, adapt the dispatch filename accordingly. If the repository has no `go.mod`, use its established way of installing the current pinned `git-tag-inc` CLI. The important contract is shared version arithmetic plus the exact-origin/idempotent-tag/race-guard flow.

### 27.6 Generic GitHub Release publisher

For repositories not using GoReleaser as the release owner, prefer a single publisher. This variant uses the GitHub CLI already present on GitHub-hosted runners rather than introducing another release action, and makes retry behavior explicit:

```yaml
  publisher:
    name: Publish GitHub Release
    needs: [route, release-ready]
    if: ${{ needs.route.outputs.publisher == 'true' && needs.release-ready.result == 'success' }}
    runs-on: ubuntu-latest
    concurrency:
      group: ${{ github.workflow }}-publish-${{ github.ref }}
      cancel-in-progress: false
    permissions:
      contents: write
    steps:
      - uses: actions/download-artifact@v8
        with:
          name: release-candidates
          path: release-candidates
      - name: Publish release idempotently
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          set -euo pipefail
          if gh release view "$GITHUB_REF_NAME" >/dev/null 2>&1; then
            gh release upload "$GITHUB_REF_NAME" release-candidates/* --clobber
          else
            gh release create "$GITHUB_REF_NAME" release-candidates/* --verify-tag --generate-notes
          fi
```

The existing release must correspond to the immutable tag context selected by the workflow. Do not hide an ownership conflict with `|| true`.

### 27.7 GoReleaser publisher

When GoReleaser owns GitHub Release creation, do not also run the generic publisher:

```yaml
  publisher:
    name: Publish With GoReleaser
    needs: [route, release-ready]
    if: ${{ needs.route.outputs.publisher == 'true' && needs.release-ready.result == 'success' }}
    runs-on: ubuntu-latest
    concurrency:
      group: ${{ github.workflow }}-publish-${{ github.ref }}
      cancel-in-progress: false
    permissions:
      contents: write
      packages: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: goreleaser/goreleaser-action@v7
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Prerelease classification:** If the repository accepts SemVer prerelease tags (e.g. `v1.2.3-rc.1`, `v1.2.3-beta.2`, `v1.2.3-alpha.1`, or deliberate `-test` releases), its `.goreleaser.yaml` configuration must explicitly preserve prerelease classification. The canonical form is:

```yaml
release:
  prerelease: auto
```

Accepting a prerelease tag pattern in GitHub Actions is not sufficient if GoReleaser subsequently publishes it as an ordinary stable release. You must keep stable tags, SemVer prerelease tags, snapshot/test builds (which should not publish GitHub Releases), and manual recovery paths explicitly distinct. Do not introduce a second generic release publisher merely to manipulate the prerelease state of a GoReleaser-owned release.

If `goreleaser/goreleaser-action` is a new external CI dependency for that repository, document it. If the project already uses it, preserve the established dependency unless there is a reason to change it.

### 27.8 Artifact publication ownership

A publisher must consume artifacts produced by the selected build jobs or intentionally let the sole release tool build them. Do not do both accidentally.

Choose one of these coherent models:

1. **CI builds candidates -> CI smoke-tests them -> generic publisher uploads those same candidates.**
2. **GoReleaser is the sole release builder/publisher -> release validation proves the source/configuration before GoReleaser runs.**

Do not build one set of binaries for smoke testing and silently publish a different independently built set unless the repository's release tool necessarily owns the final build and that distinction is explicit.

### 27.9 Selective long-running verification

Race, fuzz, conformance and expensive E2E jobs should still use normal job modules with explicit routes. A common scheduled/manual-only form is:

```yaml
  extended-verification:
    name: Extended Verification
    needs: [route]
    if: ${{ github.event_name == 'schedule' || (github.event_name == 'workflow_dispatch' && inputs.mode == 'extended') }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Add repository-specific setup.
      - run: ./repository-specific-extended-verification
```

If a check is release-critical, do not leave it scheduled-only; include it in `release-ready`.

### 27.10 Special verification classes

The following are additional capability-selected patterns:

- race detector;
- fuzz testing;
- golden/TXTAR fixtures;
- conformance suites;
- generated compatibility matrices;
- database compatibility;
- GUI/headless tests;
- container smoke tests;
- package installation smoke tests;
- minimum-supported-version tests.

Not every check is mandatory. For golden/generated fixtures, normal CI should detect drift rather than automatically accepting new expected output.

### 27.11 Dart/Flutter version arithmetic

Repositories using Dart/Flutter usually define versions as `major.minor.patch+build` inside `pubspec.yaml`. The SemVer release intent and the monotonically advancing application or package build number must be handled correctly.

Cover at least these transitions:

```text
1.2.3+41 --patch--> 1.2.4+42
1.2.3+41 --minor--> 1.3.0+42
1.2.3+41 --major--> 2.0.0+42
1.2.3+41 --build--> 1.2.3+42
```

The canonical sequence should make version identity deterministic:

```text
release intent
    -> read current pubspec version
    -> determine SemVer/build change
    -> write resulting pubspec.yaml version
    -> validate/test
    -> build candidate artifacts
    -> smoke-test candidate artifacts
    -> establish immutable release/tag context
    -> publish exactly once
```

Do not use `github.run_number` directly as a blind replacement for the package build number, as this breaks across repository forks, migrations, and workflow resets.

Instead, the generated workflow should split the versioning calculation into a deterministic path (e.g., using `cider`). A release intent should explicitly increment the semantic version, but *always* advance the build number. A build-only release advances just the build number.

**Structural constraints for committed versions:**
If the version mutation is committed back to the repository, it must occur **before** the `release-ready` validation aggregate. Do not drop a version mutation into the post-validation `prepare-release-tag` job. Mutating source files inside `prepare-release-tag` would violate exact-SHA tag guards and cause release artifacts to be built from pre-mutation source.

To create a coherent release variant:
1. **Direct Commit Pipeline:** Use a dedicated pre-validation job or separate workflow that calculates the new version, writes `pubspec.yaml`, commits the result, and pushes it using `GITHUB_TOKEN`. Because a `GITHUB_TOKEN` push naturally prevents recursive workflow runs, explicitly dispatch the CI/release workflow. GitHub Actions requires dispatching against a branch or tag name, so dispatch against the authoritative branch and pass the exact pushed commit SHA as a parameter (e.g., `expected_release_sha`). At the very start of the dispatched pipeline, verify `GITHUB_SHA == expected_release_sha` and `origin/$AUTHORITATIVE_BRANCH == expected_release_sha` before running validation.
2. **Protected-Branch Alternative:** If automated commits to `main` are blocked, provide a "Prepare Release" manual action that creates a Pull Request carrying the incremented version. Merging this PR establishes the validated authoritative commit and naturally triggers ordinary CI.

Example version mutation logic using `cider` (executed in the dedicated pre-validation pipeline):

```yaml
  prepare-version-commit:
    name: Prepare Version Commit
    needs: [route]
    if: ${{ needs.route.outputs.version_mutation == 'true' && inputs.mode != 'release-validate' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - uses: dart-lang/setup-dart@v1
      - name: Install cider
        run: dart pub global activate cider
      - name: Calculate version and bump pubspec.yaml
        env:
          RELEASE_MODE: ${{ inputs.mode }}
          RELEASE_VERSION_OVERRIDE: ${{ inputs.release_version_override }}
        run: |
          set -euo pipefail

          if [[ -n "$RELEASE_VERSION_OVERRIDE" ]]; then
             if ! [[ "$RELEASE_VERSION_OVERRIDE" =~ ^[0-9]+\.[0-9]+\.[0-9]+\+[0-9]+$ ]]; then
               echo "Invalid override format. Must be exactly major.minor.patch+build" >&2
               exit 1
             fi

             CURRENT_VER="$(cider version)"
             CURRENT_BUILD="${CURRENT_VER#*+}"
             OVERRIDE_BUILD="${RELEASE_VERSION_OVERRIDE#*+}"

             if [[ "$OVERRIDE_BUILD" -le "$CURRENT_BUILD" ]]; then
               echo "Override build number ($OVERRIDE_BUILD) must be strictly greater than current ($CURRENT_BUILD)." >&2
               exit 1
             fi

             # Note: Exact-version overrides may intentionally roll back the SemVer component
             # (e.g. returning to a prior release branch). Only the +build number is enforced
             # to be monotonically increasing.
             cider version "$RELEASE_VERSION_OVERRIDE"
          else
            case "$RELEASE_MODE" in
              release-major) cider bump major --bump-build ;;
              release-minor) cider bump minor --bump-build ;;
              release-patch) cider bump patch --bump-build ;;
              release-build) cider bump build ;;
              *)
                echo "Unsupported release mode: $RELEASE_MODE" >&2
                exit 1
                ;;
            esac
          fi

          AUTHORITATIVE_BRANCH="${GITHUB_REF#refs/heads/}"

          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git commit -am "chore(release): prepare v$(cider version)"

          # Push the commit using GITHUB_TOKEN to naturally suppress recursive push events
          git push origin "HEAD:refs/heads/$AUTHORITATIVE_BRANCH"

          VERSION_SHA="$(git rev-parse HEAD)"

          # Handoff: explicitly dispatch downstream workflow on the branch ref,
          # passing the exact expected SHA to avoid race conditions.
          gh workflow run ci.yml --ref "$AUTHORITATIVE_BRANCH" -f mode=release-validate -f expected_release_sha="$VERSION_SHA"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Router adaptations for the committed variant:**
When selecting the Dart committed-version variant, the baseline router in §27.1 must be updated so that the initial mutation run terminates safely and forwards to the internal validation continuation:

```yaml
  workflow_dispatch:
    inputs:
      mode:
        type: choice
        required: true
        default: build
        options:
          - build
          - lint-fix
          - monthly-maintenance
          - release-major
          - release-minor
          - release-patch
          - release-build
          - release-validate
          - publish-tag
      release_version_override:
        type: string
        required: false
        default: ''
      expected_release_sha:
        type: string
        required: false
        default: ''
      allow_prs:
        type: boolean
        required: false
        default: true
```

The router logic explicitly handles `version_mutation` termination and strict `release-validate` continuation without removing normal event support. Replace the canonical router with this complete variant:

```yaml
  route:
    name: Route Event
    runs-on: ubuntu-latest
    outputs:
      validation: ${{ steps.route.outputs.validation }}
      build: ${{ steps.route.outputs.build }}
      release: ${{ steps.route.outputs.release }}
      publisher: ${{ steps.route.outputs.publisher }}
      autofix: ${{ steps.route.outputs.autofix }}
      maintenance: ${{ steps.route.outputs.maintenance }}
      version_mutation: ${{ steps.route.outputs.version_mutation }}
    steps:
      - id: route
        shell: bash
        env:
          EVENT_NAME: ${{ github.event_name }}
          REF_TYPE: ${{ github.ref_type }}
          INPUT_MODE: ${{ inputs.mode }}
          INPUT_EXPECTED_RELEASE_SHA: ${{ inputs.expected_release_sha }}
        run: |
          set -euo pipefail

          validation=false
          build=false
          release=false
          publisher=false
          autofix=false
          maintenance=false
          version_mutation=false

          case "$EVENT_NAME" in
            pull_request)
              validation=true
              build=true
              ;;
            push)
              validation=true
              build=true
              if [[ "$REF_TYPE" == "tag" ]]; then
                publisher=true
              fi
              ;;
            schedule)
              validation=true
              build=true
              maintenance=true
              ;;
            workflow_dispatch)
              case "$INPUT_MODE" in
                build)
                  validation=true
                  build=true
                  ;;
                lint-fix)
                  autofix=true
                  ;;
                monthly-maintenance)
                  validation=true
                  build=true
                  maintenance=true
                  ;;
                release-major|release-minor|release-patch|release-build)
                  # Version mutation terminates after dispatching the downstream validation run
                  version_mutation=true
                  ;;
                release-validate)
                  if ! [[ "${INPUT_EXPECTED_RELEASE_SHA:-}" =~ ^[0-9a-f]{40}$ ]]; then
                    echo "release-validate requires a full 40-character expected_release_sha" >&2
                    exit 1
                  fi
                  validation=true
                  build=true
                  release=true
                  ;;
                publish-tag)
                  if [[ "$REF_TYPE" != "tag" || "$GITHUB_REF" != refs/tags/v* ]]; then
                    echo "publish-tag requires a v* tag ref; got $GITHUB_REF" >&2
                    exit 1
                  fi
                  validation=true
                  build=true
                  publisher=true
                  ;;
                *)
                  echo "Unsupported manual mode: $INPUT_MODE" >&2
                  exit 1
                  ;;
              esac
              ;;
            *)
              echo "Unsupported event: $EVENT_NAME" >&2
              exit 1
              ;;
          esac

          echo "validation=$validation" >> "$GITHUB_OUTPUT"
          echo "build=$build" >> "$GITHUB_OUTPUT"
          echo "release=$release" >> "$GITHUB_OUTPUT"
          echo "publisher=$publisher" >> "$GITHUB_OUTPUT"
          echo "autofix=$autofix" >> "$GITHUB_OUTPUT"
          echo "maintenance=$maintenance" >> "$GITHUB_OUTPUT"
          echo "version_mutation=$version_mutation" >> "$GITHUB_OUTPUT"
```

Because the `release-validate` payload operates on the exact pushed SHA rather than blindly trusting the branch tip, the downstream workflow must verify the target SHA before commencing any expensive operations:

```yaml
  release-origin-guard:
    name: Verify Release Origin
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 1
      - name: Verify exact authoritative commit
        env:
          INPUT_MODE: ${{ inputs.mode }}
          EXPECTED: ${{ inputs.expected_release_sha }}
        run: |
          set -euo pipefail

          if [[ "$INPUT_MODE" != "release-validate" ]]; then
            echo "Not release-validate mode. Skipping SHA check."
            exit 0
          fi

          AUTHORITATIVE_BRANCH="${GITHUB_REF#refs/heads/}"

          # Fetch the tip of the authoritative branch explicitly into a tracking ref
          git fetch origin "$AUTHORITATIVE_BRANCH:refs/remotes/origin/$AUTHORITATIVE_BRANCH" --depth=1
          ORIGIN_SHA="$(git rev-parse "origin/$AUTHORITATIVE_BRANCH")"

          if [[ "$GITHUB_SHA" != "$EXPECTED" ]] || [[ "$ORIGIN_SHA" != "$EXPECTED" ]]; then
            echo "Race condition detected: GITHUB_SHA ($GITHUB_SHA) or origin ($ORIGIN_SHA) does not match expected_release_sha ($EXPECTED)." >&2
            exit 1
          fi
```

To guarantee the guard runs before expensive work, **all selected validation jobs** must explicitly declare it in their `needs` array. For example:

```yaml
  flutter-test:
    name: Flutter Test
    needs: [route, release-origin-guard]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.validation == 'true' && needs.release-origin-guard.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: subosito/flutter-action@v2
      - run: flutter pub get
      - run: dart analyze
      - run: flutter test
```

The `validation` aggregate then depends on the router, the guard, and only the concrete validation jobs (do not include `build` here):

```yaml
  validation:
    name: Validation Aggregate
    needs: [route, release-origin-guard, flutter-test]
    if: ${{ always() && needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - name: Require selected validation jobs
        env:
          GUARD_RESULT: ${{ needs.release-origin-guard.result }}
          FLUTTER_RESULT: ${{ needs.flutter-test.result }}
        run: |
          set -euo pipefail
          [[ "$GUARD_RESULT" == "success" ]]
          [[ "$FLUTTER_RESULT" == "success" ]]
```

When composing additional selected validation jobs, add each job to `validation.needs` and explicitly assert its successful result alongside the guard and Flutter test. Do not accept failed, cancelled or unexpectedly skipped validation jobs. The rest of the pipeline (`build`, `release-ready`) remains downstream of the successful validation aggregate as in the canonical topology.

**Tagging policy and handoff:**
For committed versions, the durable cross-run handoff is the `pubspec.yaml` file itself. When the main release pipeline reaches the `prepare-release-tag` job (after validation and artifact builds succeed), it does not calculate an auto-increment. Instead, it reads the full version directly from the already-validated commit:

```yaml
      - name: Derive exact tag from pubspec
        run: |
          TAG="v$(cider version)"
          echo "TAG=$TAG" >> "$GITHUB_ENV"
```

The job then proceeds to tag exactly `GITHUB_SHA` using the same remote-tag, idempotency, and race checks outlined in §27.5.

When build-only releases are supported, always tag the full version including the build number (e.g., `v1.2.4+42` instead of `v1.2.4`). Stripping the build number causes tagging ambiguity or collision if a subsequent build `v1.2.4+43` is created. Do not prescribe one tag policy universally; state the consequences and require the repository's generated workflow to choose the policy deliberately based on whether multiple builds of a single SemVer release are published.

Ensure write permissions (`contents: write`) are tightly scoped to the specific job responsible for the version commit or Git tagging handoff.


### 27.8 Regression Prevention

Even when generated from canonical guidance, the actual implementation must be verified against regressions. Explicitly verify the following properties (e.g., using a dry-run `workflow_dispatch` test or static analysis), distinguishing between an intentionally disabled capability and a required capability that was unexpectedly skipped:

1. **Tag Routing:** A normal version-tag push and manual `publish-tag` request must enable all required validation and build stages alongside publication.
2. **Release-Critical Scope:** Every release-critical check explicitly executes for the relevant release route.
3. **Strict Gates:** Failed or unexpectedly skipped required checks must cause `release-ready` to fail. Ensure `release-ready` uses `if: always()` and asserts the explicit `success` of its dependencies.
4. **Downstream Enforcement:** Tag preparation and publication must explicitly require `needs.release-ready.result == 'success'` to proceed.
5. **Manual Paths:** Manual release preparation and tag-context publication must both follow the same required release contract and race protections (such as explicit commit origin verification).

**Lightweight Verification Matrix:**
Verify these scenarios via routing/condition tests or by intentionally failing a mock job on a test branch:
- *Successful Publication:* Normal `v*` tag push -> Validation passes -> Build passes -> `release-ready` passes -> Publication succeeds.
- *Skipped Required Check:* Job skipped unexpectedly -> `release-ready` runs but fails success assertion -> Publication skips.
- *Failed Validation/Build:* Job fails -> `release-ready` runs but fails success assertion -> Publication skips.
- *Manual Publication:* `workflow_dispatch` with `mode=publish-tag` -> Validates/builds run -> `release-ready` enforces success -> Publication succeeds.
- *Manual Preparation:* `workflow_dispatch` with `mode=release-major` -> Validates/builds run -> `release-ready` enforces success -> Tag preparation succeeds after origin race checks.

## 28. Existing-workflow migration procedure

When modernising an existing repository, follow this concrete procedure:

1. inventory workflows and jobs;
2. inventory repository capabilities and declared support;
3. identify generated content/examples;
4. identify unit/integration/E2E capabilities;
5. identify duplicate validation and duplicate release ownership;
6. design the target single-file graph;
7. move compatible jobs into the central workflow;
8. retain only technically justified separate workflows;
9. delete superseded workflow files;
10. validate generated content;
11. validate generated examples;
12. validate workflow YAML;
13. verify every manual mode reaches useful work;
14. verify scheduled paths;
15. verify artifact smoke tests and release gates.

This is a semantic migration, not merely a YAML rearrangement.

The generation agent should prefer the canonical modules over inventing equivalent one-off wiring. Deviate when repository reality requires it, and explain the deviation in the PR.

## 29. Anti-patterns

Do not generate:

- feature-branch `push` plus PR validation that runs the same commit twice without a reason;
- PR state-only events rerunning the ordinary validation graph when the commit has not changed;
- `pull_request: closed` rerunning the normal validation graph after a merge push;
- a broad concurrency rule that cancels main/tag/release runs;
- multiple GitHub Release owners;
- tag creation before release validation;
- release recovery that silently calculates a newer version;
- assumptions that a `GITHUB_TOKEN` tag push automatically triggers another workflow;
- `release: published` feeding back into publication;
- broad workflow-global write permissions for convenience;
- reserved `GITHUB_*` variables redefined in `env:`;
- user-controlled `${{ inputs.* }}` inserted directly into shell source;
- unused `workflow_dispatch` inputs or router outputs;
- unnecessary new external Actions dependencies without PR documentation;
- heavyweight security lanes in repositories that have not selected that risk posture;
- generator drift checks without validating the generated artifact;
- normal CI which silently rewrites/commits generated expectations;
- separate compatibility workflows that could be ordinary jobs in the main graph;
- runtime discovery of repository structure that the generation agent already knew;
- irrelevant platform/language jobs copied from a generic template;
- placeholder aggregate jobs left in the generated workflow;
- hand-wavy comments such as "repository-specific checks go here" where a selected canonical module should have been instantiated;
- a minimalist workflow that silently omits an obvious repository capability;
- dead legacy workflow files left beside the new workflow;
- tiny CI helper scripts whose only purpose is to move understandable YAML elsewhere.

## 30. Generation acceptance checklist

Before opening a CI PR, verify:

- repository capabilities were discovered at generation time;
- the resulting workflow is bespoke rather than runtime-generic;
- one central workflow is used unless each exception is explained;
- obsolete workflow files are removed;
- default-branch pushes run;
- PR opening and PR updates run without duplicate feature-branch push validation;
- state-only PR events do not rerun ordinary validation unless a concrete lifecycle job requires them;
- tag publication runs only for eligible tags;
- `pull_request: closed` is absent unless it has a concrete cheap lifecycle job;
- scheduled verification performs meaningful work and cannot release;
- manual inputs all route to useful jobs and no exposed input is dead;
- irrelevant events/jobs exit cheaply;
- concurrency cancels only genuinely superseded/conflicting work;
- permissions are minimal;
- newly introduced external CI dependencies are listed and justified;
- referenced action/tool versions were checked at generation time;
- reserved GitHub environment variables are not overridden;
- user input crosses into shell safely;
- generated committed output is regenerated and drift-checked where applicable;
- generated artifacts/examples are independently validated;
- examples/sample configuration are exercised where practical;
- unit/integration/E2E layers match the project rather than a generic template;
- compatibility matrices correspond to real support claims;
- workflows themselves are validated where appropriate;
- release artifacts are smoke-tested where applicable;
- release validation precedes permanent tagging;
- the authoritative branch SHA is checked before tag creation and immediately before a new tag is pushed;
- release recovery is exact-tag/exact-SHA;
- manual release preparation is non-cancelling and serialized where version races are possible;
- exactly one publisher exists;
- generic release publication has explicit retry behavior;
- GoReleaser publication is not duplicated;
- external/human-created eligible tags behave as intended where supported;
- selected canonical modules were instantiated rather than replaced with vague placeholders;
- the release gate explicitly names every selected release-critical job;
- repository-native tests and documentation/site checks pass.

## 31. Migration notes from superseded guidance

The earlier posts remain useful as historical rationale, but their strongest applicable rules are incorporated here:

- broad project-type coverage remains available as selectable modules rather than one giant generic workflow;
- concrete YAML remains part of the generation specification where it constrains routing, validation, generation, artifacts or release safety;
- the release-safe single-owner and exact-tag recovery rules remain mandatory;
- the one-file target is restored as the normative architecture rather than merely "fewest files";
- periodic verification remains a baseline for maintained repositories;
- repository-specific behavior is discovered by the generation agent and encoded explicitly rather than rediscovered at runtime;
- ecosystem-neutral orchestration does not mean implementation-free prose: selected capabilities should use the canonical module library so separate agents converge on the same structure.
