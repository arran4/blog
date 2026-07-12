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

When adding new words to the custom dictionary in `.cspell.json`, ensure that the `words` array remains alphabetically sorted (case-insensitive) and does not contain duplicates.
