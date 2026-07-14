---
title: "Imagining a JavaScript-less SPA World"
date: 2025-07-21T10:25:01+10:00
draft: false
tags: ["javascript", "webdev", "standards"]
categories: ["notes"]
author: "Arran Ubels"
---

A brain dump exploring what browsers might need in order to deliver the snappy feel of today’s single page apps without any JavaScript. The idea came from asking ChatGPT to outline a true "JS‑free" SPA.

## The Core Idea

- **New form attributes**
  - `async` to fetch responses without a full reload
  - `update="#target"` to inject the returned fragment into a selector
- **CSS pseudo-classes**
  - `:loading` to style the in-flight state for spinners and disabled buttons

With only HTML and CSS we could get async submission, live loading indicators and partial DOM updates.

## Working with Current APIs

Progressive enhancement would still rely on a plain `<form>` fallback. Today you can hack around it with hidden iframes and CSS-only tricks, but real apps still need bits of JS.

## What Browsers Would Need

- **HTML**: define the `async` boolean on forms and an `update` attribute for selectors.
- **CSS**: introduce `:loading`, `:error`, `:idle` and other states tied to network activity.
- **Fetch & Insert**: the browser would fetch the form and swap the returned fragment into the update target automatically.
- **Error & Progress**: declarative hooks for status messages and retries.

## Example Markup

Below is a minimal page showing how a browser **could** handle an asynchronous
form without any scripting:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Async Form without JS</title>
  <style>
    /* hide the loader by default */
    form[async] .loader { display: none; }
    /* when the form is in-flight, show the loader */
    form[async]:loading .loader { display: inline-block; }
  </style>
</head>
<body>

  <!--
    async  → tell the browser "do this submission via XHR/fetch under the hood"
    update → CSS selector for where to inject the response HTML
  -->
  <form action="/subscribe" method="post" async update="#message">
    <label>
      Email
      <input type="email" name="email" required>
    </label>
    <button type="submit">Subscribe</button>
    <!--
      this element is automatically shown while the request is pending,
      thanks to the :loading pseudo-class above
    -->
    <span class="loader">Sending…</span>
  </form>

  <!-- server can return just a fragment of HTML to replace this -->
  <div id="message"></div>

</body>
</html>
```

The important rule is:

```css
form:loading .loader {
  display: inline-block;
}
```

## Accessibility

These features would need to map `:loading` to `aria-busy="true"`, manage focus on injected content and announce loading messages to screen readers.

## Interim Solutions

Libraries like **htmx** or **Hotwire Turbo** offer much of this with small JavaScript payloads, but native support would further reduce complexity and script overhead.

## Wider Implications

Faster initial loads, fewer XSS vectors and simpler build pipelines. But questions remain around file uploads, push updates and standardising declarative error handling.

## Why We Write So Much JavaScript

Modern frameworks evolved as workarounds for gaps in HTML and CSS. Much of the code in today’s apps simply compensates for missing browser features. When the template element shipped, frameworks didn’t vanish—they became leaner and new ones emerged. Similar declarative network controls could again lighten our toolkits. Some resistance may come from developers who are understandably attached to the frameworks they know best.

## Open Questions

The markup above doesn’t address routing or persistent state. A future spec might allow reading and writing to local or session storage without scripts, perhaps via form-backed inputs or special attributes. There is still plenty to explore in how a JS-less UI would manage client-side data.

Feedback is welcome—what other features would you want to see in a JS‑less world?
