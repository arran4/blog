---
title: "BTOP Running in Various Terminals"
date: 2025-07-16T00:00:00+10:00
draft: false
tags: ["btop", "linux", "terminals"]
categories: ["tools"]
author: "Arran Ubels"
---

`btop` is one of my favourite system monitoring tools. It works well in most terminal emulators, but some quirks pop up depending on the environment. Below are a few quick notes on how it behaves in different terminals I have used recently.

## Windows Terminal

Using `btop` inside **Windows Terminal** under WSL works perfectly. Colours and mouse support behave just like they do on Linux.

## Kitty

In Kitty the experience is also solid, though I needed to tweak the font size for better alignment.

## tmux

When running inside `tmux`, `btop` initially refused to render correctly. Adding `TERM=screen-256color` before launching fixed the issue.

Overall `btop` is portable, but sometimes a small configuration change is required for everything to look right.
