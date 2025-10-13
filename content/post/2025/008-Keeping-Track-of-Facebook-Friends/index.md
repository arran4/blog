---
title: "Keeping Track of Friends on Facebook When Their Accounts Keep Disappearing"
date: 2025-07-21T12:00:00+10:00
draft: false
tags: ["facebook", "automation", "personal-process"]
categories: ["notes"]
author: "Arran Ubels"
---

It turns out the biggest challenge with Facebook these days is not the lack of a wall—it is the
friends who constantly disappear and reappear. Between account deactivations, privacy panics,
experiments with quitting social media, and the looming spectre of real-name or ID laws, profiles
blink out of existence for weeks at a time. I am terrible at keeping up with people even when the
directory stays stable, so that churn leaves me forgetting who moved, changed jobs or quietly
vanished from my digital orbit. This post documents the lightweight workflow I now use to keep a
personal "rolodex" of where everyone is and what they are up to.

The solution is not complicated: run a quick export, stash the output in a private repo and jot a
few notes about what changed. It is manual, but it gives me a stable record that survives whatever
Facebook is doing on any given week.

## Exporting the Friends List

1. Open [https://www.facebook.com/friends/list](https://www.facebook.com/friends/list) in a desktop
   browser and sign in if needed.
2. Scroll to the bottom of the page to force Facebook to load the entire list.
3. Open the developer console.
4. Paste one of the snippets below (they are the same logic tailored to Firefox and Chrome) and hit
   enter.

### Firefox console snippet

```javascript
console.log(
  Array
    .from(window.document.getElementsByTagName("a"))
    .filter((f) => Boolean(f.querySelector("span")))
    .map((f) => [f.querySelector("span").innerText, f.getAttribute("href")])
    .filter((f) => f && f[0] && new RegExp("^https://www\\.facebook\\.com/[^?/]+$").exec(f[1]))
    .sort()
    .map((e) => `${e[0]} ( ${e[1]} )`)
    .join("\n")
);
```

### Chrome (and Chromium-based) console snippet

```javascript
console.log(
  Array
    .from(window.document.getElementsByTagName("a"))
    .map((f) => [f.innerText, f.getAttribute("href")])
    .filter((f) => f && f[0] && new RegExp("^https://www\\.facebook\\.com/[^?/]+$").exec(f[1]))
    .sort()
    .map((e) => `${e[0]} ( ${e[1]} )`)
    .join("\n")
);
```

Both snippets iterate over every link on the page, collect the name and profile URL, filter out
anything that is not a canonical friend profile and log a clean "Name ( URL )" list to the
console. Copy the output into a local file named `list.txt` so you can diff it later.

## Turning the Export into a Habit

I drop the file into a private Git repository alongside a short note about what changed. Whenever I
get the itch to check in with people, I rerun the export, overwrite `list.txt` and review the diff.
If new names appear or old ones disappear, I add a reminder in my calendar or send a quick message.

This ritual sounds a little obsessive, but it keeps me anchored. The point is not surveillance—it
is a gentler way of nudging myself to reconnect with the humans behind those profile pictures.
