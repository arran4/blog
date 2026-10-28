#!/usr/bin/env python3
"""Match published Hugo posts to GitHub Discussions; --apply saves direct URLs."""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

DISCUSSION_URL = re.compile(r"https://github\.com/arran4/blog/discussions/\d+/?")
POST_PATH = re.compile(r"/blog/post/(\d{4})/([^/]+)/", re.I)
FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---(?=\r?\n|$)", re.S)
LIST = """
query($owner:String!, $name:String!, $after:String) {
  repository(owner:$owner,name:$name) {
    id
    discussionCategories(first:100) { nodes { id name } }
    discussions(first:100,after:$after) {
      nodes { id title url body }
      pageInfo { hasNextPage endCursor }
    }
  }
}
"""
CREATE = """
mutation($repo:ID!, $category:ID!, $title:String!, $body:String!) {
  createDiscussion(input:{repositoryId:$repo,categoryId:$category,title:$title,body:$body}) {
    discussion { id title url body }
  }
}
"""

def graphql(query, vars):
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query":query,"variables":vars}).encode(),
        headers={"Authorization":f"Bearer {token}", "Accept":"application/vnd.github+json",
                 "Content-Type":"application/json", "User-Agent":"arran4-blog-discussion-sync"})
    with urllib.request.urlopen(req, timeout=40) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError(f"GitHub GraphQL: {data['errors']}")
    return data["data"]

def key(year, slug):
    return (year, re.sub(r"[^\w]+", "-", urllib.parse.unquote(slug).casefold()).strip("-"))

def field(header, name):
    match = re.search(r"^"+re.escape(name)+r":\s*(.*?)\s*$", header, re.M)
    return match.group(1).strip().strip("'\"") if match else None

def posts():
    for path in sorted(Path("content/post").glob("*/*/index.md")):
        source = path.read_text(encoding="utf-8")
        match = FRONT.match(source)
        if not match:
            raise RuntimeError(f"Missing YAML front matter: {path}")
        header = match.group(1)
        if (field(header, "draft") or "").lower() == "true":
            continue
        title = field(header, "title")
        if not title or title in ("|", ">"):
            raise RuntimeError(f"Missing or unsupported title: {path}")
        yield {"path":path, "source":source, "end":match.end(),
               "title":title, "key":key(path.parent.parent.name,path.parent.name),
               "discussion":field(header,"discussion")}

def discussions():
    items, cursor, repository = [], None, None
    while True:
        data = graphql(LIST, {"owner":"arran4","name":"blog","after":cursor})
        repository = data["repository"]
        if not repository:
            raise RuntimeError("Repository is unavailable to the token")
        conn = repository["discussions"]
        items += conn["nodes"]
        if not conn["pageInfo"]["hasNextPage"]:
            return repository,items
        cursor = conn["pageInfo"]["endCursor"]

def paths(d):
    result = set()
    for value in (d["title"],d.get("body") or ""):
        result.update(key(*match.groups()) for match in POST_PATH.finditer(value))
    return result

def choose_discussion(post, matches):
    """Prefer the correctly titled post discussion over legacy blank-title duplicates.

    Fail rather than guessing when multiple matching, correctly titled
    discussions exist, or when the candidates cannot be distinguished.
    """
    unique = {d["url"]: d for d in matches}
    if len(unique) > 1:
        titled = [d for d in unique.values()
                  if d["title"].split(" - /blog/post/", 1)[0].strip() == post["title"]]
        if len(titled) == 1:
            return titled[0]
        raise RuntimeError(f"Ambiguous discussions for {post['path']}: {list(unique)}")
    return next(iter(unique.values()), None)

def insert_link(post, url):
    if not DISCUSSION_URL.fullmatch(url):
        raise RuntimeError(f"Unexpected discussion URL: {url}")
    source, end = post["source"], post["end"]
    marker = re.search(r"\r?\n---(?=\r?\n|$)", source[4:end])
    if marker is None:
        raise RuntimeError(f"Malformed front matter: {post['path']}")
    where = marker.start()+4
    post["path"].write_text(source[:where]+'\ndiscussion: "'+url+'"'+source[where:],
                            encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Create discussions and update files")
    args = parser.parse_args()
    repo_name = os.environ.get("GITHUB_REPOSITORY","arran4/blog")
    if repo_name != "arran4/blog":
        raise RuntimeError(f"Refusing another repository: {repo_name}")
    entries = list(posts())
    title_counts = Counter(p["title"] for p in entries)
    if len({p["key"] for p in entries}) != len(entries):
        raise RuntimeError("Ambiguous post directory names after normalization")
    repo,all_discussions = discussions()
    category = next((c["id"] for c in repo["discussionCategories"]["nodes"]
                     if c["name"] == "Announcements"),None)
    if not category:
        raise RuntimeError("Missing Announcements discussion category")
    by_path,by_title,by_url = defaultdict(list),defaultdict(list),{}
    for d in all_discussions:
        by_url[d["url"].rstrip("/")] = d
        for path_key in paths(d):
            by_path[path_key].append(d)
        if " - /blog/post/" in d["title"] or "A new blog post" in (d.get("body") or ""):
            by_title[d["title"].split(" - /blog/post/",1)[0].strip()].append(d)
    assigned = {}
    created,updated,existing,missing = 0,0,0,0
    for post in entries:
        old = post["discussion"]
        matches = by_path.get(post["key"],[])
        if not matches and title_counts[post["title"]]==1:
            matches = by_title.get(post["title"],[])
        candidate = choose_discussion(post, matches)
        if old:
            if not DISCUSSION_URL.fullmatch(old):
                raise RuntimeError(f"Invalid discussion URL for {post['path']}: {old}")
            d = by_url.get(old.rstrip("/"))
            if not d:
                raise RuntimeError(f"Broken existing discussion URL: {post['path']}: {old}")
            if candidate and candidate["url"].rstrip("/") != old.rstrip("/"):
                raise RuntimeError(f"Conflicting discussions: {post['path']}")
            existing += 1
        elif candidate:
            d = candidate
        else:
            missing += 1
            if not args.apply:
                print(f"Would create: {post['path']}")
                continue
            year,normalized_slug = post["key"]
            site_url = f"https://arran4.github.io/blog/post/{year}/{urllib.parse.quote(normalized_slug)}/"
            slug = post["path"].parent.name
            d = graphql(CREATE, {"repo":repo["id"],"category":category,
                "title":f"{post['title']} - /blog/post/{year}/{slug}/",
                "body":f"A new blog post has been published: **{post['title']}**! "
                       f"Read it at <{site_url}>. @arran4"})["createDiscussion"]["discussion"]
            by_url[d["url"].rstrip("/")] = d
            created += 1
            time.sleep(1)
        url = d["url"].rstrip("/")
        if url in assigned and assigned[url] != post["path"]:
            raise RuntimeError(f"Discussion shared by posts: {post['path']} and {assigned[url]}")
        assigned[url] = post["path"]
        if not old:
            print(f"{'Recording' if args.apply else 'Would record'}: {post['path']} -> {url}")
            if args.apply:
                insert_link(post,url)
                updated += 1
    print(f"Published: {len(entries)}, already linked: {existing}, "
          f"new discussions: {created}, new links: {updated}, missing: {missing}")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError,urllib.error.URLError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        sys.exit(1)
