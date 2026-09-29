"""Movie CRUD service."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.schemas.movie import MovieCreate, MovieUpdate


async def create_movie(db: AsyncSession, data: MovieCreate) -> Movie:
    movie = Movie(**data.model_dump())
    db.add(movie)
    await db.flush()
    await db.refresh(movie)
    return movie


async def get_movie(db: AsyncSession, movie_id: int) -> Movie | None:
    result = await db.execute(select(Movie).where(Movie.id == movie_id))
    return result.scalar_one_or_none()


async def list_movies(
    db: AsyncSession,
    genre: str | None = None,
    language: str | None = None,
    page: int = 1,
    size: int = 20,
) -> list[Movie]:
    query = select(Movie)
    if genre:
        query = query.where(Movie.genre.ilike(f"%{genre}%"))
    if language:
        query = query.where(Movie.language.ilike(f"%{language}%"))
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_movie(db: AsyncSession, movie_id: int, data: MovieUpdate) -> Movie | None:
    movie = await get_movie(db, movie_id)
    if not movie:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(movie, field, value)
    await db.flush()
    await db.refresh(movie)
    return movie


async def delete_movie(db: AsyncSession, movie_id: int) -> bool:
    movie = await get_movie(db, movie_id)
    if not movie:
        return False
    await db.delete(movie)
    await db.flush()
    return True
