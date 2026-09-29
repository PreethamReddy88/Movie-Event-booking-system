"""Pydantic schemas for bookings."""

from datetime import datetime

from pydantic import BaseModel


class BookingCreate(BaseModel):
    show_id: int
    seat_ids: list[int]
    idempotency_key: str


class BookingOut(BaseModel):
    id: int
    user_id: int
    show_id: int
    status: str
    idempotency_key: str
    created_at: datetime
    seats: list[str] = []  # seat numbers

    model_config = {"from_attributes": True}
