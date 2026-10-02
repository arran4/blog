---
title: "Readable Test Fixtures: Prefer Named Data Over Opaque Bytes"
date: 2026-10-02T09:57:27+10:00
draft: false
tags:
  - go
  - testing
  - fixtures
  - embed
  - http
categories:
  - Testing
  - Software Development
---

<!-- cspell:words httptest testdata txtar -->

A test fixture is part of the test's explanation. If a reviewer cannot tell what a fixture represents, the test has lost an important part of its documentation.

The clearest example is binary data written directly into a Go string:

```go
w.Write([]byte("PK\\x03\\x04\\x14\\x00\\b\\x00..."))
```

It may be technically correct, but it is effectively opaque. A reviewer cannot reasonably inspect the archive, update it safely, or tell whether a one-byte change is intentional.

My default is now: **do not inline substantial binary protocol or archive data in a test body. Give it a name and a representation that matches what the test cares about.**

## If exact bytes matter, use a named embedded fixture

When the precise encoded bytes are the contract, put the fixture in `testdata` and embed it:

```go
//go:embed testdata/module-v1.0.0.zip
var moduleV100Zip []byte
```

The test becomes descriptive:

```go
proxy := newProxy(t, map[string]response{
    "/example/module/@v/v1.0.0.zip": {
        ContentType: "application/zip",
        Body:        moduleV100Zip,
    },
})
```

The binary file can be inspected with ordinary archive tooling, replaced deliberately, and reused by more than one case.

`go:embed` is especially useful here because the test no longer depends on its working directory and does not need to copy the fixture to disk merely to read it.

## If archive structure matters, generate the bytes from readable input

Often the exact ZIP encoding does not matter. The test only needs a valid archive containing particular files.

In that case, a builder is better than committing a binary:

```go
zipData := mustZip(t, map[string][]byte{
    "example/module@v1.0.0/go.mod": []byte(`module example/module
go 1.22
`),
    "example/module@v1.0.0/module.go": []byte("package module\n"),
})
```

This is readable in code review and keeps the archive in memory.

For larger trees, a `txtar` fixture can make the source even clearer:

```txt
-- example/module@v1.0.0/go.mod --
module example/module
go 1.22
-- example/module@v1.0.0/module.go --
package module
```

The test helper can turn that readable tree into whatever archive format the protocol needs.

## Choose representation according to the assertion

A useful rule is:

| What the test cares about | Fixture representation |
| --- | --- |
| exact binary bytes | named embedded binary fixture |
| files contained in an archive | readable map or txtar, then build in memory |
| path/tree discovery | `fstest.MapFS` |
| one small text request/response | inline string or byte slice |
| many protocol responses | declarative response table plus embedded/text fixtures |

The fixture should make the important property obvious and hide incidental encoding detail.

## Large HTTP switches are another form of opaque fixture setup

This works for a tiny test server:

```go
switch r.URL.Path {
case "/v1/info":
    w.Write(info)
case "/v1/mod":
    w.Write(mod)
case "/v1/archive":
    w.Write(archive)
}
```

It becomes difficult to read when a test adds many modules, versions, status cases, headers, and alternate responses.

Prefer a small declarative server helper:

```go
type response struct {
    Status      int
    ContentType string
    Body        []byte
}

func newFixtureServer(t testing.TB, routes map[string]response) *httptest.Server {
    t.Helper()
    return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        route, ok := routes[r.URL.Path]
        if !ok {
            http.NotFound(w, r)
            return
        }
        if route.ContentType != "" {
            w.Header().Set("Content-Type", route.ContentType)
        }
        status := route.Status
        if status == 0 {
            status = http.StatusOK
        }
        w.WriteHeader(status)
        _, _ = w.Write(route.Body)
    }))
}
```

Then the test describes the protocol fixture rather than implementing a miniature server inline:

```go
server := newFixtureServer(t, map[string]response{
    "/example/module/@v/v1.0.0.info": {Body: infoData},
    "/example/module/@v/v1.0.0.mod":  {Body: modData},
    "/example/module/@v/v1.0.0.zip":  {ContentType: "application/zip", Body: zipData},
})
```

If request validation matters, make that part explicit too: record requests, declare expected methods or headers, and compare the recorded requests after the operation.

## Embed a fixture tree when the protocol is mostly static data

A larger fake service can use a whole embedded directory:

```go
//go:embed testdata/proxy
var proxyFixtureFS embed.FS
```

A helper can map request paths to files below that root. This keeps protocol data out of Go control flow while still allowing tests to override individual responses for failures.

The same principle applies to JSON APIs, HTML fixtures, package registries, mail messages, and generated source corpora.

## Do not make binary fixtures mysterious

An embedded binary fixture should have provenance.

Prefer at least one of:

- a nearby readable source fixture from which it can be regenerated;
- a small generator helper or command;
- a comment explaining what property makes the binary special;
- a deterministic generation test if exact bytes are expected to remain stable.

Otherwise an opaque file merely moves the mystery from a Go literal into `testdata`.

## Standard practice

For test fixtures:

- never inline large escaped binary blobs in a test body;
- use `go:embed` for named exact-byte fixtures when encoded bytes are important;
- generate archives in memory from readable maps or txtar when archive contents are what matter;
- prefer declarative HTTP response tables over large path switches;
- keep static protocol data in fixture files rather than control flow;
- make fixture provenance or regeneration obvious when binary bytes are checked in.

A good fixture lets the reviewer understand the scenario before running the test.
