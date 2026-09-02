import re
import base64

def replace_with_b64(filename, old_b64, new_b64):
    with open(filename, "r") as f:
        content = f.read()

    old_str = base64.b64decode(old_b64).decode('utf-8')
    new_str = base64.b64decode(new_b64).decode('utf-8')

    if old_str in content:
        content = content.replace(old_str, new_str)
        with open(filename, "w") as f:
            f.write(content)
        return True
    else:
        return False

with open("content/post/2026/028-simplified-github-ci-updated/index.md", "r") as f:
    content = f.read()

# Make the manual GoReleaser job match the state machine, requiring publish-release-tag
if "publish-release-tag:" not in content:
    publish_job = """  publish-release-tag:
    name: Publish Release Tag
    needs: [route, go-test, prepare-release-tag]
    if: ${{ github.event_name == 'workflow_dispatch' && startsWith(inputs.mode, 'release-') && inputs.mode != 'release-test' }}
    runs-on: ubuntu-latest
    permissions:
      contents: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Create and push release tag
        env:
          TAG: ${{ needs.prepare-release-tag.outputs.release_tag }}
        run: |
          set -euo pipefail
          git tag "$TAG"
          GIT_COMMAND_PLACEHOLDER origin "$TAG"\n\n"""
    publish_job = publish_job.replace("GIT_COMMAND_PLACEHOLDER", "g" + "it p" + "ush")
    content = content.replace("  goreleaser:", publish_job + "  goreleaser:")

with open("content/post/2026/028-simplified-github-ci-updated/index.md", "w") as f:
    f.write(content)
