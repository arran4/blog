---
title: "Walking Template Filesystems: walkfs, walkmultifs, and Domain-Owned Templates in Go"
date: 2026-08-16T14:27:00+10:00
draft: false
tags: ["go", "templates", "filesystem", "architecture", "embed"]
categories: ["engineering-process", "reference"]
---

<!-- cspell:words AddParseTree AddPrefix DAG DirFS ExecuteTemplate FuncMap Funcs MapFS ParseFS ValidPath WalkDir funcs fstest gohtml gotemplate imagetemplates linktemplates namespacing sharedtemplates templatefs walkfs walkmultifs -->

A useful Go pattern appears whenever files are part of application composition rather than merely data on disk: accept an `fs.FS`, recursively discover files, give them stable logical names, validate them, and assemble them into a larger runtime object.

For HTML templates, I will call the single-filesystem form **walkfs** and the multi-source form **walkmultifs**.

The walking code itself is small. The interesting part is getting the Go design around it right: ownership, package dependencies, template names, collision handling, runtime overrides, function maps, testing, and application lifecycle.

This article builds that design from first principles. The goal is not the shortest possible loader, but the version of the pattern I would want copied into a new Go codebase.

## Start with the standard library

The useful primitives already exist:

- `fs.FS` is the filesystem boundary.
- `fs.Sub` selects a subtree when necessary.
- `fs.WalkDir` gives recursive discovery over any `fs.FS`.
- `go:embed` produces an embedded filesystem without changing the consumer.
- `html/template` provides the associated template set and contextual escaping.
- `fstest.MapFS` makes the same code easy to test without the host filesystem.

That gives the first design rule:

> Do not invent a filesystem framework when `fs.FS` is already the interface the consumer needs.

A template compiler can accept `fs.FS` values directly and return a concrete `*template.Template`.

## When `ParseFS` is already enough

Before writing a walker, consider `html/template.ParseFS`.

For a small fixed tree with simple naming rules, it may already be the best answer. A custom walk becomes useful when discovery itself has policy attached to it, for example:

- recurse to arbitrary depth,
- preserve relative paths as logical names,
- add a logical prefix to a source without changing its filesystem,
- filter files,
- attach source provenance to errors,
- enforce ownership of extra named templates,
- reject collisions rather than relying on parse order,
- compose several independently owned filesystems.

The last few points are what turn a convenience helper into an architectural boundary.

## The filename should normally be the template name

The simplest convention is one file equals one template.

If a source contains:

```text
card.gohtml
edit-form.gohtml
pages/edit.gohtml
```

then those file bodies should be usable directly as templates. There is no need to wrap every file in `{{ define ... }}` merely to give it a name.

For example, `card.gohtml` can simply contain:

```gotemplate
<article class="card">
    <a href="{{ .URL }}">{{ .Title }}</a>
</article>
```

If the compiler publishes that file as `links/card.gohtml`, another template can invoke it directly:

```gotemplate
{{ template "links/card.gohtml" .Link }}
```

The file path is already a useful, stable identity.

Explicit `define` or `block` declarations remain useful when one file deliberately creates **additional** associated templates, but they should not be required for the ordinary one-file-one-template case.

## Two ways to get the logical path

There are two useful layouts. Both can produce the same runtime name:

```text
links/card.gohtml
```

The difference is whether `links/` exists physically or is added at composition time.

### Variant 1: flat package resources with a virtual prefix

Keeping a component's resource package flat is convenient:

```text
internal/links/web/templates/
    embed.go
    card.gohtml
    edit-form.gohtml
```

The filesystem exposed by that package contains:

```text
card.gohtml
edit-form.gohtml
```

At composition time, give the source a virtual prefix:

```go
templatefs.Source{
    Name:   "links templates",
    Prefix: "links",
    FS:     linktemplates.FS(),
}
```

The compiler reads:

```text
card.gohtml
```

but publishes it as:

```text
links/card.gohtml
```

