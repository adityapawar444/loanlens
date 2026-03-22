from __future__ import annotations

from pathlib import Path
from typing import Literal, cast

import typer
from prompt_toolkit import prompt

from loanlens.cli._common import get_console
from loanlens.config import AppConfig, StorageBackend, save_config
from loanlens.models import AdjustmentMode, ODBalanceMode

app = typer.Typer(help="Interactive setup wizard.")
RoundingLiteral = Literal["rupee", "ten"]


def run_wizard(defaults_only: bool = False) -> AppConfig:
    default_config = AppConfig()
    if defaults_only:
        save_config(default_config)
        return default_config

    data_dir = prompt("Data directory", default=str(default_config.data_dir))
    storage = prompt("Storage backend [json/sqlite]", default=default_config.storage_backend.value)
    od_mode = prompt(
        "OD balance mode [DAILY/MONTHLY_AVERAGE]",
        default=default_config.od_balance_mode.value,
    )
    emi_rounding = prompt("EMI rounding [rupee/ten]", default=default_config.emi_rounding)
    adjustment = prompt(
        "Adjustment mode [ADJUST_EMI/ADJUST_TENURE]",
        default=default_config.adjustment_mode.value,
    )
    items_per_page = prompt("Items per page", default=str(default_config.items_per_page))
    color_enabled = prompt("Enable colour [y/n]", default="y")
    config = AppConfig(
        data_dir=Path(data_dir),
        storage_backend=StorageBackend(storage),
        od_balance_mode=ODBalanceMode(od_mode),
        emi_rounding=cast(RoundingLiteral, emi_rounding),
        adjustment_mode=AdjustmentMode(adjustment),
        items_per_page=int(items_per_page),
        color_enabled=color_enabled.lower().startswith("y"),
    )
    save_config(config)
    return config


@app.command()
def run(ctx: typer.Context) -> None:
    config = run_wizard(defaults_only=bool((ctx.obj or {}).get("yes", False)))
    if (ctx.obj or {}).get("json_output", False):
        typer.echo(config.model_dump_json(indent=2))
        return
    get_console(ctx).print(f"Wizard complete. Config saved to {config.config_file}")
