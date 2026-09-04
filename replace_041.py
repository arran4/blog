import sys

with open('content/post/2026/041-release-safe-single-owner-github-ci/index.md', 'r') as f:
    content = f.read()

# Update Canonical model flow description
old_flow = """### Manual release

```
workflow_dispatch
-> release gates succeed
-> calculate/tag exact validated commit
-> push tag with GITHUB_TOKEN
-> same workflow publishes exactly once
```"""

new_flow = """### Manual release

```
manual release dispatch
-> compute and validate exactly one tag
-> push the tag with the normal GITHUB_TOKEN
-> explicitly workflow-dispatch the publisher workflow at that tag ref using GITHUB_TOKEN
-> publisher run performs normal tested release build
-> exactly one GitHub Release owner publishes
```"""
content = content.replace(old_flow, new_flow)

# Update the explanation above Canonical model
old_model_desc = """The preferred default model creates the tag and publishes the GitHub Release in the same workflow run. This treats GitHub's `GITHUB_TOKEN` event recursion suppression as intentional duplicate prevention in the manual path: a manual run publishes the release exactly once, and its tag push does not spawn a second release workflow."""

new_model_desc = """The preferred default model computes the tag, pushes it using `GITHUB_TOKEN`, and then explicitly dispatches the publisher using `GITHUB_TOKEN`. GitHub's event-recursion rule suppresses ordinary events (like `push`) caused by `GITHUB_TOKEN` to prevent infinite loops. However, GitHub explicitly makes `workflow_dispatch` and `repository_dispatch` exceptions to that recursion suppression. By manually dispatching the workflow at the newly pushed tag using `GITHUB_TOKEN`, we avoid needing a PAT (Personal Access Token) while maintaining a separate, canonical release-publisher run."""
content = content.replace(old_model_desc, new_model_desc)

old_script_actual = '''          git push origin "$TAG" || (
            VERIFY_SHA=$(git ls-remote --tags origin "refs/tags/$TAG" | awk '{print $1}')
            if [[ "$VERIFY_SHA" == "${GITHUB_SHA}" ]]; then
              echo "Tag successfully verified on remote after push error."
            else
              echo "Tag push failed and remote verification failed." >&2
              exit 1
            fi
          )
```

Do NOT expect the manual tag push to start another workflow when using `GITHUB_TOKEN`. This job acts as the unified bridge to the same-run publisher.'''

new_script = '''          git push origin "$TAG" || (
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

Do NOT expect the manual tag push to start another workflow when using `GITHUB_TOKEN` because ordinary events are suppressed. Instead, this job explicitly dispatches the workflow at the tag, relying on the `workflow_dispatch` exception to the recursion rule. The publisher mode verifies it is running at an eligible tag and cannot recursively create/push another tag or dispatch itself again.'''
content = content.replace(old_script_actual, new_script)


# We need to update the gate in 041
old_gate_permissions = """  release-context:
    name: Release Context & Gate
    needs: [route, prepare-release-tag, release-validation, build-release-artifacts]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write"""

new_gate_permissions = """  release-context:
    name: Release Context & Gate
    needs: [route, prepare-release-tag, release-validation, build-release-artifacts]
    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
      actions: write"""
content = content.replace(old_gate_permissions, new_gate_permissions)

# Update Migration checklist
old_migration = """3. For manual `release-*` dispatch, compute the tag, push it, and publish the release in the same run (or require a `TAG_PUSH_TOKEN`)."""
new_migration = """3. For manual `release-*` dispatch, compute the tag, push it with `GITHUB_TOKEN`, and explicitly dispatch the publisher workflow at that tag ref (or explicitly document a trigger-capable GitHub App/PAT if you specifically want the raw tag push event itself to trigger)."""
content = content.replace(old_migration, new_migration)

# Update audit guidance
old_audit_guidance = """1. **Assuming default `GITHUB_TOKEN` tag pushes start another workflow:**
   - `actions/checkout` using default credentials
   - followed by `git push origin "$TAG"`
   - combined with the expectation that `on: push: tags` starts the release run.
   *Fix:* Update these repositories to publish the release directly within the manual workflow run."""
new_audit_guidance = """1. **Assuming default `GITHUB_TOKEN` tag pushes start another workflow:**
   - `actions/checkout` using default credentials
   - followed by `git push origin "$TAG"`
   - combined with the expectation that `on: push: tags` starts the release run.
   *Fix:* Replace this broken pattern with either explicit workflow/repository dispatch using `GITHUB_TOKEN` (preferred), or an explicitly documented trigger-capable GitHub App/PAT credential. This correction was found in practice when a generated workflow correctly refused to proceed without `RELEASE_PAT`/`GH_PAT`; the better general guidance is to avoid needing that repository secret in the first place."""
content = content.replace(old_audit_guidance, new_audit_guidance)

old_audit_guidance_2 = """   *Fix:* If you genuinely require the strict tag-push-owner model (where a pushed tag must start a separate workflow), the credential must have **Contents write permission** for tag pushes. A non-empty secret check (`if: env.TAG_PUSH_TOKEN != ''`) does not prove the token is usable or has the correct permissions. GitHub App credentials are preferable to a broad long-lived PAT where practical. Prefer the same-run manual publication model to remove this credential requirement entirely. Do not require a PAT solely to force recursive workflow execution."""
new_audit_guidance_2 = """   *Fix:* If you genuinely require the strict tag-push-owner model (where a pushed tag must start a separate workflow), the credential must have **Contents write permission** for tag pushes. A non-empty secret check (`if: env.TAG_PUSH_TOKEN != ''`) does not prove the token is usable or has the correct permissions. GitHub App credentials are preferable to a broad long-lived PAT where practical. Prefer the secret-free explicit-dispatch manual publication model to remove this credential requirement entirely. Treat a PAT/App token as an optional alternate architecture, not a universal prerequisite. Do not require a PAT solely to force recursive workflow execution."""
content = content.replace(old_audit_guidance_2, new_audit_guidance_2)

# One more place in 041 to fix: the `route` job explanation for workflow_dispatch
old_route = """            workflow_dispatch)
              # A manual release mode pushes the tag and publishes the release in the same run.
              # It sets run_release=true to publish immediately.
              run_code_checks=true
              run_release=true
              ;;"""

new_route = """            workflow_dispatch)
              # A manual release mode pushes the tag and explicitly dispatches the publisher.
              run_code_checks=true
              run_release=true
              ;;"""
content = content.replace(old_route, new_route)

# One more fix: "publisher run performs normal tested release build" - the github-release and goreleaser jobs are publisher runs, they should verify they are running at a tag if needed. Actually the instructions say:
# "- the publisher mode verifies it is running at an eligible tag; - the publisher mode cannot recursively create/push another tag or dispatch itself again; - genuine external tag pushes continue to route to publication normally."
# The `github-release` job in `041` says:
old_github_release = """    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' }}"""
new_github_release = """    if: ${{ !failure() && !cancelled() && needs.route.outputs.run_release == 'true' && startsWith(github.ref, 'refs/tags/') }}"""
content = content.replace(old_github_release, new_github_release)

with open('content/post/2026/041-release-safe-single-owner-github-ci/index.md', 'w') as f:
    f.write(content)
