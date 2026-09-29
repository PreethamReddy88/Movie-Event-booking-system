"""Admin-only routes — CRUD for movies, theatres, shows, and seat generation."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas.movie import MovieCreate, MovieOut, MovieUpdate
from app.schemas.seat import SeatOut
from app.schemas.show import ShowCreate, ShowOut
from app.schemas.theatre import TheatreCreate, TheatreOut, TheatreUpdate
from app.services import movie_service, show_service, theatre_service

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_admin)])


# ── Movies ──

@router.post("/movies", response_model=MovieOut, status_code=status.HTTP_201_CREATED)
async def create_movie(data: MovieCreate, db: AsyncSession = Depends(get_db)):
    return await movie_service.create_movie(db, data)


@router.put("/movies/{movie_id}", response_model=MovieOut)
async def update_movie(movie_id: int, data: MovieUpdate, db: AsyncSession = Depends(get_db)):
    movie = await movie_service.update_movie(db, movie_id, data)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@router.delete("/movies/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(movie_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await movie_service.delete_movie(db, movie_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Movie not found")


# ── Theatres ──

@router.post("/theatres", response_model=TheatreOut, status_code=status.HTTP_201_CREATED)
async def create_theatre(data: TheatreCreate, db: AsyncSession = Depends(get_db)):
    return await theatre_service.create_theatre(db, data)


@router.put("/theatres/{theatre_id}", response_model=TheatreOut)
async def update_theatre(
    theatre_id: int, data: TheatreUpdate, db: AsyncSession = Depends(get_db)
):
    theatre = await theatre_service.update_theatre(db, theatre_id, data)
    if not theatre:
        raise HTTPException(status_code=404, detail="Theatre not found")
    return theatre


@router.delete("/theatres/{theatre_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_theatre(theatre_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await theatre_service.delete_theatre(db, theatre_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Theatre not found")


@router.post(
    "/theatres/{theatre_id}/generate-seats",
    response_model=list[SeatOut],
    status_code=status.HTTP_201_CREATED,
)
async def generate_seats(
    theatre_id: int,
    rows: int = 10,
    seats_per_row: int = 10,
    premium_rows: int = 2,
    db: AsyncSession = Depends(get_db),
):
    try:
        seats = await theatre_service.generate_seats(
            db, theatre_id, rows, seats_per_row, premium_rows
        )
        return seats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ── Shows ──

@router.post("/shows", response_model=ShowOut, status_code=status.HTTP_201_CREATED)
async def create_show(data: ShowCreate, db: AsyncSession = Depends(get_db)):
    show = await show_service.create_show(db, data)
    return ShowOut(
        id=show.id,
        movie_id=show.movie_id,
        theatre_id=show.theatre_id,
        show_time=show.show_time,
        price=float(show.price),
    )
