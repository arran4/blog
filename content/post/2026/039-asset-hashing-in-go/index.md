---
title: "Asset Hashing in Go: Cache Busting Web Resources"
date: 2026-08-27T13:38:30+00:00
draft: false
tags: ["Go", "Web Development", "Templates", "Cache Busting"]
categories: ["Programming"]
---

When building web applications, you often encounter a common frustration: you update a CSS or JavaScript file, deploy the new version, and your users complain that the site looks broken. The culprit? Browser caching.

Browsers cache static assets to improve load times, which is generally a good thing. But when an asset changes, the browser might still serve the stale, cached version. The solution to this problem is **cache busting**, and a robust way to implement it is through **asset hashing**.

In this post, we'll explore an elegant asset hashing implementation in Go, inspired by the [`goa4web` framework](https://github.com/arran4/goa4web/blob/b09a4e2a4009aa9efd9f61ff39fc8b28ddcf297a/core/templates/templates.go#L196-L198).

## What is Asset Hashing?

Asset hashing involves generating a unique identifier (a hash) based on the file's contents and appending it to the file's URL—often as a query parameter (e.g., `/css/styles.css?v=a1b2c3d4`).

When the file changes, its contents change, resulting in a new hash. This forces the browser to treat it as a completely new resource and download the latest version, immediately reflecting your updates. When the file hasn't changed, the hash remains the same, and the browser safely uses its cached copy.

## The `goa4web` Implementation

Let's look at how the `goa4web` project tackles this problem natively in Go using `html/template`.

First, a custom template function is registered when compiling the site templates:

```go
funcs["assetHash"] = func(p string) string {
    return GetAssetHash(p, opts...)
}
```

This makes the `assetHash` function available inside HTML templates.

The heavy lifting is done in the `GetAssetHash` function:

```go
func GetAssetHash(webPath string, opts ...Option) string {
    cfg := newCfg(opts...)
    base := path.Base(webPath)

    // Development mode
    if cfg.Dir != "" {
        b, err := getAssetContent(base, cfg)
        if err != nil {
            return webPath
        }
        sum := sha256.Sum256(b)
        h := hex.EncodeToString(sum[:])[:16]
        return webPath + "?v=" + h
    }

    // Production mode (cached)
    assetHashesLock.RLock()
    h, ok := assetHashes[base]
    assetHashesLock.RUnlock()
    if ok {
        return webPath + "?v=" + h
    }

    // (If not in cache, it would compute it once and store it in assetHashes)
    // ...
}
```

### Development vs. Production Modes

This implementation cleverly distinguishes between development and production environments using a configuration flag (`cfg.Dir != ""`):

1. **Development Mode:** If the app is configured to serve assets from a local directory (meaning developers are actively modifying files), the hash is recomputed *on every single request*. It reads the file, calculates the SHA-256 hash, and appends it to the URL. This ensures developers see their changes instantly without restarting the Go server.
2. **Production Mode:** In production (where assets are likely embedded into the binary using `go:embed` and don't change at runtime), computing the hash on every request is a waste of CPU. Instead, the function checks an in-memory map (`assetHashes`), protected by an `sync.RWMutex`. The hash is calculated just once on startup (or on the first request) and then cached indefinitely.

## How to Set It Up in Your Go App

To implement this pattern in your own Go web applications, here is what you need:

### 1. Requirements

*   **File Reading:** A way to read the asset files. You can use the `os` package during development, and Go 1.16+'s `go:embed` package for production deployment.
*   **Cryptography:** The `crypto/sha256` standard library package to compute the secure hash of the file contents.
*   **Encoding:** The `encoding/hex` package to convert the raw byte hash into a readable string.
*   **Templates:** The `html/template` package to inject the hash into your HTML pages.

### 2. Implementation Steps

**Step 1: Write the Hashing Logic**
Create a function that reads the file content, calculates its SHA-256 hash, and returns the first few characters of the hex string (16 characters is plenty to avoid collisions for web assets).

```go
import (
    "crypto/sha256"
    "encoding/hex"
    "os"
)

func generateHash(filepath string) (string, error) {
    bytes, err := os.ReadFile(filepath)
    if err != nil {
        return "", err
    }
    sum := sha256.Sum256(bytes)
    return hex.EncodeToString(sum[:])[:16], nil
}
```

**Step 2: Add it to your Template FuncMap**
When parsing your HTML templates, register your function so it can be invoked directly from the HTML.

```go
import "html/template"

func main() {
    funcMap := template.FuncMap{
        "assetHash": func(path string) string {
            // In a real app, integrate the Dev/Prod logic here!
            hash, err := generateHash("public" + path)
            if err != nil {
                return path // Fallback to unhashed path on error
            }
            return path + "?v=" + hash
        },
    }

    tmpl := template.Must(template.New("").Funcs(funcMap).ParseFiles("index.html"))
    // Execute template...
}
```

**Step 3: Use it in your HTML**
Finally, update your HTML files to wrap asset paths in the new template function.

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Before: -->
    <!-- <link rel="stylesheet" href="/css/styles.css"> -->

    <!-- After: -->
    <link rel="stylesheet" href="{{ assetHash "/css/styles.css" }}">
</head>
<body>
    <script src="{{ assetHash "/js/app.js" }}"></script>
</body>
</html>
```

When rendered, the output will look something like this:

```html
<link rel="stylesheet" href="/css/styles.css?v=8f434346648f6b96">
<script src="/js/app.js?v=9a8b7c6d5e4f3g2h"></script>
```

## Conclusion

Asset hashing is a necessary pattern for any serious web application to ensure users are always running the latest client-side code. By leveraging Go's standard library `crypto/sha256` and custom template functions, you can implement a powerful, cache-busting asset manager that is fast in production and seamless during development.
