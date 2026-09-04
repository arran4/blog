---
title: "Release-Safe Single-Owner GitHub CI/CD"
date: 2026-09-04T08:39:00+00:00
draft: false
tags: ["github-actions", "ci", "cd", "release", "automation", "goreleaser"]
categories: ["devops", "reference", "automation"]
---

This is the focused release-safety companion to the current general CI guidance in `042-simplified-github-ci-release-safe`. Use `042` as the canonical document when creating or upgrading an entire CI workflow, and use this article for the detailed single-release-owner rationale and migration checks. These rules supersede the older `006-github-ci-and-deploy`, `011-simplified-github-ci`, and `028-simplified-github-ci-updated` draft-promotion examples where they conflict.

The important rule is simple:

> **For one tag, exactly one job or release tool owns creation and publication of the GitHub Release.**

Artifact builders may produce and upload artifacts. Other jobs may react after publication. They must not independently create another release for the same tag.

This rule exists because a workflow can otherwise create a draft release with `softprops/action-gh-release`, also run `gh release create`, and also run again for `release: published`. GitHub permits draft releases that do not behave like the canonical published release, so this can leave `untagged-*` draft entries behind even when a normal release for the version is eventually published.

## The failure pattern to remove

Do not combine patterns like these for the same version:

```yaml
manual-gh-release:
  # ...
  run: gh release create "$TAG" --generate-notes || true

publish-draft:
  # ...
  uses: softprops/action-gh-release@v2
  with:
    draft: true
    tag_name: ${{ needs.prepare-release-tag.outputs.release_tag || github.ref_name }}

promote-release:
  # Placeholder is not promotion.
  run: echo "Promotion step placeholder"
```

Do not route `release: published` back into the same release-producing lane either:

```bash
release)
  run_release=true
  ;;
```

That event is emitted *after* a release has been published. Treat it as a downstream notification event unless you have an explicit, idempotent recovery workflow.

Also do not hide duplicate-release failures with `|| true`. A failed `gh release create` may be the signal that another job already created a draft or published release.



### The manual credential recursion trap

Use the `arran4/kgithub-notify` failure from Actions run 33820455345, job 100861817524, as a motivating example. The workflow had a non-empty `OVERLAY_GITHUB_TOKEN`, checkout succeeded, but `git push` failed with HTTP 403 because the token lacked the correct permissions. Do not blindly attempt to push tags and assume success without verifying permissions.

## Canonical model: manual dispatch pushes the tag and publishes the release

The preferred default model creates the tag and publishes the GitHub Release in the same workflow run. This treats GitHub's `GITHUB_TOKEN` event recursion suppression as intentional duplicate prevention in the manual path: a manual run publishes the release exactly once, and its tag push does not spawn a second release workflow.

### Manual release

```
workflow_dispatch
-> release gates succeed
-> calculate/tag exact validated commit
-> push tag with GITHUB_TOKEN
-> same workflow publishes exactly once
```

### Independent tag push

```
human/external vX.Y.Z push
-> normal tag-triggered workflow
-> required gates
-> same publisher publishes exactly once
```


### Router

```yaml
jobs:
  route:
    runs-on: ubuntu-latest
    outputs:
      run_code_checks: ${{ steps.route.outputs.run_code_checks }}
      run_release: ${{ steps.route.outputs.run_release }}
    steps:
      - id: route
        shell: bash
        run: |
          set -euo pipefail

          run_code_checks=false
          run_release=false

          case "${{ github.event_name }}" in
            push)
              run_code_checks=true
              if [[ "${{ github.ref }}" == refs/tags/v* ]]; then
                run_release=true
              fi
              ;;
            pull_request)
              run_code_checks=true
              ;;
            workflow_dispatch)
              # A manual release mode pushes the tag and publishes the release in the same run.
              # It sets run_release=true to publish immediately.
              run_code_checks=true
              run_release=true
              ;;
            release)
              # Downstream notification only. Never create the same release again here.
              ;;
          esac

          echo "run_code_checks=$run_code_checks" >> "$GITHUB_OUTPUT"
          echo "run_release=$run_release" >> "$GITHUB_OUTPUT"
```

