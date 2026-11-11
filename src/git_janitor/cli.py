from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from . import __version__
from .cleaner import candidates, delete, fetch
from .models import RepoStatus, SweepCandidate
from .scanner import display_name, find_repos, scan as scan_repos

app = typer.Typer(
    help="Audit local Git repositories and clean up merged or stale branches.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console(highlight=False)
err = Console(stderr=True, highlight=False)

PathArg = typer.Argument(Path("."), exists=True, file_okay=False, resolve_path=True, help="Directory to search.")
DaysOpt = typer.Option(30, "--days", min=1, help="Branches with no commits in this many days are stale.")


def version_callback(value: bool) -> None:
    if value:
        console.print(f"git-janitor {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True, help="Show version."),
) -> None:
    pass


def status_cell(repo: RepoStatus) -> str:
    return "[green]clean[/]" if repo.dirty == 0 else f"[yellow]{repo.dirty} dirty[/]"


def count_cell(value: int | None) -> str:
    if value is None:
        return "[dim]-[/]"
    return f"[yellow]{value}[/]" if value else "[dim]0[/]"


def render_table(repos: list[RepoStatus]) -> Table:
    table = Table(box=box.SIMPLE_HEAD, header_style="dim", show_edge=False, pad_edge=False)
    table.add_column("REPO", style="bold")
    table.add_column("BRANCH")
    table.add_column("STATUS")
    table.add_column("UNPUSHED", justify="right")
    table.add_column("STALE", justify="right")
    for repo in repos:
        branch = f"[dim]{repo.branch}[/]" if repo.branch.startswith("(") else repo.branch
        table.add_row(repo.name, branch, status_cell(repo), count_cell(repo.unpushed), count_cell(len(repo.stale)))
    return table


@app.command()
def scan(
    path: Path = PathArg,
    days: int = DaysOpt,
    as_json: bool = typer.Option(False, "--json", help="Print JSON instead of a table."),
) -> None:
    """Show branch, working tree and push status for every repo under PATH."""
    repos = scan_repos(path, days)
    if as_json:
        typer.echo(json.dumps([r.to_dict() for r in repos], indent=2))
        return
    if not repos:
        err.print(f"[dim]No Git repositories found under {path}[/]")
        return
    console.print(render_table(repos))
    console.print(f"[dim]{len(repos)} repos, stale = no commits in {days}+ days[/]")


def count_branches(n: int, kind: str) -> str:
    return f"{n} {kind} branch" + ("" if n == 1 else "es")


NOTES = {
    "merged": "[green]merged[/]",
    "squashed": "[green]squash-merged[/]",
    "gone": "[yellow]remote branch deleted[/] [dim](unmerged)[/]",
}

Plan = list[tuple[Path, str, SweepCandidate]]


def print_candidates(name: str, found: list[SweepCandidate]) -> None:
    console.print(f"[bold]{name}[/]")
    width = max(len(c.branch.name) for c in found)
    for c in found:
        note = NOTES.get(c.reason, f"[yellow]stale[/] [dim]({c.age} days, unmerged)[/]")
        console.print(f"  {c.branch.name:<{width}}  {note}")


def run_deletes(batch: Plan, force: bool) -> int:
    failed = 0
    for repo, name, c in batch:
        if delete(repo, c, force=force):
            console.print(f"  [red]deleted[/] {c.branch.name} [dim]{name}[/]")
        else:
            failed += 1
            err.print(f"  [yellow]skipped[/] {c.branch.name} [dim]{name}: git refused to delete it[/]")
    return failed


def confirm_and_delete(batch: Plan, question: str, force: bool) -> int:
    if batch and typer.confirm(question):
        return run_deletes(batch, force)
    return 0


@app.command()
def sweep(
    path: Path = PathArg,
    days: int = DaysOpt,
    force: bool = typer.Option(False, "--force", "--yes", "-y", help="Actually delete branches (asks first)."),
    fetch_first: bool = typer.Option(False, "--fetch", help="Run git fetch --prune in each repo first."),
) -> None:
    """Find merged and stale branches under PATH. Dry run unless --force is given."""
    plan: Plan = []
    for repo in find_repos(path):
        name = display_name(repo, path)
        if fetch_first and not fetch(repo):
            err.print(f"[yellow]fetch failed[/] [dim]{name}, using local state[/]")
        found = candidates(repo, days)
        if found:
            print_candidates(name, found)
            plan.extend((repo, name, c) for c in found)

    if not plan:
        console.print("[dim]Nothing to sweep.[/]")
        return

    merged = [p for p in plan if p[2].reason == "merged"]
    squashed = [p for p in plan if p[2].reason == "squashed"]
    unmerged = [p for p in plan if p[2].reason in ("gone", "stale")]
    console.print()

    if not force:
        console.print(
            f"[dim]Dry run: {len(merged) + len(squashed)} merged, {len(unmerged)} unmerged. "
            "Re-run with --force to delete.[/]"
        )
        return

    # -d refuses squash-merged branches since they aren't ancestors of main, hence -D there
    failed = confirm_and_delete(merged, f"Delete {count_branches(len(merged), 'merged')} with git branch -d?", False)
    failed += confirm_and_delete(
        squashed, f"Delete {count_branches(len(squashed), 'squash-merged')} with git branch -D?", True
    )
    failed += confirm_and_delete(
        unmerged,
        f"Force-delete {count_branches(len(unmerged), 'unmerged')} with git branch -D? Their commits will be lost.",
        True,
    )
    if failed:
        raise typer.Exit(1)
