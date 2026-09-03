---
title: "Release-Safe Single-Owner GitHub CI/CD"
date: 2026-09-03T21:05:00+10:00
draft: false
tags: ["github-actions", "ci", "cd", "release", "automation", "goreleaser", "agents"]
categories: ["devops", "reference", "automation"]
---

This is the focused release-safety companion to the current general CI guidance in `042-simplified-github-ci-release-safe`. Use `042` when creating or upgrading an entire workflow, and this article for the duplicate-release rationale and migration audit.

These rules supersede the older `006-github-ci-and-deploy`, `011-simplified-github-ci`, and `028-simplified-github-ci-updated` release examples where they conflict.

The invariant is:

> **For one tag, exactly one job or release tool owns creation/publication of the GitHub Release.**

Artifact builders may produce files. Other jobs may react after publication. They must not independently create another GitHub Release for the same tag.

---

## Designed for Jules / repository-local agents

This migration can be performed by an agent that has access to the checked-out repository but **no GitHub API/UI access and little git awareness**.

The agent is expected to:

- read `AGENTS.md` and repository-local instructions,
- inspect `.github/workflows/` and local release configuration,
- search files for release creators and event routing,
- edit the workflow/configuration,
- run local validators/tests where available,
- describe any GitHub-side checks that a human should perform later.

The agent is **not** expected to:

- inspect the Releases page,
- query workflow runs,
- inspect/open/update PRs or issues,
- verify secrets/settings,
- delete historical draft releases,
- browse GitHub for current Action versions,
- perform release administration itself.

Do not block the local fix because those capabilities are unavailable.

The generated GitHub Actions workflow may still contain normal git/GitHub runtime operations such as `git fetch`, `git tag`, `git push`, `GITHUB_TOKEN`, GoReleaser, or release actions. Jules only needs to author and reason about that YAML; it does not need to perform those operations during implementation.

---

## The failure pattern to remove

A locally visible broken pattern looks like this:

```yaml
manual-gh-release:
  run: gh release create "$TAG" --generate-notes || true

publish-draft:
  uses: softprops/action-gh-release@v2
  with:
    draft: true
    tag_name: ${{ needs.prepare-release-tag.outputs.release_tag || github.ref_name }}

promote-release:
  run: echo "Promotion step placeholder"
```

It may also route `release: published` back into primary publication:

```bash
release)
  run_release=true
  ;;
```

This creates multiple potential owners:

1. manual dispatch may create a release,
2. another job may create a draft,
3. a tag-push publisher/GoReleaser may publish another release,
4. `release: published` may trigger publication logic again.

A placeholder promotion job is not promotion. `|| true` around `gh release create` can hide the collision instead of fixing it.

Jules can identify this bug entirely from the local workflow graph. Live GitHub evidence is useful confirmation, not a prerequisite.

---

## Local audit procedure

Search all repository-local workflow/release files, not only `ci.yml`:

```text
.github/workflows/*.yml
.github/workflows/*.yaml
.goreleaser.yml
.goreleaser.yaml
goreleaser.yml
goreleaser.yaml
```

Search for:

```text
softprops/action-gh-release
gh release create
goreleaser/goreleaser-action
publish-draft
promote-release
draft: true
release:
types: [published]
run_release
workflow_dispatch
refs/tags
```

Then answer from those files:

1. Which event requests or computes the version?
2. Which job creates/pushes the tag?
3. Which jobs build/stage artifacts?
4. Which exact job/tool creates the GitHub Release?
5. Can manual dispatch create a release directly?
6. Can tag push create one too?
7. Does GoReleaser publish one?
8. Can `release: published` re-enter publication?
9. Does another workflow publish the same tag pattern?
10. Does `|| true` hide a creation failure?

If more than one path can create the GitHub Release for the same semantic tag, fix the event graph.

---

## Preferred architecture

The default flow is:

```text
manual workflow_dispatch release-patch
        |
        v
compute/validate vX.Y.Z
        |
        v
workflow pushes vX.Y.Z tag
        |
        v
fresh tag-push workflow run
        |
        v
lint/test/build artifacts
        |
        v
ONE GitHub Release owner
        |
        v
release published
        |
        v
release: published downstream consumers only
```

The manual run should prepare/push the tag, not publish the GitHub Release itself.

A typical manual tag job may contain:

