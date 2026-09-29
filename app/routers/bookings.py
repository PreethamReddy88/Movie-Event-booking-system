"""Booking routes — create, list, get, and cancel bookings with rate limiting."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.booking import Booking
from app.models.booking_seat import BookingSeat
from app.models.seat import Seat
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingOut
from app.services import booking_service

router = APIRouter(prefix="/api/bookings", tags=["Bookings"])
limiter = Limiter(key_func=get_remote_address)


def _booking_to_out(booking: Booking, seat_numbers: Optional[List[str]] = None) -> BookingOut:
    return BookingOut(
        id=booking.id,
        user_id=booking.user_id,
        show_id=booking.show_id,
        status=booking.status.value,
        idempotency_key=booking.idempotency_key,
        created_at=booking.created_at,
        seats=seat_numbers or [],
    )


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def create_booking(
    request: Request,
    data: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        booking = await booking_service.create_booking(db, current_user.id, data)
        # Fetch seat numbers for the response.
        bs_result = await db.execute(
            select(BookingSeat).where(BookingSeat.booking_id == booking.id)
        )
        booking_seats = bs_result.scalars().all()
        seat_ids = [bs.seat_id for bs in booking_seats]
        seat_result = await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))
        seats = seat_result.scalars().all()
        seat_numbers = [s.seat_number for s in seats]
        return _booking_to_out(booking, seat_numbers)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=list[BookingOut])
async def list_bookings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    bookings = await booking_service.list_user_bookings(db, current_user.id)
    result = []
    for b in bookings:
        bs_result = await db.execute(
            select(BookingSeat).where(BookingSeat.booking_id == b.id)
        )
        booking_seats = bs_result.scalars().all()
        seat_ids = [bs.seat_id for bs in booking_seats]
        if seat_ids:
            seat_result = await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))
            seats = seat_result.scalars().all()
            seat_numbers = [s.seat_number for s in seats]
        else:
            seat_numbers = []
        result.append(_booking_to_out(b, seat_numbers))
    return result


@router.get("/{booking_id}", response_model=BookingOut)
async def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    b_result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    b = b_result.scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if b.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this booking")

    bs_result = await db.execute(
        select(BookingSeat).where(BookingSeat.booking_id == b.id)
    )
    booking_seats = bs_result.scalars().all()
    seat_ids = [bs.seat_id for bs in booking_seats]
    if seat_ids:
        seat_result = await db.execute(select(Seat).where(Seat.id.in_(seat_ids)))
        seats = seat_result.scalars().all()
        seat_numbers = [s.seat_number for s in seats]
    else:
        seat_numbers = []
    return _booking_to_out(b, seat_numbers)


@router.post("/{booking_id}/cancel", response_model=BookingOut)
async def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        booking = await booking_service.cancel_booking(db, booking_id, current_user.id)
        return _booking_to_out(booking)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

