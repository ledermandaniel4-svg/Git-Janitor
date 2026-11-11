# Changelog

## Unreleased

## 0.1.0 - 2026-11-10

- `scan`: find repos up to 3 levels deep and show branch, dirty files, unpushed commits and stale branches. `--days` and `--json` options.
- `sweep`: list merged and stale branches as a dry run; delete them with `--force` after confirmation. `main`, `master`, `develop` and the current branch are never deleted.
- Works as `git janitor` when installed.
