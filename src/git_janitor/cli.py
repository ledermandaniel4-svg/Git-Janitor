from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from . import __version__
from .cleaner import candidates, delete
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
        raise typer.Exit(1)
    console.print(render_table(repos))
    console.print(f"[dim]{len(repos)} repos, stale = no commits in {days}+ days[/]")


def count_branches(n: int, kind: str) -> str:
    return f"{n} {kind} branch" + ("" if n == 1 else "es")


def print_candidates(name: str, found: list[SweepCandidate]) -> None:
    console.print(f"[bold]{name}[/]")
    width = max(len(c.branch.name) for c in found)
    for c in found:
        if c.reason == "merged":
            note = "[green]merged[/]"
        else:
            note = f"[yellow]stale[/] [dim]({c.age} days, unmerged)[/]"
        console.print(f"  {c.branch.name:<{width}}  {note}")


def run_deletes(batch: list[tuple[Path, SweepCandidate]], force: bool) -> int:
    failed = 0
    for repo, c in batch:
        if delete(repo, c, force=force):
            console.print(f"  [red]deleted[/] {c.branch.name} [dim]{repo.name}[/]")
        else:
            failed += 1
            err.print(f"  [yellow]skipped[/] {c.branch.name} [dim]{repo.name}: git refused to delete it[/]")
    return failed


@app.command()
def sweep(
    path: Path = PathArg,
    days: int = DaysOpt,
    force: bool = typer.Option(False, "--force", "--yes", "-y", help="Actually delete branches (asks first)."),
) -> None:
    """Find merged and stale branches under PATH. Dry run unless --force is given."""
    plan: list[tuple[Path, SweepCandidate]] = []
    for repo in find_repos(path):
        found = candidates(repo, days)
        if found:
            print_candidates(display_name(repo, path), found)
            plan.extend((repo, c) for c in found)

    if not plan:
        console.print("[dim]Nothing to sweep.[/]")
        return

    merged = [(r, c) for r, c in plan if c.reason == "merged"]
    stale = [(r, c) for r, c in plan if c.reason == "stale"]
    console.print()

    if not force:
        console.print(
            f"[dim]Dry run: {len(merged)} merged, {len(stale)} stale. Re-run with --force to delete.[/]"
        )
        return

    failed = 0
    if merged and typer.confirm(f"Delete {count_branches(len(merged), 'merged')} with git branch -d?"):
        failed += run_deletes(merged, force=False)
    if stale and typer.confirm(
        f"Force-delete {count_branches(len(stale), 'unmerged stale')} with git branch -D? Their commits will be lost.",
        default=False,
    ):
        failed += run_deletes(stale, force=True)
    if failed:
        raise typer.Exit(1)
