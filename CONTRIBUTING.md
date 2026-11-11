# Contributing

## Setup

```sh
git clone https://github.com/ledermandaniel4-svg/Git-Janitor
cd Git-Janitor
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

## Layout

- `src/git_janitor/scanner.py` finds repos and reads their state
- `src/git_janitor/cleaner.py` decides which branches can go and deletes them
- `src/git_janitor/cli.py` is the Typer app and all terminal output
- `src/git_janitor/models.py` holds the dataclasses passed between them

All Git access goes through `scanner.git()`, which shells out to the `git` binary. Please don't add a Git library dependency.

## Pull requests

- Add a test for behavior changes. Tests build throwaway repos in `tmp_path`; see `tests/conftest.py` for the helpers, including backdated commits.
- Anything that deletes data should stay behind a dry run by default and an explicit confirmation.
- Keep output plain: short lines, a few colors, no emoji.
- Add a line under "Unreleased" in `CHANGELOG.md`.
