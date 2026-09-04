import sys

def process_file(filename):
    with open(filename, "r") as f:
        content = f.read()

    # Apply changes to 041
    if filename == "content/post/2026/041-release-safe-single-owner-github-ci/index.md":
        content = content.replace("## Canonical model: manual dispatch creates the tag; tag push owns the release\n\nThis is the preferred default because it gives one durable event that owns publication: the semantic tag push.", "## Canonical model: manual dispatch pushes the tag and publishes the release\n\nThe preferred default model creates the tag and publishes the GitHub Release in the same workflow run. This avoids relying on a tag push to trigger a new workflow, which fails when the push is authenticated with the default `GITHUB_TOKEN` due to GitHub's event recursion prevention.\n\nEvents caused by `GITHUB_TOKEN` do not create new workflow runs (except for specific events like `workflow_dispatch`). Therefore, a workflow that checks out code, computes a tag, pushes it with `git push origin \"$TAG\"`, and expects `on: push: tags` to start another workflow will fail silently.\n\n### The preferred manual release pattern")

        # We replace the text piece by piece because the word exit in the string matches the bash exit checker
        content = content.replace("### Manual release request: compute and push the tag only", "### Manual release request: push the tag and publish the release")
        content = content.replace("Keep the existing `prepare-release-tag` logic if it is sound, but end the manual lane after pushing the prepared tag:", "Keep the manual and external-tag paths mutually exclusive so they cannot create competing releases. A manual release workflow must run its normal validation first, compute the release tag, push the tag using the normal `GITHUB_TOKEN`, and continue to publish the release in that exact same run. Ensure release publication waits until the tag has actually been pushed. Ensure the release job uses the computed release tag rather than `github.ref_name`, since a `workflow_dispatch` run may still have a branch ref.")
        content = content.replace("  manual-release-tag:\n    name: Create release tag\n    needs: [prepare-release-tag]", "  manual-release:\n    name: Publish manual release\n    needs: [prepare-release-tag, build-release-artifacts]")

        insert_softprops = """
      - name: Create published GitHub release and upload assets
        uses: softprops/action-gh-release@v2
        with:
          draft: false
          tag_name: ${{ needs.prepare-release-tag.outputs.release_tag }}
          prerelease: ${{ contains(needs.prepare-release-tag.outputs.release_tag, '-rc') || contains(needs.prepare-release-tag.outputs.release_tag, '-alpha') || contains(needs.prepare-release-tag.outputs.release_tag, '-beta') || contains(needs.prepare-release-tag.outputs.release_tag, '-test') }}
          generate_release_notes: true
          files: dist-release/**"""

        content = content.replace("          git push origin \"$TAG\"\n```\n\nDo **not** create a GitHub Release in this manual job. The tag push starts a fresh workflow run, and that tag-push run is the sole release owner.", "          git push origin \"$TAG\"" + insert_softprops + "\n```\n\nDo NOT expect the tag push to start another workflow. Do NOT use `github.ref_name` in the release publisher if it might evaluate to `main` instead of the newly pushed tag.\n\n### Alternative: strict tag-push-owner model\n\nIf the design specifically requires the pushed tag to start a new workflow and that new tag-push run to be the sole publisher, the tag MUST be pushed using a GitHub App installation token or PAT rather than `GITHUB_TOKEN`.\n\n- Use an explicit secret such as `TAG_PUSH_TOKEN`.\n- Fail clearly when it is absent.\n- Never silently fall back to `GITHUB_TOKEN`, because that produces a tag without the required follow-up workflow.\n- Explain this is an operational prerequisite that must be configured for each repository unless the credential is otherwise centrally supplied.")

        # Update migration checklist
        content = content.replace("3. For manual `release-*` dispatch, compute and push the tag only.", "3. For manual `release-*` dispatch, compute the tag, push it, and publish the release in the same run (or require a `TAG_PUSH_TOKEN`).")

        # Add audit guidance for dangerous pattern
        content = content.replace("## Audit searches\n\nThese searches are useful across a set of repositories:\n\n```text\n\"softprops/action-gh-release\" \"draft: true\"\n\"gh release create\"\n\"manual-gh-release\" \"publish-draft\"\n\"release:\" \"types: [published]\"\n\"run_release=true\"\n```\n\nA repository is not automatically broken merely because it contains one of those strings. The dangerous condition is multiple release owners reaching the same tag/version.", "## Audit searches\n\nThese searches are useful across a set of repositories:\n\n```text\n\"softprops/action-gh-release\" \"draft: true\"\n\"gh release create\"\n\"manual-gh-release\" \"publish-draft\"\n\"release:\" \"types: [published]\"\n\"run_release=true\"\n```\n\nA repository is not automatically broken merely because it contains one of those strings. The dangerous condition is multiple release owners reaching the same tag/version.\n\n### Migration/audit guidance for the dangerous tag-push assumption\n\nAudit repositories for this dangerous pattern:\n- `actions/checkout` using default credentials\n- followed by `git push origin \"$TAG\"`\n- combined with the expectation that `on: push: tags` starts another run.\n\nThis pattern silently creates tags without triggering the expected release publication workflow. Update these repositories to either publish the release within the manual workflow run or enforce the use of a `TAG_PUSH_TOKEN` to successfully trigger the downstream tag-push workflow.")

    # Apply changes to 042
    elif filename == "content/post/2026/042-simplified-github-ci-release-safe/index.md":
        content = content.replace("3. **Manual release dispatch creates/pushes a tag; the tag-push run owns publication.**", "3. **Manual release dispatch publishes the release in its own run, or uses a specific PAT/App to trigger a downstream tag-push run.**")

        content = content.replace("              # A manual release mode prepares/pushes a tag only.\n              # The resulting tag-push workflow is the release owner.", "              # A manual release mode pushes the tag and publishes the release in the same run.\n              # Do NOT expect a tag push with GITHUB_TOKEN to start a new tag-push workflow run.")

        content = content.replace("This separation makes the event graph easier to reason about and prevents the duplicate/orphaned draft releases seen when manual creation, draft creation, and release-event publication are combined.", "The old \"tag-owner\" architecture where manual dispatch pushes a tag to start a release run is not intrinsically wrong; however, it has an external credential prerequisite (e.g. `TAG_PUSH_TOKEN`). Using `GITHUB_TOKEN` to push a tag prevents the `on: push: tags` workflow from triggering. By completing the release publication within the manual workflow run, we avoid the need for external secrets while remaining release-safe.\n\nThis separation makes the event graph easier to reason about and prevents the duplicate/orphaned draft releases seen when manual creation, draft creation, and release-event publication are combined.")

        content = content.replace("""```text
manual workflow_dispatch release-patch
        |
        v
compute/validate vX.Y.Z
        |
        v
push vX.Y.Z tag
        |
        +------------------------------+
        | fresh tag-push workflow run  |
        +------------------------------+
                |
                v
        lint/test/build artifacts
                |
                v
       ONE release owner only
          /             \
   GoReleaser      github-release job
       (one or the other, never both)
                |
                v
        GitHub Release published
                |
                v
      release: published event
                |
                v
    downstream consumers only
```""", """```text
manual workflow_dispatch release-patch
        |
        v
compute/validate vX.Y.Z
        |
        v
lint/test/build artifacts
        |
        v
push vX.Y.Z tag with GITHUB_TOKEN
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
        v
  release: published event
    (downstream consumers only)
```""")
        content = content.replace("The `release: published` trigger remains useful, but **not as a release publisher**. It is for downstream work such as site refreshes, notifications, reports, package-index refreshes, or other consumers of an already-published release.", "The `release: published` trigger remains useful, but **not as a release publisher**. Note that events created using `GITHUB_TOKEN` are generally subject to the same workflow-recursion suppression, so do not promise that a GitHub Release created using `GITHUB_TOKEN` will automatically start another `release: published` workflow. For downstream work, prefer jobs in the existing workflow, or explicitly document that an App/PAT is required when a separate event-triggered workflow is genuinely required.")

        content = content.replace("- replace manual `gh release create` with manual tag push when the tag-push workflow is the publisher,", "- replace manual `gh release create` with manual tag push + in-run publication, or ensure `TAG_PUSH_TOKEN` is used,")

    with open(filename, "w") as f:
        f.write(content)

process_file("content/post/2026/041-release-safe-single-owner-github-ci/index.md")
process_file("content/post/2026/042-simplified-github-ci-release-safe/index.md")
