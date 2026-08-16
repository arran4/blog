---
title: "Walking Template Filesystems: walkfs, walkmultifs, and Domain-Owned Templates in Go"
date: 2026-08-16T12:01:00+10:00
draft: false
tags: ["go", "templates", "filesystem", "architecture", "embed"]
categories: ["engineering-process", "reference"]
---

<!-- cspell:words AddParseTree DAG DirFS ExecuteTemplate FuncMap Funcs MapFS OpenGraph ParseFS ValidPath WalkDir funcs fstest goa4web gobookmarks gohtml gotemplate imagetemplates linktemplates namespacing sharedtemplates templatefs walkfs walkmultifs -->

I have ended up using the same small pattern in several Go projects: take an `fs.FS`, recursively walk it, select files of interest, and compile those files into a larger object using stable names derived from their paths.

In [goa4web](https://github.com/arran4/goa4web), the current HTML template loader in [`core/templates/templates.go`](https://github.com/arran4/goa4web/blob/main/core/templates/templates.go) is one example. It uses `fs.WalkDir` to discover `*.gohtml` files and parses them into one `html/template.Template` set. A similar recursive helper exists in [gobookmarks](https://github.com/arran4/gobookmarks/blob/main/template_utils.go).

There is not currently an API in goa4web literally called `walkfs`. I am using **walkfs** as a name for the recurring pattern, and **walkmultifs** for its natural extension: assembling files contributed by several independent `fs.FS` values.

The code is small. The interesting part is getting the ownership, naming, collision and dependency rules right.

This article uses goa4web as motivation, not as the architecture to copy exactly. If I were implementing the pattern fresh, I would make the generic implementation stricter than the current code.

## Start with the standard library

The useful primitives already exist:

- `fs.FS` is the filesystem boundary.
- `fs.Sub` selects a subtree when necessary.
- `fs.WalkDir` gives recursive discovery over any `fs.FS`.
- `go:embed` produces an embedded filesystem without changing the consumer.
- `html/template` provides the template namespace and contextual escaping.
- `fstest.MapFS` makes the same code easy to test.

That means I would not start by inventing a filesystem framework or a domain registration interface.

The compiler can accept `fs.FS` directly. The standard-library interface is already the abstraction.

## Why walk rather than only use `ParseFS`?

`html/template.ParseFS` is the first thing to consider, and for a small fixed tree it may be all that is needed.

A manual walk becomes useful when discovery itself has policy attached to it:

- recurse to arbitrary depth,
- preserve relative paths as names instead of relying on base filenames,
- filter files,
- attach source provenance to errors,
- enforce namespace ownership,
- reject collisions rather than accepting load-order behaviour,
- compose several independently owned filesystems.

That last point matters once templates move next to the code that owns them.

For example:

```text
internal/links/
    service.go
    worker/
        fetch.go
    web/
        handler.go
        templates/
            embed.go
            card.gohtml
            edit.gohtml

internal/images/
    service.go
    web/
        handler.go
        templates/
            embed.go
            image.gohtml
```

The exact directory names are not important. What matters is that a links template can be owned by the links web adapter without forcing every template file back into one application-wide directory.

## The tempting implementation is not quite strong enough

A first extraction of the existing pattern might look like this:

```go
func WalkHTML(root *template.Template, namespace string, fsys fs.FS) error {
    return fs.WalkDir(fsys, ".", func(p string, d fs.DirEntry, err error) error {
        if err != nil {
            return err
        }
        if d.IsDir() || path.Ext(p) != ".gohtml" {
            return nil
        }

        b, err := fs.ReadFile(fsys, p)
        if err != nil {
            return err
        }

        name := path.Join(namespace, p)
        if root.Lookup(name) != nil {
            return fmt.Errorf("duplicate template %q", name)
        }

        _, err = root.New(name).Parse(string(b))
        return err
    })
}
```

That catches a duplicate **file-derived** name, but Go templates have a second namespace hidden inside the file contents.

This file:

```text
links/card.gohtml
```

can contain:

```gotemplate
{{ define "links/card" }}
    ...
{{ end }}
```

The file template and the explicit definition are different associated templates. Another file can define `links/card` too. Parsing directly into the shared destination makes it harder to prove which source owned which resulting name, and the template APIs support replacement/overlay use cases where later parse trees can replace earlier definitions.

For domain composition I want the opposite default: **a duplicate owner is an error**.

So the stronger implementation parses each file in isolation first, inspects the resulting template names, validates ownership, and only then merges it into the final set.

## A stricter `templatefs` compiler

I would keep the public API small:

```go
package templatefs

import (
    "fmt"
    "html/template"
    "io/fs"
    "path"
    "sort"
    "strings"
)

type Source struct {
    Namespace string
    FS        fs.FS
}

type origin struct {
    Namespace string
    File      string
}

func Compile(funcs template.FuncMap, sources ...Source) (*template.Template, error) {
    out := template.New("root").Funcs(funcs)

    owners := map[string]origin{}
    namespaces := map[string]struct{}{}

    for _, src := range sources {
        if err := validateSource(src); err != nil {
            return nil, err
        }
        if _, exists := namespaces[src.Namespace]; exists {
            return nil, fmt.Errorf("duplicate template namespace %q", src.Namespace)
        }
        namespaces[src.Namespace] = struct{}{}

        err := fs.WalkDir(src.FS, ".", func(p string, d fs.DirEntry, walkErr error) error {
            if walkErr != nil {
                return fmt.Errorf("walk %s:%s: %w", src.Namespace, p, walkErr)
            }
            if d.IsDir() || path.Ext(p) != ".gohtml" {
                return nil
            }

            b, err := fs.ReadFile(src.FS, p)
            if err != nil {
                return fmt.Errorf("read %s:%s: %w", src.Namespace, p, err)
            }

            fileName := path.Join(src.Namespace, p)
            parsed, err := template.New(fileName).Funcs(funcs).Parse(string(b))
            if err != nil {
                return fmt.Errorf("parse %s:%s: %w", src.Namespace, p, err)
            }

            candidates := parsed.Templates()
            sort.Slice(candidates, func(i, j int) bool {
                return candidates[i].Name() < candidates[j].Name()
            })

            for _, candidate := range candidates {
                if candidate.Tree == nil {
                    continue
                }

                name := candidate.Name()
                if !fs.ValidPath(name) || !strings.HasPrefix(name, src.Namespace+"/") {
                    return fmt.Errorf(
                        "%s:%s defines template %q outside path namespace %q",
                        src.Namespace,
                        p,
                        name,
                        src.Namespace,
                    )
                }

                if previous, exists := owners[name]; exists {
                    return fmt.Errorf(
                        "template %q defined by both %s:%s and %s:%s",
                        name,
                        previous.Namespace,
                        previous.File,
                        src.Namespace,
                        p,
                    )
                }

                if _, err := out.AddParseTree(name, candidate.Tree); err != nil {
                    return fmt.Errorf("add template %q from %s:%s: %w", name, src.Namespace, p, err)
                }

                owners[name] = origin{
                    Namespace: src.Namespace,
                    File:      p,
                }
            }

            return nil
        })
        if err != nil {
            return nil, err
        }
    }

    return out, nil
}

func validateSource(src Source) error {
    if src.FS == nil {
        return fmt.Errorf("template namespace %q has a nil filesystem", src.Namespace)
    }
    if src.Namespace == "" || src.Namespace == "." || !fs.ValidPath(src.Namespace) {
        return fmt.Errorf("invalid template namespace %q", src.Namespace)
    }
    return nil
}
```

This is still deliberately small. It is mostly standard library glue.

The important difference from a direct shared parse is that every name is checked **before** it is admitted to the final namespace.

A file can therefore contain:

```gotemplate
{{ define "links/card" }}
    ...
{{ end }}
```

but this is rejected:

```gotemplate
{{ define "card" }}
    ...
{{ end }}
```

and so is a second definition of `links/card` from another file.

The path validation also rejects names such as `links/../shared/pager`; the namespace rule is path-like rather than a raw string-prefix convention.

The source namespace is not just decoration; it is an ownership rule.

## Why parse one file at a time?

There are two reasons.

First, the filename itself gets a stable namespaced identity such as:

```text
links/pages/edit.gohtml
```

Second, explicit `define` or `block` declarations created while parsing that file can be attributed to the same source file before anything is merged globally.

Parsing an entire source into one temporary shared set would improve isolation between domains, but it could still allow later files within that source to replace names established by earlier files. Per-file isolation plus an explicit ownership map closes that hole too.

The compiler is now capable of answering a useful error precisely:

```text
template "links/card" defined by both links:card.gohtml and links:partials/card.gohtml
```

That is considerably better than discovering at runtime that a different definition happened to win.

## `walkmultifs` is composition, not a union filesystem

At this point `walkmultifs` does not need to be a new implementation at all. It is simply the fact that `Compile` accepts several sources:

```go
tmpl, err := templatefs.Compile(funcs,
    templatefs.Source{
        Namespace: "shared",
        FS:        sharedtemplates.FS(),
    },
    templatefs.Source{
        Namespace: "links",
        FS:        linktemplates.FS(),
    },
    templatefs.Source{
        Namespace: "images",
        FS:        imagetemplates.FS(),
    },
)
```

I prefer this to making the sources pretend to be one `fs.FS`.

A union filesystem has to invent precedence rules for duplicate paths, merged directory listings and file-versus-directory conflicts. Those semantics are useful when implementing an **override** filesystem, but they are not the semantics I want for independent domains.

For domain composition, a duplicate owner should normally fail.

For overrides, precedence should be intentional and implemented one layer earlier.

That gives two separate concepts:

```text
overlay FS      = which physical file a source exposes
source compiler = which sources contribute templates
```

Those should not be conflated merely because both involve more than one filesystem.

## Let the resource package stay a leaf

`go:embed` is package-local, which fits this structure well.

A template resource package can be almost empty:

```go
package templates

import (
    "embed"
    "io/fs"
)

//go:embed *.gohtml
var embedded embed.FS

func FS() fs.FS {
    return embedded
}
```

It does not import its parent handler package. Directory nesting does not imply an import relationship in Go.

For example, these are independent packages:

```text
internal/links/web
internal/links/web/templates
```

The templates package can remain a leaf that knows only about `embed` and `io/fs`.

I also would not introduce this interface just because it is possible:

```go
type TemplateSource interface {
    FS() fs.FS
}
```

The compiler only needs an `fs.FS`, so accepting `fs.FS` is simpler. If a second behaviour eventually appears, an interface can be introduced by the consumer then.

## Keep the composition root above the domains

The final executable, or another application-composition package near it, is the right place to know which domains exist.

A useful dependency graph is:

```text
                    cmd/application
                   /      |       \
                  v       v        v
             links/web  images/web  templatefs
                |           |
                v           v
              links       images

cmd/application
    -> links/web/templates
    -> images/web/templates
    -> shared/templates
```

The arrows all point one way.

The generic compiler does **not** import the domain packages. The domains do **not** import the composition package. The composition package imports the pieces and passes values between them.

That is the important Go property: the dependency graph stays a DAG.

## FAQ: won't this create import loops?

Not if ownership and composition are kept separate.

This is safe:

```text
application
    -> links/web
    -> links/web/templates
    -> templatefs

links/web
    -> links

links/web/templates
    -> embed/io/fs
```

This is not:

```text
links/web
    -> application templates
    -> links/web
```

Nor is this:

```text
common
    -> template compiler
    -> common
```

The usual cure is not a registry or `init()` hook. It is to move assembly upward and pass the completed dependency downward.

If a handler needs to render templates, the simplest option is often to give it the compiled `*template.Template`.

If tests or multiple rendering implementations make an interface useful, define the small interface on the **consumer** side:

```go
type Renderer interface {
    ExecuteTemplate(io.Writer, string, any) error
}
```

`*template.Template` already satisfies that shape.

I would not add the interface solely to say that dependency injection is happening. Passing a concrete value is also dependency injection.

### A goa4web-specific example

The current goa4web code has a concrete version of this concern: `core/common.GetTemplateFuncs` imports `core/templates` because its custom `include` helper calls back into template compilation.

That is useful existing behaviour, but it is not a pattern I would recommend copying into a fresh design. I logged [goa4web issue #3066](https://github.com/arran4/goa4web/issues/3066) to track separating that reverse dependency from template compilation.

For a new implementation, I would first ask whether a custom `include` function is needed at all.

Go templates already have template association and the built-in actions:

```gotemplate
{{ template "shared/pager" . }}
```

and:

```gotemplate
{{ block "shared/content" . }}
    ... default content ...
{{ end }}
```

Those are preferable when the requirement is simply to render another associated template. They do not require application code to rediscover or recompile the template set.

Only if function-like rendering semantics are genuinely required would I inject a renderer/provider rather than using the built-in template actions.

## Template functions need the same discipline

Template names are not the only global namespace. Function names are global to the template set too.

`Funcs` must be registered before parsing templates which refer to those function names, so the composition root should construct the function map **before** calling `Compile`.

If several domains contribute functions, merge those maps explicitly and reject duplicate names rather than silently deciding that one domain wins.

For example, prefer recognisably owned names:

```text
assetURL
linksURL
imageURL
formatLocalTime
```

rather than letting unrelated packages each register a generic name such as `url`.

There is also a lifetime issue. A compiled template set is normally application-scoped and executed concurrently. Functions captured into it should therefore be safe for that lifetime.

Request-specific state is usually better passed in the execution data/view model than captured into a template function while compiling the application template set.

That keeps the useful lifecycle simple:

```text
startup:
    construct stable FuncMap
    compile templates
    construct handlers

request:
    construct view data
    ExecuteTemplate
```

Go's template implementation is designed around this shape: construction happens before serving, then the constructed templates can be executed concurrently.

## Compile once, execute many

I would treat template compilation as startup work unless runtime editing is an explicit application feature.

That means:

1. build the complete function map,
2. construct effective filesystems,
3. compile and validate every source,
4. fail startup if any template is invalid or collides,
5. pass the completed template set to handlers,
6. execute it concurrently without mutating it.

This moves failures from user requests to process startup and makes the dependency graph much easier to understand.

It also avoids a subtle anti-pattern where a helper recompiles templates while a template is already being executed.

## Runtime overrides remain possible

Embedded ownership does not require giving up runtime template overrides.

Suppose the embedded sources are:

```text
shared
links
images
```

A development directory can mirror that logical layout:

```text
templates/
    shared/
    links/
    images/
```

If runtime configuration replaces a whole source, composition can simply choose a different `fs.FS`:

```go
linksFS := linktemplates.FS()
if cfg.TemplateDir != "" {
    linksFS = os.DirFS(filepath.Join(cfg.TemplateDir, "links"))
}
```

If the requirement is **partial** override with embedded fallback, that is where an overlay filesystem is appropriate:

```text
runtime links FS
       |
       v
embedded links FS
       |
       v
one effective links source
```

Then that one effective source is passed to `templatefs.Compile`.

My [go-subcommand overlay filesystem](https://github.com/arran4/go-subcommand/blob/main/overlay_template_fs.go) is an example of the different problem: overlay semantics intentionally have precedence. Domain composition should not inherit those semantics accidentally.

## Namespaces should include explicit definitions

With this compiler, filenames and explicit definitions follow the same ownership rule.

A links source might contain:

```text
card.gohtml
pages/edit.gohtml
```

which creates file-derived names:

```text
links/card.gohtml
links/pages/edit.gohtml
```

and the contents can define components such as:

```gotemplate
{{ define "links/card" }}...{{ end }}
{{ define "links/edit-form" }}...{{ end }}
```

Shared pieces belong in a shared source:

```gotemplate
{{ define "shared/pager" }}...{{ end }}
```

A links file defining `shared/pager` is rejected. If it really is shared, move ownership to shared templates instead of allowing an implicit cross-domain overwrite.

This gives template names the same kind of useful signal as Go package names: the name tells me where ownership should live.

## Cross-source references are still fine

Isolation during parsing does not mean isolation during execution.

A shared layout can refer to a domain template by name:

```gotemplate
{{ template "links/card" .Link }}
```

and a links page can use a shared component:

```gotemplate
{{ template "shared/pager" .Pager }}
```

The compiler merges all accepted parse trees into one associated template set before anything is executed.

The boundary controls **who may define a name**, not who may invoke it.

That distinction is important. Namespacing prevents accidental ownership collisions without preventing deliberate composition.

## Testing the pattern

This design is easy to test without touching the host filesystem.

`fstest.MapFS` can construct sources such as:

```go
links := fstest.MapFS{
    "card.gohtml": {
        Data: []byte(`{{ define "links/card" }}card{{ end }}`),
    },
}
```

I would have tests for at least:

- recursive discovery,
- stable file-derived names,
- valid namespaced `define` declarations,
- a definition outside its source namespace,
- duplicate explicit definitions in two files,
- duplicate source namespaces,
- parse errors with source and filename in the error,
- cross-source `{{ template }}` calls,
- a complete application compile using the production source list,
- representative renders of top-level templates.

The compile tests prove ownership and syntax. Render tests catch missing referenced templates and data-contract mistakes that a filesystem walker cannot prove by itself.

For runtime overlays, test the overlay filesystem separately. That keeps precedence tests out of the domain-composition tests.

## A migration path for an existing application

For an existing monolith I would not start by moving files.

A safer sequence is:

1. Identify the current recursive loading behaviour and capture it in tests.
2. Introduce the strict compiler while still pointing it at the existing central filesystem.
3. Register all template functions before compilation and remove any reverse dependency that recompiles templates from inside a template helper.
4. Establish namespace rules and fix ambiguous `define` names.
5. Add full-production compile and representative render tests.
6. Move one small domain's templates into a leaf resource package.
7. Compose that source explicitly at the application root.
8. Preserve runtime override behaviour by choosing or overlaying the effective filesystem before compilation.
9. Repeat domain by domain.

For goa4web specifically, issue [#3066](https://github.com/arran4/goa4web/issues/3066) tracks the reverse `common -> templates` concern independently of this article. The article should remain valid even if goa4web eventually chooses a different internal package layout.

## What I would avoid

I would avoid a few attractive shortcuts.

### Package self-registration through `init()`

A global registry lets packages appear to register their templates automatically, but it hides the application's dependency list and makes alternate assemblies and tests harder to understand.

Explicit composition is only a few lines and keeps imports visible.

### A central template package that imports every domain

That often recreates the dependency cycle problem in a different directory.

The application composition layer is allowed to know every component. A low-level template compiler should not.

### Last-one-wins domain collisions

Replacement is useful for deliberate overlays. It is a poor default for two independent domain owners claiming the same template name.

Fail early instead.

### An interface around `fs.FS` merely for architecture's sake

`fs.FS` is already the consumer boundary. Keep it until another behaviour genuinely needs abstraction.

### Request-scoped template compilation

If templates are application resources, compile them once. Pass request state as data and keep the compiled set immutable while serving.

## The architectural point

The implementation is still small.

The stronger model is:

```text
domain resource packages
        |
        v
   standard fs.FS values
        |
        v
strict template compiler
        |
        v
one immutable associated template set
        |
        v
handlers receive the finished renderer
```

`walkfs` is recursive discovery over an abstract filesystem.

`walkmultifs` is explicit composition of several independently owned sources.

The important part is not inventing a clever multi-filesystem object. It is preserving ownership while assembling one runtime template namespace, and doing so with normal Go tools: `fs.FS`, `go:embed`, `html/template`, explicit imports, startup composition, and small consumer-side dependencies where they are actually useful.

That is the version of the pattern I would want to copy into a new Go project.

## References

- [goa4web `core/templates/templates.go`](https://github.com/arran4/goa4web/blob/main/core/templates/templates.go)
- [goa4web `core/common.GetTemplateFuncs`](https://github.com/arran4/goa4web/blob/main/core/common/funcs.go)
- [goa4web issue #3066: decouple template include helpers from template compilation](https://github.com/arran4/goa4web/issues/3066)
- [goa4web template loading specification](https://github.com/arran4/goa4web/blob/main/specs/templates.md)
- [gobookmarks recursive template parser](https://github.com/arran4/gobookmarks/blob/main/template_utils.go)
- [go-subcommand overlay template filesystem](https://github.com/arran4/go-subcommand/blob/main/overlay_template_fs.go)
- [Go `io/fs`](https://pkg.go.dev/io/fs)
- [Go `fs.WalkDir`](https://pkg.go.dev/io/fs#WalkDir)
- [Go `html/template`](https://pkg.go.dev/html/template)
- [Go `Template.Funcs`](https://pkg.go.dev/html/template#Template.Funcs)
- [Go `Template.AddParseTree`](https://pkg.go.dev/html/template#Template.AddParseTree)
- [Go `Template.Templates`](https://pkg.go.dev/html/template#Template.Templates)
- [Go `testing/fstest`](https://pkg.go.dev/testing/fstest)
