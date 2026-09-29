"""Public movie browsing routes — no auth required."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.movie import MovieOut
from app.services import movie_service

router = APIRouter(prefix="/api/movies", tags=["Movies"])


@router.get("", response_model=list[MovieOut])
async def list_movies(
    genre: str | None = None,
    language: str | None = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_db),
):
    return await movie_service.list_movies(db, genre=genre, language=language, page=page, size=size)


@router.get("/{movie_id}", response_model=MovieOut)
async def get_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    movie = await movie_service.get_movie(db, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie
