from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from loanlens.models.loan import AdjustmentMode


class RateRevision(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    revision_id: UUID = Field(default_factory=uuid4)
    loan_id: UUID
    effective_date: date
    old_roi: Decimal
    new_roi: Decimal
    adjustment_mode: AdjustmentMode
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("old_roi", "new_roi")
    @classmethod
    def _positive_roi(cls, value: Decimal) -> Decimal:
        if value <= Decimal("0"):
            msg = "roi must be greater than zero"
            raise ValueError(msg)
        return value
