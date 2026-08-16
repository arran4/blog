---
title: "Shell: Better Than and More Than"
date: 2026-08-16T09:51:10+10:00
draft: true
tags: ["linux", "shell", "cli", "unix", "tools"]
categories: ["tools"]
author: "Arran Ubels"
---

There are a lot of lists of "modern Unix commands", but they often put two quite different ideas in the same bucket.

Sometimes I want **a better version of the command I already use**. It should solve essentially the same problem, fit into roughly the same place in my workflow, and improve the experience without asking me to adopt a whole new model.

Other times I want **more than the old command**. I am willing to trade some simplicity, compatibility, or composability for a tool which exposes more information, is interactive, or replaces several steps of a workflow at once.

That gives this article two deliberately different questions for each familiar command:

- **Better than `$PROG`**: what would I reach for when I still want to do `$PROG`'s job, just better?
- **More than `$PROG`**: what would I reach for when the original command is now too small for the job?

`top` is the clearest example. `htop` is, to me, a better `top`. `btop` is more than `top`.

This is intended to be a living article. I expect to add commands, examples, screenshots, and corrections as I use the tools in real situations rather than trying to turn it into an enormous list in one pass.

A note on dates: the classic Unix command names often have several historical implementations and are older than the Linux projects which currently ship them. Where a single "first release" would be misleading, I describe the implementation lineage instead. For the newer tools I include the first public release or project date where upstream documents it clearly.

## `top`

`top` gives a continuously refreshed view of processes and basic system load. On a Linux machine it is one of the quickest ways to answer questions such as "what is consuming the CPU?" or "which process is using all the memory?" without needing a graphical desktop.

What it does particularly well is availability. On Linux, `top` is normally supplied by the `procps`/`procps-ng` family and is close to being something you can expect to find on any conventional installation.

What it does not try to be is a rich system dashboard. It is primarily process-oriented. There is a lot of information available through its interactive modes and configuration, but discovering and navigating that information is not the reason most people reach for `top`.

- **Lineage:** long-standing Unix-style process monitor; the common Linux implementation is maintained in `procps-ng`.
- **Source:** `procps-ng` project.
- **Distribution situation:** effectively ubiquitous on conventional Linux distributions, commonly through a `procps` package.

### Better than `top`

#### `htop`

`htop` keeps the same basic mental model: this is still an interactive process viewer. The difference is that the interaction is the point rather than an afterthought.

The process list is easier to navigate, sorting and filtering are more discoverable, trees are useful, meters are visible without building your own `top` configuration, and process actions can be performed directly from the interface. If I was going to teach someone one interactive process viewer for day-to-day use, this is the obvious step up from `top`.

It is not a drop-in replacement in scripts because neither `top` nor `htop` should usually be the basis of machine-readable process automation. For that, `ps`, `/proc`, or a purpose-built interface remains a better foundation.

- **First released:** `htop` was created in 2004; upstream records Hisham Muhammad as its developer and maintainer from 2004 to 2019, with the current team taking over in 2020.
- **Source:** `htop-dev/htop` on GitHub.
- **Distribution situation:** mature and broadly packaged across Linux distributions and other Unix-like systems.

So for this article:

> **Better than `top`: `htop`** — the same job, with a substantially better interactive interface.

### More than `top`

#### `btop`

`btop` crosses the line from "process viewer" into "resource monitor". Processes are still there, but CPU, memory, disks, network activity and, on supported Linux configurations, GPU information can all share the screen.

That makes it a different choice. If I only want to find and kill a process, `htop` is often less visually expensive and closer to the original problem. If I am trying to understand what the machine is doing as a whole, `btop` saves me from assembling the picture from several commands.

The current C++ `btop` is itself the third iteration of the author's monitor after `bashtop` and `bpytop`. Upstream released `btop` 1.0.0 for Linux on 18 September 2021.

- **First released:** 18 September 2021 for `btop` 1.0.0 on Linux.
- **Source:** `aristocratos/btop` on GitHub.
- **Distribution situation:** upstream documents native packages for several Linux and BSD distributions as well as Homebrew and release binaries. It is now straightforward to obtain on most systems where I would want it.

