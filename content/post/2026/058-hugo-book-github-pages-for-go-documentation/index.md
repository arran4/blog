---
title: "Publishing Go Documentation with Hugo Book and GitHub Pages"
date: 2026-10-28T00:00:00+11:00
draft: false
guidance: ["documentation", "ci-cd"]
tags: ["go", "hugo", "github-pages", "github-actions", "documentation", "hugo-book", "open-source"]
categories: ["Software Development", "DevOps"]
---

<!-- cspell:words gtroff gitlink submodules -->

A README is a useful entry point to a Go project, but it is not the best place for every installation detail, command, API, example, and limitation. I wanted navigable documentation **without keeping two copies of it**.

I adopted [Hugo Book](https://github.com/alex-shpak/hugo-book) in [go-subcommand](https://github.com/arran4/go-subcommand), whose [documentation is already on GitHub Pages](https://arran4.github.io/go-subcommand/). I am now adapting the approach for [golang-gtroff](https://github.com/arran4/golang-gtroff), a **work-in-progress** pure-Go roff/man toolkit.

Publishing source documentation is not the same as publishing a stable software release. The site should be honest about what has merged, what is experimental, and what is still planned.

## How go-subcommand does it

The actual [go-subcommand CI workflow](https://github.com/arran4/go-subcommand/blob/main/.github/workflows/ci.yml) contains a Hugo build job and a Pages deployment job within its wider pipeline:

- Hugo's project root is `docs/` and the site configuration is [`docs/hugo.toml`](https://github.com/arran4/go-subcommand/blob/main/docs/hugo.toml).
- The Hugo Book theme is a Git submodule at `docs/themes/book`.
- Markdown lives under `docs/content/` with introduction, usage, reference, and advanced sections.
- GitHub Actions builds and uploads a Pages artifact; a separate deploy job publishes it.
- Publication uses only `pages: write` and `id-token: write` in the deploy job, leaving ordinary build/test jobs read-only.

This pattern avoids committing a generated `public/` site or mixing documentation publishing with GoReleaser release publication.

## Reproduce the basic setup

Add Hugo content and pin the theme as a submodule:

```sh
mkdir -p docs/content/docs
git submodule add https://github.com/alex-shpak/hugo-book docs/themes/book
```

The theme is not copied into the repository as ordinary tracked files. Git stores an exact submodule commit, and `.gitmodules` records where to fetch it.

Create `docs/hugo.toml`:

```toml
baseURL = "https://arran4.github.io/REPOSITORY/"
languageCode = "en-us"
title = "Project documentation"
theme = "book"

[params]
  BookTheme = "auto"
  BookToC = true
  BookSection = "docs"
```

For a GitHub *project* Pages site, the base URL includes the repository subpath. Without it, theme assets or navigation can accidentally target the account's root site.

Create `docs/content/_index.md` and `docs/content/docs/_index.md` for the home and documentation sections, then add Markdown pages in appropriate subdirectories. The Book theme supplies sidebar navigation and contents links.

Verify locally:

```sh
git submodule update --init --recursive
hugo --source docs --minify --baseURL "https://arran4.github.io/REPOSITORY/"
```

A successful build is only the first check. Inspect generated links, images, code blocks, and navigation under the repository subpath.

## One source of documentation, two strategies

In go-subcommand, the Hugo content directory **is** the maintained source. The pages are written directly in `docs/content/docs/`.

For golang-gtroff, guides already exist in `docs/ast.md`, `docs/cli.md`, `docs/man.md`, `docs/html.md` and `docs/convert.md`. Moving or copying them into a second maintained Markdown hierarchy would introduce unnecessary drift.

Instead, [golang-gtroff PR #61](https://github.com/arran4/golang-gtroff/pull/61) proposes a small build-only staging script that:

1. Reads the existing `docs/*.md` files.
2. Creates Hugo content pages from those files with titles and navigation weights.
3. Rewrites links to sibling guides to their website destinations and links to source files back to GitHub.
4. Excludes the staged copies from Git, so the original Markdown remains the only version to edit.

That is deliberately not a second documentation generator or a rewriting of the project documentation. It is a presentation adapter. If the project started without documentation, I would prefer the simpler go-subcommand method and write directly in Hugo content.

The staging script needs a build-and-link check: silent omissions and broken links would defeat the point of making the documentation easier to find.

## GitHub Actions: build on PRs, deploy on main

The Pages jobs should be able to validate pull requests without publishing anything. The simplified workflow is:

```yaml
name: Documentation (GitHub Pages)
on:
  push:
    branches: [main]
    paths: ['docs/**', '.gitmodules']
  pull_request:
    paths: ['docs/**', '.gitmodules']
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
        with:
          submodules: recursive
          persist-credentials: false
      - uses: peaceiris/actions-hugo@v3
        with:
          hugo-version: latest
          extended: true
      - run: hugo --source docs --minify
      - uses: actions/upload-pages-artifact@v5
        if: ${{ github.event_name != 'pull_request' }}
        with:
          path: ./docs/public

  deploy:
    if: ${{ github.event_name != 'pull_request' }}
    needs: build
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/deploy-pages@v5
        id: deployment
```

This is a **minimal example**, not a workflow to paste over a repository's existing release pipeline. The actual go-subcommand build integrates Pages into the existing [CI/CD workflow](https://github.com/arran4/go-subcommand/blob/main/.github/workflows/ci.yml), and my [canonical GitHub Actions reference](/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/) describes the wider release-safety and permission requirements.

The golang-gtroff PR uses a focused docs-only workflow because replacing its actively developed release workflow merely to add Pages would increase merge conflicts and change unrelated release behavior.

## Avoid accidentally publishing a private project

I added a stricter condition to the proposed golang-gtroff upload/deploy jobs:

```yaml
if: ${{ github.event_name != 'pull_request' && github.event.repository.private == false }}
```

**A repository being private does not mean its GitHub Pages website is private.** I want the documentation build to be testable before publication without creating a public route around the decision to make the repository public.

Before flipping visibility, I still need to review Git history, Actions logs, copied documentation and licensing for sensitive material. A WIP banner is useful, but it is not a secret scan.

When the repository is ready, select **Settings → Pages → Build and deployment → GitHub Actions**. A workflow file alone does not necessarily configure the site's deployment source.

Then use the actual deployed Pages URL in GitHub's About homepage. That homepage, repository description, topics and visibility are **repository settings**, not values that a normal code PR changes.

## Work in progress should be explicit

The current [golang-gtroff Pages PR](https://github.com/arran4/golang-gtroff/pull/61) also adds an unmistakable **work-in-progress** notice to the README and website. The project has useful syntax parsing, source-aware AST inspection and basic rendering/conversion, but it is not a complete GNU groff implementation, and there is no stable binary release.

This is the distinction I want readers to see:

- **Public source:** Inspect or contribute to an unfinished project.
- **Public documentation:** Understand the implemented subset and limitations.
- **Release artifacts:** Download a versioned build after separate tests and platform gates.
- **Announcement:** Deliberately invite a broader audience when the project is ready.

The last two do not have to happen just because the first two do.

One operational caveat is that GitHub Actions quota exhaustion may prevent a job from taking its first step. That is missing verification, not an executed Hugo build failure. The site should not be claimed as deployed until the workflow actually runs and the Pages URL works.

## Checklist before calling it done

A useful Pages integration should have an observable result: PR documentation builds pass without deployment, the theme checkout is pinned, only maintained Markdown is edited, relative links resolve, the project base URL works, the public site clearly states its maturity, and the deploy job has narrowly scoped permissions.

The broader principle is **give documentation a navigable home while leaving its source of truth where maintainers already work**.
