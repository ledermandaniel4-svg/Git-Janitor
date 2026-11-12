from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import Branch, RepoStatus

SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__"}
BASE_BRANCHES = ("main", "master")
PROTECTED = frozenset({"main", "master", "develop"})


def git(repo: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def is_repo(path: Path) -> bool:
    # .git is a file for worktrees and submodules
    return (path / ".git").exists()


def find_repos(root: Path, max_depth: int = 3) -> Iterator[Path]:
    root = root.resolve()
    if is_repo(root):
        yield root
        return
    if max_depth <= 0:
        return
    try:
        children = sorted(p for p in root.iterdir() if p.is_dir() and not p.is_symlink())
    except PermissionError:
        return
    for child in children:
        if child.name.startswith(".") or child.name in SKIP_DIRS:
            continue
        yield from find_repos(child, max_depth - 1)


def unique_repos(root: Path) -> list[Path]:
    # Linked worktrees share branches with their main repo, so keep one path per repo
    seen: set[Path] = set()
    repos = []
    for repo in find_repos(root):
        key = common_dir(repo)
        if key not in seen:
            seen.add(key)
            repos.append(repo)
    return repos


def current_branch(repo: Path) -> str:
    # symbolic-ref works on an unborn branch too, so a fresh repo still reports its name
    name = git(repo, "symbolic-ref", "--short", "-q", "HEAD")
    if name:
        return name
    sha = git(repo, "rev-parse", "--short", "HEAD")
    return f"(detached {sha})" if sha else "(unknown)"


def checked_out(repo: Path) -> set[str]:
    # Includes branches checked out in other worktrees, which git refuses to delete anyway
    out = git(repo, "worktree", "list", "--porcelain") or ""
    return {line.removeprefix("branch refs/heads/") for line in out.splitlines() if line.startswith("branch ")}


def common_dir(repo: Path) -> Path:
    # Same value for a repo and all of its linked worktrees
    out = git(repo, "rev-parse", "--git-common-dir") or ".git"
    return (repo / out).resolve()


def dirty_count(repo: Path) -> int:
    out = git(repo, "status", "--porcelain")
    return len(out.splitlines()) if out else 0


def unpushed_count(repo: Path) -> int | None:
    if git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") is None:
        return None
    out = git(repo, "rev-list", "--count", "@{u}..HEAD")
    return int(out) if out else 0


def base_branch(repo: Path) -> str | None:
    for name in BASE_BRANCHES:
        if git(repo, "rev-parse", "--verify", "-q", f"refs/heads/{name}") is not None:
            return name
    return None


def base_refs(repo: Path) -> list[str]:
    # Check origin/main too: after a fetch it can be ahead of a local main nobody pulled.
    base = base_branch(repo)
    if base is None:
        return []
    refs = [base]
    if git(repo, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{base}") is not None:
        refs.append(f"origin/{base}")
    return refs


def merged_into(repo: Path, ref: str) -> set[str]:
    out = git(repo, "branch", "--merged", ref, "--format=%(refname:short)")
    return set(out.splitlines()) if out else set()


def list_branches(repo: Path) -> list[Branch]:
    fmt = "%(refname:short)%00%(committerdate:unix)%00%(upstream:track)"
    out = git(repo, "for-each-ref", f"--format={fmt}", "refs/heads")
    if not out:
        return []  # no commits yet
    merged = set().union(*(merged_into(repo, ref) for ref in base_refs(repo)))
    branches = []
    for line in out.splitlines():
        name, ts, track = line.split("\0")
        branches.append(
            Branch(
                name=name,
                last_commit=datetime.fromtimestamp(int(ts), tz=timezone.utc),
                merged=name in merged,
                gone=track == "[gone]",
            )
        )
    return branches


def stale_branches(branches: list[Branch], days: int, now: datetime, skip: set[str]) -> list[Branch]:
    return [b for b in branches if b.name not in skip and b.age_days(now) >= days]


def display_name(repo: Path, root: Path) -> str:
    root = root.resolve()
    if repo == root:
        return repo.name
    return os.path.relpath(repo, root)


def inspect(repo: Path, root: Path, days: int = 30, now: datetime | None = None) -> RepoStatus:
    now = now or datetime.now(timezone.utc)
    branch = current_branch(repo)
    stale = stale_branches(list_branches(repo), days, now, skip=PROTECTED | {branch} | checked_out(repo))
    return RepoStatus(
        name=display_name(repo, root),
        path=repo,
        branch=branch,
        dirty=dirty_count(repo),
        unpushed=unpushed_count(repo),
        stale=[b.name for b in stale],
    )


def scan(root: Path, days: int = 30, now: datetime | None = None) -> list[RepoStatus]:
    return [inspect(repo, root, days, now) for repo in find_repos(root)]
