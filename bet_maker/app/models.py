import uuid
from enum import Enum as PyEnum

from app.database import Base
from sqlalchemy import DateTime, Enum, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func


class BetStatus(PyEnum):
    NOT_PLAYED = "ещё не сыграла"
    WON = "выиграла"
    LOST = "проиграла"


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[Numeric] = mapped_column(
        Numeric(precision=10, scale=2), nullable=False
    )
    status: Mapped[BetStatus] = mapped_column(
        Enum(BetStatus), nullable=False, default=BetStatus.NOT_PLAYED
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
