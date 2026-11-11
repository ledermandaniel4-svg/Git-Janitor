# git-janitor

`git-janitor` finds the Git repos under a directory, tells you which ones have uncommitted or unpushed work, and deletes branches you no longer need.

```
$ git janitor scan ~/code
REPO             BRANCH               STATUS    UNPUSHED   STALE
────────────────────────────────────────────────────────────────
api              main                 clean            0       2
work/dashboard   feature/charts       2 dirty          3       0
work/infra       (detached 8450cc3)   clean            -       0
3 repos, stale = no commits in 30+ days

$ git janitor sweep ~/code
api
  merged-fix  merged
  old-spike   stale (101 days, unmerged)

Dry run: 1 merged, 1 stale. Re-run with --force to delete.
```

`UNPUSHED` shows `-` when the current branch has no upstream.

## Install

Requires Python 3.10+ and `git` on your `PATH`.

```sh
pipx install git+https://github.com/ledermandaniel4-svg/Git-Janitor
```

From a local checkout, for development:

```sh
git clone https://github.com/ledermandaniel4-svg/Git-Janitor
cd Git-Janitor
pip install -e '.[dev]'
```

Both install a `git-janitor` executable. Git picks up any `git-*` command on your `PATH`, so `git janitor` works too.

## Usage

```sh
git janitor scan                 # repos under the current directory, up to 3 levels deep
git janitor scan ~/code --days 60
git janitor scan ~/code --json   # for scripts and jq

git janitor sweep ~/code         # dry run: list what would be deleted
git janitor sweep ~/code --force # delete, after asking
```

`scan` skips `node_modules`, `.venv` and hidden directories, and doesn't look inside a repo for nested repos.

`sweep` picks up local branches that are either merged into `main` (or `master`) or have had no commits for `--days` days (default 30). It never touches `main`, `master`, `develop` or the branch you have checked out.

With `--force` (alias `--yes`) it asks twice:

1. Delete merged branches with `git branch -d`.
2. Force-delete unmerged stale branches with `git branch -D`. This defaults to no, since those commits exist nowhere else unless you pushed them.

If `git branch -d` refuses a branch (for example, it's merged into `main` but you're on another branch that doesn't contain it), the branch is skipped and the command exits with status 1.

## License

MIT
