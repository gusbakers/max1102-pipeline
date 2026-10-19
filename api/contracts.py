"""Shared claim contract for HTTP and the streaming pilot."""
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Claim(BaseModel):
    model_config = ConfigDict(extra='forbid')
    claim_id: str = Field(min_length=1, max_length=64, pattern=r'^[A-Za-z0-9_-]+$')
    claim_amount: Decimal = Field(ge=0, le=50000, max_digits=7, decimal_places=2)
    claim_status: Literal['PAID', 'DENIED', 'PENDING']
    service_date: date
