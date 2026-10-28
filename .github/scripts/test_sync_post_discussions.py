"""Regression tests for per-post discussion reconciliation."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_post_discussions as sync


class SyncDiscussionTests(unittest.TestCase):
    def test_repository_posts_are_parseable_and_unambiguous(self):
        entries = list(sync.posts())
        self.assertGreater(len(entries), 0, "No blog posts discovered")
        keys = [post["key"] for post in entries]
        self.assertEqual(len(keys), len(set(keys)), "Ambiguous post paths")
        for post in entries:
            url = post["discussion"]
            if url:
                self.assertRegex(url, sync.DISCUSSION_URL)

    def test_normalizes_legacy_paths_and_encoded_spaces(self):
        self.assertEqual(sync.key("2022", "005-Synology Office Encryption"),
                         sync.key("2022", "005-synology%20office-encryption"))
        item = {"title": "My Post - /blog/post/2022/005-My Post/",
                "body": "Read <https://arran4.github.io/blog/post/2022/005-My%20Post/>"}
        self.assertEqual(sync.paths(item), {sync.key("2022", "005-My Post")})

    def test_frontmatter_link_preserves_date_and_body(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "index.md"
            source = ('---\ntitle: "Example"\ndate: 2022-01-02T03:04:05Z\n'
                      'draft: false\n---\n\nArticle text.\n')
            file.write_text(source, encoding="utf-8")
            match = sync.FRONT.match(source)
            self.assertIsNotNone(match)
            sync.insert_link({"path": file, "source": source, "end": match.end()},
                             "https://github.com/arran4/blog/discussions/87")
            actual = file.read_text(encoding="utf-8")
            self.assertEqual(actual, source.replace(
                "\n---\n", '\ndiscussion: "https://github.com/arran4/blog/discussions/87"\n---\n'))
            self.assertIn("date: 2022-01-02T03:04:05Z", actual)

    def test_reuses_discussion_and_second_run_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root)
            folder = base / "content" / "post" / "2026" / "001-My-Post"
            folder.mkdir(parents=True)
            file = folder / "index.md"
            file.write_text('---\ntitle: "My Post"\ndate: 2026-01-01\n'
                            'draft: false\ntags: []\ncategories: []\n---\n\nBody\n',
                            encoding="utf-8")
            repo = {"id": "R_repository",
                    "discussionCategories": {"nodes": [{"name": "Announcements",
                                                        "id": "C_category"}]},
                    "discussions": {"nodes": [{
                        "id": "D_discussion",
                        "title": "My Post - /blog/post/2026/001-My-Post/",
                        "url": "https://github.com/arran4/blog/discussions/200",
                        "body": "A new blog post has been published: My Post"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None}}}
            def fake_api(query, vars):
                self.assertEqual(query, sync.LIST, "No new discussion must be created")
                return {"repository": repo}
            previous = Path.cwd()
            try:
                os.chdir(base)
                with patch.object(sync, "graphql", side_effect=fake_api), \
                     patch.object(sys, "argv", ["sync", "--apply"]):
                    self.assertEqual(sync.main(), 0)
                    self.assertEqual(sync.main(), 0)
                self.assertEqual(
                    file.read_text(encoding="utf-8").count("discussion:"), 1)
            finally:
                os.chdir(previous)

    def test_draft_is_ignored(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / "content" / "post" / "2026" / "001-Draft"
            folder.mkdir(parents=True)
            (folder / "index.md").write_text(
                "---\ntitle: Draft\ndate: 2026-01-01\ndraft: true\n---\n",
                encoding="utf-8")
            previous = Path.cwd()
            try:
                os.chdir(root)
                self.assertEqual(list(sync.posts()), [])
            finally:
                os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
