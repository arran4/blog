---
title: "GoReleaser Template Caveats: tolower vs lower"
date: 2026-09-01T23:14:43Z
draft: false
tags: [goreleaser, ci, github-actions, templates, caveats]
categories: [DevOps]
---

When configuring GoReleaser to publish Docker images to registries like GitHub Container Registry (`ghcr.io`), you often want to dynamically inject the repository name using the `GITHUB_REPOSITORY` environment variable.

However, Docker registries enforce lowercase names for images. A common mistake is attempting to use the `lower` function in the GoReleaser template to achieve this:

```yaml
dockers:
  - image_templates:
      - "ghcr.io/{{ .Env.GITHUB_REPOSITORY | lower }}:latest" # WRONG!
```

This will result in an error during the release process:

```
docker build failed: failed to execute image template 'ghcr.io/{{ .Env.GITHUB_REPOSITORY | lower }}:latest': template: failed to apply "ghcr.io/{{ .Env.GITHUB_REPOSITORY | lower }}:latest": function "lower" not defined
```

## The Solution: Use `tolower`

GoReleaser uses the `text/template` engine but provides its own set of custom template functions. For lowercase conversion, GoReleaser provides `tolower`, not `lower`.

The correct configuration is:

```yaml
dockers:
  - image_templates:
      - "ghcr.io/{{ .Env.GITHUB_REPOSITORY | tolower }}:latest" # CORRECT!
```

### Why this happens

While `lower` might seem intuitive or familiar from other templating systems, GoReleaser's template function map specifically defines `tolower` (and `toupper` for uppercase). You can review the available template functions in the [GoReleaser Template Documentation](https://goreleaser.com/customization/templates/).

When writing your own `.goreleaser.yaml` files, especially when replacing placeholder values like `OWNER/REPO` with dynamic environment variables, remember to use `tolower` to ensure compatibility with Docker registry naming constraints.
