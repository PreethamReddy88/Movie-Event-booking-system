"""Public show browsing and seat map routes."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.seat import SeatMapItem
from app.schemas.show import ShowOut
from app.services import booking_service, show_service

router = APIRouter(prefix="/api/shows", tags=["Shows"])


@router.get("/movie/{movie_id}", response_model=list[ShowOut])
async def list_shows_for_movie(
    movie_id: int,
    city: str | None = None,
    show_date: date | None = None,
    db: AsyncSession = Depends(get_db),
):
    shows = await show_service.list_shows_for_movie(db, movie_id, city=city, show_date=show_date)
    result = []
    for s in shows:
        result.append(
            ShowOut(
                id=s.id,
                movie_id=s.movie_id,
                theatre_id=s.theatre_id,
                show_time=s.show_time,
                price=float(s.price),
                movie_title=s.movie.title if s.movie else None,
                theatre_name=s.theatre.name if s.theatre else None,
            )
        )
    return result


@router.get("/{show_id}/seats", response_model=list[SeatMapItem])
async def get_seat_map(show_id: int, db: AsyncSession = Depends(get_db)):
    try:
        seat_map = await booking_service.get_seat_map(db, show_id)
        return seat_map
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
