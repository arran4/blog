---
title: "Effective Error Handling in Go: Wrapping, Sentinels, and Custom Types"
date: 2026-07-10T13:32:59+10:00
draft: false
tags:
  - golang
  - error-handling
  - programming
  - best-practices
categories:
  - Software Development
  - Go
---

Error handling in Go is straightforward, explicit, and forces developers to deal with failure states right at the point of origin. While `if err != nil` is a running joke in the community, when used correctly, Go's error handling produces robust, debuggable, and maintainable software.

In my Go projects, I adhere to a set of practices that ensure errors are not just checked, but are rich with context and actionable. Let's dive into how I handle errors effectively.

## 1. Sentinel Errors: The Bedrock of Predictability

Sentinel errors are predefined error variables that indicate a specific, expected failure condition. They act as "sentinels" that your code can watch out for.

```go
package user

import "errors"

// Sentinel errors
var (
	ErrNotFound           = errors.New("user not found")
	ErrInvalidEmail       = errors.New("invalid email format")
	ErrDatabaseConnection = errors.New("database connection failed")
)
```

Using sentinel errors allows callers to confidently check for specific failures without parsing error strings (which is brittle and prone to breaking on typos or refactors).

## 2. Wrapping Errors: Adding Crucial Context

When an error occurs deep within a call stack, simply returning it up the chain strips away valuable context. When the error finally surfaces, it might just say `"no such file or directory"`, leaving you wondering *which* file and *why* it was being accessed.

Go 1.13 introduced error wrapping using the `%w` verb in `fmt.Errorf`, and Go 1.20 added the ability to use multiple `%w` verbs in a single `fmt.Errorf` call. This is crucial for building an informative trail.

### The Rule of Thumb: Wrap Generously

Whenever you pass an error up the stack, wrap it with context about what you were trying to do.

```go
func processUserFile(filename string) error {
    file, err := os.Open(filename)
    if err != nil {
        // We wrap the sentinel/os error and provide details using multiple %w verbs
        // Note: os.Open's error often contains the filename already, but wrapping
        // ensures we capture the context if the failure happens elsewhere (like read/close).
        return fmt.Errorf("failed to open user config %w: %w", ErrNotFound, err)
    }
    defer file.Close()

    // ...
    return nil
}
```

Notice the pattern here: `fmt.Errorf("(details if necessary) %w: %w", sentinel error, nested error)`.

**Desirable Consequences:**
- **Debuggability:** When an error is logged at the top level, it prints a complete sentence explaining the failure chain: `"failed to open user config user not found: open /etc/config.json: no such file or directory"`.
- **Traceability:** You can see exactly which layers of your application the error passed through.

*Tip: Er on the side of adding more context rather than less.*

## 3. Extracting and Checking: `errors.Is` and `errors.As`

Because we are heavily wrapping errors, we can no longer simply use equality (`err == ErrNotFound`) to check for sentinel errors. The original error is buried inside layers of `fmt.Errorf`.

This is where `errors.Is` and `errors.As` come in.

### `errors.Is` for Sentinels

Use `errors.Is` to check if a specific sentinel error exists anywhere in the chain.

```go
err := processUserFile("missing.json")
if errors.Is(err, ErrNotFound) {
    // Handle the specific 'not found' case
    fmt.Println("Looks like the file is missing, falling back to defaults.")
}
```

You can also use a `switch` statement when checking against multiple specific sentinels. This approach scales beautifully, especially when handling special cases like `io.EOF`:

```go
err := performAction()
switch {
case errors.Is(err, io.EOF):
    // EOF often requires different handling, such as silently returning
    // rather than treating it as a true error.
    return nil
case errors.Is(err, ErrNotFound):
    return handleNotFound()
case err != nil:
    // A catch-all for any other error
    return fmt.Errorf("unexpected error occurred: %w", err)
}
```

### `errors.As` for Custom Types

Use `errors.As` when you need to extract a specific *type* of error from the chain to access its fields.

```go
var pathErr *os.PathError
if errors.As(err, &pathErr) {
    fmt.Println("Failed operation:", pathErr.Op)
    fmt.Println("Failed path:", pathErr.Path)
}
```

