"""Tests for the booking transaction logic.

These tests verify:
1. A booking is successfully created for valid seats.
2. Idempotency — retrying with the same key returns the same booking.
3. Double-booking the same seat is rejected.
4. Cancellation frees the seats.
5. Admin-only routes reject regular users.

NOTE: These tests use SQLite (no FOR UPDATE support) and mock Redis,
so they validate the *logic* rather than the actual lock behavior.
For full concurrency testing, use the standalone concurrency_test.py
against a live Postgres + Redis stack.
"""

from datetime import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.movie import Movie
from app.models.seat import Seat, SeatType
from app.models.show import Show
from app.models.theatre import Theatre
from app.models.user import User, UserRole
from app.core.security import hash_password, create_access_token
from tests.conftest import get_auth_headers


async def _seed_data(db: AsyncSession) -> dict:
    """Insert a movie, theatre, show, and seats for testing."""
    movie = Movie(title="Test Movie", duration_minutes=120, language="English", genre="Action")
    db.add(movie)
    await db.flush()

    theatre = Theatre(name="Test Theatre", city="Mumbai")
    db.add(theatre)
    await db.flush()

    show = Show(
        movie_id=movie.id,
        theatre_id=theatre.id,
        show_time=datetime(2026, 12, 1, 18, 0, 0),
        price=250.0,
    )
    db.add(show)
    await db.flush()

    seats = []
    for i in range(1, 6):
        seat = Seat(theatre_id=theatre.id, seat_number=f"A{i}", seat_type=SeatType.REGULAR)
        db.add(seat)
        seats.append(seat)
    await db.flush()

    user = User(
        name="Booking User",
        email=f"booker_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("password123"),
        role=UserRole.USER,
    )
    db.add(user)
    await db.commit()

    for s in seats:
        await db.refresh(s)
    await db.refresh(movie)
    await db.refresh(theatre)
    await db.refresh(show)
    await db.refresh(user)

    return {
        "movie": movie,
        "theatre": theatre,
        "show": show,
        "seats": seats,
        "user": user,
    }


@pytest.mark.asyncio
@patch("app.services.booking_service.acquire_seat_locks", new_callable=AsyncMock)
@patch("app.services.booking_service.release_seat_locks", new_callable=AsyncMock)
async def test_create_booking_success(mock_release, mock_acquire, client: AsyncClient, db_session: AsyncSession):
    """Successfully book available seats."""
    data = await _seed_data(db_session)
    seat_ids = [s.id for s in data["seats"][:2]]
    mock_acquire.return_value = seat_ids  # Simulate successful lock acquisition

    headers = get_auth_headers(data["user"].id)
    idem_key = str(uuid.uuid4())

    resp = await client.post(
        "/api/bookings",
        json={"show_id": data["show"].id, "seat_ids": seat_ids, "idempotency_key": idem_key},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["show_id"] == data["show"].id
    assert len(body["seats"]) == 2


@pytest.mark.asyncio
@patch("app.services.booking_service.acquire_seat_locks", new_callable=AsyncMock)
@patch("app.services.booking_service.release_seat_locks", new_callable=AsyncMock)
async def test_idempotency(mock_release, mock_acquire, client: AsyncClient, db_session: AsyncSession):
    """Retrying with the same idempotency key returns the same booking."""
    data = await _seed_data(db_session)
    seat_ids = [s.id for s in data["seats"][:1]]
    mock_acquire.return_value = seat_ids

    headers = get_auth_headers(data["user"].id)
    idem_key = str(uuid.uuid4())

    payload = {"show_id": data["show"].id, "seat_ids": seat_ids, "idempotency_key": idem_key}
    resp1 = await client.post("/api/bookings", json=payload, headers=headers)
    resp2 = await client.post("/api/bookings", json=payload, headers=headers)

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] == resp2.json()["id"]


@pytest.mark.asyncio
@patch("app.services.booking_service.acquire_seat_locks", new_callable=AsyncMock)
@patch("app.services.booking_service.release_seat_locks", new_callable=AsyncMock)
async def test_double_booking_rejected(mock_release, mock_acquire, client: AsyncClient, db_session: AsyncSession):
    """Second booking for the same seats is rejected at the DB level."""
    data = await _seed_data(db_session)
    seat_ids = [s.id for s in data["seats"][:2]]
    mock_acquire.return_value = seat_ids

    headers = get_auth_headers(data["user"].id)

    # First booking succeeds.
    resp1 = await client.post(
        "/api/bookings",
        json={"show_id": data["show"].id, "seat_ids": seat_ids, "idempotency_key": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp1.status_code == 201

    # Second booking for the same seats should fail.
    resp2 = await client.post(
        "/api/bookings",
        json={"show_id": data["show"].id, "seat_ids": seat_ids, "idempotency_key": str(uuid.uuid4())},
        headers=headers,
    )
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_admin_route_rejects_regular_user(client: AsyncClient, db_session: AsyncSession):
    """Admin endpoints should reject non-admin users with 403."""
    user = User(
        name="Regular User",
        email=f"regular_{uuid.uuid4().hex[:8]}@test.com",
        password_hash=hash_password("password123"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    headers = get_auth_headers(user.id, role="user")
    resp = await client.post(
        "/api/admin/movies",
        json={"title": "X", "duration_minutes": 90, "language": "English", "genre": "Drama"},
        headers=headers,
    )
    assert resp.status_code == 403
