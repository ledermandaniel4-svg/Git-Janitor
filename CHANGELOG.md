# Changelog

## Unreleased

- `sweep` now finds squash- and rebase-merged branches, and branches whose remote was deleted.
- `sweep --fetch` runs `git fetch --prune` in each repo first.
- Merges are checked against `origin/main` as well as local `main`.
- `scan` no longer counts `main`, `master` or `develop` as stale.
- `scan` exits 0 when no repos are found, same as `scan --json`.

## 0.1.0 - 2026-11-10

First version: `scan` and `sweep` with `--days`, `--json` and `--force`.
