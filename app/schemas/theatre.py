"""Pydantic schemas for theatres."""

from pydantic import BaseModel


class TheatreCreate(BaseModel):
    name: str
    city: str
    address: str | None = None


class TheatreUpdate(BaseModel):
    name: str | None = None
    city: str | None = None
    address: str | None = None


class TheatreOut(BaseModel):
    id: int
    name: str
    city: str
    address: str | None

    model_config = {"from_attributes": True}
