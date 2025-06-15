# blog

I guess always under development.

Found at:

https://arran4.github.io/blog/

Subscribe to new posts via RSS:
https://arran4.github.io/blog/index.xml

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