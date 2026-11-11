from pathlib import Path

import pytest

from gitutil import commit, run


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
