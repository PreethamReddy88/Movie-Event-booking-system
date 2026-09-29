"""Seat model — physical seats belonging to a theatre."""

import enum

from sqlalchemy import Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class SeatType(str, enum.Enum):
    REGULAR = "regular"
    PREMIUM = "premium"


class Seat(Base):
    __tablename__ = "seats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    theatre_id: Mapped[int] = mapped_column(ForeignKey("theatres.id"), index=True)
    seat_number: Mapped[str] = mapped_column(String(10))  # e.g. "A1", "B5"
    seat_type: Mapped[SeatType] = mapped_column(
        Enum(SeatType), default=SeatType.REGULAR, server_default="regular"
    )

    # Relationships
    theatre: Mapped["Theatre"] = relationship(back_populates="seats")  # type: ignore[name-defined]
    booking_seats: Mapped[list["BookingSeat"]] = relationship(back_populates="seat")  # type: ignore[name-defined]
