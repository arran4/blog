---
title: "Goreleaser Error: fatal: tag already exists"
date: 2026-06-18 07:12:56+00:00
draft: false
tags: ["git", "github-actions", "goreleaser", "ci", "cd"]
categories: ["development", "troubleshooting"]
---

If you use GoReleaser inside a GitHub Action workflow to automatically build and release your binaries, you might occasionally encounter an error that looks like this:

```
Run git tag v0.0.2

fatal: tag 'v0.0.2' already exists

Error: Process completed with exit code 128.
```

This error halts your pipeline entirely because Git correctly refuses to create a tag that has already been created. But why does this happen, and how do you resolve it?

## The Problem

GoReleaser or your CI pipeline relies on Git tags to understand what version to build and publish. When an action attempts to run a `git tag vX.Y.Z` command, but that tag is already present in your local or remote repository, the command fails with a fatal error.

This commonly happens in a few scenarios:
1. **Triggering manually without incrementing the version:** If you have a `workflow_dispatch` trigger that takes a version string, and you run it twice with the same version string (like `v0.0.2`), the second run will fail because the tag was created by the first run.
2. **Failed previous releases:** If your CI workflow previously ran and successfully created the tag but failed in a later step (e.g., during building or uploading assets), the tag will still exist. Re-running the pipeline will result in this exact error when it reaches the tagging step again.
3. **Duplicate automated tagging:** Your script may blindly attempt to tag the commit without first checking if the remote branch already has that tag.

## How to Fix It

Depending on what you are trying to achieve, there are two primary ways to resolve this issue.

### Option 1: Delete the conflicting tag and retry (For failed releases)

If your previous pipeline failed and you are explicitly trying to retry or overwrite that exact same release version (e.g., `v0.0.2`), you will need to delete the tag first.

You should delete the tag both locally and on your remote repository:

```bash
# Delete the tag locally
git tag -d v0.0.2

# Delete the tag on the remote repository
git push origin :refs/tags/v0.0.2
```

Once the tag has been removed from the remote, you can safely trigger your GitHub Action workflow again.

### Option 2: Increment the version (For new releases)

If the previous release was successful and you are actually trying to push new changes, you should not be reusing the `v0.0.2` tag.

Instead, increment your version number according to Semantic Versioning conventions (e.g., to `v0.0.3` or `v0.1.0`), and trigger the release workflow with the new tag.

```bash
# Create a new tag for the new version
git tag v0.0.3

# Push the new tag to the remote
git push origin v0.0.3
```

By ensuring your Git tags accurately represent your releases without duplicates, your CI/CD pipeline using GoReleaser will continue to run smoothly.
