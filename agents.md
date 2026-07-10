# Agent Instructions

## Content Conventions

All markdown posts must have a valid hugo front matter header containing at least:
- title
- date
- draft
- tags
- categories

You should check that all files have valid front matter headers. For example, using a simple grep command:
```bash
for file in $(find content/post -name "*.md" -not -name "_index.md"); do
  if ! head -n 1 "$file" | grep -q "^---$"; then
    echo "Error: $file is missing a front matter header."
    exit 1
  fi
done
```

## Submitting changes
Before submitting any changes, you must run the spell checker to ensure there are no spelling errors in the documentation and content files.

Run the following command:
```bash
npx cspell --config .cspell.json "README.md" "content/**/*.md"
```

## Dependency and Version Management

When upgrading or managing dependencies, you must adhere strictly to the following rules:
- **Never Downgrade:** You must never downgrade Go, or any other tool or dependency (e.g., in `go.mod`, `package.json`, `pubspec.yaml`) to resolve an issue without explicit permission from the user. If an issue cannot be resolved without a downgrade, you should submit a partial fix and let CI fail rather than attempting a downgrade.
- **Use Generic Tags and Keywords:** Use generic major tags (like `@v9`) for actions and keywords like `latest` (e.g., `version: latest`) instead of rigidly pinning to minor or patch versions unless otherwise instructed by the user.
- **Respect Minimum Versions:** You must respect minimum version bounds specified in this `agents.md` file, `go.mod`, `package.json`, and `pubspec.yaml` (or any equivalent manifest file). Do not propose changes that lower these minimum bounds.
