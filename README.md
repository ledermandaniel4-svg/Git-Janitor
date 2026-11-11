# git-janitor

Finds every Git repo under a directory, shows which ones have uncommitted or unpushed work, and cleans up branches that have already been merged.

```
$ git janitor scan ~/code
REPO           BRANCH               STATUS    UNPUSHED   STALE
──────────────────────────────────────────────────────────────
api            main                 clean            1       2
dotfiles       main                 clean            -       0
work/billing   invoice-pdf          2 dirty          3       0
work/site      (detached 4903fac)   clean            -       0
4 repos, stale = no commits in 30+ days

$ git janitor sweep ~/code --fetch
api
  docs/typos         merged
  fix/retry-timeout  squash-merged
  spike/grpc         stale (119 days, unmerged)

Dry run: 2 merged, 1 unmerged. Re-run with --force to delete.
```

`-` under UNPUSHED means the branch has no upstream to compare against.

## Install

Needs Python 3.10+ and `git`.

```sh
pipx install git+https://github.com/ledermandaniel4-svg/Git-Janitor
```

Or from a checkout:

```sh
git clone https://github.com/ledermandaniel4-svg/Git-Janitor
cd Git-Janitor
pip install -e '.[dev]'
```

This installs a `git-janitor` command. Git runs anything named `git-*` on your `PATH` as a subcommand, so `git janitor` works as well.

## Usage

```sh
git janitor scan                  # current directory, 3 levels deep
git janitor scan ~/code --days 60
git janitor scan ~/code --json | jq '.[] | select(.dirty > 0) | .name'

git janitor sweep ~/code          # dry run
git janitor sweep ~/code --fetch  # fetch --prune each repo first
git janitor sweep ~/code --force  # actually delete, asks first
```

`scan` skips `node_modules`, `.venv` and dot-directories. It stops at the first repo it finds on a path, so submodules and nested repos aren't listed separately.

### What sweep deletes

A local branch is a candidate if it's:

- **merged**: an ancestor of `main` (or `master`)
- **squash-merged**: its changes are already on `main` as a squash or rebase merge, which is what GitHub's "Squash and merge" and "Rebase and merge" buttons produce
- **remote branch deleted**: its upstream is gone, usually because the PR was closed
- **stale**: no commits in `--days` days (default 30)

`main`, `master`, `develop` and whatever you have checked out are never touched.

Merges are checked against both your local `main` and `origin/main`. If you merge PRs on GitHub and don't pull often, use `--fetch` so `origin/main` is current.

`--force` (or `--yes`) asks up to three questions: merged branches go through `git branch -d`, squash-merged ones need `git branch -D` because Git can't see them as merged, and unmerged ones (stale or remote deleted) also need `-D`. All three default to no. Answer no to the last one unless you're sure, since those commits may not exist anywhere else.

Squash detection compares patches, so a branch that kept getting commits after it was squash-merged won't match and is left alone. It'll show up as stale eventually.

## License

MIT
