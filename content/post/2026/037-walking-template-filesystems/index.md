---
title: "Walking Template Filesystems: walkfs, walkmultifs, and Domain-Owned Templates in Go"
date: 2026-08-16T12:23:18+10:00
draft: false
tags: ["go", "templates", "filesystem", "architecture", "embed"]
categories: ["engineering-process", "reference"]
---

<!-- cspell:words AddParseTree DAG DirFS ExecuteTemplate FuncMap Funcs MapFS ParseFS ValidPath WalkDir funcs fstest gohtml gotemplate imagetemplates linktemplates namespacing sharedtemplates templatefs walkfs walkmultifs -->

A useful Go pattern appears whenever files are part of application composition rather than merely data on disk: accept an `fs.FS`, recursively discover files, give them stable logical names, validate them, and assemble them into a larger runtime object.

For HTML templates, I will call the single-filesystem form **walkfs** and the multi-source form **walkmultifs**.

The walking code itself is small. The interesting part is getting the Go design around it right: ownership, package dependencies, template namespaces, collision handling, runtime overrides, function maps, testing, and application lifecycle.

This article builds that design from first principles. The goal is not the shortest possible loader, but the version of the pattern I would want copied into a new Go codebase.

## Start with the standard library

The useful primitives already exist:

- `fs.FS` is the filesystem boundary.
- `fs.Sub` selects a subtree when necessary.
- `fs.WalkDir` gives recursive discovery over any `fs.FS`.
- `go:embed` produces an embedded filesystem without changing the consumer.
- `html/template` provides the associated template set and contextual escaping.
- `fstest.MapFS` makes the same code easy to test without the host filesystem.

That means the first design rule is simple:

> Do not invent a filesystem framework when `fs.FS` is already the interface the consumer needs.

A template compiler can accept `fs.FS` values directly and return a concrete `*template.Template`.

## When `ParseFS` is already enough

Before writing a walker, consider `html/template.ParseFS`.

For a small fixed tree with simple naming rules, it may already be the best answer. A custom walk becomes useful only when file discovery itself has policy attached to it, for example:

- recurse to arbitrary depth,
- preserve relative paths as logical names,
- filter files,
- attach source provenance to errors,
- enforce namespace ownership,
- reject collisions rather than relying on parse order,
- compose several independently owned filesystems.

The last few points are what turn a convenience helper into an architectural boundary.

## Keep templates next to the code that owns them

A domain-oriented application might look roughly like this:

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

internal/shared/
    web/
        templates/
            embed.go
            layout.gohtml
            pager.gohtml
