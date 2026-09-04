---
title: "Release-Safe Single-Owner GitHub CI/CD"
date: 2026-09-03T21:05:00+10:00
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

## Canonical model: manual dispatch pushes the tag and publishes the release

The preferred default model creates the tag and publishes the GitHub Release in the same workflow run. This avoids relying on a tag push to trigger a new workflow, which fails when the push is authenticated with the default `GITHUB_TOKEN` due to GitHub's event recursion prevention.

Events caused by `GITHUB_TOKEN` do not create new workflow runs (except for specific events like `workflow_dispatch`). Therefore, a workflow that checks out code, computes a tag, pushes it with `git push origin "$TAG"`, and expects `on: push: tags` to start another workflow will fail silently.

### The preferred manual release pattern

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
              run_code_checks=true
              # A manual release mode pushes the tag and publishes the release in the same run.
              # It sets run_release=true to publish immediately.
              ;;
            release)
              # Downstream notification only. Never create the same release again here.
              ;;
          esac

          echo "run_code_checks=$run_code_checks" >> "$GITHUB_OUTPUT"
          echo "run_release=$run_release" >> "$GITHUB_OUTPUT"
```

### Manual release request: push the tag and publish the release

Keep the manual and external-tag paths mutually exclusive so they cannot create competing releases. A manual release workflow must run its normal validation first, compute the release tag, push the tag using the normal `GITHUB_TOKEN`, and continue to publish the release in that exact same run. Ensure release publication waits until the tag has actually been pushed. Ensure the release job uses the computed release tag rather than `github.ref_name`, since a `workflow_dispatch` run may still have a branch ref.

```yaml
  manual-release:
    name: Publish manual release
    needs: [prepare-release-tag, test, build-release-artifacts]
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
          tag_name: ${{ needs.prepare-release-tag.outputs.release_tag }}
          prerelease: ${{ contains(needs.prepare-release-tag.outputs.release_tag, '-rc') || contains(needs.prepare-release-tag.outputs.release_tag, '-alpha') || contains(needs.prepare-release-tag.outputs.release_tag, '-beta') || contains(needs.prepare-release-tag.outputs.release_tag, '-test') }}
          generate_release_notes: true
          files: dist-release/**
```

Do NOT expect the tag push to start another workflow. Do NOT use `github.ref_name` in the release publisher if it might evaluate to `main` instead of the newly pushed tag.

### Alternative: strict tag-push-owner model

If the design specifically requires the pushed tag to start a new workflow and that new tag-push run to be the sole publisher, the tag MUST be pushed using a GitHub App installation token or PAT rather than `GITHUB_TOKEN`.

- Use an explicit secret such as `TAG_PUSH_TOKEN`.
- Fail clearly when it is absent.
- Never silently fall back to `GITHUB_TOKEN`, because that produces a tag without the required follow-up workflow.
- Explain this is an operational prerequisite that must be configured for each repository unless the credential is otherwise centrally supplied.

## Non-GoReleaser projects

After tested artifacts fan in, the one release owner job creates the published release and attaches the files. We run it for both external tag pushes and manual mode (where it depends on the tag being pushed).

```yaml
  github-release:
    name: Publish GitHub release
    # Wait for the manual tag push if in manual mode, otherwise just wait for artifacts
    needs: [route, build-release-artifacts, push-release-tag]
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
          tag_name: ${{ needs.prepare-release-tag.outputs.release_tag || github.ref_name }}
          prerelease: ${{ contains(needs.prepare-release-tag.outputs.release_tag || github.ref_name, '-rc') || contains(needs.prepare-release-tag.outputs.release_tag || github.ref_name, '-alpha') || contains(needs.prepare-release-tag.outputs.release_tag || github.ref_name, '-beta') || contains(needs.prepare-release-tag.outputs.release_tag || github.ref_name, '-test') }}
          generate_release_notes: true
          files: dist-release/**
```

There is no separate `publish-draft`, no placeholder `promote-release`, and no competing `gh release create` job.

If a project intentionally requires human-reviewed drafts, the same single-owner rule still applies: one job creates the draft, later code must locate and patch **that same release ID** to `draft=false`, and no other job may call `gh release create` for the tag.

## GoReleaser projects

If GoReleaser publishes the GitHub Release, **GoReleaser is the release owner**.

Run it as the one release lane, providing the explicit tag to GoReleaser via `GORELEASER_CURRENT_TAG` so it works even when `github.ref` is a branch (during manual mode):

```yaml
  goreleaser:
    needs: [route, test, push-release-tag]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
          fetch-tags: true
      - uses: goreleaser/goreleaser-action@v6
        with:
          distribution: goreleaser
          version: latest
          args: release --clean
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GORELEASER_CURRENT_TAG: ${{ needs.prepare-release-tag.outputs.release_tag || github.ref_name }}
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
2. Choose exactly one owner for the tag. Prefer the same-run manual/push lane.
3. For manual `release-*` dispatch, compute the tag, push it, and publish the release in the same run (or require a `TAG_PUSH_TOKEN`).
4. Remove `publish-draft` jobs that independently create a draft when another release creator exists.
5. Remove placeholder `promote-release` jobs. If drafts are genuinely required, promote the exact existing release by ID.
6. Do not set `run_release=true` for `release: published` in the primary publisher router.
7. Remove `|| true` around release creation. Duplicate creation is an error that should be visible.
8. Keep build/test/artifact jobs separate from the one release publication owner.
9. Preserve prerelease semantics (`rc`, `alpha`, `beta`, `test`) in the owner job.
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
   *Fix:* If you genuinely require the strict tag-push-owner model, state that the credential must have **Contents write permission**. A non-empty secret check (`if: env.TAG_PUSH_TOKEN != ''`) does not prove the token is usable or has the correct permissions. Prefer the same-run manual publication model to remove this credential requirement entirely.

## Agent rule

When generating or upgrading an entire CI workflow, use the current general guide and keep this article as the focused release-safety reference:

```yaml
# Agent rules for generation:
# https://arran4.github.io/blog/post/2026/042-simplified-github-ci-release-safe/
# Release safety details:
# https://arran4.github.io/blog/post/2026/041-release-safe-single-owner-github-ci/
```

The `041` rules take precedence over older CI articles for release ownership, draft creation, tag routing, and `release: published` behavior.