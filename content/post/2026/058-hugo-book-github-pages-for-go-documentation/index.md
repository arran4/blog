---
title: "Building a Developer Information Portal with Hugo Book and GitHub Pages"
date: 2026-10-28T19:20:00+11:00
draft: false
guidance: ["documentation", "ci-cd"]
tags: ["documentation", "developer-experience", "hugo", "hugo-book", "github-pages", "github-actions", "go", "open-source"]
categories: ["Software Development", "DevOps"]
---

<!-- cspell:words godoc peaceiris -->

Too many projects have a README, a Go package reference, and a growing pile of Markdown files named `SPEC.md`, `DESIGN.md`, or `IMPLEMENTATION_PLAN.md`. Some were written to coordinate an agent for one task. Months later they look like official documentation, even when they describe an abandoned approach or an implementation that has changed.

What I want instead is a **developer information portal**: a navigable, maintained set of pages that helps a person get started, complete real tasks, understand the system, diagnose problems, and contribute. A portal does not need a custom web application or a second documentation database. Plain Markdown, [Hugo](https://gohugo.io/), the [Hugo Book theme](https://github.com/alex-shpak/hugo-book), and GitHub Pages are sufficient for many projects.

This is a general, reproducible setup. `OWNER` and `REPOSITORY` are placeholders, not names of an existing project. The pages shown below are **documentation templates**: replace fictional commands and claims with tested behaviour before publishing them as instructions.

## Decide what the portal is for

A portal should answer a different set of questions from an API reference.

| Reader's question | Best home |
| --- | --- |
| What is this project, and should I use it? | Portal home / overview |
| How do I install it and see a successful result? | Getting started |
| How do I complete a particular task? | How-to guide |
| Can you teach me the workflow from beginning to end? | Tutorial |
| Why does the system work this way? | Concepts, architecture, or a decision record |
| How do I configure it or diagnose a problem? | Configuration guide, troubleshooting, operations |
| What commands and flags exist? | Concise CLI reference, ideally generated or checked against the executable |
| What Go packages, types, functions and methods exist? | **GoDoc / [pkg.go.dev](https://pkg.go.dev/)**, generated from source comments |
| What is planned, disputed, or not yet implemented? | Issue, roadmap, proposal, or explicitly marked draft |

**Do not build another GoDoc.** Keep package-level contracts and symbol-level API documentation alongside the Go code. A guide can show *why* and *when* to use an API, demonstrate an end-to-end workflow, then link to its authoritative `pkg.go.dev` entry. Copying signatures, comments, and method lists into Hugo creates two references that will drift.

This distinction also applies outside Go: keep generated API and schema references with their generators, and use the portal for the explanations and tasks that generated output cannot provide.

### A useful information architecture

I start with a small, reader-oriented navigation rather than a directory for each internal subsystem.

| Section | Contents | What makes it useful |
| --- | --- | --- |
| **Start here** | Overview, prerequisites, installation, first successful result | A newcomer can verify that the project works |
| **Tutorials** | Guided, sequential learning exercises | Explain each step and its expected result |
| **How-to guides** | Focused tasks such as upgrading, integrating, or troubleshooting | Start from the reader's goal, not a source file |
| **Concepts** | Vocabulary, mental model, lifecycle and important constraints | Explain the system before its implementation details |
| **Architecture** | Major components, boundaries, data flow, trade-offs | Describe the current design, with a diagram when useful |
| **Reference** | Configuration, supported formats, compatibility, CLI options | Facts that cannot simply be delegated to GoDoc or generated tools |
| **Contributing / operating** | Local development, testing, releases, deployment, debugging | Help someone change or run the system safely |

A small project may only need **Start here**, **How-to**, **Concepts**, and **Reference**. Add sections when they serve actual readers, not to fill a template. A README remains the short project introduction and link into the portal; it does not need to repeat the guides.

## 1. Create a self-contained Hugo site

The following example assumes a Git repository already exists and you want its documentation source in `docs/`. Install Git and a current Hugo release locally, then verify the tools:

~~~sh
git --version
hugo version
~~~

Inside the repository, add Hugo Book as a **Git submodule**, not a copied theme tree, and create the first content directories:

~~~sh
mkdir -p docs/content/docs/{tutorials,how-to,concepts,reference}
git submodule add https://github.com/alex-shpak/hugo-book docs/themes/book
~~~

The Git submodule records a particular theme commit. Commit both `.gitmodules` and the submodule entry. Updating the theme later should be a reviewed change, just like updating a dependency.

Create `docs/hugo.toml`:

~~~toml
baseURL = "https://OWNER.github.io/REPOSITORY/"
languageCode = "en-us"
title = "Developer portal"
theme = "book"

[params]
  BookTheme = "auto"
  BookSection = "docs"
  BookToC = true
~~~

Replace `OWNER` and `REPOSITORY` with the real GitHub account and project. A project Pages site normally lives at `/REPOSITORY/`, **not** at the account's URL root. Getting that `baseURL` wrong can break assets and navigation after deployment even when the local preview looks fine. For a custom domain, use the actual intended site URL instead.

The initial tree will look like this once the next steps are complete:

~~~text
docs/
├── hugo.toml
├── themes/book/                  # Git submodule
└── content/
    ├── _index.md                 # Portal home
    └── docs/
        ├── _index.md             # Documentation landing page
        ├── getting-started.md
        ├── tutorials/
        │   └── _index.md
        ├── how-to/
        │   ├── _index.md
        │   └── diagnosing-a-failure.md
        ├── concepts/
        │   ├── _index.md
        │   └── architecture.md
        └── reference/
            └── _index.md
~~~

The `_index.md` files define section landing pages. Ordinary `.md` files define content pages. Hugo Book can build a sidebar from that hierarchy and each page's front matter. Use `weight` to give readers an intentional order rather than relying on alphabetical filenames.

## 2. Give readers a clear entry point

Create `docs/content/_index.md`. This is the front door, not a dump of internal implementation notes:

~~~markdown
---
title: "Developer portal"
---

# Developer portal

Learn what this project does, get it running, and discover how to use,
extend, and troubleshoot it.

- [Start here](docs/getting-started/) for prerequisites and a first result.
- [How-to guides](docs/how-to/) for specific tasks.
- [Concepts](docs/concepts/) for the system's design and terminology.
- [Reference](docs/reference/) for configuration and compatibility.

For Go package signatures and exported symbols, use the project's
package documentation on pkg.go.dev.
~~~

Create `docs/content/docs/_index.md`:

~~~markdown
---
title: "Documentation"
weight: 1
---

The documentation is organised by what you want to achieve.

**New here?** Start with [Getting started](getting-started/).

**Have a task?** Choose a how-to guide.

**Need to understand a trade-off?** Read Concepts or Architecture.
~~~

These links are relative to their pages, so check them at the final project Pages URL. The public home page should also state the project's maturity when relevant: experimental, stable, or subject to breaking changes. Avoid implying that a published website means a stable release exists.

## 3. Write a getting-started guide that reaches a result

The most important page is not an exhaustive catalogue. It is the shortest **verified** path from a clean environment to something useful. A good guide explicitly says:

1. **Who it is for and what they will achieve.** A reader needs a destination.
2. **Prerequisites.** Tools, supported versions, credentials, permissions, and platform assumptions.
3. **Installation.** Copyable commands with version or repository references.
4. **First task.** Inputs, commands, expected output, and a way to confirm success.
5. **Failure recovery.** One or two common errors with links to troubleshooting.
6. **Next steps.** The natural next tutorial, task guide, and API reference.

For example, create `docs/content/docs/getting-started.md` with this **adaptable structure**:

~~~markdown
---
title: "Getting started"
weight: 10
---

# Getting started

**Goal:** Install the project and complete one small, successful task.

## Before you begin

- Supported operating systems and minimum tool versions: [fill in].
- Required permissions and network access: [fill in].
- Time or external resources required: [fill in].

## Install

[Use the actual tested install or build commands here.]
[Say which release, commit, or package repository they use.]

## First successful task

[Supply a small fixture or sample input.]
[Show the exact command or API call that processes it.]

**Expected result:** [Include a realistic, checked output fragment.]

**Verify:** [Show an independent way to confirm the result,
not just "the command exits without an error".]

## If it fails

- [Known failure]: [cause and next action].
- See [Diagnosing a failure](how-to/diagnosing-a-failure/).

## Next

- [How-to guides](how-to/) for real-world tasks.
- [Architecture](concepts/architecture/) for the mental model.
- The Go API reference on pkg.go.dev for exported symbols.
~~~

The bracketed text is intentionally unfinished: **do not publish invented commands as if they were tested**. An agent can propose a draft, but it should run or inspect the real application, check the flags and output, and remove every placeholder before calling the page complete.

A tutorial should go further than getting started, building a progressively richer example with checkpoints. A how-to should do the opposite: assume the reader already knows the basics and solve one specific problem without a long detour.

## 4. Build pages around tasks and explanations

Create `docs/content/docs/how-to/_index.md`:

~~~markdown
---
title: "How-to guides"
weight: 30
---

Each guide solves one task. Start with the desired outcome,
give the prerequisites, then show and verify the steps.
~~~

Then `docs/content/docs/how-to/diagnosing-a-failure.md`:

~~~markdown
---
title: "Diagnosing a failure"
weight: 10
---

# Diagnosing a failure

## When to use this guide

Use this when [a specific observable failure] occurs.

## Capture evidence

1. Record the installed version and platform.
2. Reproduce the problem with the smallest input.
3. Capture the relevant command output or log excerpt.
4. Remove credentials and personal information before sharing.

## Identify the cause

| Symptom | Likely cause | Next check |
| --- | --- | --- |
| [Actual error text] | [Verified explanation] | [Specific command] |

## Fix and verify

[Give a known-good resolution, then repeat the failing operation.]
[Describe what success looks like.]

## Still blocked?

[Link to the issue template, support channel, or known limitation.]
~~~

This is more useful than an agent-created `diagnosis-spec.md` that merely names a hoped-for logging feature. Every line should help someone troubleshoot a real version, and the page should grow as actual failure modes become known.

### Concepts and architecture are explanations, not symbol inventories

Create `docs/content/docs/concepts/_index.md`:

~~~markdown
---
title: "Concepts and architecture"
weight: 40
---

Start here to understand the components, boundaries and
design decisions behind the user-facing workflows.
~~~

Create `docs/content/docs/concepts/architecture.md`:

~~~markdown
---
title: "Architecture"
weight: 10
---

# Architecture

## The problem and overall approach

[What problem is the project designed to solve?
What are the key constraints?]

## Mental model

[Define the three to five concepts readers must understand.]

## Data and control flow

[Describe one request or operation from input to output.
Include a diagram only if it makes the flow clearer.]

## Boundaries and trade-offs

[Who owns state? Where are errors handled?
Which choices were deliberate and what do they cost?]

## Limitations and extension points

[What is unsupported? Where can a contributor add behaviour?]

## Further reading

[Link to the relevant implementation, decision record,
GoDoc package pages, tests and focused how-to guides.]
~~~

A meaningful architecture page explains *why components exist and how they interact*. It does not need an embedded inventory of every struct, method, or file. If a diagram is useful, keep it small and verify it against the implementation; do not generate a vast dependency graph just because a tool can.

Finally create `docs/content/docs/reference/_index.md`:

~~~markdown
---
title: "Reference"
weight: 50
---

Use this section for stable, checkable facts that aren't already
maintained by a more authoritative generator:

- Supported configuration fields and defaults.
- File formats, compatibility and interoperability constraints.
- CLI behaviour, when not generated directly by the program.
- Links to generated API documentation and external standards.

For Go packages, types and functions, follow the pkg.go.dev links.
~~~

Treat hand-written reference data as a liability unless it is tested or generated. For instance, show an annotated configuration with a real example and source link, but do not manually mirror a flag table when the binary can already generate one.

## 5. Preview and inspect the site locally

From the repository root:

~~~sh
git submodule update --init --recursive
hugo server --source docs
~~~

Open the address printed by Hugo (usually `http://localhost:1313/`). Use the sidebar: can a newcomer reach Getting started in one click? Are related tasks grouped together? Do links go to the right page instead of leaving the GitHub Pages project subpath?

Run the release build too:

~~~sh
hugo --source docs --minify
~~~

It should create `docs/public/`. Add `/docs/public/` and `/docs/resources/` to `.gitignore` if they are not already ignored. **Do not commit generated HTML.** Hugo succeeding does not prove every internal link, technical claim, command, or output example is correct. Review the actual published path and test the commands independently.

## 6. Build on pull requests, deploy from main

Configure the repository's **Settings → Pages → Build and deployment** source as **GitHub Actions**. Then add `.github/workflows/docs.yml`. This is a standalone example; integrate the jobs with existing CI where appropriate instead of replacing unrelated test and release jobs.

~~~yaml
name: Developer documentation

on:
  pull_request:
    paths:
      - "docs/**"
      - ".gitmodules"
      - ".github/workflows/docs.yml"
  push:
    branches: [main]
    paths:
      - "docs/**"
      - ".gitmodules"
      - ".github/workflows/docs.yml"
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
          hugo-version: "0.158.0"
          extended: true

      - name: Build and validate the site
        run: hugo --source docs --minify

      - name: Upload Pages artifact
        if: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}
        uses: actions/upload-pages-artifact@v5
        with:
          path: docs/public

  deploy:
    if: ${{ github.event_name != 'pull_request' && github.ref == 'refs/heads/main' }}
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
      - name: Deploy site
        id: deployment
        uses: actions/deploy-pages@v5
~~~

The build is deliberately runnable on a PR, without publishing it. Main builds and deploys the site as a Pages artifact; no `gh-pages` branch, committed site output, or software release is required. The deployment job has the narrow permissions needed by GitHub Pages, while the build job remains read-only.

This example only runs on documentation-related changes. If code changes can invalidate the docs, broaden the PR trigger or run documentation verification in the main test pipeline. For long-lived projects, pin third-party actions to reviewed commit SHAs and update them deliberately.

Do not assume a private repository implies a private Pages website. Review the actual GitHub Pages visibility and access model for your plan and organisation before enabling deployment. Remove secrets, internal hostnames, credentials, and customer data from documentation and history; a draft banner is not access control.

For more on CI permissions and release separation, see my [GitHub Actions reference](/blog/post/2026/043-canonical-github-actions-ci-cd-super-reference/).

## 7. Replace agent-generated spec piles with maintained pages

A developer portal changes what I ask agents to produce. I do not want an agent creating a new `docs/feature-x-spec.md` for every issue and leaving it beside contradictory planning notes. If a change affects people who use, operate, or extend the software, it should normally update the appropriate **existing portal page**.

That is not a reason to throw away every specification. A versioned protocol contract, externally agreed requirement, security policy, or machine-consumed schema may need to remain independently authoritative. The distinction is between an actual contract and a disposable implementation plan masquerading as product documentation.

### An inventory and migration process

1. **Find the existing Markdown.** Identify READMEs, `docs/*.md`, `SPEC.md`, `PLAN.md`, agent outputs, and issue-linked proposals. Find which files are referenced by other people or tools before moving them.
2. **Classify each document.** Is it current behaviour, a tutorial, a proposed feature, an architectural decision, an external contract, or a completed task plan? Check it against source, tests, released versions and open issues.
3. **Extract the useful information.** Put setup steps in Getting started, user tasks in How-to, conceptual models in Concepts, and verified trade-offs in Architecture or a decision record. Move unimplemented work to issues or a clearly labelled roadmap.
4. **Consolidate by reader intent.** Prefer one maintained page per topic over separate `feature-spec-v1.md`, `feature-spec-final.md` and `feature-spec-implementation.md` files. Preserve important decisions and link to their discussions.
5. **Retire safely.** Update incoming links, add redirects if published URLs change, and delete or archive obsolete copies only after their useful contents and contractual status have been accounted for.
6. **Make documentation part of completion.** A feature PR updates the affected user and maintainer guides; reviews check that instructions, screenshots, commands and examples still match reality.

If a design is not settled, use an issue, proposal, or decision record with its **status, alternatives, decision, rationale and date**. Do not bury unresolved plans in a page that appears to describe current behaviour. An accepted decision record explains historical *why*; the main architecture guide explains the *current system*. Both can link to each other.

### A better instruction for coding agents

I would include a short rule in repository agent guidance, along these lines:

> Update the existing developer portal documentation relevant to a change. Write for someone trying to install, use, understand, debug or contribute to the software. Prefer runnable, verified examples and explanations of outcomes and trade-offs. Link to GoDoc for symbol-level API details. Do not create standalone specification or implementation-plan Markdown files unless the task requires a durable, separately reviewed contract or proposal. Identify and reconcile obsolete documentation rather than adding another overlapping copy.

An agent-produced guide is still a draft until it has passed human review and reality checks. The output should not merely narrate what the agent changed; it should help the next person do something with the software. Good examples state expected results, prerequisites, failure cases and supported versions. A useful explanatory page states scope, design constraints, alternatives and consequences.

## 8. Keep the portal useful after the first deployment

The difficult part is maintenance, not Hugo configuration. I use a short documentation review checklist on each relevant PR:

- **Navigation:** Can the intended reader find the page from a task-oriented heading or navigation link?
- **Truthfulness:** Does the page describe merged, usable behaviour? Are experimental or future behaviours visibly marked?
- **Verifiability:** Were commands executed or outputs checked against a real build? Does a clean environment work?
- **Boundaries:** Does the guide explain an outcome or concept rather than duplicate GoDoc, generated CLI help, or source comments?
- **Continuity:** Did the change update existing pages and links, retire stale copies, and preserve decisions and real contracts?
- **Publishing safety:** Does PR CI build without deploying, does main deploy correctly, and is the site safe to make public?

Add spell checking and link checking as the repository matures, but avoid confusing a green static-site build with verified documentation. An inaccurate first-run example is worse than a smaller honest one.

The goal is **not more Markdown**. It is a stable place for human-oriented knowledge: a newcomer can achieve a first result, a user can find a task, and a maintainer can understand the system without deciphering a history of agent-generated plans.