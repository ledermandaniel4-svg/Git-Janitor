# Changelog

## Unreleased

## 1.0.1 - 2026-11-11

- `scan`: find repos up to 3 levels deep and show the current branch, dirty files, unpushed commits and stale branches. Supports `--days` and `--json`.
- `sweep`: list branches that are merged, squash- or rebase-merged, deleted on the remote, or stale. Dry run unless `--force`, and asks before deleting.
- `sweep --fetch` runs `git fetch --prune` in each repo first.
- Works as `git janitor`; `-h` shows help.
- Repos with linked worktrees are swept once, and branches checked out in any worktree are skipped.
