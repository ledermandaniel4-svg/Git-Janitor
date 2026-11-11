from conftest import commit, run

from git_janitor.scanner import find_repos, scan


def test_find_repos_respects_depth_and_skips(tmp_path, make_repo):
    make_repo("a")
    make_repo("group/b")
    make_repo("x/y/z")
    make_repo("x/y/z/too-deep")
    make_repo("w/x/y/z")
    make_repo("node_modules/pkg")
    make_repo(".hidden/c")
    make_repo(".venv/d")

    found = {p.relative_to(tmp_path).as_posix() for p in find_repos(tmp_path)}

    assert found == {"a", "group/b", "x/y/z"}


def test_root_repo_is_scanned_itself(make_repo):
    repo = make_repo()
    assert list(find_repos(repo)) == [repo]


def test_clean_repo(tmp_path, make_repo):
    make_repo("api")
    [status] = scan(tmp_path)

    assert status.name == "api"
    assert status.branch == "main"
    assert status.dirty == 0
    assert status.unpushed is None
    assert status.stale == []


def test_dirty_count(tmp_path, make_repo):
    repo = make_repo()
    (repo / "file.txt").write_text("edited\n")
    (repo / "new.txt").write_text("new\n")

    [status] = scan(tmp_path)

    assert status.dirty == 2


def test_unpushed_commits(tmp_path, make_repo):
    remote = tmp_path / "remote.git"
    run(tmp_path, "init", "-q", "--bare", str(remote))
    repo = make_repo("work/app")
    run(repo, "remote", "add", "origin", str(remote))
    run(repo, "push", "-q", "-u", "origin", "main")
    commit(repo, "one")
    commit(repo, "two")

    [status] = scan(tmp_path / "work")

    assert status.unpushed == 2


def test_stale_branches_use_days_threshold(tmp_path, make_repo):
    repo = make_repo()
    run(repo, "checkout", "-q", "-b", "fresh")
    commit(repo, "recent", days_ago=5)
    run(repo, "checkout", "-q", "main")

    [default] = scan(tmp_path)
    [strict] = scan(tmp_path, days=3)

    # main itself is checked out, so it never counts as stale
    assert default.stale == []
    assert strict.stale == ["fresh"]


def test_detached_head(tmp_path, make_repo):
    repo = make_repo()
    sha = run(repo, "rev-parse", "--short", "HEAD")
    run(repo, "checkout", "-q", "--detach")

    [status] = scan(tmp_path)

    assert status.branch == f"(detached {sha})"


def test_repo_without_commits(tmp_path, make_repo):
    make_repo(commits=False)
    [status] = scan(tmp_path)

    assert status.branch == "main"
    assert status.stale == []
    assert status.unpushed is None