```

The exact directory names are not important. The ownership rule is.

A template that exists because the links web adapter exists can be owned by that adapter. Shared layouts can be owned by a deliberately shared presentation package. The application does not need to put every template file back into one physical directory merely because all templates are compiled into one runtime set.

That is where `walkmultifs` becomes useful: **physical ownership stays local while runtime composition stays global**.

## The tempting implementation is not quite strong enough

A first version of `walkfs` might look like this:

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

This is useful, but it only checks the name derived from the **file path**.

Go templates have another namespace inside the files themselves.

A file named:

```text
card.gohtml
```

can contain:

```gotemplate
{{ define "links/card" }}
    ...
{{ end }}
```

That explicit definition becomes another associated template. A second file can define the same name, and Go's template APIs support legitimate replacement and overlay use cases.

For independently owned application components, replacement is usually the wrong default. If two sources both claim the same logical template name, I want compilation to fail.

So a stronger implementation should:

1. parse each file in isolation,
2. inspect every template created by that parse,
3. validate ownership of every resulting name,
4. detect duplicates with source provenance,
5. only then add the parse trees to the final template set.

## A stricter `templatefs` compiler

The public API can still stay small:

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

This is deliberately ordinary Go. It is mostly standard-library glue.

The important property is that every logical name is checked **before** it is admitted to the final associated template set.

A links source may define:

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

The path validation also rejects names such as:

```text
links/../shared/pager
```

so the ownership rule is path-like rather than a raw string-prefix convention.

The namespace is not decoration. It is part of the compilation contract.

## Why parse one file at a time?

There are two useful identities to preserve.

First, the file itself gets a stable logical name such as:

```text
links/pages/edit.gohtml
```

Second, any explicit `define` or `block` declarations created while parsing that file can be attributed to the same source file before anything is merged globally.

Parsing one whole domain into a temporary shared template set would isolate domains from one another, but it could still allow later files inside that domain to replace definitions established by earlier files.

Per-file parsing plus an explicit ownership map closes that hole too.

It also permits precise errors such as:

```text
template "links/card" defined by both links:card.gohtml and links:partials/card.gohtml
```

That is substantially easier to diagnose than finding out later that one definition happened to win.

## `walkmultifs` is composition, not a union filesystem

At this point, `walkmultifs` does not require a separate filesystem implementation. It is simply the fact that the compiler accepts several sources:

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

This is preferable to pretending that independent component filesystems are one filesystem.

A union filesystem has to define semantics for:

- duplicate paths,
- directory listing merges,
- source precedence,
- a file in one source colliding with a directory in another,
- distinguishing a miss from a source-specific error.

Those are useful questions when building an **overlay** filesystem. They are not necessary for component composition.

For independently owned sources, a collision should normally fail.

For overrides, precedence should be intentional and implemented one layer earlier.

That gives two separate concepts:

```text
overlay FS      = which physical file a source exposes
source compiler = which sources contribute templates
```

Keeping those concepts separate makes both easier to reason about.

## Let resource packages stay leaf packages

`go:embed` is package-local, which fits this structure well.

A resource package can be almost empty:

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

It does not need to import the handler that conceptually owns it. Directory nesting does not imply an import relationship in Go.

These can be independent packages:

```text
internal/links/web
internal/links/web/templates
```

The resource package can remain a leaf that knows only about `embed` and `io/fs`.

I also would not introduce this interface merely because it is possible:

```go
type TemplateSource interface {
    FS() fs.FS
}
```

The compiler needs an `fs.FS`, so `fs.FS` should remain the boundary. If another required behaviour appears later, an interface can be introduced by the consumer at that point.

## Keep the composition root above the components

The final executable, or a nearby application-composition package, is the right place to know which components exist.

A useful dependency graph looks like this:

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

The arrows point one way.

The generic compiler does **not** import the component packages. The components do **not** import the composition package. The composition package imports the pieces and passes values between them.

That is the important Go property: the import graph stays a DAG.

## FAQ: won't this create import loops?

Not if ownership and composition remain separate.

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
    -> application/templates
    -> links/web
```

Nor is this:

```text
common
    -> template compiler
    -> common
```

The usual cure is not a registry or an `init()` hook. It is to move assembly upward and pass the completed dependency downward.

If a handler needs templates, the simplest option is often to give it the compiled `*template.Template` directly.

If tests or multiple rendering implementations make an interface useful, define the narrow interface on the **consumer** side:

```go
type Renderer interface {
    ExecuteTemplate(io.Writer, string, any) error
}
```

`*template.Template` already satisfies that shape.

Do not add an interface solely to make the code look like dependency injection. Passing a concrete dependency from the composition root is dependency injection too.

## Prefer template association over a custom `include`

A dependency cycle often appears when a low-level helper tries to rediscover or recompile the global template set while a template is being rendered.

Before introducing a callback, renderer provider, or global template registry, ask whether Go's associated-template actions already express the requirement.

For example:

```gotemplate
{{ template "shared/pager" . }}
```

and:

```gotemplate
{{ block "shared/content" . }}
    ... default content ...
{{ end }}
```

These operate inside the already-compiled associated template set. They do not require application code to find the compiler again.

Only introduce function-like rendering when its semantics are genuinely different from `template` or `block`. If that is required, inject a narrow rendering dependency from above rather than importing the application composition package from below.

## Template functions need the same discipline

Template names are not the only global namespace. Function names are shared by the template set too.