## 4. Custom Error Types for HTTP Handling

Sometimes, simple string-based errors aren't enough. When dealing with HTTP servers, you often need to attach HTTP status codes and user-facing messages to your internal errors.

Creating custom error types is highly effective here.

```go
package httperr

import "fmt"

// UserError represents an error that can be safely returned to a client
type UserError struct {
    StatusCode int
    Message    string
    Err        error // The underlying internal error
}

func (e *UserError) Error() string {
    if e.Err != nil {
        return fmt.Sprintf("HTTP %d - %s: %v", e.StatusCode, e.Message, e.Err)
    }
    return fmt.Sprintf("HTTP %d - %s", e.StatusCode, e.Message)
}

// Unwrap allows errors.Is and errors.As to work with the wrapped error.
// If multiple errors were wrapped, Go 1.20+ supports returning a slice: func (e *UserError) Unwrap() []error
func (e *UserError) Unwrap() error {
    return e.Err
}

// Helper for easy creation
func NewUserError(status int, msg string, err error) error {
    return &UserError{
        StatusCode: status,
        Message:    msg,
        Err:        err,
    }
}
```

### Using Custom Errors in Handlers

In your HTTP handlers or middleware, you can inspect the error chain to see if a `UserError` was returned. If it was, you extract the status code and message. If not, you default to a safe 500 Internal Server Error, ensuring internal implementation details don't leak to the client.

```go
func myHandler(w http.ResponseWriter, r *http.Request) {
    err := performAction()
    if err != nil {
        handleHTTPError(w, err)
        return
    }
    w.WriteHeader(http.StatusOK)
}

func handleHTTPError(w http.ResponseWriter, err error) {
    var uErr *UserError

    // Check if the error chain contains a UserError
    if errors.As(err, &uErr) {
        // We found a UserError, safely return its details
        http.Error(w, uErr.Message, uErr.StatusCode)
        // Log the internal error for debugging
        log.Printf("Request failed: %v", uErr.Err)
        return
    }

    // Fallback: If it's not a UserError, it's an unexpected internal error
    log.Printf("Internal Server Error: %v", err)
    http.Error(w, "Internal Server Error", http.StatusInternalServerError)
}
```

## 5. When Not To Use Errors: Application Outcomes vs. Unexpected Faults

While robust error handling is critical, it is equally important to recognize when *not* to use errors, or at least how to categorize them properly to avoid unnecessary noise like stack traces or panics.

### Application Outcomes Are Not Always Errors

If you are building an application designed to informatively exit successfully or unsuccessfully—such as a linter, a validation tool, or a sanity checking sort of app used in a script—a failure in validation is often an expected outcome, not a system error. While returning an error to represent these states is common in Go, treating them as exceptional system failures is what we want to avoid.

Technically, a linter finding a violation is an `ApplicationOutcome`, not an `ApplicationOutcomeError`. There was no system failure, so there is absolutely no reason to create a stack trace. Structuring your program to return an outcome result rather than an error for these expected states keeps your application logic clean and prevents expected failures from being treated as catastrophic system crashes.

### User Errors vs. Unexpected Outcomes

Similarly, we must distinguish between errors caused by the user (like providing invalid input) and truly unexpected system faults.

User-caused errors do not need a stack trace. They should be handled gracefully using custom types, much like the `UserError` discussed above. When encountering a user error, you should inform the user of what they did wrong and exit cleanly, without causing a panic (e.g., never use `log.Panic` for invalid input).

Stack trace logs and panics should be strictly limited to unexpected outcomes—situations where the system enters an invalid state and we cannot immediately pinpoint the blame to user input. By reserving stack traces for actual bugs, you ensure that your logs remain actionable and aren't cluttered with user mistakes.


## Conclusion

By defining clear sentinel errors, generously wrapping errors with contextual information, and leveraging `errors.Is`, `errors.As`, and custom error types, you transform Go's error handling from a tedious chore into a powerful tool for building resilient systems. It takes slightly more typing up front, but pays massive dividends when debugging production issues at 3 AM.
