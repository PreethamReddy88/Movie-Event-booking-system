"""Movie model."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int]
    language: Mapped[str] = mapped_column(String(50))
    genre: Mapped[str] = mapped_column(String(100))

    # Relationships
    shows: Mapped[list["Show"]] = relationship(back_populates="movie")  # type: ignore[name-defined]
