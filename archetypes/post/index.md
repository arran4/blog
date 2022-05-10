---
title: "{{ replace .Name "-" " " | replaceRE "[0-9]{3}[ -]" "" | title }}"
date: {{ .Date }}
draft: false
tags: ["untagged"]
categories: ["uncategorized"]
---

