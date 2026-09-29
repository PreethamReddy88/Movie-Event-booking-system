"""BookingSeat join table — maps booked seats to a booking."""

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class BookingSeat(Base):
    __tablename__ = "booking_seats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    seat_id: Mapped[int] = mapped_column(ForeignKey("seats.id"), index=True)

    # Relationships
    booking: Mapped["Booking"] = relationship(back_populates="booking_seats")  # type: ignore[name-defined]
    seat: Mapped["Seat"] = relationship(back_populates="booking_seats")  # type: ignore[name-defined]

    __table_args__ = (
        # A seat can only appear once per booking.
        UniqueConstraint("booking_id", "seat_id", name="uq_booking_seat"),
    )