```yaml
manual-release-tag:
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

Do not add `gh release create` to that job when the tag-push run is the publisher.

---

## Non-GoReleaser projects

One tag-push job should create the release and attach tested artifacts:

```yaml
github-release:
  name: Publish GitHub release
  needs: [route, build-release-artifacts]
  if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') }}
  runs-on: ubuntu-latest
  permissions:
    contents: write
  steps:
    - uses: actions/download-artifact@v5
      with:
        path: dist-release
        pattern: '*-release'
        merge-multiple: true

    - uses: softprops/action-gh-release@v2
      with:
        draft: false
        generate_release_notes: true
        prerelease: ${{ contains(github.ref_name, '-rc') || contains(github.ref_name, '-alpha') || contains(github.ref_name, '-beta') || contains(github.ref_name, '-test') }}
        files: dist-release/**
```

There is no independent `publish-draft`, no competing `gh release create`, and no fake promotion step.

For notes-only repositories, omit the artifact/files handling.

---

## GoReleaser projects

If the local GoReleaser configuration/workflow publishes GitHub Releases, **GoReleaser is the release owner**.

Typical shape:

```yaml
goreleaser:
  needs: [route, test]
  if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && github.event_name == 'push' && startsWith(github.ref, 'refs/tags/v') }}
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

Preserve repository-local GoReleaser environment/secrets/configuration, but remove any second GitHub Release creator around it.

Do not combine it with another `softprops/action-gh-release` publisher or manual `gh release create` for the same tag.

---

## `release: published` is downstream

The release event is useful for consumers of an already-published release, such as:

- web-site refreshes,
- notifications,
- metadata/index updates,
- documentation deployment,
- reporting.

It should not call the primary release creator again.

A router should treat it like:

```bash
release)
  run_post_release=true
  ;;
```

not:

```bash
release)
  run_release=true
  ;;
```

---

## Intentional draft releases

A human-reviewed draft flow is allowed only when it is genuinely intended. Then:

1. one job creates the draft,
2. the workflow resolves/records that same release,
3. artifacts are uploaded to it,
4. promotion changes that exact release to `draft=false`,
5. no other job creates a second release for the tag.

Do not infer that human-reviewed drafts are required merely because an old generated workflow contains `draft: true`.

A placeholder `echo` is not a valid promotion implementation.

---

## What Jules should change

For the duplicate-owner migration, Jules should normally:

1. inspect all local workflow/release configuration,
2. identify the release-owner paths,
3. choose exactly one GitHub Release owner,
4. make manual `release-*` dispatch prepare/push the tag only,
5. ensure semantic tag push reaches the sole publisher,
6. remove competing `publish-draft` release creation,
7. remove placeholder promotion jobs,
8. stop `release: published` from setting primary `run_release`,
9. make GoReleaser sole owner when it already publishes releases,
10. remove `|| true` that hides release-creation collisions,
11. preserve existing build/test/artifact/prerelease behaviour,
12. update the workflow's guidance pointer to `042`/`041`,
13. run local validation/tests available in the environment.

Do not broaden the task into unrelated dependency/Action-major churn.

---

## Action versions

Do not require Jules to verify current Action majors on GitHub.

For a focused migration:

- preserve existing compatible Action versions,
- use versions explicitly supplied by the task/guide when introducing a necessary action,
- leave latest-major verification to a human/GitHub-capable follow-up if it matters.

This release-safety fix should not depend on network discovery.

---

## Local validation

Validate what is available locally:

- YAML syntax,
- `actionlint` if available,
- `needs` dependencies,
- referenced outputs,
- conditions across all triggering events,
- reachability of artifact jobs on tag push,
- only one local GitHub Release creator for each semantic tag,
- no GoReleaser + second GitHub Release publisher combination,
- no `release: published` route back into creation,
- repository-local tests/static checks relevant to the changed files.

If a validator is unavailable, state that in the handoff. Do not pretend GitHub CI was observed.

---

## Human / GitHub-side follow-up

The coding agent should leave these to a human or GitHub-capable reviewer unless the task explicitly provides those capabilities:

- inspect the Releases page for historical orphaned `untagged-*` drafts,
- decide whether those historical drafts should be deleted,
- verify repository secrets/settings,
- observe the next real release workflow run,
- update PR/issue metadata if the agent cannot,
- verify latest Action majors if desired.

Historical duplicate drafts are evidence of the old bug; deleting them is **not** part of the repository-file fix.

---

## Expected Jules handoff

Report:

- files changed,
- old local release event graph,
- new local release event graph,
- which job/tool is now the sole GitHub Release owner,
- local tests/validators run,
- anything that could not be validated locally,
- GitHub-side follow-ups for the human reviewer.

Do not ask Jules to inspect GitHub or manage a PR merely to complete the code change.

---

## Agent pointer

When generating/upgrading the workflow, use:

```yaml
# Agent rules for generation:
# https://arran4.github.io/blog/post/2026/042-simplified-github-ci-release-safe/
# Release safety details:
# https://arran4.github.io/blog/post/2026/041-release-safe-single-owner-github-ci/
```

The single-owner rule takes precedence over older CI examples.