import sys

def process_file(filename):
    with open(filename, "r") as f:
        content = f.read()

    if filename == "content/post/2026/042-simplified-github-ci-release-safe/index.md":
        content = content.replace("              # A manual release mode prepares/pushes a tag only.\n              # The resulting tag-push workflow is the release owner.", "              # A manual release mode pushes the tag and publishes the release in the same run.\n              # Do NOT expect a tag push with GITHUB_TOKEN to start a new tag-push workflow run.")

    with open(filename, "w") as f:
        f.write(content)

process_file("content/post/2026/042-simplified-github-ci-release-safe/index.md")
