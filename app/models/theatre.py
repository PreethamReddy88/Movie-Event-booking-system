"""Theatre model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Theatre(Base):
    __tablename__ = "theatres"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(100), index=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    shows: Mapped[list["Show"]] = relationship(back_populates="theatre")  # type: ignore[name-defined]
    seats: Mapped[list["Seat"]] = relationship(back_populates="theatre")  # type: ignore[name-defined]
