from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Branch:
    name: str
    last_commit: datetime
    merged: bool = False
    gone: bool = False  # upstream was deleted on the remote

    def age_days(self, now: datetime) -> int:
        return (now - self.last_commit).days


@dataclass
class RepoStatus:
    name: str
    path: Path
    branch: str
    dirty: int
    unpushed: int | None  # None when the branch has no upstream
    stale: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["path"] = str(self.path)
        return data


@dataclass
class SweepCandidate:
    branch: Branch
    reason: str  # merged, squashed, gone or stale
    age: int
