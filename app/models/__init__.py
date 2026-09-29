"""SQLAlchemy declarative base and model re-exports.

Import every model here so that `Base.metadata` contains all tables
when Alembic or `create_all` inspects it.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so their tables are registered on Base.metadata.
from app.models.user import User  # noqa: E402, F401
from app.models.movie import Movie  # noqa: E402, F401
from app.models.theatre import Theatre  # noqa: E402, F401
from app.models.show import Show  # noqa: E402, F401
from app.models.seat import Seat  # noqa: E402, F401
from app.models.booking import Booking  # noqa: E402, F401
from app.models.booking_seat import BookingSeat  # noqa: E402, F401
from app.models.payment import Payment  # noqa: E402, F401
