---
title: "Walking Template Filesystems: walkfs, walkmultifs, and Domain-Owned Templates in Go"
date: 2026-08-16T11:15:04+10:00
draft: false
tags: ["go", "templates", "filesystem", "architecture", "embed"]
categories: ["engineering-process", "reference"]
---

<!-- cspell:words walkfs walkmultifs goa4web gobookmarks -->

I have ended up using the same small pattern in several Go projects: take an `fs.FS`, recursively walk it, select files of interest, read them, and add them to a larger object using their relative paths as stable names.

In [goa4web](https://github.com/arran4/goa4web), the most interesting example is the HTML template loader in [`core/templates/templates.go`](https://github.com/arran4/goa4web/blob/main/core/templates/templates.go). The code uses `fs.Sub` to select the `site` tree, `fs.WalkDir` to recursively discover `*.gohtml` files, and then explicitly creates each template using its relative path as the template name.

There is not currently a function or package in goa4web literally called `walkfs`. I am using **walkfs** here as a name for that recurring pattern because I think it is worth making explicit.

The question becomes more interesting if a monolithic application is reorganised around domains. If links, images, forums, subscriptions, users and other areas begin owning their handlers, workers, database-facing code and templates, then there is no longer one filesystem containing all templates. The natural extension is what I will call **walkmultifs**: walk several independent filesystems into one logical template namespace.

That sounds like a tiny implementation detail. It is actually a useful architectural boundary.

## The existing goa4web pattern

The current site template loader is roughly this:

```go
fsys := getFS("site", cfg)
root := template.New("root").Funcs(funcs)

err := fs.WalkDir(fsys, ".", func(p string, d fs.DirEntry, err error) error {
    if err != nil {
        return err
    }
    if d.IsDir() || filepath.Ext(p) != ".gohtml" {
        return nil
    }

    b, err := fs.ReadFile(fsys, p)
    if err != nil {
        return err
    }

    _, err = root.New(p).Parse(string(b))
    return err
})
```

The actual implementation also handles embedded-versus-development filesystems, template functions and caching, but the important part is the walk.

This is subtly different from treating templates as a bag of strings.

The path is useful data.

If the filesystem contains:

```text
pages/article.gohtml
pages/forum.gohtml
partials/header.gohtml
partials/post.gohtml
```

then those names can remain:

```text
pages/article.gohtml
pages/forum.gohtml
partials/header.gohtml
partials/post.gohtml
```

inside the template set.

That gives templates a stable namespace which follows the source tree. It also means two `index.gohtml` files can coexist if they live in different directories.

The same basic pattern appears in my [gobookmarks `ParseFSRecursive`](https://github.com/arran4/gobookmarks/blob/main/template_utils.go). That helper recursively walks an `fs.FS`, filters by extension, derives the path relative to a base directory and calls `t.New(name).Parse(...)`.

So this is not really a goa4web-specific trick. It is a small reusable Go pattern.

## Why walk instead of only using `ParseFS`?

Go's `html/template` and `text/template` packages already have `ParseFS`, and it is excellent when the files to parse can be described cleanly by a small set of patterns.

The manual walk becomes useful when I want more control over discovery and naming:

- arbitrary recursive directory depth,
- filtering based on extension or directory,
- an explicitly controlled template name,
- logging the originating filesystem,
- collision detection,
- mixing embedded and runtime filesystems,
- composing files owned by several packages.

The important point is not that `ParseFS` is inadequate. It is that once file discovery itself becomes part of the application's composition model, `fs.WalkDir` is a clearer abstraction point.

## Extracting the pattern as `walkfs`

Before moving templates between packages, I would first extract the current behaviour without changing ownership.

A generic helper could look like this:

```go
package templatefs

import (
    "fmt"
    "html/template"
    "io/fs"
    "path"
    "strings"
)

type Source struct {
    Name   string
    FS     fs.FS
    Root   string
    Prefix string
}

func WalkHTML(root *template.Template, src Source) error {
    fsys := src.FS
    if src.Root != "" && src.Root != "." {
        var err error
        fsys, err = fs.Sub(fsys, src.Root)
        if err != nil {
            return fmt.Errorf("sub filesystem %s: %w", src.Name, err)
        }
    }

    return fs.WalkDir(fsys, ".", func(p string, d fs.DirEntry, err error) error {
        if err != nil {
            return err
        }
        if d.IsDir() || !strings.HasSuffix(p, ".gohtml") {
            return nil
        }

        b, err := fs.ReadFile(fsys, p)
        if err != nil {
            return fmt.Errorf("read %s:%s: %w", src.Name, p, err)
        }

        rel := strings.TrimPrefix(p, "./")
        name := path.Join(src.Prefix, rel)

        if root.Lookup(name) != nil {
            return fmt.Errorf("template %q already exists before loading %s", name, src.Name)
        }

        if _, err := root.New(name).Parse(string(b)); err != nil {
            return fmt.Errorf("parse %s:%s as %q: %w", src.Name, p, name, err)
        }
        return nil
    })
}
```

This is intentionally boring.

That is a feature. The current loader is doing useful work, but the walking behaviour does not need to know anything about HTTP handlers, links, forums or the application configuration. It can become a low-level dependency.

The first refactor can therefore be:

```text
current central template tree
            |
            v
      templatefs.WalkHTML
```

with no directory movement at all.

Once that is tested, moving ownership becomes much less risky.

## From `walkfs` to `walkmultifs`

The simplest implementation of `walkmultifs` is almost disappointingly small:

```go
func WalkMultiHTML(root *template.Template, sources ...Source) error {
    for _, src := range sources {
        if err := WalkHTML(root, src); err != nil {
            return err
        }
    }
    return nil
}
```

Conceptually, however, this changes the model from:

```text
one application
    -> one template filesystem
        -> one template set
```

to:

```text
shared templates -----\
links templates -------\
images templates -------+--> one compiled template set
forum templates --------/
subscription templates -/
```

The domains keep ownership of the files. The application composition layer decides which domains are assembled into the running application.

That is much closer to how I want a domain-oriented Go application to behave.

## A possible domain layout

Suppose external links become a real domain instead of being primarily a handler directory. A layout might be:

```text
internal/links/
    service.go
    model.go
    worker/
        fetch.go
    db/
        queries.go
    handler/
        routes.go
        pages.go
        templates/
            embed.go
            card.gohtml
            edit.gohtml
```

Images could independently become:

```text
internal/images/
    service.go
    worker/
    handler/
        routes.go
        templates/
            embed.go
            image.gohtml
```

The exact directories are less important than the dependency direction.

The link worker should not import the HTTP handler package just to get at some shared implementation. The event bus should not need to know about handlers. HTTP handling, background work and persistence can all depend inward on the links domain.

Templates are slightly unusual because they belong to the HTTP presentation adapter but must eventually be composed into one global `html/template.Template`.

That is precisely where `walkmultifs` helps.

## `go:embed` makes ownership local

There is an important practical constraint here: `//go:embed` patterns are relative to the package containing the directive. They cannot reach arbitrarily upward through `..` into other packages.

If templates live here:

```text
internal/links/handler/templates/
```

then an embed declaration should also live in or above that directory within the same package tree, for example:

```go
package templates

import (
    "embed"
    "io/fs"
)

//go:embed *.gohtml
a4
var embedded embed.FS

func FS() fs.FS {
    return embedded
}
```

In real code the stray `a4` above should of course not exist; the declaration is simply:

```go
//go:embed *.gohtml
var embedded embed.FS
```

I have left the corrected form separately because the important part is the package boundary: the package that owns the resources embeds them and exposes an `fs.FS`, rather than a central templates package reaching into every domain.

This is already consistent with patterns inside goa4web. [`handlers/forum/static.go`](https://github.com/arran4/goa4web/blob/main/handlers/forum/static.go) embeds the forum's JavaScript and CSS next to the forum handler, while [`internal/faq_templates/embed.go`](https://github.com/arran4/goa4web/blob/main/internal/faq_templates/embed.go) owns its own embedded text resources.

HTML templates can follow the same ownership model.

## Keep composition above the domains

A trap would be to replace one central dependency problem with another.

For example, this looks convenient:

```go
package templates

import (
    "example/internal/images/handler/templates"
    "example/internal/links/handler/templates"
)
```

but now the central templates package knows every domain in the application. If a handler also imports helpers from that central package, it is easy to create cycles or make the dependency graph confusing.

A cleaner split is:

```text
internal/templatefs
    generic walking/parsing only

internal/links/handler/templates
    owns link templates

internal/images/handler/templates
    owns image templates

cmd/goa4web (or another application composition package)
    imports the domains and templatefs
    assembles the final template set
```

In code:

```go
root := template.New("root").Funcs(funcs)

err := templatefs.WalkMultiHTML(root,
    templatefs.Source{
        Name:   "shared",
        FS:     sharedtemplates.FS(),
        Prefix: "shared",
    },
    templatefs.Source{
        Name:   "links",
        FS:     linktemplates.FS(),
        Prefix: "links",
    },
    templatefs.Source{
        Name:   "images",
        FS:     imagetemplates.FS(),
        Prefix: "images",
    },
)
```

The composition root is allowed to know that the application contains links and images. The low-level template walker is not.

This distinction becomes more valuable as the same domain starts owning more pieces:

```text
links
  domain/service
  db adapter
  HTTP adapter
  worker adapter
  template resources
```

instead of keeping those pieces distributed across unrelated global directories.

## Do we actually need a merged `fs.FS`?

Probably not at first.

There are two different things that can be called a multi-filesystem abstraction.

The first is a **union filesystem**: several filesystems are presented as though they were one `fs.FS`. If the same path exists in multiple inputs, some precedence rule decides which file wins.

The second is a **multi-source walker**: walk each filesystem independently and load the results into one destination namespace.

For templates I prefer the second model initially.

A union filesystem has to answer questions such as:

- How are directory listings merged?
- Which source wins if both contain `partials/header.gohtml`?
- Does `Open` use first-match or last-match precedence?
- What happens when one source contains a file where another contains a directory?
- How are errors distinguished from a simple miss?

Those are valid questions when overrides are the purpose of the abstraction. My [`go-subcommand` overlay filesystem](https://github.com/arran4/go-subcommand/blob/main/overlay_template_fs.go) is an example: it deliberately checks the overlay first, falls back to the base filesystem, and merges directory entries.

Domain composition has a different default requirement. A collision is more likely to be a mistake than an override.

So `walkmultifs` should initially fail on collisions instead of silently defining precedence.

## Namespacing should be explicit

If every domain has a template called:

```text
edit.gohtml
```

then simply walking several roots into the same namespace will collide.

There are three possible policies:

1. **Require globally unique relative paths.**
2. **Prefix every source with a domain name.**
3. **Allow ordered override semantics.**

For domain-owned templates I prefer explicit prefixes:

```text
shared/layout.gohtml
links/edit.gohtml
links/card.gohtml
images/edit.gohtml
forum/thread.gohtml
```

That makes ownership visible at execution time too:

```go
t.ExecuteTemplate(w, "links/edit.gohtml", data)
```

This is better than relying on load order to decide which `edit.gohtml` happens to win.

Shared layout templates can deliberately live under a shared namespace.

## File names are not the only template namespace

There is one extra complication with Go templates.

A file named:

```text
links/card.gohtml
```

can contain:

```gotemplate
{{ define "card" }}
...
{{ end }}
```

That definition enters the same template set under the name `card`. Prefixing the filename alone does not turn it into `links/card`.

So a multi-domain template design also needs a convention for explicit `define` names.

For example:

```gotemplate
{{ define "links/card" }}
...
{{ end }}
```

or, for truly shared components:

```gotemplate
{{ define "shared/pager" }}
...
{{ end }}
```

I would add tests which compile the complete production template set and fail when unexpected duplicate names appear. goa4web already has template compilation and name-related tests, so this is a natural extension rather than a new testing style.

## Runtime template overrides are the hard part

The current goa4web design supports two sources for templates:

1. embedded templates in the binary,
2. a runtime `--templates-dir`/`TEMPLATES_DIR` filesystem for development and customisation.

This is documented in [`specs/templates.md`](https://github.com/arran4/goa4web/blob/main/specs/templates.md), and it is an important capability to preserve.

Centralising every embedded template happens to make runtime replacement simple because one directory mirrors one embedded tree.

With domain-owned templates, the application instead needs to map the runtime tree back onto its sources.

One option is to keep a virtual external layout such as:

```text
templates/
    shared/
    links/
    images/
    forum/
```

and construct each source from either:

```text
embedded domain FS
```

or:

```text
os.DirFS("templates/links")
```

Another option is a per-domain overlay:

```text
runtime override FS
        |
        v
embedded domain FS
```

followed by `walkmultifs` across the resulting domain filesystems.

That separates two concepts cleanly:

```text
overlay = where a domain gets a file from
walkmultifs = which domains contribute templates
```

I would not combine those into one magical filesystem abstraction unless there is a strong need.

## The same model applies beyond templates

This is why the filesystem abstraction interests me more than the template parser itself.

A domain can expose resources through narrow interfaces:

```go
type TemplateSource interface {
    FS() fs.FS
}
```

or, more simply, just return an `fs.FS`.

The caller does not need to know whether the files are:

- embedded,
- on disk,
- generated for a test,
- stored in `fstest.MapFS`,
- overlaid for development.

That follows the same principle I described in [Go FSs Everywhere: Treat Side Effects as Dependencies](../007-Go-FSs-Everywhere/): use filesystem interfaces as boundaries so the implementation can change without rewriting the consumer.

`walkfs` is the consumer-side half of that idea. It takes an abstract filesystem seriously instead of immediately converting the problem back into operating-system paths.

## A migration path for goa4web

I would not begin a domain refactor by moving every template at once. The safer sequence is:

1. Extract the existing recursive parser into a generic `walkfs`-style helper.
2. Add tests for recursive discovery, relative naming, bad templates and duplicate names.
3. Make the existing central template loader use that helper with no behavioural change.
4. Generalise the helper to accept several named sources: `walkmultifs`.
5. Define an explicit naming and collision policy.
6. Move one small domain's templates as a pilot.
7. Preserve runtime override behaviour for that domain.
8. Only then repeat the move for other domains.

External links would be a reasonable pilot because the surrounding code is already a candidate for stronger domain separation: HTTP actions and background OpenGraph fetching should not need to be one architectural unit merely because they both operate on links.

The target does not have to be doctrinaire. Shared templates can remain shared. Generic layouts, navigation and application-wide error pages are legitimately application-level resources.

The useful rule is:

> If a template only makes sense because a domain exists, the domain should be able to own it. If a template describes the shell of the whole application, the application can own it.

`walkmultifs` lets those two kinds of ownership coexist in one compiled Go template set.

## What I would avoid

I would avoid three shortcuts.

First, I would not make every domain register itself through `init()` into a global template registry. That hides dependencies and makes tests and alternate application assemblies harder to reason about.

Second, I would not make the generic template package import every domain. The application composition layer should do that wiring.

Third, I would not make collisions implicitly last-one-wins unless implementing an intentional override layer. Domain composition should be deterministic and preferably fail loudly when two owners claim the same name.

## The architectural point

The code for `walkmultifs` might only be a loop around `walkfs`.

The important change is what the loop means.

A central filesystem says:

```text
all templates belong to the application template package
```

A list of filesystem sources says:

```text
each component owns its resources;
the application decides how components are assembled
```

That is a much better fit for a codebase moving toward domain ownership.

It also avoids solving the problem by physically centralising files that are conceptually local. Links can own link templates. Forums can own forum assets. Workers can operate on domain services without importing handlers. The final executable remains responsible for integration.

In that model, `walkfs` is a useful little mechanism and `walkmultifs` is mostly composition policy.

That is exactly the sort of abstraction I like: small enough to understand completely, but placed at a boundary where it removes a much larger architectural constraint.

## References

- [goa4web `core/templates/templates.go`](https://github.com/arran4/goa4web/blob/main/core/templates/templates.go)
- [goa4web template extraction/walking code](https://github.com/arran4/goa4web/blob/main/core/templates/extract.go)
- [goa4web template loading specification](https://github.com/arran4/goa4web/blob/main/specs/templates.md)
- [goa4web forum-local embedded assets](https://github.com/arran4/goa4web/blob/main/handlers/forum/static.go)
- [goa4web FAQ-local embedded templates](https://github.com/arran4/goa4web/blob/main/internal/faq_templates/embed.go)
- [gobookmarks recursive template parser](https://github.com/arran4/gobookmarks/blob/main/template_utils.go)
- [go-subcommand overlay template filesystem](https://github.com/arran4/go-subcommand/blob/main/overlay_template_fs.go)
- [Go `io/fs.WalkDir`](https://pkg.go.dev/io/fs#WalkDir)
- [Go `html/template`](https://pkg.go.dev/html/template)