### Release Context Gate: normalize tag and safely push if manual

Keep the manual and external-tag paths mutually exclusive so they cannot create competing releases. We introduce a common `release-context` job that runs for BOTH `push` tags and `workflow_dispatch` manual releases *after* all validation gates successfully pass. It normalizes the tag, safely pushes it if it was a manual request, and exports the tag for downstream publishers.

*(This snippet is schematic. In a complete workflow, this gate must explicitly depend on every repository-appropriate validation job—see `042` for the full dynamic gate pattern.)*

```yaml
  release-validation:
    name: Release Validation Gate
    needs: [route, prepare-release-tag, test] # <-- depend on all actual required tests
    if: ${{ !failure() && !cancelled() && needs.test.result == 'success' }}
    runs-on: ubuntu-latest
    steps:
      - run: echo "Validation complete"

  release-context:
    name: Release Context & Gate
    needs: [route, prepare-release-tag, release-validation, build-release-artifacts]
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

          TAG="${{ needs.prepare-release-tag.outputs.release_tag || github.ref_name }}"
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
              echo "To retry a failed publication for this exact version, ensure release_version_override is used and GITHUB_SHA matches." >&2
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



## Non-GoReleaser projects

After tested artifacts fan in, the one release owner job creates the published release and attaches the files. We run it for both external tag pushes and manual mode (where it depends on the tag being pushed).

```yaml
  github-release:
    name: Publish GitHub release
    needs: [route, build-release-artifacts, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      discussions: write
    steps:
      - name: Collect release artifacts
        uses: actions/download-artifact@v5
        with:
          path: dist-release
          pattern: '*-release'
          merge-multiple: true

      - name: Create published GitHub release and upload assets
        uses: softprops/action-gh-release@v2
        with:
          draft: false
          tag_name: ${{ needs.release-context.outputs.release_tag }}
          prerelease: ${{ contains(needs.release-context.outputs.release_tag, '-rc') || contains(needs.release-context.outputs.release_tag, '-alpha') || contains(needs.release-context.outputs.release_tag, '-beta') || contains(needs.release-context.outputs.release_tag, '-test') }}
          generate_release_notes: true
          files: dist-release/**
```

There is no separate `publish-draft`, no placeholder `promote-release`, and no competing `gh release create` job.

If a project intentionally requires human-reviewed drafts, the same single-owner rule still applies: one job creates the draft, later code must locate and patch **that same release ID** to `draft=false`, and no other job may call `gh release create` for the tag.

## GoReleaser projects

If GoReleaser publishes the GitHub Release, **GoReleaser is the release owner**.


### Ensuring correct tag context in the manual same-run publisher

Ensure the manual same-run publisher has the correct tag context. If GoReleaser requires `GORELEASER_CURRENT_TAG` or a local tag, show the correct pattern. Since `github.ref` might be a branch rather than a tag during a manual `workflow_dispatch` run, you must explicitly pass the computed tag to your publisher. For example:


```yaml
  goreleaser:
    needs: [route, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
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
      - uses: goreleaser/goreleaser-action@v7
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GORELEASER_CURRENT_TAG: ${{ needs.release-context.outputs.release_tag }}
```

Do not add `softprops/action-gh-release`, `gh release create`, or a second release-producing `release: published` lane around it.

## `release: published` is downstream

It can still be useful for work that should happen only after GitHub confirms the release is public, for example:

- updating a web site,
- sending notifications,
- refreshing external metadata,
- producing reports.

Those jobs should consume the published release. They should not create it again.

## Idempotent recovery is different from a second owner


## Address retry/recovery semantics

If publication fails after a tag has been pushed, a rerun should not blindly attempt to recreate the same tag and fail. Document an appropriate state-aware approach:
- verify whether the expected tag already exists and points at the expected commit;
- reuse it for recovery when safe;
- fail clearly if it points elsewhere;
- never silently move an existing release tag.

A manually-invoked recovery job may inspect an existing release and upload missing assets, but it should require an explicit version/tag and verify state first. For example:


```bash
set -euo pipefail

gh release view "$TAG" >/dev/null
# upload only the known missing asset(s)
gh release upload "$TAG" dist/my-artifact --clobber
```

That is recovery against the canonical release, not a second publication path.

## Migration checklist for existing generated workflows

When updating repositories generated from the older articles:

1. Identify every place that can create a GitHub Release: `gh release create`, `softprops/action-gh-release`, GoReleaser, language-specific publishers, and API calls to `/releases`.
2. Choose exactly one owner for the tag. Prefer the unified same-run manual and external-tag release-context lane.
3. For manual `release-*` dispatch, compute the tag, push it, and publish the release in the same run (or require a `TAG_PUSH_TOKEN`).
4. Remove `publish-draft` jobs that independently create a draft when another release creator exists.
5. Remove placeholder `promote-release` jobs. If drafts are genuinely required, promote the exact existing release by ID.
6. Do not set `run_release=true` for `release: published` in the primary publisher router.
7. Remove `|| true` around release creation. Duplicate creation is an error that should be visible.
8. Keep build/test/artifact jobs separate from the one release publication owner.
9. Preserve release mode semantics:
   - normal major/minor/patch releases publish normally;
   - RC/alpha/beta prereleases publish as prereleases where appropriate;
   - test/snapshot modes must not accidentally create normal published releases;
   - explain that GoReleaser `--snapshot` does not publish a normal GitHub Release.
10. Check the Releases page for old `untagged-*` drafts. Fixing the workflow prevents new duplicates; historical drafts should be reviewed and deleted separately if they are obsolete.

## Audit searches

These searches are useful across a set of repositories:

```text
"softprops/action-gh-release" "draft: true"
"gh release create"
"manual-gh-release" "publish-draft"
"release:" "types: [published]"
"run_release=true"
```

A repository is not automatically broken merely because it contains one of those strings. The dangerous condition is multiple release owners reaching the same tag/version.

### Migration/audit guidance for dangerous tag-push assumptions

Audit repositories for these two dangerous patterns:

1. **Assuming default `GITHUB_TOKEN` tag pushes start another workflow:**
   - `actions/checkout` using default credentials
   - followed by `git push origin "$TAG"`
   - combined with the expectation that `on: push: tags` starts the release run.
   *Fix:* Update these repositories to publish the release directly within the manual workflow run.

2. **Using a PAT/App token solely to force the second run without validation:**
   - Repositories that added a `TAG_PUSH_TOKEN` to bypass the `GITHUB_TOKEN` limitation but fail to validate it.
   *Fix:* If you genuinely require the strict tag-push-owner model (where a pushed tag must start a separate workflow), the credential must have **Contents write permission** for tag pushes. A non-empty secret check (`if: env.TAG_PUSH_TOKEN != ''`) does not prove the token is usable or has the correct permissions. GitHub App credentials are preferable to a broad long-lived PAT where practical. Prefer the same-run manual publication model to remove this credential requirement entirely. Do not require a PAT solely to force recursive workflow execution.

## Agent rule

When generating or upgrading an entire CI workflow, use the current general guide and keep this article as the focused release-safety reference:

```yaml
# Agent rules for generation:
# https://arran4.github.io/blog/post/2026/042-simplified-github-ci-release-safe/
# Release safety details:
# https://arran4.github.io/blog/post/2026/041-release-safe-single-owner-github-ci/
```

The `041` rules take precedence over older CI articles for release ownership, draft creation, tag routing, and `release: published` behavior.