I already have a separate post showing **BTOP running in various terminals**, which is a useful companion when terminal rendering itself becomes part of the question.

So for this article:

> **More than `top`: `btop`** — not merely a nicer process list, but a broader terminal system dashboard.

## `grep`

`grep` searches text for matching lines. It is one of the best examples of a Unix tool whose narrowness is a feature: it composes beautifully, its behaviour is well understood, and it works equally well on files and streams.

The limitation becomes obvious when the thing I really mean is "search this source tree". Recursive traversal, binary files, ignore files, hidden directories, source-control metadata, useful colours, line numbers, file types, and performance all become part of the problem around the regular expression itself.

- **Lineage:** `grep` dates back to early Unix; GNU `grep` is the common GNU/Linux implementation.
- **Source:** GNU `grep`.
- **Distribution situation:** foundational Unix/Linux tooling and effectively universal.

### Better than `grep`

#### `ripgrep` (`rg`)

For searching a directory tree, `ripgrep` is the version of the job I usually meant when I typed a recursive `grep` command.

It recursively searches directories, understands `.gitignore`-style filtering by default, skips hidden and binary files unless asked otherwise, has useful source-search output, and is designed for speed. Importantly, it remains recognisably a text-search command. I can pipe to it, pipe from it, request machine-oriented output, or turn off the convenient defaults when I need behaviour closer to traditional `grep`.

Andrew Gallant publicly introduced `ripgrep` on 23 September 2016. The project supports Linux, macOS, and Windows and provides release binaries as well as distribution/package-manager installs.

- **First released:** publicly introduced 23 September 2016.
- **Source:** `BurntSushi/ripgrep` on GitHub.
- **Distribution situation:** widely packaged, with upstream release binaries for Linux, macOS, and Windows.

There is still an important reason not to alias `grep` to `rg`: their defaults are intentionally different. A script expecting every file to be searched should not silently acquire `ripgrep`'s ignore behaviour.

So for this article:

> **Better than `grep` for tree search: `ripgrep`** — still text and regular expressions, but with the surrounding source-tree problem handled properly.

### More than `grep`

#### `ast-grep` (`sg`)

Once I want to search **code as code**, textual regular expressions become the wrong abstraction surprisingly quickly.

`ast-grep` matches syntax-tree structure rather than merely matching characters. Patterns can look like ordinary source code while metavariables stand in for syntax nodes. The same machinery can be used for structural search, linting, and rewriting.

This is not a general replacement for `grep`; it is deliberately more specialised. I would not use it to search a log file. I would use it when a text match produces false positives because I care whether something is a function call, expression, declaration, or some other syntactic structure.

The upstream changelog records the `v0.1.0` line in September 2022.

- **First release line:** September 2022 (`v0.1.0`).
- **Source:** `ast-grep/ast-grep` on GitHub.
- **Distribution situation:** upstream provides installation through several ecosystems including Cargo, npm, pip, Homebrew, Scoop, MacPorts, Nix, and `mise`.

So for this article:

> **More than `grep` for source code: `ast-grep`** — search and rewrite syntax rather than pretending syntax is only text.

## `df`

`df` reports space at the filesystem level: total capacity, used space, available space, and the mount that owns it. That is a different question from `du`. `df` tells me **which filesystem is full**; `du` helps me work out **what inside it consumed the space**.

The classic command remains extremely useful, especially in scripts and on minimal systems. Its human-facing output, however, can become noisy on a modern machine with many mounts, loop devices, network filesystems, containers, and other special entries.

- **Lineage:** traditional Unix utility; on GNU systems it is provided by GNU Coreutils.
- **Source:** GNU Coreutils.
- **Distribution situation:** foundational tooling and effectively universal.

### Better than `df`

#### `duf`

`duf` is one of the unusually clean fits for this article because upstream describes it directly as a **better `df` alternative**. It asks the same filesystem-capacity question rather than turning disk usage into a different job.

