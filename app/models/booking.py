"""Booking model — a user's reservation for a show."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    show_id: Mapped[int] = mapped_column(ForeignKey("shows.id"), index=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.PENDING, server_default="pending"
    )
    idempotency_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="bookings")  # type: ignore[name-defined]
    show: Mapped["Show"] = relationship(back_populates="bookings")  # type: ignore[name-defined]
    booking_seats: Mapped[list["BookingSeat"]] = relationship(  # type: ignore[name-defined]
        back_populates="booking", cascade="all, delete-orphan"
    )
    payment: Mapped["Payment | None"] = relationship(back_populates="booking", uselist=False)  # type: ignore[name-defined]
