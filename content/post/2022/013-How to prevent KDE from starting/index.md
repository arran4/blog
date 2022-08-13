---
title: "How to Prevent KDE From Starting"
date: 2022-08-14T01:11:45+10:00
draft: false
tags: ["bugs"]
categories: ["kde"]
---

Turns out I could crash ksplashqml quite reliably rendering
my kde setup unusable simply by having a bad `XDG_DATA_DIRS`
configured in my `.zshenv` file.

I'm not sure what caused it. But it might be because it was
already set, or that it ended with a `:`

![img.png](img.png)

--

Edit

Actually a bit more looking around and it turns out
it is if `XDG_DATA_DIRS` contains the same entry twice 
it crashes.

