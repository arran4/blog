---
title: "Canonical GitHub Actions CI/CD Super-Reference"
date: 2026-09-08T06:33:54Z
draft: false
tags: ["github-actions", "ci", "cd", "release", "automation", "goreleaser", "canonical"]
categories: ["devops", "reference", "automation"]
---

<!-- cspell:words actionlint AppImage Buildx GOPATH GoReleaser jurplel mvcommon myapp nFPM prerelease qmake semver stefanzweifel todate TXTAR zizmor -->

This is the canonical GitHub Actions CI/CD generation reference.

It supersedes `006`, `011`, `028`, `041` and `042` where they conflict. Older posts remain useful as rationale, but an agent should normally need only this article plus the target repository to create or modernise its CI.

The goal is consistency without generic bloat: the agent discovers what the repository actually contains, selects the applicable capabilities here, and writes a bespoke workflow that already knows what it is responsible for. The checked-in workflow should not rediscover the project on every run.

## 1. Purpose and design objective

A generated workflow should be:

- **single-owner:** one coherent CI/CD dependency graph and exactly one GitHub Release publisher per tag;
- **single-file by default:** normally one `.github/workflows/ci.yml` or `.github/workflows/ci.yaml`;
- **event-efficient:** run when new information needs validation, and cheaply avoid work that an event cannot require;
- **repository-specific:** include only languages, platforms, generators, services, packaging and release mechanisms that exist in the repository;
- **release-safe:** validation precedes permanent tagging and publication;
- **self-verifying:** generated files, examples, workflows and built release artifacts are checked when those capabilities exist;
- **maintainable:** avoid unnecessary helper files and duplicated policy.

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

The result of discovery is a tailored checked-in workflow. Runtime capability discovery is a fallback only for facts that genuinely vary during a run. Do not build a giant `discover` job which re-detects known project structure on every invocation.

## 3. One self-contained workflow is the normative target

The normal result is exactly one coherent `.github/workflows/ci.yml` or `.github/workflows/ci.yaml` containing validation, build, maintenance and release orchestration.

When upgrading an existing repository, actively attempt to fold these into that workflow:

- workflow validation;
- generated-output and generated-example verification;
- lint/static analysis;
- unit/component tests;
- integration/service compatibility tests;
- selective end-to-end/system smoke tests;
- build and package jobs;
- artifact smoke verification;
- release gates;
- tag preparation;
- publication;
- scheduled verification;
- ordinary maintenance and autofix.

Use native `needs:` edges so the dependency graph is visible in one place. Delete superseded workflow files after consolidation. Do not keep disabled wrappers or legacy compatibility YAML simply because it already exists.

A second workflow needs a concrete reason. Valid exceptions include:

- a genuine reusable `workflow_call` interface;
- a materially different secret or trust boundary;
- a GitHub event/platform limitation that prevents coherent consolidation;
- genuinely independent administrative automation;
- a large family of independently scheduled generated maintenance workflows where forcing every schedule into one monolithic file would materially reduce readability or maintainability.

Historical structure is not an exception. If more than one workflow remains, the PR should explain why each additional workflow cannot reasonably be a job in the central graph.

The same principle applies to support files. Keep small routing and shell logic inline. Do not create helper scripts merely to make YAML look smaller. Preserve or introduce helper code when it is substantial, naturally belongs to the repository's implementation language, is shared with production logic, or materially improves direct testing.

## 4. Capability selection

Classify discovered capabilities before writing jobs:

- **Universal baseline:** event routing, ordinary validation, minimal permissions, useful manual dispatch where applicable, and periodic verification for maintained repositories.
- **Enable when present:** language-specific lint/test, generation checks, examples, integration/services, E2E/system smoke, platform/toolchain matrices, packaging, containers, release artifacts, GoReleaser.
- **Optional policy:** autofix PRs, dependency-update PRs, expensive scheduled checks.
- **Exception requiring explanation:** additional workflow files, bespoke version arithmetic, unusual release ownership, or unusually broad permissions.

Do not add a lane merely because this article contains an example. Do not omit an obvious lane merely to keep YAML short.

## 5. Trigger model: run when information changes, avoid duplicate runs

The trigger set should cover every state transition that needs validation without running the same logical validation twice.

The standard baseline is:

