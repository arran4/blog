import os
import re
import sys
import json
import urllib.request
from collections import defaultdict

def get_local_posts():
    """Returns a dict of year -> list of (number, folder_name)"""
    posts = defaultdict(list)
    base_dir = "content/post"
    if not os.path.exists(base_dir):
        return posts

    for year in os.listdir(base_dir):
        year_path = os.path.join(base_dir, year)
        if not os.path.isdir(year_path) or not year.isdigit():
            continue

        for post in os.listdir(year_path):
            post_path = os.path.join(year_path, post)
            if not os.path.isdir(post_path):
                continue

            # Extract number from start of folder name, e.g., "001-Type-Switched-Variadic-System"
            match = re.match(r'^(\d+)-', post)
            if match:
                number = match.group(1)
                posts[year].append((number, post))

    return posts

def get_pr_files(repo, pr_number, token):
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/files?per_page=100"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'token {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'check-post-numbers-script')

    files = []
    page = 1
    try:
        while True:
            paginated_url = f"{url}&page={page}"
            req = urllib.request.Request(paginated_url)
            req.add_header('Authorization', f'token {token}')
            req.add_header('Accept', 'application/vnd.github.v3+json')
            req.add_header('User-Agent', 'check-post-numbers-script')

            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                files.extend([f['filename'] for f in data])
                page += 1
        return files
    except Exception as e:
        print(f"Failed to fetch files for PR {pr_number}: {e}")
        return []

def get_open_prs(repo, token):
    url = f"https://api.github.com/repos/{repo}/pulls?state=open&per_page=100"
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'token {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    req.add_header('User-Agent', 'check-post-numbers-script')

    prs = []
    page = 1
    try:
        while True:
            paginated_url = f"{url}&page={page}"
            req = urllib.request.Request(paginated_url)
            req.add_header('Authorization', f'token {token}')
            req.add_header('Accept', 'application/vnd.github.v3+json')
            req.add_header('User-Agent', 'check-post-numbers-script')

            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                prs.extend([pr['number'] for pr in data])
                page += 1
        return prs
    except Exception as e:
        print(f"Failed to fetch open PRs: {e}")
        return []

def extract_post_info_from_path(path):
    # content/post/2026/011-simplified-github-ci/...
    parts = path.split('/')
    if len(parts) >= 4 and parts[0] == 'content' and parts[1] == 'post':
        year = parts[2]
        folder = parts[3]
        if year.isdigit():
            match = re.match(r'^(\d+)-', folder)
            if match:
                return year, match.group(1), folder
    return None, None, None

def main():
    repo = os.environ.get('GITHUB_REPOSITORY')
    token = os.environ.get('GITHUB_TOKEN')

    event_path = os.environ.get('GITHUB_EVENT_PATH')
    current_pr = None
    if event_path and os.path.exists(event_path):
        with open(event_path, 'r') as f:
            event_data = json.load(f)
            if 'pull_request' in event_data:
                current_pr = event_data['pull_request']['number']

    if not repo or not token or not current_pr:
        print("Not running in a PR context or missing token/repo. Success for non-PR build.")
        sys.exit(0)

    print(f"Current PR: {current_pr}")

    # 1. Get files changed in current PR
    current_pr_files = get_pr_files(repo, current_pr, token)
    current_pr_posts = {} # (year, number) -> folder
    current_pr_folders = set()
    for f in current_pr_files:
        year, number, folder = extract_post_info_from_path(f)
        if year and number:
            current_pr_posts[(year, number)] = folder
            current_pr_folders.add(folder)

    if not current_pr_posts:
        print("No new/modified posts in this PR. Success.")
        sys.exit(0)

    print(f"Posts modified in this PR: {current_pr_posts}")

    # 2. Check local collisions, but only fail if they involve folders modified in this PR
    local_posts = get_local_posts()
    local_collision_found = False
    for year, posts in local_posts.items():
        seen = defaultdict(list)
        for number, folder in posts:
            seen[number].append(folder)

        for number, folders in seen.items():
            if len(folders) > 1:
                # Only care if this PR actually touched one of the colliding folders
                if any(f in current_pr_folders for f in folders):
                    print(f"Error: Local collision detected in year {year} for number {number}. Folders: {', '.join(folders)} (involves current PR)")
                    local_collision_found = True

    if local_collision_found:
        print("Local collisions involving PR found. Exiting with error.")
        sys.exit(1)

    # 3. Check against open PRs with lower numbers
    open_prs = get_open_prs(repo, token)
    lower_prs = [pr for pr in open_prs if pr < current_pr]

    print(f"Checking against lower priority PRs (lower PR numbers): {lower_prs}")

    conflict_found = False
    for pr in lower_prs:
        pr_files = get_pr_files(repo, pr, token)
        for f in pr_files:
            year, number, folder = extract_post_info_from_path(f)
            if year and number:
                if (year, number) in current_pr_posts:
                    current_folder = current_pr_posts[(year, number)]
                    if current_folder != folder:
                        print(f"Error: Collision detected! Current PR {current_pr} uses {year}/{number} for '{current_folder}', but lower priority PR {pr} uses it for '{folder}'.")
                        conflict_found = True

    if conflict_found:
        print("PR collisions found. Exiting with error.")
        sys.exit(1)

    print("No collisions found. Success.")
    sys.exit(0)

if __name__ == '__main__':
    main()