Its default presentation groups devices into useful categories, adapts to terminal width and theme, highlights usage, and makes sorting and filtering straightforward. It can restrict output to particular devices, filesystems, or mount points, and it also has JSON output when a structured result is useful.

The important distinction is that it still is not something I would blindly substitute for `df` in old scripts. Traditional `df` wins on portability and established output contracts; `duf` wins when a human is looking at the result.

- **Project history:** the upstream repository dates to 20 September 2020.
- **Source:** `muesli/duf` on GitHub.
- **Distribution situation:** unusually broad for a modern replacement. Upstream documents packages for major Linux distributions, including Gentoo as `sys-fs/duf`, as well as BSD, macOS, Windows, Android/Termux, and release binaries.

So for this article:

> **Better than `df`: `duf`** — substantially the same filesystem-space report, but designed around a person actually trying to read it.

### More than `df`

I do not have a clean choice here yet, and that is worth preserving rather than manufacturing symmetry. Once I move beyond filesystem capacity, the problem branches in several directions: block-device topology, mount relationships, per-directory consumption, interactive cleanup, or a whole-system dashboard. Tools such as `lsblk`, `findmnt`, `du`/`dua`, and `btop` answer different versions of those questions rather than forming one obvious "more than `df`" successor.

## `du`

`du` answers a simple but extremely useful question: how much disk space is being used by these files and directories?

Its weakness is not the calculation. The weakness is the investigation that usually follows. I run `du`, add human-readable output, constrain the depth, pipe it through `sort`, perhaps add `head`, then repeat the command further down the directory tree.

That is a good demonstration of Unix composition, but it is also a sign that "where did my disk space go?" has become a higher-level task than `du` itself.

- **Lineage:** traditional Unix utility; on GNU systems it is provided by GNU Coreutils.
- **Source:** GNU Coreutils.
- **Distribution situation:** foundational tooling and effectively universal.

### Better than `du`

#### `dust`

`dust` describes itself succinctly as "du + rust = dust" and is aimed at making the useful answer visible without first constructing a `du | sort | head` pipeline.

It shows the largest entries in a directory hierarchy, uses bars to make relative usage obvious, and deliberately limits the display to something that fits the terminal rather than dumping an exhaustive recursive listing by default.

That is why I put it in the "better" category. It is still fundamentally answering the `du` question. It just chooses defaults and a presentation that match the common investigative use of `du` much better.

- **Project history:** a modern Rust implementation; upstream release history predates its 2020 `0.4.x` series and remains actively maintained.
- **Source:** `bootandy/dust` on GitHub.
- **Distribution situation:** upstream documents Cargo, Homebrew, Snap, Conda, direct release binaries, and several other package channels. Distribution-native availability varies more than `htop` or `ripgrep`, so I would still check the system package manager first.

So for this article:

> **Better than `du`: `dust`** — answer the same disk-usage question with useful hierarchy and scale already in the output.

### More than `du`

#### `ncdu`

`ncdu` turns disk-usage inspection into an interactive browser. After scanning, I can move around the hierarchy, sort it, inspect entries, refresh, and, when appropriate, delete files directly from the interface.

That crosses the "more than" line for me because the output is no longer merely a better report. It becomes a workflow for investigating and cleaning a filesystem.

`ncdu` has also been around much longer than many of the tools normally collected under the "modern Unix" label. Upstream records version 0.1 on 21 February 2007 and the first stable 1.0 release on 6 April 2007. The project now maintains a newer 2.x line as well.

- **First released:** 21 February 2007 (`0.1`); first stable release 6 April 2007 (`1.0`).
- **Source:** the upstream `ncdu` project at yorhel.nl.
- **Distribution situation:** long-established and broadly available in Unix/Linux package repositories; upstream also publishes release sources.

So for this article:

> **More than `du`: `ncdu`** — an interactive disk-usage investigation and cleanup tool, not just another way to print byte totals.

#### `dua` (`dua-cli`)