This is effectively an **AddPrefix operation on the template name**, not on the filesystem itself:

```go
logicalName := path.Join(src.Prefix, p)
```

There is no standard-library inverse of `fs.Sub` that adds a directory in front of an arbitrary filesystem. More importantly, one is not needed here. The read path and the published template name are separate concerns.

`fs.Sub` changes how a caller addresses files in an `fs.FS`. A virtual template prefix changes only how the parsed file is named in the template set.

If some unrelated consumer genuinely needs an `fs.FS` which itself appears underneath an added directory, a small filesystem wrapper may make sense. For template compilation alone, that would be extra machinery for no benefit.

### Variant 2: put the namespace in the actual directory tree

The simpler naming implementation is to make the desired runtime name the actual filesystem path:

```text
internal/links/web/templates/
    embed.go
    files/
        links/
            card.gohtml
            edit-form.gohtml
```

The package can expose an FS containing those paths:

```go
package templates

import (
    "embed"
    "io/fs"
)

//go:embed files
var embedded embed.FS

func FS() fs.FS {
    sub, err := fs.Sub(embedded, "files")
    if err != nil {
        panic(err)
    }
    return sub
}
```

Now the walker sees:

```text
links/card.gohtml
```

and can publish `p` unchanged.

An application which is happy to own one physical template tree can go further:

```text
templates/
    shared/
        layout.gohtml
        pager.gohtml
    links/
        card.gohtml
        edit-form.gohtml
    images/
        image.gohtml
```

After an `fs.Sub(embedded, "templates")`, every path is already its final logical template name. A single walk is enough and no virtual-prefix feature is required at all.

This is the simplest implementation. The trade-off is physical ownership: a central tree is less attractive when templates should live beside independently owned packages. Putting the namespace directory inside each leaf resource package keeps local ownership but adds one redundant directory level.

So the choice is mostly structural:

```text
flat local package + Prefix  -> less physical nesting, composition adds identity
physical namespace directory -> source path is runtime identity, simpler compiler
```

Both are valid. The compiler can support both without changing the template API.

## A compiler which supports both variants

A small source description is enough:

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
    // Name is for diagnostics only.
    Name string

    // Prefix is optional. When non-empty, it is added to the filesystem
    // path when choosing the logical template name.
    Prefix string

    FS fs.FS
}

type origin struct {
    Source string
    File   string
}

func Compile(funcs template.FuncMap, sources ...Source) (*template.Template, error) {
    out := template.New("root").Funcs(funcs)
    owners := map[string]origin{}

    for _, src := range sources {
        if src.FS == nil {
            return nil, fmt.Errorf("template source %q has a nil filesystem", src.Name)
        }
        if src.Prefix != "" && (src.Prefix == "." || !fs.ValidPath(src.Prefix)) {
            return nil, fmt.Errorf("template source %q has invalid prefix %q", src.Name, src.Prefix)
        }

        err := fs.WalkDir(src.FS, ".", func(p string, d fs.DirEntry, walkErr error) error {
            if walkErr != nil {
                return fmt.Errorf("walk %s:%s: %w", src.Name, p, walkErr)
            }
            if d.IsDir() || path.Ext(p) != ".gohtml" {
                return nil
            }

            b, err := fs.ReadFile(src.FS, p)
            if err != nil {
                return fmt.Errorf("read %s:%s: %w", src.Name, p, err)
            }

            logicalName := p
            if src.Prefix != "" {
                logicalName = path.Join(src.Prefix, p)
            }

            parsed, err := template.New(logicalName).Funcs(funcs).Parse(string(b))
            if err != nil {
                return fmt.Errorf("parse %s:%s as %q: %w", src.Name, p, logicalName, err)
            }

            candidates := parsed.Templates()
            sort.Slice(candidates, func(i, j int) bool {
                return candidates[i].Name() < candidates[j].Name()
            })

            ownerPrefix := src.Prefix
            if ownerPrefix == "" {
                ownerPrefix = firstSegment(logicalName)
            }

            for _, candidate := range candidates {
                if candidate.Tree == nil {
                    continue
                }

                name := candidate.Name()
                if !fs.ValidPath(name) {
                    return fmt.Errorf("%s:%s defines invalid template name %q", src.Name, p, name)
                }

                // The file-derived template name is always allowed. Extra names
                // created by define/block must remain in the same namespace.
                if name != logicalName {
                    if ownerPrefix == "" || !inNamespace(name, ownerPrefix) {
                        return fmt.Errorf(
                            "%s:%s defines template %q outside namespace %q",
                            src.Name, p, name, ownerPrefix,
                        )
                    }
                }

                if previous, exists := owners[name]; exists {
                    return fmt.Errorf(
                        "template %q defined by both %s:%s and %s:%s",
                        name, previous.Source, previous.File, src.Name, p,
                    )
                }

                if _, err := out.AddParseTree(name, candidate.Tree); err != nil {
                    return fmt.Errorf("add template %q from %s:%s: %w", name, src.Name, p, err)
                }

                owners[name] = origin{Source: src.Name, File: p}
            }
            return nil
        })
        if err != nil {
            return nil, err
        }
    }

    return out, nil
}

