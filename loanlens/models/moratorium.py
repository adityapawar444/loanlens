from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MoratoriumType(StrEnum):
    INTEREST_CAPITALISE = "INTEREST_CAPITALISE"
    INTEREST_DEFER = "INTEREST_DEFER"
    FULL_DEFER = "FULL_DEFER"


class Moratorium(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    moratorium_id: UUID = Field(default_factory=uuid4)
    loan_id: UUID
    from_date: date
    to_date: date
    moratorium_type: MoratoriumType
    reason: str = ""
    approved_by: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _validate_range(self) -> Moratorium:
        if self.to_date < self.from_date:
            msg = "to_date cannot be before from_date"
            raise ValueError(msg)
        return self
