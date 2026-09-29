"""Show service — creating shows and listing with filters."""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.show import Show
from app.models.theatre import Theatre
from app.schemas.show import ShowCreate


async def create_show(db: AsyncSession, data: ShowCreate) -> Show:
    show = Show(**data.model_dump())
    db.add(show)
    await db.flush()
    await db.refresh(show)
    return show


async def get_show(db: AsyncSession, show_id: int) -> Show | None:
    result = await db.execute(
        select(Show)
        .options(selectinload(Show.movie), selectinload(Show.theatre))
        .where(Show.id == show_id)
    )
    return result.scalar_one_or_none()


async def list_shows_for_movie(
    db: AsyncSession,
    movie_id: int,
    city: str | None = None,
    show_date: date | None = None,
) -> list[Show]:
    """List shows for a movie, optionally filtered by city and date."""
    query = (
        select(Show)
        .options(selectinload(Show.movie), selectinload(Show.theatre))
        .where(Show.movie_id == movie_id)
    )
    if city:
        query = query.join(Theatre).where(Theatre.city.ilike(f"%{city}%"))
    if show_date:
        # Filter shows on the given date (compare date portion of show_time).
        from sqlalchemy import func
        query = query.where(func.date(Show.show_time) == show_date)
    query = query.order_by(Show.show_time)
    result = await db.execute(query)
    return list(result.scalars().all())