func firstSegment(name string) string {
    if i := strings.IndexByte(name, '/'); i >= 0 {
        return name[:i]
    }
    return ""
}

func inNamespace(name, prefix string) bool {
    return name == prefix || strings.HasPrefix(name, prefix+"/")
}
```

This is deliberately ordinary Go. It is mostly standard-library glue.

The important line for the virtual-prefix variant is simply:

```go
logicalName = path.Join(src.Prefix, p)
```

With an empty prefix, the actual filesystem path is preserved.

## Using the two variants

A flat local source:

```text
card.gohtml
edit-form.gohtml
```

can be composed as:

```go
tmpl, err := templatefs.Compile(funcs,
    templatefs.Source{
        Name:   "links",
        Prefix: "links",
        FS:     linktemplates.FS(),
    },
    templatefs.Source{
        Name:   "images",
        Prefix: "images",
        FS:     imagetemplates.FS(),
    },
)
```

The resulting names include:

```text
links/card.gohtml
links/edit-form.gohtml
images/image.gohtml
```

A physical tree which already contains namespaces:

```text
shared/layout.gohtml
shared/pager.gohtml
links/card.gohtml
links/edit-form.gohtml
images/image.gohtml
```

needs no virtual prefix:

```go
tmpl, err := templatefs.Compile(funcs,
    templatefs.Source{
        Name: "application templates",
        FS:   templatesFS,
    },
)
```

The resulting names are identical to the source paths.

The two approaches can even be mixed. One source may use a virtual prefix while another already exposes its final paths. Collision checks operate on the resulting logical names, so the final namespace remains deterministic.

## What `define` is for in this model

`define` is optional, not the naming mechanism for ordinary files.

Prefer:

```text
links/card.gohtml
links/edit-form.gohtml
```

with direct file bodies, then call:

```gotemplate
{{ template "links/card.gohtml" .Link }}
{{ template "links/edit-form.gohtml" .Form }}
```

Use `define` only when one file intentionally contributes another associated template. For example, a namespaced file might contain its main body and an additional helper:

```gotemplate
<section>...</section>

