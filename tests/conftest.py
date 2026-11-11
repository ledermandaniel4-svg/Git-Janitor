import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

NOW = datetime.now(timezone.utc)


def run(repo: Path, *args: str, days_ago: int = 0) -> str:
    when = (NOW - timedelta(days=days_ago)).strftime("%Y-%m-%dT%H:%M:%S%z")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    result = subprocess.run(["git", "-C", str(repo), *args], env=env, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def commit(repo: Path, message: str = "change", days_ago: int = 0) -> None:
    (repo / "file.txt").write_text(f"{message}\n")
    run(repo, "add", "file.txt")
    run(repo, "commit", "-m", message, days_ago=days_ago)


@pytest.fixture
def make_repo(tmp_path):
    def factory(rel: str = "repo", commits: bool = True) -> Path:
        repo = tmp_path / rel
        repo.mkdir(parents=True)
        run(repo, "init", "-q", "-b", "main")
        if commits:
            commit(repo, "initial", days_ago=100)
        return repo

    return factory
