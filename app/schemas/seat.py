"""Pydantic schemas for seats and seat maps."""

from pydantic import BaseModel


class SeatOut(BaseModel):
    id: int
    theatre_id: int
    seat_number: str
    seat_type: str

    model_config = {"from_attributes": True}


class SeatMapItem(BaseModel):
    """A single seat in the seat map with availability info."""
    id: int
    seat_number: str
    seat_type: str
    is_booked: bool
