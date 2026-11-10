<!-- cspell:words maxdepth mindepth -->

# blog

I guess always under development.

This blog is mostly used for agent prompt templates.

Found at:

https://arran4.github.io/blog/

Subscribe to new posts via RSS:
https://arran4.github.io/blog/index.xml

## Guidance

The repository uses the `/guidance/` URL path (e.g., `/guidance/ci-cd/`) to provide stable, currently recommended reference links for human readers and agents, avoiding hard-coded links to specific older blog posts.

## GitHub Discussions

Posts link to their own GitHub Discussions using the discussion URL in YAML
front matter. The footer shows this link conditionally; No comments widget is embedded.

The discussion sync workflow runs on main-branch post changes and can also be
dispatched manually. It reuses existing discussions, creates missing ones, and
opens a draft PR recording verified links for review. Repository Actions must
be permitted to create pull requests.

To audit locally, supply GH_TOKEN and run:
python3 .github/scripts/sync_post_discussions.py
The workflow uses --apply to create and record links.

## Random notes / snippets

### Create a new post
```bash
read -p "Post Title? " PostTitle && hugo new -k post "post/$(date +%Y)/$(printf "%03d" $(($(find content/post/$(date +%Y) -mindepth 1 -maxdepth 1 -type d | wc -l )+1)))-$PostTitle"
```

```zsh
echo "Post Title? " && read PostTitle && hugo new -k post "post/$(date +%Y)/$(printf "%03d" $(($(find content/post/$(date +%Y) -mindepth 1 -maxdepth 1 -type d | wc -l )+1)))-$PostTitle"
```

### Date in right format
```bash
 date --rfc-3339=sec
```

## License

This project is licensed under the [Creative Commons Attribution-ShareAlike 4.0 International License](LICENSE).