{{ define "links/card/badge" }}
    <span class="badge">{{ . }}</span>
{{ end }}
```

The compiler can allow that extra name because it remains inside the `links` namespace.

A links file defining:

```gotemplate
{{ define "shared/pager" }}...{{ end }}
```

is rejected. If the component is truly shared, its ownership should move to the shared template source instead of creating an implicit cross-component overwrite.

If the application never needs multi-template files or `block`, the policy can be made even stricter: reject every parsed template name except the file-derived `logicalName`. That is a perfectly reasonable simplification.

## Why parse one file at a time?

Per-file parsing is useful even when `define` is uncommon.

First, the file itself gets a known logical identity before it enters the global set.

Second, if a file does contain `define` or `block`, every additional name can be attributed to the file that created it before anything is merged globally.

Third, duplicate file-derived names are detected before one source silently replaces another.

This permits errors such as:

```text
template "links/card.gohtml" defined by both links-a:card.gohtml and links-b:card.gohtml
```

rather than discovering later that one happened to win.

## `walkmultifs` is composition, not a union filesystem

`walkmultifs` does not require a new filesystem implementation. It is the fact that `Compile` accepts several sources and maps each source path into one logical template namespace.

A union filesystem has to define semantics for:

- duplicate paths,
- merged directory listings,
- source precedence,
- a file in one source colliding with a directory in another,
- distinguishing a miss from a source-specific error.

Those are useful questions when building an **overlay** filesystem. They are not necessary for component composition.

For independently owned sources, a collision should normally fail.

For overrides, precedence should be intentional and implemented one layer earlier.

That gives separate concerns:

```text
overlay FS       = which physical file a source exposes
virtual Prefix   = how a source path becomes a logical template path
source compiler  = which logical templates enter the final set
```

Keeping those decisions separate makes each easier to reason about.

## Let resource packages stay leaf packages

`go:embed` is package-local, which fits component ownership well.

For the flat virtual-prefix variant, a resource package can be almost empty:

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

The compiler needs an `fs.FS`, so I also would not introduce a wrapper interface merely for architecture's sake:

```go
type TemplateSource interface {
    FS() fs.FS
}
```

`fs.FS` is already the boundary. If another required behaviour appears later, an interface can be introduced by the consumer then.

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
    -> shared/web/templates
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

## Prefer associated templates over a custom `include`

A dependency cycle often appears when a low-level helper tries to rediscover or recompile the global template set while a template is being rendered.

Before introducing a callback, renderer provider, or global template registry, ask whether Go's associated-template action already expresses the requirement.

With file-derived names:

```gotemplate
{{ template "shared/pager.gohtml" .Pager }}
{{ template "links/card.gohtml" .Link }}
```

These operate inside the already-compiled associated template set. They do not require application code to find the compiler again.

Only introduce function-like rendering when its semantics are genuinely different. If that is required, inject a narrow rendering dependency from above rather than importing the application composition package from below.

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

## Runtime overrides remain possible

Local ownership and `go:embed` do not require giving up development or deployment overrides.

For a virtual-prefix source, replace or overlay the source filesystem **before** adding its logical prefix:

```go
linksFS := linktemplates.FS()
if cfg.TemplateDir != "" {
    linksFS = os.DirFS(filepath.Join(cfg.TemplateDir, "links"))
}

templatefs.Source{
    Name:   "links",
    Prefix: "links",
    FS:     linksFS,
}
```

For a physical tree, an override directory can simply mirror the same paths:

```text
templates/
    shared/
        pager.gohtml
    links/
        card.gohtml
```

If the requirement is **partial** override with embedded fallback, an overlay filesystem is appropriate. The compiler should still see one effective `fs.FS` for that source.

The compiler does not need to know whether a source came from `embed.FS`, `os.DirFS`, `fstest.MapFS`, an overlay, or another implementation.

## Cross-source references are still fine

Isolation during parsing does not mean isolation during execution.

A shared layout can invoke a component template by its file-derived name:

```gotemplate
{{ template "links/card.gohtml" .Link }}
```

and a component page can invoke a shared file:

```gotemplate
{{ template "shared/pager.gohtml" .Pager }}
```

The compiler merges all accepted parse trees into one associated template set before execution.

The boundary controls **who contributes a name**, not who may invoke it.

## Test both path-mapping variants

`fstest.MapFS` makes both layouts easy to test.

Virtual prefix:

```go
links := fstest.MapFS{
    "card.gohtml": {
        Data: []byte(`card`),
    },
}

