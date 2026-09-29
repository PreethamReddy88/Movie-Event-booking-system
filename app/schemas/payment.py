"""Pydantic schemas for payments."""

from datetime import datetime

from pydantic import BaseModel


class PaymentCreate(BaseModel):
    booking_id: int
    simulate_failure: bool = False


class PaymentOut(BaseModel):
    id: int
    booking_id: int
    amount: float
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
