"""
Auto-update the repository table in README.md.

Fetches all public, non-fork repositories for GH_USERNAME via the GitHub
API, sorts them by stars (falls back to most-recently-pushed), and writes
a markdown table between the <!-- REPOS-START --> / <!-- REPOS-END -->
markers in README.md.

Run manually:
    GH_USERNAME=your-username GH_TOKEN=ghp_xxx python scripts/update_readme_repos.py

In CI this is wired up by .github/workflows/update-readme.yml and runs
automatically every day, so the README always reflects your current repos
with no manual editing.
"""

import os
import sys
import requests

USERNAME = os.environ.get("GH_USERNAME", "hayaxxdev-bit")
TOKEN = os.environ.get("GH_TOKEN")
README_PATH = "README.md"
MAX_REPOS = 10  # how many repos to show in the table

START_MARKER = "<!-- REPOS-START -->"
END_MARKER = "<!-- REPOS-END -->"


def fetch_repos():
    headers = {"Accept": "application/vnd.github+json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    repos = []
    page = 1
    while True:
        resp = requests.get(
            f"https://api.github.com/users/{USERNAME}/repos",
            headers=headers,
            params={"per_page": 100, "page": page, "type": "owner"},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        repos.extend(batch)
        page += 1

    # skip forks, sort by stars desc then last pushed desc
    repos = [r for r in repos if not r.get("fork")]
    repos.sort(key=lambda r: (r.get("stargazers_count", 0), r.get("pushed_at", "")), reverse=True)
    return repos[:MAX_REPOS]


def build_table(repos):
    if not repos:
        return "| _no public repositories found_ | | | | |"

    lines = ["| Repo | ⭐ Stars | 🍴 Forks | Language | Last Push |", "|---|---|---|---|---|"]
    for r in repos:
        name = r["name"]
        url = r["html_url"]
        stars = r.get("stargazers_count", 0)
        forks = r.get("forks_count", 0)
        lang = r.get("language") or "—"
        pushed = (r.get("pushed_at") or "")[:10]
        lines.append(f"| [{name}]({url}) | {stars} | {forks} | {lang} | {pushed} |")
    return "\n".join(lines)


def update_readme(table_md):
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    if START_MARKER not in content or END_MARKER not in content:
        print(f"Markers {START_MARKER}/{END_MARKER} not found in {README_PATH}", file=sys.stderr)
        sys.exit(1)

    before, rest = content.split(START_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)

    comment = (
        "<!-- This section is updated automatically every day by the GitHub Action\n"
        "     in .github/workflows/update-readme.yml — don't edit it by hand. -->\n"
    )

    new_content = f"{before}{START_MARKER}\n{comment}{table_md}\n{END_MARKER}{after}"

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)


def main():
    repos = fetch_repos()
    table_md = build_table(repos)
    update_readme(table_md)
    print(f"Updated README.md with {len(repos)} repositories.")


if __name__ == "__main__":
    main()