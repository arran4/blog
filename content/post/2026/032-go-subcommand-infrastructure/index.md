---
title: "Refactoring Go CLIs with go-subcommand and Agent Feedback Files"
date: 2026-08-06T10:42:00Z
draft: false
tags: ["Go", "CLI", "Code Generation", "LLM", "Agents", "go-subcommand", "GoReleaser"]
categories: ["Programming", "Artificial Intelligence"]
---

A Go CLI often begins with a small `main.go`, a few flags, and a switch statement. Then it grows.

Before long, `cmd/` contains argument parsing, configuration loading, filesystem access, database calls, output formatting, and the actual application logic. Adding a command means copying another block of flag handling. Testing a command means pretending to invoke the entire executable. Changing the CLI framework risks touching the whole program.

[[go-subcommand](https://github.com/arran4/go-subcommand)](https://github.com/arran4/go-subcommand) takes a different approach. The functions and their documentation comments define the command grammar, while `gosubc` generates the executable code under `cmd/`.

The important distinction is that `go-subcommand` is a standalone CLI tool used for code generation, not a runtime CLI framework. It is not a dependency, and your application does not need to import it. The generated command implementation is self-contained and dependency-free.

This changes how I structure a Go CLI:

* application logic lives outside `cmd/`;
* ordinary Go functions are the command entry points;
* comments define the CLI grammar;
* `cmd/` is generated output rather than hand-maintained infrastructure;
* GoReleaser configuration, workflows, and man pages can be generated from the same project.

It also works particularly well with coding agents. The source of truth remains small and human-readable, generated files are clearly off limits, and agents can record blockers or discoveries in structured files rather than improvising incorrect changes.

## Refactor Before Generating

The first step in converting an existing application is not to generate a new command tree. It is to remove the application from the old command tree.

Consider a backup utility with this layout:

```text
cmd/
  vault/
    main.go
    backup.go
    restore.go
    list.go
```

A typical `backup.go` might currently do all of the following:

1. declare and parse flags;
2. read the configuration file;
3. validate paths;
4. open the repository;
5. create the backup;
6. select the output format;
7. print progress and errors.

That makes `cmd/vault/backup.go` both a user-interface adapter and the implementation of the backup system.

Before introducing `gosubc`, move the actual work into a normal package:

```text
internal/
  backup/
    create.go
    restore.go
    list.go
```

The resulting API might look like this:

```go
package backup

import "time"

type CreateRequest struct {
	Config      string
	Source      string
	Destination string
	Compression string
	Timeout     time.Duration
	Verbose     bool
}

func Create(request CreateRequest) error {
	// Validate the request, open the repository, create the archive,
	// and return an error to the caller.
	return nil
}
```

The command function should translate CLI parameters into this application API. It should not contain the backup implementation itself.

For most applications, implementation code belongs in one of three places:

* `internal/` when it is specific to this repository;
* `pkg/` when it is intentionally exposed as a reusable package;
* the module root for a small application that does not benefit from another directory layer.

There is no requirement to create an elaborate package hierarchy. The important rule is simply that business logic does not remain trapped inside generated or hand-written executable code.

## The Grammar Is Written in Go Comments

`go-subcommand` does not require a separate YAML file, command registry, or invented grammar language. It reads specially formatted documentation comments attached to Go functions.

The central form is:

```go
// FunctionName is a subcommand `root parent child`
func FunctionName(...) error {
	// ...
}
```

The command path inside the backticks defines the hierarchy.

For example:

```go
// Create is a subcommand `vault backup create`
func Create(...) error {
	// ...
}
```

This produces the command path:

```console
vault backup create
```

A sibling function can define another command:

```go
// Restore is a subcommand `vault backup restore`
func Restore(...) error {
	// ...
}
```

The shared `vault backup` prefix creates the nested command structure. There is no separate section where the parent-child relationship must be registered.

The Go function signature defines the values that will be passed to the command. The documentation comment describes how CLI arguments map onto those values.

## A Practical Backup CLI Grammar

The following example describes a realistic backup application. The command functions are thin adapters around the application implementation.

```go
package vault

import (
	"time"

	"example.com/vault/internal/backup"
)

// Vault is a subcommand `vault` -- Inspect or manage the backup repository.
//
// Running vault without a child command displays the current repository
// status.
//
// Flags:
//
//   config:  -c --config  (default: "./vault.yaml") Configuration file
//   verbose: -v --verbose                           Enable verbose logging
func Vault(config string, verbose bool) error {
	return backup.Status(config, verbose)
}

// Create is a subcommand `vault backup create` -- Create a new backup.
//
// Creates a backup from a local source directory and writes it to the
// selected repository destination.
//
// Aliases: new
//
// Flags:
//
//   config:      (from parent)
//   verbose:     (from parent)
//   source:      @1                                  Directory to back up
//   destination: -d --destination (required)        Backup destination
//   compression: -z --compression (default: "zstd") Compression format
//   timeout:     --timeout (default: 30m)            Maximum operation time
func Create(
	config string,
	verbose bool,
	source string,
	destination string,
	compression string,
	timeout time.Duration,
) error {
	return backup.Create(backup.CreateRequest{
		Config:      config,
		Verbose:     verbose,
		Source:      source,
		Destination: destination,
		Compression: compression,
		Timeout:     timeout,
	})
}

// List is a subcommand `vault backup list` -- List available backups.
//
// Flags:
//
//   config:  (from parent)
//   verbose: (from parent)
//   limit:   -n --limit (default: 20) Maximum number of results
//   json:    --json                   Write machine-readable JSON
func List(config string, verbose bool, limit int, json bool) error {
	return backup.List(backup.ListRequest{
		Config:  config,
		Verbose: verbose,
		Limit:   limit,
		JSON:    json,
	})
}

// Restore is a subcommand `vault backup restore` -- Restore a backup.
//
// Restores an entire snapshot, or selected paths when additional positional
// arguments are supplied.
//
// Flags:
//
//   config:   (from parent)
//   verbose:  (from parent)
//   snapshot: @1                         Snapshot ID to restore
//   target:   -t --target (required)     Restore destination
//   force:    -f --force                 Replace existing files
//   paths:    ...                        Optional paths within the snapshot
func Restore(
	config string,
	verbose bool,
	snapshot string,
	target string,
	force bool,
	paths ...string,
) error {
	return backup.Restore(backup.RestoreRequest{
		Config:   config,
		Verbose:  verbose,
		Snapshot: snapshot,
		Target:   target,
		Force:    force,
		Paths:    paths,
	})
}
```

This one file describes:

* the root command;
* nested `backup create`, `backup list`, and `backup restore` commands;
* inherited root flags;
* aliases;
* positional arguments;
* required flags;
* default values;
* booleans;
* integers;
* durations;
* variadic positional arguments;
* short descriptions;
* extended command help.

The implementation functions remain normal Go functions. They can be called from tests, another executable, a server, or a scheduled job without constructing fake command-line arguments.

## Understanding the Parameter Grammar

A `Flags:` block maps function parameter names to their CLI representation.

| Syntax                     | Meaning                                        |
| -------------------------- | ---------------------------------------------- |
| `-v --verbose`             | Short and long flag names                      |
| `(default: 20)`            | Value used when the flag is omitted            |
| `(required)`               | The command fails if the value is not supplied |
| `(from parent)`            | Use a flag declared by an ancestor command     |
| `@1`                       | First positional argument                      |
| `@2`                       | Second positional argument                     |
| `...`                      | Remaining positional arguments                 |
| `1...3`                    | A bounded number of positional arguments       |
| `(parser: ParseValue)`     | Parse a string using a custom function         |
| `(generator: CurrentUser)` | Supply a value from code instead of a flag     |

The Go type remains important. A parameter declared as `int` is parsed as an integer. A `bool` becomes a switch. A `time.Duration` accepts values such as `30s`, `10m`, or `2h`.

Pointers preserve the difference between an omitted value and an explicitly supplied zero value. Slices support repeatable flags, while variadic parameters support remaining positional arguments. Returning an `error` lets the generated executable propagate failures to an appropriate exit status.

For a repository-specific type, a custom parser can keep conversion logic outside the generated command:

```go
// Deploy is a subcommand `infractl deploy` -- Deploy an environment.
//
// Flags:
//
//   target: --target (required; parser: ParseTarget) Deployment target
func Deploy(target Target) error {
	return RunDeployment(target)
}
```

A parser from another package can also be referenced with its import path.

## Descriptions, Aliases, and Help

The text following the command declaration becomes the short description:

```go
// Create is a subcommand `vault backup create` -- Create a new backup.
```

Additional prose becomes extended help:

```go
// Create is a subcommand `vault backup create` -- Create a new backup.
//
// Reads files from the source directory, applies exclusion rules from the
// configuration, and writes a content-addressed archive to the destination.
```

Aliases can be declared separately:

```go
// Aliases: new, add
```

or inline:

```go
// Create is a subcommand `vault backup create` (aka: new)
```

Because this information is kept beside the function, the command declaration, help text, and implementation are less likely to drift apart.

## Add the Generator

The `gosubc` tool must be run from the root of your module, in the same folder as your `go.mod` file.

You can run it directly from the web without installing using:

```console
go run github.com/arran4/go-subcommand/cmd/gosubc@latest generate
```

Or install the generator with:

```console
go install github.com/arran4/go-subcommand/cmd/gosubc@latest
```

Then add a `generate.go` file to the module:

```go
package vault

//go:generate sh -c "command -v gosubc >/dev/null 2>&1 && gosubc generate || go run github.com/arran4/go-subcommand/cmd/gosubc generate"
```

The fallback to `go run` means contributors and CI jobs do not have to install `gosubc` manually before running generation.

Run:

```console
go generate ./...
```

For the example above, the generator creates the executable infrastructure under:

```text
cmd/
  vault/
```

This generated directory contains the command parser, usage output, dispatch logic, and executable entry point. You do not need to maintain a separate `main()` function or manually register every command.

That does not mean the compiled application lacks a `main()` function. It means the generator owns it.

## Treat `cmd/` as Generated Output

Once the migration is complete, `cmd/` should be treated like any other generated directory.

Do not fix a parsing problem by editing a generated file. Change the function declaration or grammar comment and regenerate.

Do not implement a feature directly inside `cmd/vault`. Add or update the application function and regenerate.

A useful generated-code check in CI is:

```console
go generate ./...
git diff --exit-code
```

If generation changes committed files, the source grammar and generated output are out of sync.

Generated output may still be committed to the repository. Committing it makes builds reproducible without requiring the generator at ordinary build time and makes generated changes visible during review. The source of truth, however, remains the application functions and their comments.

## Inspect and Validate Before Generating

`gosubc` provides commands for inspecting the recognised grammar:

```console
gosubc list
```

This lists detected commands and is useful when checking whether functions have been discovered under the expected command paths.

Validate the grammar with:

```console
gosubc validate
```

Validation should be run before deleting the old executable. It can identify conflicting paths or invalid declarations while the original CLI is still available for comparison.

A practical migration sequence is:

1. record the existing `--help` output;
2. add tests around the current command behaviour;
3. move implementation logic out of `cmd/`;
4. add command grammar comments to the new entry functions;
5. run `gosubc list`;
6. run `gosubc validate`;
7. generate the replacement `cmd/` directory;
8. compare old and new help output;
9. run unit, integration, and CLI tests;
10. delete the old hand-written command infrastructure.

This sequence separates behavioural refactoring from generator adoption. When something breaks, it is easier to identify whether the problem came from moving the implementation or describing the CLI.

## Generate Man Pages and Release Infrastructure

The same grammar can generate Unix man pages:

```console
gosubc generate --man-dir ./man
```

Descriptions and extended help from the source comments become part of the generated documentation. That gives another reason to write useful command comments rather than placeholder text.

`gosubc` can also generate GoReleaser configuration:

```console
gosubc goreleaser
```

A GitHub Actions workflow can be included when required:

```console
gosubc goreleaser --go-releaser-github-workflow
```

Release generation should still be reviewed against what the repository actually ships. A project that only provides a library should not acquire binary packaging just because a generator supports it. For an actual CLI, however, generating the executable tree and initial release infrastructure from the same project removes a considerable amount of repeated setup.

## Why This Structure Works Well with Coding Agents

Generated command code creates an obvious boundary for an agent:

* edit application functions;
* edit command grammar comments;
* do not edit generated `cmd/` files;
* run validation and generation;
* test the result.

This is much safer than asking an agent to modify a large hand-written command tree where parsing, application logic, and output formatting are mixed together.

There is still a second problem: agents often encounter something that is relevant but cannot safely be resolved inside the current task.

Examples include:

* the old CLI accepts a flag whose behaviour is undocumented;
* an integration test requires unavailable credentials;
* two existing commands use contradictory defaults;
* the generator does not yet support a required parameter pattern;
* the agent notices an unrelated bug while moving the implementation;
* a useful command is discovered but falls outside the requested migration.

Instead of allowing the agent to guess, silently omit behaviour, or expand the task indefinitely, I use structured feedback files.

I described the broader pattern in [Using gap.md to Guide LLMs in Complex Projects]({{< ref "030-using-gap-md-for-llms" >}}). For CLI migrations, I normally use three files.

### `bug.md`

Use `bug.md` for a confirmed defect.

A useful entry includes:

```markdown
## Restore overwrites files without --force

Status: Confirmed
Found while: Migrating `vault backup restore`
Affected code: `cmd/vault/restore.go`
Reproduction: `vault backup restore abc123 --target ./existing`
Expected: Refuse to overwrite unless `--force` is supplied
Actual: Existing files are replaced
Evidence: Existing integration test documents the current result but contradicts help output
Suggested next action: Confirm intended compatibility behaviour before changing it
```

The important part is distinguishing an existing bug from a regression introduced by the migration.

### `gap.md`

Use `gap.md` when required information or infrastructure is missing.

```markdown
## Destination flag default is unknown

Status: Blocking behavioural parity
Affected command: `vault backup create`
Question: Should `--destination` be required, or default to the repository in vault.yaml?
Why this matters: The current code appears to support both behaviours depending on call path
Evidence:
- `cmd/vault/backup.go` marks the flag optional
- `internal/config/config.go` supplies a configured repository
- README examples always pass --destination
Work that can continue: Move backup implementation and define all other flags
Required decision: Select required flag or configuration fallback
```

A gap is not necessarily a software defect. It is a statement that the agent lacks enough information to make a reliable decision.

### `featurerequest.md`

Use `featurerequest.md` for a valid improvement outside the current task.

```markdown
## Add `vault backup verify`

Status: Out of scope
User value: Verify archive integrity without restoring files
Suggested grammar: `vault backup verify <snapshot>`
Possible flags:
- `--full` to read all stored objects
- `--json` for automation
Relevant implementation: Existing checksum reader in `internal/storage`
Compatibility concerns: None identified
```

This captures the idea without allowing it to derail the migration.

## A Reusable Agent Instruction

The following instruction can be placed in a task, `AGENTS.md`, or repository-specific agent guidance:

```text
When modifying this Go CLI:

1. Treat Go functions and their go-subcommand documentation comments as the
   source of truth for the CLI grammar.

2. Treat files under cmd/ as generated output. Do not hand-edit generated
   command files. Change the source function or grammar and regenerate.

3. Before generating the CLI, move non-CLI implementation out of cmd/. Prefer
   internal/ for repository-specific code, pkg/ for deliberately reusable
   packages, or the module root for a small application.

4. Preserve existing command paths, flag names, aliases, defaults, positional
   arguments, help text, exit behaviour, and error behaviour unless the task
   explicitly requests a compatibility change.

5. Run:
     gosubc list
     gosubc validate
     go generate ./...
     go test ./...

6. If a confirmed pre-existing defect is discovered, record it in bug.md with
   reproduction steps, evidence, scope, and a suggested next action.

7. If required information, access, infrastructure, or an API is missing,
   record it in gap.md. Explain why it blocks the work, what evidence was
   found, what questions must be answered, and what work can continue safely.

8. If a useful but out-of-scope improvement is discovered, record it in
   featurerequest.md with user value, proposed command grammar, implementation
   notes, and compatibility concerns.

9. Do not invent answers to gaps, silently remove existing behaviour, or
   implement unrelated feature requests merely to complete the current task.
```

These files do not have to remain permanent repository documentation. They can be reviewed, converted into GitHub issues, linked from the pull request, and removed once their contents have been resolved.

Their purpose is to give the agent a safe and productive response other than guessing.

## The Result

After migration, the repository has a clearer division of responsibility:

```text
generate.go                 Generator entry point
internal/backup/            Application implementation
commands.go                 Functions and CLI grammar
cmd/vault/                  Generated executable
man/                        Generated documentation
.goreleaser.yaml            Release configuration, when applicable
bug.md                      Confirmed incidental defects
gap.md                      Missing decisions or prerequisites
featurerequest.md           Out-of-scope improvements
```

The application is no longer organised around flag parsing. It is organised around callable Go functions, with a command grammar layered on top.

That provides several practical benefits:

* application logic is easier to test;
* command hierarchy is visible in source comments;
* the generated CLI has no runtime framework dependency;
* nested commands and flags remain consistent;
* man pages and release configuration can be generated;
* agents have an explicit boundary between source and generated output;
* blockers and incidental discoveries are recorded instead of hidden.

The main lesson is not merely to replace one CLI implementation with another. It is to stop treating `cmd/` as the application.

Move the application into ordinary Go code, describe its command grammar beside the functions, generate the disposable executable layer, and give both human and automated contributors a structured way to report what they cannot safely finish.