```yaml
on:
  push:
    branches: [main, master]
    tags: ['v*']

  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
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
- **Reopening or marking a draft ready can run CI** because review state changed.
- **Eligible version tags run the publication/release path.**
- **Scheduled runs prove a quiet repository still works.**
- **Manual dispatch exposes only useful operator actions.**

Do not subscribe to `pull_request: closed` by default. A merge already produces the authoritative-branch push that needs normal CI. Add `closed` only when the repository has a concrete cleanup/lifecycle action that cannot be handled elsewhere, and route it only to that cheap cleanup path rather than rerunning the normal test/build graph.

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

If using workflow-level PR cancellation, make non-PR runs unique rather than placing unrelated events into one shared group. Release-critical jobs may instead use their own job-level concurrency group with `cancel-in-progress: false`.

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
  +-- workflow/dependency validation
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
  +-- release-validation aggregate
  |
  +-- immutable tag/release context
  |
  +-- exactly one publisher
  |
  +-- post-release work
```

Independent checks should run in parallel when they can. Release publication should depend on one clear aggregate release gate rather than each repository reinventing complicated skipped-job expressions.

## 11. Testing hierarchy

Use the cheapest useful test at each layer:

- many unit/component tests with controlled dependencies;
- fewer integration tests against real filesystem/process/database/network/service boundaries;
- a small number of end-to-end/system tests where they provide confidence that cheaper tests cannot.

Do not require browser automation simply because a repository has a web UI. Prefer programmable rendering or handler seams when they prove the behavior more cheaply and deterministically.

Use E2E/system tests when the actual assembled system matters, for example:

- invoke the built CLI as a subprocess;
- start a disposable server and make HTTP requests;
- start a real temporary database/service;
- bring up a Compose environment;
- launch a built container and probe it;
- exercise browser-level behavior that genuinely depends on the browser;
- install a package and run a smoke command.

Expensive, non-release-critical E2E, fuzz or compatibility tests may run on a schedule or manual mode. Anything required to claim a release is valid must gate publication.

## 12. Generated outputs are a first-class capability

Classify generated content as:

1. **Committed generated output** — must remain synchronized with its source;
2. **Generated examples/documentation/fixtures** — must remain synchronized and should be validated as artifacts;
3. **Ephemeral build/test output** — should normally remain uncommitted.

For committed generated output, the normal validation pattern is:

```text
run authoritative generator
        |
        v
check working tree/diff
        |
        +-- clean -> continue
        |
        +-- changed -> fail and show the diff
```

For Go, `go generate ./...` followed by a clean-tree check is a common implementation, but use the repository's authoritative deterministic generator when `go generate ./...` is too broad or inappropriate.

Normal CI must not silently accept and commit regenerated output. An optional automation lane may regenerate and open a focused PR, but that does not replace the validation check.

## 13. Validate generated artifacts, not only drift

"Up to date" and "valid" are separate assertions.

After regeneration and drift checking, validate the generated artifact with the normal validator/compiler/parser for that artifact:

- generated GitHub Actions YAML -> regenerate -> diff check -> `actionlint`;
- generated Go source -> regenerate -> diff check -> compile/test;
- generated configuration -> regenerate -> load with the production parser;
- generated examples -> regenerate -> diff check -> compile or run representative examples;
- generated man pages/docs -> regenerate -> perform the repository's structural/build validation.

Generated workflow examples are particularly important: a generator can deterministically reproduce invalid YAML. Drift checking alone will not detect that.

## 14. Runnable examples and documentation smoke tests

Inspect `examples/`, demos, sample configuration and documented commands.

Where practical:

- compile examples;
- run cheap examples;
- parse sample configs;
- exercise CLI `--help` and `--version`;
- verify documented representative commands still parse/run;
- validate generated example output.

Do not execute examples with destructive or external side effects merely for coverage.

## 15. Language and ecosystem modules

These are selectable modules, not mandatory blocks.

### Go

Typical checks:

```yaml
- uses: actions/setup-go@v7
  with:
    go-version-file: go.mod
- run: go test ./...
- run: go vet ./...
```

Use `gofmt`/`golangci-lint` where the repository already uses them or where adding them is justified. Test minimum supported Go versions when the project makes such a compatibility claim.

### Node / JavaScript / TypeScript

Typical checks:

```yaml
- uses: actions/setup-node@v7
  with:
    node-version: '20'
    cache: npm
- run: npm ci
- run: npm test
```

