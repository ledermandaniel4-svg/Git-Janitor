from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import Branch, SweepCandidate
from .scanner import PROTECTED, base_refs, checked_out, current_branch, git, list_branches

# commit-tree needs an identity even for a throwaway commit
TEMP_IDENTITY = ("-c", "user.name=git-janitor", "-c", "user.email=git-janitor@localhost")


def fetch(repo: Path) -> bool:
    if not git(repo, "remote"):
        return True
    return git(repo, "fetch", "--prune", "--quiet") is not None


def all_picked(repo: Path, ref: str, rev: str) -> bool:
    # `git cherry` marks commits that already exist on ref (by patch id) with "-"
    out = git(repo, "cherry", ref, rev)
    return bool(out) and all(line.startswith("-") for line in out.splitlines())


def squash_merged(repo: Path, branch: str, refs: list[str]) -> bool:
    for ref in refs:
        fork = git(repo, "merge-base", ref, branch)
        if not fork:
            continue
        # Rebase merges copy each commit onto main, so patch ids match one by one.
        if all_picked(repo, ref, branch):
            return True
        # Squash merges collapse the branch into one commit. Build a throwaway commit with
        # the branch's whole diff and compare that instead. Nothing references it, so gc drops it.
        temp = git(repo, *TEMP_IDENTITY, "commit-tree", f"{branch}^{{tree}}", "-p", fork, "-m", "squash check")
        if temp and all_picked(repo, ref, temp):
            return True
    return False


def classify(repo: Path, branch: Branch, refs: list[str], days: int, now: datetime) -> str | None:
    if branch.merged:
        return "merged"
    if squash_merged(repo, branch.name, refs):
        return "squashed"
    if branch.gone:
        return "gone"
    if branch.age_days(now) >= days:
        return "stale"
    return None


def candidates(repo: Path, days: int = 30, now: datetime | None = None) -> list[SweepCandidate]:
    now = now or datetime.now(timezone.utc)
    skip = PROTECTED | {current_branch(repo)} | checked_out(repo)
    refs = base_refs(repo)
    found = []
    for branch in list_branches(repo):
        if branch.name in skip:
            continue
        reason = classify(repo, branch, refs, days, now)
        if reason:
            found.append(SweepCandidate(branch, reason, branch.age_days(now)))
    return found


def delete(repo: Path, candidate: SweepCandidate, force: bool = False) -> bool:
    flag = "-D" if force else "-d"
    return git(repo, "branch", flag, candidate.branch.name) is not None
