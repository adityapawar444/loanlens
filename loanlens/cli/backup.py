from __future__ import annotations

import shutil
from pathlib import Path

import typer

from loanlens.cli._common import get_config

app = typer.Typer(help="Backup commands.")


@app.command("create")
def create(ctx: typer.Context) -> None:
    config = get_config(ctx)
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    target = config.backup_dir / f"manual-{len(list(config.backup_dir.glob('*.json'))) + 1}.json"
    shutil.copy2(config.data_file, target)
    typer.echo(str(target))


@app.command("list")
def list_backups(ctx: typer.Context) -> None:
    backups = sorted(get_config(ctx).backup_dir.glob("*.json"))
    for backup in backups:
        typer.echo(str(backup))


@app.command("restore")
def restore(ctx: typer.Context, backup_path: Path) -> None:
    config = get_config(ctx)
    shutil.copy2(backup_path, config.data_file)
    typer.echo(str(config.data_file))
