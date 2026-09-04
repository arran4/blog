import sys

with open('content/post/2026/042-simplified-github-ci-release-safe/index.md', 'r') as f:
    content = f.read()

# Update Rule 3
old_rule3 = """3. **Manual release dispatch publishes the release in its own run, or uses a specific PAT/App to trigger a downstream release run.**"""
new_rule3 = """3. **Manual release dispatch explicitly dispatches the publisher workflow using `GITHUB_TOKEN`, or uses a specific PAT/App to trigger a downstream release run.**"""
content = content.replace(old_rule3, new_rule3)

old_route = """            workflow_dispatch)
              case "${{ inputs.mode }}" in
                lint-fix)
                  run_code_checks=true
                  is_nightly=true
                  ;;
                build)
                  run_code_checks=true
                  run_build=true
                  ;;
                release-*)
                  # A manual release mode pushes the tag and publishes the release in the same run.
                  # It sets run_release=true to publish immediately.
                  run_code_checks=true
                  run_build=true
                  run_release=true
                  ;;"""
new_route = """            workflow_dispatch)
              case "${{ inputs.mode }}" in
                lint-fix)
                  run_code_checks=true
                  is_nightly=true
                  ;;
                build)
                  run_code_checks=true
                  run_build=true
                  ;;
                release-*)
                  # A manual release mode explicitly dispatches the publisher.
                  run_code_checks=true
                  run_build=true
                  run_release=true
                  ;;"""
content = content.replace(old_route, new_route)

old_release_context_permissions = """  release-context:
    name: Release Context
    needs: [route, prepare-release-tag, release-validation, build-release-artifacts]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write"""
new_release_context_permissions = """  release-context:
    name: Release Context
    needs: [route, prepare-release-tag, release-validation, build-release-artifacts]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write"""
content = content.replace(old_release_context_permissions, new_release_context_permissions)

old_release_context_script = """          git push origin "$TAG" || (
            VERIFY_SHA=$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}')
            if [[ "$VERIFY_SHA" == "${GITHUB_SHA}" ]]; then
              echo "Tag successfully verified on remote after push error."
            else
              echo "Tag push failed and remote verification failed." >&2
              exit 1
            fi
          )
```

Do NOT expect the manual tag push to start another workflow when using `GITHUB_TOKEN`. This job acts as the unified bridge to the same-run publisher."""

new_release_context_script = """          git push origin "$TAG" || (
            VERIFY_SHA=$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}')
            if [[ "$VERIFY_SHA" == "${GITHUB_SHA}" ]]; then
              echo "Tag successfully verified on remote after push error."
            else
              echo "Tag push failed and remote verification failed." >&2
              exit 1
            fi
          )

          # Explicitly dispatch the publisher workflow at the new tag ref
          if [[ "${{ github.event_name }}" == "workflow_dispatch" ]]; then
            gh workflow run "${{ github.workflow }}" --ref "$TAG"
          fi
```

Do NOT expect the manual tag push to start another workflow when using `GITHUB_TOKEN` because ordinary events are suppressed. Instead, this job explicitly dispatches the workflow at the tag, relying on the `workflow_dispatch` exception to the recursion rule. The publisher mode verifies it is running at an eligible tag and cannot recursively create/push another tag or dispatch itself again."""
content = content.replace(old_release_context_script, new_release_context_script)


# Now we also need to ensure the publisher requires the tag context in 042. Let's see if 042 has a publisher job:
old_github_release_job = """  github-release:
    name: Publish GitHub release
    needs: [route, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}"""
new_github_release_job = """  github-release:
    name: Publish GitHub release
    needs: [route, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && startsWith(github.ref, 'refs/tags/') }}"""
content = content.replace(old_github_release_job, new_github_release_job)

old_goreleaser_job = """  goreleaser:
    name: Run GoReleaser
    needs: [route, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}"""
new_goreleaser_job = """  goreleaser:
    name: Run GoReleaser
    needs: [route, release-context]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && startsWith(github.ref, 'refs/tags/') }}"""
content = content.replace(old_goreleaser_job, new_goreleaser_job)

with open('content/post/2026/042-simplified-github-ci-release-safe/index.md', 'w') as f:
    f.write(content)
