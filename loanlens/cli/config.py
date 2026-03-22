from __future__ import annotations

from pathlib import Path

import typer

from loanlens.cli._common import get_config
from loanlens.config import AppConfig, StorageBackend, save_config
from loanlens.models import AdjustmentMode, ODBalanceMode

app = typer.Typer(help="Configuration commands.")


@app.command("show")
def show(ctx: typer.Context) -> None:
    typer.echo(get_config(ctx).model_dump_json(indent=2))


@app.command("set")
def set_value(ctx: typer.Context, key: str, value: str) -> None:
    config = get_config(ctx)
    updates: dict[str, object] = {
        "storage_backend": StorageBackend(value)
        if key == "storage_backend"
        else config.storage_backend,
        "data_dir": Path(value) if key == "data_dir" else config.data_dir,
        "od_balance_mode": ODBalanceMode(value)
        if key == "od_balance_mode"
        else config.od_balance_mode,
        "adjustment_mode": AdjustmentMode(value)
        if key == "adjustment_mode"
        else config.adjustment_mode,
        "emi_rounding": value if key == "emi_rounding" else config.emi_rounding,
        "backup_count": int(value) if key == "backup_count" else config.backup_count,
        "color_enabled": (
            value.lower() == "true" if key == "color_enabled" else config.color_enabled
        ),
        "date_format": value if key == "date_format" else config.date_format,
        "currency_symbol": value if key == "currency_symbol" else config.currency_symbol,
        "items_per_page": int(value) if key == "items_per_page" else config.items_per_page,
    }
    updated = AppConfig(**updates)
    save_config(updated)
    typer.echo(updated.model_dump_json(indent=2))
