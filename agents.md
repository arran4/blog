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
find content/post -name "*.md" -not -name "_index.md" -print0 | while IFS= read -r -d '' file; do
  if ! head -n 1 "$file" | grep -q "^---$"; then
    echo "Error: $file is missing a front matter header."
    # do not exit 1 directly inside while loop as it fails the bash environment
  fi
done
```

## Nested Directories

Hugo requires `_index.md` files in nested content directories (like `content/post/<year>/`) to render category listing pages correctly. If you create a new year directory or any nested directory, you must also create an `_index.md` file within it containing basic front matter (e.g., `title: <Year> Posts`).

You should verify this by running:
```bash
find content/post -mindepth 1 -maxdepth 1 -type d -print0 | while IFS= read -r -d '' dir; do
  if [ ! -f "$dir/_index.md" ]; then
    echo "Error: Missing _index.md in $dir"
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