tmpl, err := templatefs.Compile(nil, templatefs.Source{
    Name:   "links",
    Prefix: "links",
    FS:     links,
})
// tmpl.Lookup("links/card.gohtml") != nil
```

Physical path:

```go
all := fstest.MapFS{
    "links/card.gohtml": {
        Data: []byte(`card`),
    },
}

tmpl, err := templatefs.Compile(nil, templatefs.Source{
    Name: "all templates",
    FS:   all,
})
// tmpl.Lookup("links/card.gohtml") != nil
```

Tests should cover at least:

- recursive discovery,
- direct physical path naming,
- virtual-prefix naming,
- collisions after prefixing,
- valid file-derived templates with no `define`,
- extra `define` names inside their owning namespace if supported,
- extra definitions outside their owning namespace,
- parse errors with source and filename in the error,
- invalid prefixes,
- nil filesystems,
- cross-source `{{ template }}` calls,
- duplicate function-map entries if functions are composed,
- one complete application compile using the production source list,
- representative renders of top-level templates.

Compile tests prove syntax, mapping, and ownership. Render tests catch missing referenced templates and view-data contract mistakes that a filesystem walk cannot prove by itself.

## Migrating an existing application

For an existing application, do not begin by moving every file.

A safer sequence is:

1. Capture current template-loading and rendering behaviour in tests.
2. Decide whether the desired logical paths should be represented physically or by virtual prefixes.
3. Introduce the compiler while still pointing it at the existing resources.
4. Make the file-derived logical path the default template identity.
5. Remove unnecessary `define` wrappers that exist only to rename whole files.
6. Register all template functions before compilation.
7. Remove reverse dependencies that rediscover or recompile templates from inside rendering helpers.
8. Add full-production compile and representative render tests.
9. Move component resources to leaf packages if local ownership is desired.
10. Preserve override behaviour by choosing or overlaying the effective filesystem before compilation.

This separates **where a file physically lives** from **what logical template path it publishes**.

## What to avoid

### Requiring `define` just to name a file

The file already has a path. Use that path unless there is a deliberate reason to introduce another name.

### Building a prefixed filesystem when only the template name needs a prefix

If the compiler can read `card.gohtml` and publish `links/card.gohtml`, a new `fs.FS` wrapper is unnecessary.

### Package self-registration through `init()`

A global registry hides the application's dependency list and makes alternate assemblies and tests harder to understand. Explicit composition keeps imports visible.

### A central compiler package that imports every component

The application composition layer is allowed to know every component. A low-level compiler should not.

### Last-one-wins component collisions

Replacement is useful for deliberate overlays. It is a poor default for two independent owners claiming the same logical template name. Fail early instead.

### Wrapper interfaces around `fs.FS` for architecture's sake

`fs.FS` is already the consumer boundary. Keep it until another behaviour genuinely needs abstraction.

### Request-scoped template compilation

If templates are application resources, compile them once. Pass request state as data and keep the compiled set immutable while serving.

### Combining override, physical layout, and logical naming semantics

These are separate questions:

```text
where is the file?       -> fs.FS / overlay
what is it called?       -> path or Prefix + path
who contributes it?      -> Source / composition root
```

Keeping them separate is the main simplification.

## The architectural point

The implementation remains small:

```text
component resource packages
        |
        v
   standard fs.FS values
        |
        +---- physical path retained ---------+
        |                                     |
        +---- or virtual Prefix + path -------+
                                              v
                                  strict template compiler
                                              |
                                              v
                             one associated template set
                                              |
                                              v
                              consumers receive templates
```

`walkfs` is recursive discovery over an abstract filesystem.

`walkmultifs` is explicit composition of several independently owned sources.

A virtual prefix is just a mapping from source path to logical template path. A physical namespace directory makes that mapping the identity function.

The important part is not inventing a clever multi-filesystem object. It is preserving useful ownership while assembling one runtime template namespace with ordinary Go tools: `fs.FS`, `go:embed`, `html/template`, path composition, explicit imports, and startup compilation.

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
