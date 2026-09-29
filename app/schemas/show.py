"""Pydantic schemas for shows."""

from datetime import datetime

from pydantic import BaseModel


class ShowCreate(BaseModel):
    movie_id: int
    theatre_id: int
    show_time: datetime
    price: float


class ShowOut(BaseModel):
    id: int
    movie_id: int
    theatre_id: int
    show_time: datetime
    price: float
    movie_title: str | None = None
    theatre_name: str | None = None

    model_config = {"from_attributes": True}