`dua` is another useful answer to the "more than `du`" question, but with a different balance. Its name expands to **Disk Usage Analyzer**: it can produce an aggregate command-line report, but it also has an interactive mode for exploring disk use and deleting unwanted data.

The project emphasises scanning speed and parallel traversal. That makes it interesting when the filesystem tree itself is large enough that waiting for the analysis becomes part of the problem. It also deliberately reaches beyond reporting by making deletion part of the workflow.

I would not collapse `ncdu` and `dua` into a single recommendation without using both for a while. `ncdu` has a long history and a very established interactive model; `dua` is a newer Rust-era design with a strong focus on scan speed and a useful non-interactive aggregate mode as well.

- **Project history:** the upstream repository dates to 29 May 2019.
- **Source:** `Byron/dua-cli` on GitHub.
- **Distribution situation:** upstream documents release binaries, Cargo, several Linux distribution packages, Homebrew and MacPorts, and Windows package managers.

So for this article:

> **More than `du`: `dua`** — fast disk-usage analysis that can continue into an interactive cleanup workflow.

## `ifconfig`

`ifconfig` is a slightly different case because this is not only about modernising the user experience. On Linux, it belongs to the old `net-tools` family, while modern network configuration and inspection is built around Netlink and the `iproute2` tools.

`ifconfig` can still be useful on systems where it is present, and the name continues to exist on non-Linux Unix systems with their own implementations. But on a contemporary Linux machine, learning `ifconfig` as the primary networking interface means learning the legacy vocabulary first.

What it does is mostly interface address and flag inspection/configuration. What it does not give you is the coherent modern Linux view across addresses, links, routes, neighbours, namespaces, and the rest of the networking stack.

- **Lineage:** classic BSD/Unix networking command; Linux commonly receives it from the legacy `net-tools` package.
- **Source:** Linux `net-tools` for the legacy Linux implementation.
- **Distribution situation:** still available in many distributions, but often no longer installed by default.

### Better than `ifconfig`

#### `ip address` / `ip`

The direct modern Linux answer is the `ip` command from `iproute2`.

For the narrow `ifconfig` use case, `ip address` is the closest conceptual replacement. But the important improvement is that the same command family also covers links, routes, neighbours, rules, tunnels, namespaces, and more.

It is not "better" because it is prettier; many people initially find `ip` output denser. It is better because it exposes the networking model Linux actually uses now, instead of preserving an interface designed around older kernel networking APIs.

- **Release/lineage:** `ip` is part of the long-running `iproute2` suite, maintained alongside modern Linux networking; upstream release tarballs are published through kernel.org.
- **Source:** `iproute2`.
- **Distribution situation:** standard Linux networking tooling and normally available as an `iproute2`/`iproute` package.

So for this article:

> **Better than `ifconfig` on Linux: `ip`** — the current native command family for inspecting and configuring the Linux network stack.

### More than `ifconfig`

#### `nmcli`

`nmcli` operates one level higher. It is the command-line client for NetworkManager, so it can report device state but can also create and modify connection profiles, connect to Wi-Fi, manage VPN-oriented configuration, control radios, and activate persistent network configurations.

That distinction matters. `ip` shows and manipulates kernel networking state. `nmcli` manages NetworkManager's desired and persistent configuration. Using one when I really mean the other is a common source of confusion.

This also means `nmcli` is not universally appropriate. A server or minimal system which does not use NetworkManager does not benefit from having a NetworkManager client installed just to replace `ifconfig`.

- **Release/lineage:** `nmcli` is part of NetworkManager and has been part of the project since the 0.8-era releases.
- **Source:** `NetworkManager/NetworkManager`.
- **Distribution situation:** available wherever NetworkManager is packaged; commonly installed by default on distributions and desktop environments which use NetworkManager, but intentionally absent from systems using a different network manager.

So for this article:

> **More than `ifconfig`: `nmcli`** — when the task is not merely looking at an interface but managing a NetworkManager-controlled connection lifecycle.

## Candidates to add next

