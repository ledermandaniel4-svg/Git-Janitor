import pytest
from gitutil import commit, run
from typer.testing import CliRunner

from git_janitor.cleaner import candidates, fetch
from git_janitor.cli import app


def reasons(repo):
    return {c.branch.name: c.reason for c in candidates(repo)}


@pytest.fixture
def github(tmp_path, make_repo):
    """A local clone with a pushed `feature` branch, plus a second clone acting as the GitHub UI."""
    remote = tmp_path / "remote.git"
    run(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))

    local = make_repo("local")
    run(local, "remote", "add", "origin", str(remote))
    run(local, "push", "-q", "-u", "origin", "main")
    run(local, "checkout", "-q", "-b", "feature")
    commit(local, "first", file="a.txt")
    commit(local, "second", file="b.txt")
    run(local, "push", "-q", "-u", "origin", "feature")
    run(local, "checkout", "-q", "main")

    web = tmp_path / "web"
    run(tmp_path, "clone", "-q", str(remote), str(web))
    return local, web


def finish_pr(web, how):
    commit(web, "someone else's PR", file="other.txt")
    if how == "squash":
        run(web, "merge", "-q", "--squash", "origin/feature")
        run(web, "commit", "-q", "-m", "Add feature (#1)")
    elif how == "rebase":
        run(web, "cherry-pick", "origin/main..origin/feature")
    run(web, "push", "-q", "origin", "main")
    run(web, "push", "-q", "origin", "--delete", "feature")


def test_local_squash_merge(make_repo):
    repo = make_repo()
    run(repo, "checkout", "-q", "-b", "feature")
    commit(repo, "one", file="a.txt")
    commit(repo, "two", file="b.txt")
    run(repo, "checkout", "-q", "main")
    commit(repo, "unrelated", file="c.txt")
    run(repo, "merge", "-q", "--squash", "feature")
    run(repo, "commit", "-q", "-m", "squash")

    assert reasons(repo) == {"feature": "squashed"}


def test_partially_merged_branch_is_kept(make_repo):
    repo = make_repo()
    run(repo, "checkout", "-q", "-b", "feature")
    commit(repo, "one", file="a.txt")
    run(repo, "checkout", "-q", "main")
    run(repo, "merge", "-q", "--squash", "feature")
    run(repo, "commit", "-q", "-m", "squash")
    run(repo, "checkout", "-q", "feature")
    commit(repo, "more work", file="b.txt")
    run(repo, "checkout", "-q", "main")

    assert reasons(repo) == {}


@pytest.mark.parametrize("how", ["squash", "rebase"])
def test_merged_on_github_found_after_fetch(github, how):
    local, web = github
    finish_pr(web, how)

    assert reasons(local) == {}  # local main hasn't seen the merge yet
    assert fetch(local)
    assert reasons(local) == {"feature": "squashed"}


def test_deleted_on_remote_without_merge(github):
    local, web = github
    finish_pr(web, "close")
    fetch(local)

    [candidate] = candidates(local)
    assert candidate.reason == "gone"
    assert candidate.branch.gone


def test_sweep_fetch_and_delete_squashed(tmp_path, github):
    local, web = github
    finish_pr(web, "squash")

    result = CliRunner().invoke(app, ["sweep", str(local), "--fetch", "--force"], input="y\n")

    assert result.exit_code == 0, result.output
    assert "squash-merged" in result.output
    assert run(local, "branch", "--format=%(refname:short)") == "main"
