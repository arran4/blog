---
title: "Self-Hosted Start Pages: Homepage, gobookmarks, Homer, Dashy, Glance, Homarr, Heimdall and Flame"
date: 2026-08-16T10:13:59+10:00
draft: false
tags: ["self-hosted", "start-page", "dashboard", "bookmarks", "homepage", "configuration"]
categories: ["self-hosting", "software-comparison"]
---

<!-- cspell:words Dashy gobookmarks Heimdall Homarr -->

Self-hosted start pages tend to look interchangeable from a distance: a grid of links, a search box, perhaps some status cards, and a convenient place to start a browser session. Their configuration models are much less interchangeable.

That distinction matters if the dashboard itself is treated as infrastructure. A start page containing fifty or a hundred carefully grouped links is already a useful data set. Once it also contains service credentials, status widgets, Docker discovery rules, layout choices, icons, tabs, permissions and user-specific state, moving to another application can become a migration project rather than a configuration change.

I recently compared [Homepage](https://github.com/gethomepage/homepage) with my own [gobookmarks](https://github.com/arran4/gobookmarks). The interesting result was that the *links* are highly transplantable while the *dashboard behaviour* is not. Looking at several other projects makes the reason clearer: these applications are solving overlapping, but not identical, problems.

This article compares:

- [Homepage](https://github.com/gethomepage/homepage)
- [gobookmarks](https://github.com/arran4/gobookmarks)
- [Homer](https://github.com/bastienwirtz/homer)
- [Dashy](https://github.com/Lissy93/dashy)
- [Glance](https://github.com/glanceapp/glance)
- [Homarr](https://github.com/homarr-labs/homarr)
- [Heimdall](https://github.com/linuxserver/Heimdall)
- [Flame](https://github.com/pawelmalak/flame)

The important question is not simply which one has the longest feature list. It is: **what is the application's source of truth, and how much of that source of truth can be carried somewhere else?**

## The portability spectrum

At a high level these projects sit on a spectrum between configuration-as-data and application-managed state.

| Project | Primary model | Main source of truth | Rich service integrations | Portability of plain links |
| --- | --- | --- | --- | --- |
| gobookmarks | bookmark/start-page hierarchy | small text format, optionally Git-backed | Low | Very high |
| Homer | static launcher | YAML | Low to medium | Very high |
| Homepage | service dashboard and launcher | several YAML files and discovery metadata | Very high | Very high |
| Dashy | configurable personal dashboard | YAML, also editable through the UI | High | Very high |
| Glance | information/feed dashboard | YAML | High, but widget-oriented | High for bookmark widgets |
| Flame | app and bookmark launcher | SQLite-backed application state | Medium | High conceptually |
| Heimdall | application launcher | application database/UI | Medium to high through enhanced apps | High conceptually |
| Homarr | integrated multi-user dashboard | application-managed database/UI | High | High conceptually, lower mechanically |

"Portability of plain links" deliberately ignores styling, credentials and application-specific widget configuration. Every project can represent a URL somehow. The difference is whether that URL lives in a simple file that can be transformed mechanically, or is one record in a richer application model.

## Homepage: configuration as a dashboard description

Homepage is one of the richer configuration-as-code choices. It separates major concerns into files such as:

- `services.yaml`
- `bookmarks.yaml`
- `widgets.yaml`
- `settings.yaml`

A basic bookmark group is structurally simple:

```yaml
- Developer:
    - GitHub:
        - abbr: GH
          href: https://github.com/

- Social:
    - Reddit:
        - icon: reddit.png
          href: https://reddit.com/
          description: The front page of the internet
```

Services use a similar grouping model but can add considerably more behaviour:

```yaml
- Media:
    - Jellyfin:
        icon: jellyfin.png
        href: https://jellyfin.example.com/
        description: Movies and television
        widget:
          type: jellyfin
          url: https://jellyfin.example.com/
          key: ${JELLYFIN_API_KEY}
```

This is where the meaning of "dashboard" starts to diverge from "bookmarks". The `href` and display name are generic. The Jellyfin widget, API key, supported fields, highlighting rules and other integration settings belong specifically to Homepage's model.

Homepage also allows layout policy to be declared separately. Groups can be assigned to tabs, arranged as rows or columns, collapsed, shown with icons only, or discovered from Docker and Kubernetes metadata.

That makes Homepage's configuration very portable *within Homepage*: it is text, it can be version controlled, reviewed, templated and generated. It does not make all of those semantics portable to another dashboard.

For migration purposes I would divide Homepage configuration into three layers:

1. **Navigation data**: names, URLs and groups. Highly portable.
2. **Presentation data**: icons, descriptions, tab membership and layout. Often portable with some loss.
3. **Integration behaviour**: service widgets, monitoring and discovery. Usually destination-specific.

That separation is useful when evaluating every other project in this article.

## gobookmarks: intentionally small source data

gobookmarks takes almost the opposite approach. Its bookmark data uses a deliberately small text language:

```text
Tab: Home
Page: Services
Column
Category: Development
https://github.com GitHub
https://gitlab.com GitLab

Category: Search
https://duckduckgo.com DuckDuckGo
```

The internal hierarchy is essentially:

```text
Tab
  Page
    Block
      Column
        Category
          Entry(URL, Name)
```

That is a constrained model, but the constraint is part of the design. The file is easy to edit, easy to diff, easy to keep in Git and easy to generate. gobookmarks can use GitHub, GitLab, local Git or SQL-backed providers while retaining the same simple bookmark representation.

The cost is equally clear. A bookmark entry is basically a URL and a name. There is nowhere to preserve arbitrary Homepage fields such as:

```text
description
icon
abbr
widget
ping
highlight
```

without extending the format.

For Homepage to gobookmarks, the simple case is nearly mechanical:

```yaml
- Developer:
    - GitHub:
        - href: https://github.com/
```

becomes:

```text
Category: Developer
https://github.com/ GitHub
```

Homepage tab assignments can map to gobookmarks `Tab` directives. A Homepage group can map to a category. A service with an `href` can be reduced to a normal bookmark.

The interesting mismatch is that Homepage can have groups which appear on every tab. gobookmarks structurally owns categories underneath a tab, so an importer would either duplicate those categories into each tab or need a new shared-group concept.

Another mismatch goes in the other direction: gobookmarks has explicit pages within a tab, which do not have a direct Homepage equivalent. A conversion back to Homepage therefore needs to flatten pages or turn them into additional groups or tabs.

The result is asymmetric:

> Homepage to gobookmarks is straightforward if the goal is to preserve navigation. gobookmarks to Homepage is also straightforward for links, but a multi-page gobookmarks layout requires a policy decision.

That is still a good migration story because the irreducible data remains very small.

## Homer: probably the closest file-based cousin

Homer describes itself as a very simple static homepage and uses a YAML configuration file. That places it close to gobookmarks and the bookmark side of Homepage.

Its configuration describes groups of services and the links inside them, with additional presentation properties. Homer also supports multiple pages and "smart cards" for some richer behaviours.

For a generic migration model, this is a comfortable mapping:

```text
Homer service group  <-> common group/category
Homer service item   <-> common link
Homer page           <-> common page/tab
```

A Homer item will often contain more display metadata than a gobookmarks entry, but the core is still recognisable as a link in a named group. A converter can preserve the useful minimum and report dropped fields.

This makes Homer one of the easiest applications in the set to treat as configuration data rather than as an opaque application database.

If the main requirement is:

> "Give me a static page of organised links, configured in a file and served cheaply"

Homer is much closer to gobookmarks than Homarr or Heimdall are, even though the rendered interfaces may all look like dashboards.

## Dashy: YAML with a much larger vocabulary

Dashy also keeps a strong configuration-as-code path. Its main configuration is a YAML file, normally `user-data/conf.yml`, and the same configuration can also be edited through the user interface.

The useful portable core looks roughly like this:

```yaml
sections:
  - name: Development
    items:
      - title: GitHub
        url: https://github.com/
        description: Source hosting
        icon: favicon
```

Structurally that is an excellent source for conversion:

```text
section.name  -> category/group
item.title    -> bookmark name
item.url      -> bookmark URL
```

But Dashy's configuration vocabulary extends much further into theming, search behaviour, status checks, icons, widgets and display rules.

So Dashy has the same broad portability shape as Homepage:

- links and sections: high
- descriptions and icons: medium, depending on the destination
- layout: policy-dependent
- widgets and status behaviour: low across products

Dashy has an additional practical advantage for migration: the UI and the YAML file are not mutually exclusive worlds. A user can interactively edit the dashboard while still having a textual representation to back up, inspect or transform.

That is an important design point. "Has a UI editor" does not necessarily imply "cannot be configuration as code".

## Glance: a dashboard where bookmarks are one widget

Glance makes the category boundary especially obvious.

Its configuration is YAML, and pages contain columns which contain widgets:

```yaml
pages:
  - name: Home
    columns:
      - size: small
        widgets:
          - type: calendar

      - size: full
        widgets:
          - type: hacker-news

      - size: small
        widgets:
          - type: weather
            location: Melbourne, Australia
```

Glance also has a bookmarks widget, but bookmarks are one possible component among RSS feeds, videos, weather, calendars, market data, server information, Docker information and other widgets.

This means Glance is technically very portable as *configuration*: it is declarative YAML and even supports included configuration files. But its semantic centre is different.

Converting a Homepage bookmark group to a Glance bookmarks widget is reasonable.

Converting:

```text
Homepage service widget -> Glance widget
```

is not a generic transformation. Sometimes both applications happen to support the same external service; often their widget models, fields and authentication options differ.

Likewise a Glance page containing:

```text
calendar + RSS + Reddit + weather + markets
```

cannot meaningfully become a gobookmarks page without throwing away almost everything except links.

So Glance demonstrates why "uses YAML" and "is portable to another YAML dashboard" are not the same statement.

The syntax may be easy to parse while the semantics are incompatible.

## Homarr: application state first

Homarr explicitly advertises a different model: no YAML, with drag-and-drop configuration, authentication, user management and a large set of integrations.

For a user who wants to manage a dashboard as an application, that is a feature. The dashboard can have richer user-specific and permission-specific behaviour without forcing users to edit configuration files.

For someone treating the dashboard as repository-managed infrastructure, it changes the migration problem.

The generic link:

```text
name + URL + icon
```

is still portable in principle. The surrounding state is application-owned rather than naturally expressed as a small text file.

This creates a useful distinction:

- **semantic portability**: another dashboard can represent the same concept;
- **mechanical portability**: a deterministic transformer can consume the source configuration directly.

Homarr scores well on semantic portability for ordinary links but lower on mechanical portability than Homepage, Homer, Dashy or gobookmarks.

A migration tool may need an application-specific export, API or database reader before it even reaches a common intermediate model.

## Heimdall: mature launcher with enhanced applications

Heimdall is a long-running application dashboard and launcher. At its simplest it is a collection of tiles pointing at applications or arbitrary URLs.

It also has "Enhanced" applications that connect to supported service APIs and display live information.

That makes its conceptual shape familiar:

```text
plain application tile -> portable link
enhanced application   -> portable link + non-portable integration
```

Heimdall itself is an application backed by SQLite rather than a static link configuration file. It does use YAML for configurable search providers, but that YAML is not the primary dashboard data.

As with Homarr, the difficulty is therefore not understanding what a tile means. It is extracting and recreating the state in a supported, reliable way.

A converter from Homepage YAML to Heimdall cannot simply emit another configuration file in the way a Homepage-to-Homer converter could. It would need to target whatever import, API or storage mechanism Heimdall supports.

## Flame: simple concepts, database-managed state

Flame sits between the minimal launchers and richer integrated dashboards.

It provides built-in editors for applications and bookmarks, search, authentication, themes, weather and Docker integration. The backend uses SQLite. It also includes an experimental importer for browser HTML bookmarks.

Its conceptual model remains migration-friendly:

```text
application
bookmark category
bookmark
```

That is much easier to map from gobookmarks or Homepage than a completely widget-driven dashboard would be.

But, again, the source of truth is the key distinction. A SQLite-backed application can represent the same information as a YAML file while still requiring a more specialised import/export path.

Flame's browser-bookmark importer is an example of the right direction: define a supported boundary between external data and the application's internal state instead of asking users to mutate the database themselves.

## A common denominator exists

Across all of these applications, a surprisingly useful common model can be written down.

Something like:

```go
type Dashboard struct {
    Pages []Page
}

type Page struct {
    Name   string
    Groups []Group
}

type Group struct {
    Name  string
    Links []Link
}

type Link struct {
    Name        string
    URL         string
    Description string
    Icon        string
}
```

is enough to represent the majority of *navigation* data in every application discussed here.

Tabs and columns can be added:

```go
type Dashboard struct {
    Tabs []Tab
}

type Tab struct {
    Name  string
    Pages []Page
}

type Page struct {
    Name    string
    Columns []Column
}
```

and application-specific information can be carried in optional metadata:

```go
type Link struct {
    Name        string
    URL         string
    Description string
    Icon        string
    Extra       map[string]any
}
```

The important point is that `Extra` should not be mistaken for interoperability. It is a place to avoid destroying source information during an import/export round trip. A Homepage `widget` object stored in `Extra` is still not automatically meaningful to Homer, Dashy or gobookmarks.

A useful migration system therefore needs two levels:

```text
source format
    |
    v
portable intermediate representation
    |
    +--> destination's native concepts
    |
    `--> warnings for information that cannot be represented
```

Warnings are important. Silent loss makes a converter appear more compatible than it really is.

For example:

```text
Imported 84 links in 11 groups.
Preserved 4 tabs.
Dropped 31 descriptions.
Dropped 47 explicit icons.
Skipped 12 Homepage service widgets.
Duplicated 2 global groups across all tabs.
```

That is a much more honest migration result than claiming "Homepage import supported".

## Pairwise transplantability

For the common case of moving links and their organisation, I would roughly rank the conversions like this:

| From / to | gobookmarks | Homepage | Homer | Dashy | Glance | Homarr / Heimdall / Flame |
| --- | --- | --- | --- | --- | --- | --- |
| gobookmarks | Native | High | High | High | Medium | Medium |
| Homepage | High | Native | High | High | Medium | Medium |
| Homer | High | High | Native | High | Medium | Medium |
| Dashy | High | High | High | Native | Medium | Medium |
| Glance | Medium | Medium | Medium | Medium | Native | Low to medium |
| DB/UI-managed dashboards | Medium | Medium | Medium | Medium | Low to medium | Application-specific |

"High" here means that names, URLs and broad grouping can be transferred without inventing much.

It does **not** mean the conversion is fully reversible.

The biggest losses tend to be:

- service-specific widgets;
- API credentials and field selections;
- health/status checks;
- application discovery rules;
- permissions and users;
- styling and theme details;
- responsive layout semantics;
- application-specific search behaviour;
- shared/global groups where ownership rules differ.

## Why gobookmarks could support importers without changing its format

For gobookmarks specifically, I do not think compatibility argues for replacing its small native format with a Homepage- or Dashy-shaped YAML file.

The small format is the useful part.

Instead, the existing import boundary could grow format-aware converters:

```text
gobookmarks import native ...
gobookmarks import homepage ...
gobookmarks import homer ...
gobookmarks import dashy ...
gobookmarks import netscape-html ...
```

The Homepage importer could accept:

```text
bookmarks.yaml
services.yaml
settings.yaml
```

and apply explicit rules:

```text
Homepage bookmark group
    -> gobookmarks Category

Homepage bookmark
    -> gobookmarks Entry

Homepage service with href
    -> gobookmarks Entry

settings.layout.<group>.tab
    -> gobookmarks Tab

nested Homepage group
    -> flatten using a documented naming policy

group visible on every Homepage tab
    -> duplicate into each generated gobookmarks Tab

widget / ping / highlight / icon / description
    -> warn when not representable
```

Homer and Dashy importers would be similarly straightforward because their link data already has an obvious textual structure.

For Homarr, Heimdall and Flame, import support would likely start from an exported file, API or documented database migration surface rather than trying to make gobookmarks understand another application's private storage layout.

This is also a good argument for making importers separate from the storage provider. "Where my gobookmarks file is stored" and "what external format I imported it from" are orthogonal concerns.

## Which kind of start page fits which job?

The projects overlap, but their centres of gravity are different.

**gobookmarks** fits when the bookmark data itself is the important asset: simple text, history, search and a hierarchy that remains easy to understand outside the application.

**Homer** fits when a static, attractive, YAML-configured launcher is the goal and a server-side application is unnecessary.

**Homepage** fits when the launcher is also a live operations dashboard, especially around self-hosted services, Docker discovery and service-specific integrations.

**Dashy** fits when a rich YAML-defined personal dashboard is wanted but interactive editing and a large amount of visual customisation are also valuable.

**Glance** fits when the page is less a launcher and more an information surface: feeds, calendars, status, media and other widgets, with bookmarks as one component.

**Homarr** fits when a full application experience, drag-and-drop management, authentication and multiple integrations matter more than keeping the dashboard definition as a small text file.

**Heimdall** fits the application-launcher model, with a mature catalogue of enhanced applications for users who want more than static tiles.

**Flame** fits users who want a relatively straightforward apps-and-bookmarks start page with built-in editing and discovery, without making file-based configuration the central workflow.

There is no single winner because "self-hosted homepage" hides at least three separate product categories:

```text
bookmark/start-page manager
        |
        +-- gobookmarks
        +-- Homer
        `-- Flame

service launcher/dashboard
        |
        +-- Homepage
        +-- Dashy
        +-- Heimdall
        `-- Homarr

information/feed dashboard
        |
        `-- Glance
```

The categories overlap, but they explain why superficially similar screenshots can conceal very different migration characteristics.

## The real lock-in test

When evaluating one of these tools, I would now ask four questions before looking at themes or screenshots:

1. **Can I obtain the complete list of links in a documented format?**
2. **Can I reproduce the grouping and navigation without clicking through the UI?**
3. **Are application-specific integrations cleanly separable from the links they decorate?**
4. **Can I version, diff and restore the state using ordinary tools?**

A dashboard does not have to answer "yes" to all four. A database-backed multi-user application may reasonably choose different tradeoffs from a static launcher.

But those answers tell you how expensive it will be to change your mind later.

For Homepage, Homer, Dashy and Glance, the configuration is already text and therefore straightforward to inspect and transform. gobookmarks goes further in deliberately keeping its core data model tiny. Homarr, Heimdall and Flame put more state behind the application boundary, which can make the interactive experience better while making generic conversion more application-specific.

The useful conclusion from comparing Homepage and gobookmarks was therefore not that their configurations are compatible. They are not.

It is that **the durable core of a start page is much smaller than most dashboard configuration formats**:

```text
name
URL
group
order
optional page/tab
```

Everything above that core should be treated as an enhancement with an explicit migration policy.

That is enough common ground to make importers practical, and perhaps enough to justify a small shared interchange model between self-hosted start-page projects without forcing any of them to adopt the same native configuration format.

## References

- Homepage repository: https://github.com/gethomepage/homepage
- Homepage bookmark configuration: https://github.com/gethomepage/homepage/blob/dev/docs/configs/bookmarks.md
- Homepage service configuration: https://github.com/gethomepage/homepage/blob/dev/docs/configs/services.md
- Homepage settings and layout: https://github.com/gethomepage/homepage/blob/dev/docs/configs/settings.md
- gobookmarks repository: https://github.com/arran4/gobookmarks
- gobookmarks bookmark model: https://github.com/arran4/gobookmarks/blob/main/bookmark_model.go
- Homer repository: https://github.com/bastienwirtz/homer
- Dashy repository: https://github.com/Lissy93/dashy
- Glance repository: https://github.com/glanceapp/glance
- Glance configuration documentation: https://github.com/glanceapp/glance/blob/main/docs/configuration.md
- Homarr repository: https://github.com/homarr-labs/homarr
- Heimdall repository: https://github.com/linuxserver/Heimdall
- Flame repository: https://github.com/pawelmalak/flame
