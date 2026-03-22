from __future__ import annotations

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loanlens.models.loan import AdjustmentMode
from loanlens.models.od import ODBalanceMode


class StorageBackend(StrEnum):
    JSON = "json"
    SQLITE = "sqlite"


class AppConfig(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    storage_backend: StorageBackend = StorageBackend.JSON
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".loanlens")
    od_balance_mode: ODBalanceMode = ODBalanceMode.DAILY
    adjustment_mode: AdjustmentMode = AdjustmentMode.ADJUST_EMI
    emi_rounding: Literal["rupee", "ten"] = "rupee"
    backup_count: int = 5
    color_enabled: bool = True
    date_format: str = "DD-MMM-YYYY"
    currency_symbol: str = "₹"
    items_per_page: int = 20

    @field_validator("backup_count", "items_per_page")
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value <= 0:
            msg = "value must be greater than zero"
            raise ValueError(msg)
        return value

    @field_validator("data_dir", mode="before")
    @classmethod
    def _resolve_data_dir(cls, value: object) -> Path:
        override = os.getenv("LOANLENS_DATA_DIR")
        if override:
            return Path(override).expanduser()
        if isinstance(value, Path):
            return value.expanduser()
        if isinstance(value, str):
            return Path(value).expanduser()
        msg = "data_dir must be a path-like string or Path instance"
        raise TypeError(msg)

    @property
    def config_file(self) -> Path:
        return self.data_dir / "config.json"

    @property
    def data_file(self) -> Path:
        return self.data_dir / "data.json"

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"


def load_config() -> AppConfig:
    env_dir = os.getenv("LOANLENS_DATA_DIR")
    base_dir = Path(env_dir).expanduser() if env_dir else Path.home() / ".loanlens"
    config_file = base_dir / "config.json"
    if config_file.exists():
        payload = json.loads(config_file.read_text(encoding="utf-8"))
        config = AppConfig.model_validate(payload)
    else:
        config = AppConfig(data_dir=base_dir)

    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    return config


def save_config(config: AppConfig) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.backup_dir.mkdir(parents=True, exist_ok=True)
    config.config_file.write_text(config.model_dump_json(indent=2), encoding="utf-8")
