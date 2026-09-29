"""Show model — a screening of a movie at a theatre."""

from datetime import datetime

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Show(Base):
    __tablename__ = "shows"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), index=True)
    theatre_id: Mapped[int] = mapped_column(ForeignKey("theatres.id"), index=True)
    show_time: Mapped[datetime]
    price: Mapped[float] = mapped_column(Numeric(10, 2))

    # Relationships
    movie: Mapped["Movie"] = relationship(back_populates="shows")  # type: ignore[name-defined]
    theatre: Mapped["Theatre"] = relationship(back_populates="shows")  # type: ignore[name-defined]
    bookings: Mapped[list["Booking"]] = relationship(back_populates="show")  # type: ignore[name-defined]