`Funcs` must be registered before parsing templates which refer to those names, so the composition root should construct the function map before calling `Compile`.

If several components contribute functions, merge those maps explicitly and reject duplicate names rather than silently deciding that one component wins.

A small helper is enough:

```go
func MergeFuncMaps(maps ...template.FuncMap) (template.FuncMap, error) {
    out := template.FuncMap{}
    for _, funcs := range maps {
        for name, fn := range funcs {
            if _, exists := out[name]; exists {
                return nil, fmt.Errorf("duplicate template function %q", name)
            }
            out[name] = fn
        }
    }
    return out, nil
}
```

Prefer recognisably owned function names where ambiguity is likely:

```text
assetURL
linksURL
imageURL
formatLocalTime
```

rather than letting unrelated components all register a generic name such as `url`.

There is also a lifetime issue. A compiled template set is normally application-scoped and executed concurrently. Functions captured into it should be safe for that lifetime.

Request-specific state is usually better passed through the execution data or view model than captured while compiling the application template set.

That keeps the lifecycle simple:

```text
startup:
    construct stable FuncMap
    construct effective filesystems
    compile templates
    construct handlers

request:
    construct view data
    ExecuteTemplate
```

## Compile once, execute many

Treat template compilation as startup work unless runtime editing is an explicit application feature.

A useful sequence is:

1. construct the complete function map,
2. construct the effective filesystems,
3. compile and validate every source,
4. fail startup if any template is invalid or collides,
5. pass the completed template set to consumers,
6. execute it concurrently without mutating it.

This moves template failures from user requests to process startup and keeps application wiring easy to understand.

It also avoids the anti-pattern where a template helper recompiles templates while a template is already being executed.

## Runtime overrides remain possible

Local ownership and `go:embed` do not require giving up development or deployment overrides.

Suppose the logical sources are:

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

If configuration replaces a complete source, composition can simply choose a different filesystem:

```go
linksFS := linktemplates.FS()
if cfg.TemplateDir != "" {
    linksFS = os.DirFS(filepath.Join(cfg.TemplateDir, "links"))
}
```

If the requirement is **partial** override with embedded fallback, an overlay filesystem is appropriate:

```text
runtime links FS
       |
       v
embedded links FS
       |
       v
one effective links source
```

The compiler should still see only one effective `fs.FS` for the `links` namespace.

That preserves the separation:

```text
overlay policy     -> effective fs.FS
composition policy -> templatefs.Source values
```

The compiler does not need to know whether a source came from `embed.FS`, `os.DirFS`, `fstest.MapFS`, an overlay, or some other implementation.

## Namespaces include explicit definitions

With the strict compiler, filenames and explicit definitions follow the same ownership rule.

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

Shared pieces belong in the shared source:

```gotemplate
{{ define "shared/pager" }}...{{ end }}
```

A links file defining `shared/pager` is rejected. If the component is truly shared, its ownership should move to the shared template source instead of creating an implicit cross-component overwrite.

Template names then carry useful ownership information in much the same way package paths do.

## Cross-source references are still fine

Isolation during parsing does not mean isolation during execution.

A shared layout can invoke a domain template by name:

```gotemplate
{{ template "links/card" .Link }}
```

and a domain page can invoke a shared component:

```gotemplate
{{ template "shared/pager" .Pager }}
```

The compiler merges all accepted parse trees into one associated template set before execution.

The boundary controls **who may define a name**, not who may invoke it.

This preserves deliberate composition while preventing accidental ownership collisions.

## Test the policy, not the host filesystem

This design is easy to test with `fstest.MapFS`:

```go
links := fstest.MapFS{
    "card.gohtml": {
        Data: []byte(`{{ define "links/card" }}card{{ end }}`),
    },
}
```

Tests should cover at least:

- recursive discovery,
- stable file-derived names,
- valid namespaced `define` declarations,
- definitions outside their source namespace,
- duplicate explicit definitions in two files,
- duplicate source namespaces,
- parse errors with source and filename in the error,
- invalid namespace paths,
- nil filesystems,
- cross-source `{{ template }}` calls,
- duplicate function-map entries if functions are composed,
- one complete application compile using the production source list,
- representative renders of top-level templates.

