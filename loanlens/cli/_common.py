from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import typer
from rich.console import Console

from loanlens.config import AppConfig
from loanlens.store.base import StoreBase


def get_state(ctx: typer.Context) -> dict[str, Any]:
    state = cast(dict[str, Any] | None, ctx.obj)
    if state is None:
        msg = "Application context is not initialized"
        raise RuntimeError(msg)
    return state


def get_store(ctx: typer.Context) -> StoreBase:
    return cast(StoreBase, get_state(ctx)["store"])


def get_config(ctx: typer.Context) -> AppConfig:
    return cast(AppConfig, get_state(ctx)["config"])


def get_console(ctx: typer.Context) -> Console:
    state = get_state(ctx)
    return Console(no_color=bool(state.get("no_color", False)))


def _json_default(value: object) -> object:
    if hasattr(value, "model_dump"):
        return cast(Any, value).model_dump(mode="json")
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def echo_json(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, default=_json_default))