Add the repository's actual lint/typecheck/build commands (`eslint`, `prettier`, `tsc`, bundling) rather than assuming names.

### Dart / Flutter

Typical validation:

```yaml
- run: flutter pub get
- run: dart analyze
- run: flutter test
```

Desktop applications may require platform-specific Linux/Windows/macOS build jobs. Only add those platforms when the project claims or releases support for them.

### C / C++ / CMake / Qt / KDE

Use the repository's actual CMake/qmake/Ninja conventions. A representative CMake shape is:

```yaml
- run: cmake -S . -B build -DBUILD_TESTING=ON
- run: cmake --build build --parallel
- run: ctest --test-dir build --output-on-failure
```

Qt/KDE projects may require additional package installation or an existing project bootstrap/container. Preserve those project-native environment contracts rather than replacing them with a generic Qt action if that loses necessary dependencies.

### Containers

Build containers when the repository actually ships or relies on them. Prefer a build-and-smoke path before publication. If GoReleaser owns the image, do not add a second image publisher for the same tags.

### Native/package-manager packaging

Debian, RPM, Flatpak, AppImage, Gentoo metadata or other packaging is selected only when the project supports it. Package builds should be treated as artifacts that can themselves need smoke/install validation.

## 16. Compatibility matrices are evidence-driven

Do not create matrices merely because they look comprehensive.

Use a matrix to prove a support claim or materially different behavior:

- a library's minimum supported language/toolchain version;
- Linux/macOS/Windows behavior where those systems are supported;
- architecture-specific release builds;
- database engine/version compatibility;
- GUI/headless variants where the project genuinely supports them.

Separate:

- the fast ordinary PR test;
- compatibility coverage;
- the release artifact matrix.

Expensive static analysis normally needs one representative/current toolchain, not every matrix entry.

## 17. Integration and service compatibility

Projects using databases, queues or local services should normally keep compatibility/integration jobs in the central workflow.

Prefer:

- GitHub Actions service containers;
- disposable local processes;
- temporary databases;
- deterministic fixtures;
- repository-provided Compose environments.

A MySQL/MariaDB/PostgreSQL/version compatibility check is normally a job/matrix in `ci.yml`, not automatically a reason for another workflow file.

Keep CI credentials ephemeral and local where possible. Do not expose production secrets to untrusted pull-request code.

## 18. Workflow validation

GitHub Actions YAML is code.

Where viable, repositories containing Actions workflows should run `actionlint`, particularly when workflows are generated or heavily templated.

When the repository's security posture warrants it, also consider:

- `zizmor`;
- dependency review;
- secret scanning;
- ecosystem vulnerability scanners.

A CI change should be reasoned through for:

- every `needs:` edge;
- every referenced output;
- event-specific contexts;
- skipped-job behavior;
- permissions;
- concurrency;
- release recursion assumptions;
- manual-dispatch routes.

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

## 20. Build artifacts and smoke verification

Build jobs should produce the artifacts that the project actually promises.

Use short Actions-artifact retention for transient handoff artifacts; one day is a good default when publication consumes them immediately.

Before publication, test actual candidate artifacts where relevant:

- run a CLI candidate with `--version`;
- verify injected version/commit/date metadata;
- execute a representative command;
- verify all expected binaries are present;
- inspect archive/package contents;
- install and smoke-test a package where practical;
- start a built container and probe a command/health endpoint;
- confirm platform/architecture artifacts match their names and targets.

Source tests do not prove a release artifact works after packaging, linking or metadata injection.

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

The skeleton is intentionally ecosystem-neutral. The generation agent replaces the comments with only the modules that the repository actually needs.

