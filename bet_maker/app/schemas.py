import decimal
import enum
from decimal import Decimal
from typing import List, Optional, Union

from app.models import BetStatus
from pydantic import UUID4, BaseModel, Field, field_serializer, field_validator


class BetCreate(BaseModel):
    event_id: str
    amount: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2)

    @field_serializer("amount")
    def serialize_decimal(self, v: Decimal, _info):
        return float(v)

    @field_validator("event_id", mode="before")
    @classmethod
    def validate_event_id(cls, value: Union[str, int]) -> str:
        if isinstance(value, int):
            return str(value)
        elif isinstance(value, str):
            return value
        raise ValueError("event_id must be a string or integer")


class BetCreateResponse(BaseModel):
    id: UUID4


class BetResponse(BaseModel):
    id: UUID4
    status: BetStatus


class BetsHistory(BaseModel):
    bets: List[BetResponse]


class PaginatedBetsHistory(BaseModel):
    items: List[BetResponse]
    total: int
    page: int
    size: int


class EventState(enum.Enum):
    NEW = 1
    FINISHED_WIN = 2
    FINISHED_LOSE = 3


class Event(BaseModel):
    event_id: str
    coefficient: Optional[decimal.Decimal] = None
    deadline: Optional[int] = None
    state: Optional[EventState] = None
