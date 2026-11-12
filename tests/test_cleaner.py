import json

from gitutil import commit, run
from typer.testing import CliRunner

from git_janitor.cleaner import candidates
from git_janitor.cli import app

runner = CliRunner()


def branches(repo):
    return set(run(repo, "branch", "--format=%(refname:short)").splitlines())


def setup_branches(repo):
    run(repo, "branch", "develop")
    run(repo, "branch", "merged-feature")  # points at main, so it counts as merged
    run(repo, "checkout", "-q", "-b", "old-spike")
    commit(repo, "abandoned", days_ago=60)
    run(repo, "checkout", "-q", "-b", "wip")
    commit(repo, "in progress", days_ago=1)
    run(repo, "checkout", "-q", "main")


def test_candidates_skip_protected_and_current(make_repo):
    repo = make_repo()
    setup_branches(repo)
    run(repo, "checkout", "-q", "-b", "current")
    run(repo, "checkout", "-q", "-b", "master")
    run(repo, "checkout", "-q", "current")

    found = {c.branch.name: c.reason for c in candidates(repo)}

    assert found == {"merged-feature": "merged", "old-spike": "stale"}


def test_sweep_dry_run_deletes_nothing(tmp_path, make_repo):
    repo = make_repo()
    setup_branches(repo)
    before = branches(repo)

    result = runner.invoke(app, ["sweep", str(tmp_path)])

    assert result.exit_code == 0
    assert "merged-feature" in result.output
    assert "old-spike" in result.output
    assert "Dry run" in result.output
    assert branches(repo) == before


def test_sweep_force_deletes_only_confirmed(tmp_path, make_repo):
    repo = make_repo()
    setup_branches(repo)

    result = runner.invoke(app, ["sweep", str(tmp_path), "--force"], input="y\nn\n")

    assert result.exit_code == 0
    assert branches(repo) == {"main", "develop", "old-spike", "wip"}


def test_sweep_force_deletes_unmerged_stale_when_confirmed(tmp_path, make_repo):
    repo = make_repo()
    setup_branches(repo)

    result = runner.invoke(app, ["sweep", str(tmp_path), "--yes"], input="y\ny\n")

    assert result.exit_code == 0
    assert branches(repo) == {"main", "develop", "wip"}


def test_sweep_force_aborts_without_confirmation(tmp_path, make_repo):
    repo = make_repo()
    setup_branches(repo)
    before = branches(repo)

    runner.invoke(app, ["sweep", str(tmp_path), "--force"], input="n\nn\n")

    assert branches(repo) == before


def test_scan_json(tmp_path, make_repo):
    make_repo("api")
    result = runner.invoke(app, ["scan", str(tmp_path), "--json"])

    assert result.exit_code == 0
    [repo] = json.loads(result.output)
    assert repo["name"] == "api"
    assert repo["branch"] == "main"
    assert repo["dirty"] == 0


def test_worktrees_are_swept_once(tmp_path, make_repo):
    repo = make_repo("app")
    run(repo, "branch", "done")
    run(repo, "branch", "in-use")
    run(repo, "worktree", "add", "-q", str(tmp_path / "app-wt"), "in-use")

    result = runner.invoke(app, ["sweep", str(tmp_path)])

    assert result.output.count("done") == 1
    assert "in-use" not in result.output  # checked out in the other worktree


def test_short_help_flag():
    result = runner.invoke(app, ["sweep", "-h"])
    assert result.exit_code == 0
    assert "--fetch" in result.output
