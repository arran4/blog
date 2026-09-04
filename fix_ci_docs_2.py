import sys

def process_file(filename):
    with open(filename, "r") as f:
        content = f.read()

    if filename == "content/post/2026/042-simplified-github-ci-release-safe/index.md":
        content = content.replace("              # A manual release mode prepares/pushes a tag only.\n              # The resulting tag-push workflow is the release owner.", "              # A manual release mode pushes the tag and publishes the release in the same run.\n              # Do NOT expect a tag push with GITHUB_TOKEN to start a new tag-push workflow run.")

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
          /             \\
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
      /             \\
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

    with open(filename, "w") as f:
        f.write(content)

process_file("content/post/2026/042-simplified-github-ci-release-safe/index.md")