The useful part of this format is deciding where a tool belongs, so I do not want to add a pairing merely because a project calls itself a "modern replacement". These are the next command families I want to test and expand:

- `ls`: likely `eza` in the **better than** slot; terminal file managers such as `superfile` and `yazi` may belong in **more than**, but that comparison needs examples because a file manager is a much bigger conceptual jump. I already package `superfile` in my Gentoo overlay, which makes it an obvious one to test next.
- `find`: `fd` is a strong **better than** candidate for interactive file-name searching. The **more than** choice needs to be more than simply "pipe it to `fzf`" unless the workflow justifies the distinction.
- `ps`: `procs` is worth testing as **better than**; an interactive monitor may be **more than**, although that overlaps the `top` section.
- `sed`: `sd` is an interesting **better than** candidate for common substitutions. Structural rewriting tools may be **more than** for source code.
- `man`: `tldr`/`tealdeer` may be **better for examples**, but they are not actually replacements for a manual. A good section should make that limitation explicit rather than declaring `man` obsolete.
- `netstat`: `ss` is the obvious modern Linux replacement. The **more than** choice needs to add a genuinely useful workflow rather than simply show sockets differently.
- `route`, `arp`, and `iwconfig`: these are closely related to the `ifconfig` transition and deserve their own `ip route`, `ip neigh`, and `iw` comparisons rather than being collapsed into one networking paragraph.

I also want screenshots where the visual difference is the reason for recommending a tool. `top`/`htop`/`btop`, `df`/`duf`, and `du`/`dust`/`ncdu`/`dua` are obvious candidates. For commands such as `grep` and `rg`, captured command/output pairs will probably be more useful than screenshots alone.

## References

The factual details above are based primarily on upstream project documentation and release history. The How-To Geek article is included as one source of inspiration for the legacy-command side of the list, not as the authority for project history.

- How-To Geek, [Stop Using Deprecated Linux Commands](https://www.howtogeek.com/stop-using-deprecated-linux-commands/).
- `htop`, [upstream source and history](https://github.com/htop-dev/htop).
- `btop`, [upstream source, installation notes, and release history](https://github.com/aristocratos/btop).
- `btop`, [upstream changelog](https://github.com/aristocratos/btop/blob/main/CHANGELOG.md).
- Andrew Gallant, [original 2016 introduction to ripgrep](https://github.com/BurntSushi/blog/blob/master/content/post/ripgrep.md).
- `ripgrep`, [upstream source](https://github.com/BurntSushi/ripgrep).
- `ast-grep`, [upstream source](https://github.com/ast-grep/ast-grep).
- `ast-grep`, [upstream changelog](https://github.com/ast-grep/ast-grep/blob/main/CHANGELOG.md).
- `duf`, [upstream source and installation documentation](https://github.com/muesli/duf).
- `dust`, [upstream source and installation documentation](https://github.com/bootandy/dust).
- `ncdu`, [upstream 1.x release history](https://dev.yorhel.nl/ncdu/changes).
- `ncdu`, [upstream 2.x release history](https://dev.yorhel.nl/ncdu/changes2).
- `dua`, [upstream source and installation documentation](https://github.com/Byron/dua-cli).
- `superfile`, [upstream source](https://github.com/yorukot/superfile).
- `arrans_overlay`, [`superfile-bin` Gentoo packaging](https://github.com/arran4/arrans_overlay/tree/main/app-misc/superfile-bin).
- `iproute2`, [upstream release archive at kernel.org](https://www.kernel.org/pub/linux/utils/net/iproute2/).
- NetworkManager, [`nmcli` examples and documentation source](https://github.com/NetworkManager/NetworkManager/blob/main/man/nmcli-examples.xml).
- NetworkManager, [upstream source](https://github.com/NetworkManager/NetworkManager).
- GNU, [`grep` project](https://www.gnu.org/software/grep/).
- GNU, [Coreutils](https://www.gnu.org/software/coreutils/).
- Arran Ubels, [BTOP Running in Various Terminals](/post/2025/006-btop-running-in-various-terminals/).
