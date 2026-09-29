"""Pydantic schemas for movies."""

from pydantic import BaseModel


class MovieCreate(BaseModel):
    title: str
    description: str | None = None
    duration_minutes: int
    language: str
    genre: str


class MovieUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    duration_minutes: int | None = None
    language: str | None = None
    genre: str | None = None


class MovieOut(BaseModel):
    id: int
    title: str
    description: str | None
    duration_minutes: int
    language: str
    genre: str

    model_config = {"from_attributes": True}
