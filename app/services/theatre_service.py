"""Theatre CRUD service with auto seat generation."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.seat import Seat, SeatType
from app.models.theatre import Theatre
from app.schemas.theatre import TheatreCreate, TheatreUpdate


async def create_theatre(db: AsyncSession, data: TheatreCreate) -> Theatre:
    theatre = Theatre(**data.model_dump())
    db.add(theatre)
    await db.flush()
    await db.refresh(theatre)
    return theatre


async def get_theatre(db: AsyncSession, theatre_id: int) -> Theatre | None:
    result = await db.execute(select(Theatre).where(Theatre.id == theatre_id))
    return result.scalar_one_or_none()


async def list_theatres(db: AsyncSession, city: str | None = None) -> list[Theatre]:
    query = select(Theatre)
    if city:
        query = query.where(Theatre.city.ilike(f"%{city}%"))
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_theatre(db: AsyncSession, theatre_id: int, data: TheatreUpdate) -> Theatre | None:
    theatre = await get_theatre(db, theatre_id)
    if not theatre:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(theatre, field, value)
    await db.flush()
    await db.refresh(theatre)
    return theatre


async def delete_theatre(db: AsyncSession, theatre_id: int) -> bool:
    theatre = await get_theatre(db, theatre_id)
    if not theatre:
        return False
    await db.delete(theatre)
    await db.flush()
    return True


async def generate_seats(
    db: AsyncSession,
    theatre_id: int,
    rows: int = 10,
    seats_per_row: int = 10,
    premium_rows: int = 2,
) -> list[Seat]:
    """Auto-generate seats for a theatre.

    Rows A through <rows> with <seats_per_row> seats each.
    First <premium_rows> rows are marked as premium, the rest as regular.
    Example: rows=10, seats_per_row=10 → A1..A10, B1..B10, ... J1..J10.
    """
    theatre = await get_theatre(db, theatre_id)
    if not theatre:
        raise ValueError(f"Theatre {theatre_id} not found")

    seats: list[Seat] = []
    for row_idx in range(rows):
        row_letter = chr(ord("A") + row_idx)
        seat_type = SeatType.PREMIUM if row_idx < premium_rows else SeatType.REGULAR
        for seat_num in range(1, seats_per_row + 1):
            seat = Seat(
                theatre_id=theatre_id,
                seat_number=f"{row_letter}{seat_num}",
                seat_type=seat_type,
            )
            db.add(seat)
            seats.append(seat)
    await db.flush()
    return seats
