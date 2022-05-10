# blog

I guess always under development.

Found at:

https://arran4.github.io/blog/

## Random notes / snippets

### Create a new post
```bash
hugo new -k post "post/$(date +%Y)/$(printf "%03d" $(($(find content/post/$(date +%Y) -mindepth 1 -maxdepth 1 -type d | wc -l )+1)))-PostTitle"
```

### Date in right format
```bash
 date --rfc-3339=sec
```