```yaml
# Generated using:
# https://arran4.github.io/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/

name: CI/CD

on:
  push:
    branches: [main, master]
    tags: ['v*']
  pull_request:
    types: [opened, synchronize, reopened, ready_for_review]
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
      publisher: ${{ steps.route.outputs.publisher }}
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
          publisher=false

          case "$EVENT_NAME" in
            pull_request)
              validation=true
              build=true
              ;;
            push)
              if [[ "$REF_TYPE" == "tag" ]]; then
                validation=true
                build=true
                publisher=true
              else
                validation=true
                build=true
              fi
              ;;
            schedule)
              validation=true
              build=true
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
          echo "publisher=$publisher" >> "$GITHUB_OUTPUT"

  validation:
    needs: [route]
    if: ${{ needs.route.outputs.validation == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Repository-specific validation modules go here.

  build:
    needs: [route, validation]
    if: ${{ needs.route.outputs.build == 'true' && needs.validation.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      # Repository-specific build/artifact modules go here.

  release-ready:
    needs: [route, validation, build]
    if: ${{ always() && needs.route.outputs.publisher == 'true' }}
    runs-on: ubuntu-latest
    steps:
      - name: Require release gates
        env:
          VALIDATION_RESULT: ${{ needs.validation.result }}
          BUILD_RESULT: ${{ needs.build.result }}
        run: |
          set -euo pipefail
          [[ "$VALIDATION_RESULT" == "success" ]]
          [[ "$BUILD_RESULT" == "success" ]]

  publisher:
    needs: [route, release-ready]
    if: ${{ needs.route.outputs.publisher == 'true' && needs.release-ready.result == 'success' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
      # Exactly one repository-specific publisher goes here.
```

For a versioned repository, extend `workflow_dispatch` with only the release/prerelease/recovery modes it actually supports. For a non-release library or configuration repository, do not add release controls merely because the larger reference discusses them.

PR cancellation, release serialization, generation checks, integration matrices and artifact smoke jobs are added from the applicable capability sections rather than embedded into every generated skeleton.

## 27. Existing-workflow migration procedure

When modernising an existing repository:

1. inventory every workflow and job;
2. inventory project capabilities and declared support;
3. identify generated content, examples and their source of truth;
4. identify unit/integration/E2E/system tests;
5. identify duplicate triggers and validation;
6. identify every release owner;
7. design the target single-file dependency graph;
8. map useful existing behavior into that graph;
9. fold compatible workflow files into the central workflow;
10. retain only concretely justified separate workflows;
11. delete superseded/dead workflow files;
12. validate generated outputs and generated examples;
13. validate workflow YAML;
14. verify every manual mode reaches useful work;
15. verify scheduled paths perform useful work and cannot release;
16. verify artifact smoke checks and release gates;
17. document remaining exceptions and newly introduced external CI dependencies.

This is a semantic migration, not a YAML rearrangement.

## 28. Anti-patterns

Do not generate:

- feature-branch `push` plus PR validation that runs the same commit twice without a reason;
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
- unnecessary new external Actions dependencies without PR documentation;
- heavyweight security lanes in repositories that have not selected that risk posture;
- generator drift checks without validating the generated artifact;
- normal CI which silently rewrites/commits generated expectations;
- separate compatibility workflows that could be ordinary jobs in the main graph;
- runtime discovery of repository structure that the generation agent already knew;
- irrelevant platform/language jobs copied from a generic template;
- a minimalist workflow that silently omits an obvious repository capability;
- dead legacy workflow files left beside the new workflow;
- tiny CI helper scripts whose only purpose is to move understandable YAML elsewhere.

## 29. Generation acceptance checklist

Before opening a CI PR, verify:

- repository capabilities were discovered at generation time;
- the resulting workflow is bespoke rather than runtime-generic;
- one central workflow is used unless each exception is explained;
- obsolete workflow files are removed;
- default-branch pushes run;
- PR opening and PR updates run without duplicate feature-branch push validation;
- tag publication runs only for eligible tags;
- `pull_request: closed` is absent unless it has a concrete cheap lifecycle job;
- scheduled verification performs meaningful work and cannot release;
- manual inputs all route to useful jobs;
- irrelevant events/jobs exit cheaply;
- concurrency cancels only genuinely superseded/conflicting work;
- permissions are minimal;
- newly introduced external CI dependencies are listed and justified;
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
- the authoritative branch SHA is checked before tag creation;
- release recovery is exact-tag/exact-SHA;
- exactly one publisher exists;
- GoReleaser publication is not duplicated;
- external/human-created eligible tags behave as intended where supported;
- repository-native tests and documentation/site checks pass.

## 30. Migration notes from superseded guidance

The earlier posts remain useful as historical rationale, but their strongest applicable rules are incorporated here:

- broad project-type coverage remains available as selectable modules rather than one giant generic workflow;
- the release-safe single-owner and exact-tag recovery rules remain mandatory;
- the one-file target is restored as the normative architecture rather than merely "fewest files";
- periodic verification remains a baseline for maintained repositories;
- repository-specific behavior is discovered by the generation agent and encoded explicitly rather than rediscovered at runtime.
