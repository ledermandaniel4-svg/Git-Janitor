from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .models import SweepCandidate
from .scanner import current_branch, git, list_branches

PROTECTED = frozenset({"main", "master", "develop"})


def candidates(repo: Path, days: int = 30, now: datetime | None = None) -> list[SweepCandidate]:
    now = now or datetime.now(timezone.utc)
    head = current_branch(repo)
    found = []
    for branch in list_branches(repo):
        if branch.name in PROTECTED or branch.name == head:
            continue
        age = branch.age_days(now)
        if branch.merged:
            found.append(SweepCandidate(branch, "merged", age))
        elif age >= days:
            found.append(SweepCandidate(branch, "stale", age))
    return found


def delete(repo: Path, candidate: SweepCandidate, force: bool = False) -> bool:
    flag = "-D" if force else "-d"
    return git(repo, "branch", flag, candidate.branch.name) is not None
