#!/usr/bin/env python3
"""
GitHub Raw URL Generator (fixed)

Usage:
    python generate_github_raw_urls.py <repo_url>

Example:
    python generate_github_raw_urls.py https://github.com/torvalds/linux
"""

import sys
import requests
import urllib.parse
from typing import List, Dict

# ----------------------------------------------------------------------
# 1. Helper: extract owner/repo from any common GitHub URL format
# ----------------------------------------------------------------------
def extract_owner_repo(repo_url: str) -> tuple:
    parsed = urllib.parse.urlparse(repo_url.strip())

    # https://github.com/owner/repo   or   https://github.com/owner/repo.git
    if parsed.scheme in ("http", "https"):
        path = parsed.path.lstrip("/")
        if path.endswith(".git"):
            path = path[:-4]
        parts = path.split("/", 2)
        if len(parts) >= 2:
            return parts[0], parts[1]

    # git@github.com:owner/repo.git
    if parsed.scheme == "" and repo_url.startswith("git@"):
        rest = repo_url.split(":", 1)[1]
        if rest.endswith(".git"):
            rest = rest[:-4]
        parts = rest.split("/", 1)
        if len(parts) == 2:
            return parts[0], parts[1]

    raise ValueError(f"Cannot parse repo URL: {repo_url}")


# ----------------------------------------------------------------------
# 2. Recursively fetch *all* file objects via the Contents API
# ----------------------------------------------------------------------
def get_all_files(owner: str, repo: str, branch: str = "main") -> List[Dict]:
    files: List[Dict] = []
    queue = [(f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents", branch)]

    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "github-raw-url-generator/1.0",
        }
    )

    while queue:
        url, cur_branch = queue.pop(0)
        params = {"ref": cur_branch} if cur_branch else {}

        resp = session.get(url, params=params, timeout=30)

        # --------------------------------------------------------------
        # Handle common error cases
        # --------------------------------------------------------------
        if resp.status_code == 404:
            if cur_branch == "main":
                # fall back to master
                queue.append((url, "master"))
                continue
            raise RuntimeError(f"Repo {owner}/{repo} not found or is private.")
        if resp.status_code != 200:
            raise RuntimeError(f"API error {resp.status_code}: {resp.text}")

        items = resp.json()

        # A single file object can be returned when the path points to a file
        if isinstance(items, dict) and items.get("type") == "file":
            files.append(items)
            continue

        if not isinstance(items, list):
            continue

        for item in items:
            if item["type"] == "file":
                files.append(item)
            elif item["type"] == "dir":
                queue.append((item["url"], cur_branch))

    return files


# ----------------------------------------------------------------------
# 3. Turn the API file dict into a raw URL
# ----------------------------------------------------------------------
def raw_url(file_info: Dict) -> str:
    # The Contents API already gives us `download_url`
    return file_info["download_url"]


# ----------------------------------------------------------------------
# 4. Main driver
# ----------------------------------------------------------------------
GITHUB_API_BASE = "https://api.github.com"

def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    repo_url = sys.argv[1]

    try:
        owner, repo = extract_owner_repo(repo_url)
        print(f"Fetching files from {owner}/{repo} …", file=sys.stderr)

        files = get_all_files(owner, repo)
        print(f"Found {len(files)} files → printing raw URLs\n", file=sys.stderr)

        for f in files:
            print(raw_url(f))

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()