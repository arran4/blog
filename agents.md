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

Hugo requires `_index.md` files in nested content directories (like `content/post/<year>/`) to render category listing pages correctly. If you create a new year directory or any nested directory, you must also create an `_index.md` file within it containing basic front matter (e.g., `title: <Year> Posts`). You can easily create this using a one-liner like:

```bash
echo -e "---\ntitle: 2027 Posts\n---" > content/post/2027/_index.md
```

You should verify this by running:
```bash
find content/post -mindepth 1 -maxdepth 1 -type d -print0 | while IFS= read -r -d '' dir; do
  if [ ! -f "$dir/_index.md" ]; then
    echo "Error: Missing _index.md in $dir"
  fi
done
```

## Submitting changes

All changes to this repository must be made on a non-default branch and submitted through a pull request. Do not commit changes directly to `main` or another default branch. Unless the user explicitly requests otherwise, create the pull request as a draft so the proposed content can be reviewed before merge.

Before submitting any changes, you must run the spell checker to ensure there are no spelling errors in the documentation and content files.

Run the following command:
```bash
npx cspell --config .cspell.json "README.md" "content/**/*.md"
```

When adding new words to the custom dictionary in `.cspell.json`, ensure that the `words` array remains alphabetically sorted (case-insensitive) and does not contain duplicates.

## Post Dates

When creating or modifying new articles (posts) in the blog, ensure that the `date` field in the frontmatter is updated to the current date/time on every commit. Continue to update this date on each commit until the article is first merged into the blog repository (i.e. to keep the published date matching the merge date). Once an article has been merged, its `date` should not be updated further.