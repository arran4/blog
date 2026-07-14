---
title: "Automated Sieve Testing with Cargo"
date: 2025-06-18T13:36:23+10:00
draft: false
tags: ["sieve", "rust", "testing"]
categories: ["tutorial"]
---


In my earlier posts I uploaded Sieve filters straight to the server using GitHub Actions. That worked well until a typo slipped through and broke my inbox. To catch those mistakes before deploying I created a small Rust project that runs my Sieve rules against a set of example messages. The tests run locally and in pull requests so I can fix issues early.

## Project layout

The test harness lives in a new Cargo project. Running `cargo init` creates the structure and a `Cargo.toml` file. Add the following dependencies:

```toml
[dependencies]
sieve-rs = "0.7"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

`sieve-rs` compiles and executes the filter, while `serde` and `serde_json` load the expected results for each test case.

Create `src/lib.rs` with a helper that compiles a Sieve script, feeds it a message and returns the actions requested by the script. The function checks for `fileinto` and `\Seen` flags so we can assert on them in tests.

```rust
use sieve::{Compiler, Event, Input, Runtime};

#[derive(Default, Debug)]
pub struct ActionResult {
    pub fileinto: Vec<String>,
    pub flags: Vec<String>,
}

pub fn actions_for_message(script: &[u8], message: &str) -> ActionResult {
    let compiler = Compiler::new();
    let compiled = compiler.compile(script).expect("compile sieve");
    let runtime = Runtime::new();
    let mut instance = runtime.filter(message.as_bytes());
    let mut input = Input::script("test", compiled);
    let mut result = ActionResult::default();

    while let Some(run) = instance.run(input) {
        match run {
            Ok(event) => match event {
                Event::FileInto { folder, flags, .. } => {
                    result.fileinto.push(folder);
                    result.flags.extend(flags);
                    input = true.into();
                }
                Event::Keep { flags, .. } => {
                    result.flags.extend(flags);
                    input = true.into();
                }
                Event::MailboxExists { .. }
                | Event::ListContains { .. }
                | Event::DuplicateId { .. } => input = false.into(),
                Event::IncludeScript { .. } => input = true.into(),
                _ => input = true.into(),
            },
            Err(_) => break,
        }
    }

    result
}
```

With this helper in place you can write normal Rust tests. Each test loads an `.eml` file and a matching `.json` file describing the expected folder and flags. Here's an example case for a GitHub notification:

```rust
#[test]
fn github_routing() {
    let script = std::fs::read("stalwart.sieve").unwrap();
    let message = std::fs::read_to_string("testcases/github_notification.eml").unwrap();
    let expected: Expected = serde_json::from_str(&std::fs::read_to_string(
        "testcases/github_notification.json",
    ).unwrap()).unwrap();
    let result = actions_for_message(&script, &message);
    assert_eq!(result.fileinto, expected.fileinto);
    let seen = result.flags.iter().any(|f| f == "\\Seen");
    assert_eq!(seen, expected.seen);
}
```

### Test messages

Place sample emails under `testcases/`. For each message there is a `.eml` file with the raw headers and a `.json` file describing the expected result. For instance, a DMARC report looks like:

```text
From: noreply-dmarc@example.com
To: user@example.com
Subject: DMARC Authentication Failure Report

Body
```

And the matching JSON:

```json
{
  "fileinto": ["Inbox/dmarc"],
  "seen": true
}
```

The GitHub notification example follows the same pattern but files the message into a repository specific folder.

## Continuous integration

A small workflow in `.github/workflows/tests.yml` runs the tests whenever `stalwart.sieve` or the Rust code changes:

```yaml
name: Test Sieve scripts
on:
  push:
    paths:
      - 'stalwart.sieve'
      - 'Cargo.toml'
      - 'src/**'
      - 'testcases/**'
      - '.github/workflows/tests.yml'
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          override: true
      - name: Install dependencies
        run: sudo apt-get update
      - name: Run tests
        run: cargo test --all-features --locked
```

Because everything runs in a local Rust process the workflow works even in restricted environments. Running `cargo test` locally gives the same result as CI, so you can confidently merge pull requests once the tests pass.

*This post was written with the assistance of an AI tool.*