Compile tests prove syntax and ownership. Render tests catch missing referenced templates and view-data contract mistakes that a filesystem walk cannot prove by itself.

If runtime overlays exist, test the overlay implementation separately. Precedence is a filesystem concern; template ownership is a compilation concern.

## Migrating an existing application

For an existing monolith, do not begin by moving files.

A safer sequence is:

1. Capture the existing template-loading and rendering behaviour in tests.
2. Introduce the strict compiler while still pointing it at the existing central filesystem.
3. Register all template functions before compilation.
4. Remove reverse dependencies that rediscover or recompile templates from inside rendering helpers.
5. Establish namespace rules and fix ambiguous `define` names.
6. Add a full-production compile test and representative render tests.
7. Move one small component's templates into a leaf resource package.
8. Compose that source explicitly at the application root.
9. Preserve override behaviour by choosing or overlaying the effective filesystem before compilation.
10. Repeat component by component.

This order separates two changes that are easy to confuse: **how templates are compiled** and **where templates are owned**.

Make compilation strict first. Move ownership second.

## What to avoid

Several attractive shortcuts work initially but weaken the design.

### Package self-registration through `init()`

A global registry lets packages appear to register templates automatically, but it hides the application's dependency list and makes alternate assemblies and tests harder to understand.

Explicit composition is only a few lines and keeps imports visible.

### A central template package that imports every component

That often recreates the dependency-cycle problem under a different directory name.

The application composition layer is allowed to know every component. A low-level compiler should not.

### Last-one-wins component collisions

Replacement is useful for deliberate overlays. It is a poor default for two independent owners claiming the same template name.

Fail early instead.

### A wrapper interface around `fs.FS` for architecture's sake

`fs.FS` is already the consumer boundary. Keep it until another behaviour genuinely needs abstraction.

### A renderer interface before there is a consumer need

Returning `*template.Template` is idiomatic and useful. Let a consumer define a smaller interface only when tests, alternate rendering engines, or another real requirement justify it.

### Request-scoped template compilation

If templates are application resources, compile them once. Pass request state as data and keep the compiled set immutable while serving.

### Combining override and ownership semantics

An overlay answers “which file wins within this logical source?” The compiler answers “which logical source owns this template name?” Keeping these decisions separate prevents accidental precedence rules from becoming architecture.

## The architectural point

The implementation remains small:

```text
component resource packages
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
consumers receive the finished templates
```

`walkfs` is recursive discovery over an abstract filesystem.

`walkmultifs` is explicit composition of several independently owned sources.

The important part is not inventing a clever multi-filesystem object. It is preserving ownership while assembling one runtime template namespace, and doing so with ordinary Go tools: `fs.FS`, `go:embed`, `html/template`, explicit imports, startup composition, and consumer-side interfaces only where they provide real value.

That is the version of the pattern I would want to copy into a new Go project.

## References

- [Go `io/fs`](https://pkg.go.dev/io/fs)
- [Go `fs.FS`](https://pkg.go.dev/io/fs#FS)
- [Go `fs.Sub`](https://pkg.go.dev/io/fs#Sub)
- [Go `fs.WalkDir`](https://pkg.go.dev/io/fs#WalkDir)
- [Go `fs.ValidPath`](https://pkg.go.dev/io/fs#ValidPath)
- [Go `embed`](https://pkg.go.dev/embed)
- [Go `html/template`](https://pkg.go.dev/html/template)
- [Go `Template.ParseFS`](https://pkg.go.dev/html/template#Template.ParseFS)
- [Go `Template.Funcs`](https://pkg.go.dev/html/template#Template.Funcs)
- [Go `Template.AddParseTree`](https://pkg.go.dev/html/template#Template.AddParseTree)
- [Go `Template.Templates`](https://pkg.go.dev/html/template#Template.Templates)
- [Go `testing/fstest`](https://pkg.go.dev/testing/fstest)
