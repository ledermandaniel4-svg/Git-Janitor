# Contributing

```sh
python -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
pytest
```

The tests create real repos in `tmp_path`. `tests/gitutil.py` has `run()` and `commit()`, which take a `days_ago` argument for faking old commits. `test_merge_detection.py` uses a bare repo plus a second clone to act as GitHub.

A few things I'd like to keep true:

- Git is called through `scanner.git()` with `subprocess`. No GitPython or similar.
- Nothing gets deleted without `--force` and a prompt.
- Output stays plain: a few colors, no emoji, no boxes.

If you change behavior, add a test and a line under Unreleased in `CHANGELOG.md`.
