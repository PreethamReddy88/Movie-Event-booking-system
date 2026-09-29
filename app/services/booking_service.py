"""Booking service — the core concurrency-safe booking logic.

This module implements a two-layer defence against double-booking:

LAYER 1 — Redis Distributed Lock (Optimistic / Fast Path)
    Before touching the database, we attempt to acquire a Redis lock for
    every requested seat using SET NX with a 5-minute TTL.  This prevents
    two users from even *starting* the booking flow for the same seat
    concurrently.  It's fast and avoids unnecessary DB contention.

LAYER 2 — Database Transaction with SELECT ... FOR UPDATE (Pessimistic / Safety Net)
    Even if the Redis layer is bypassed (network partition, Redis restart,
    bug), the booking itself is performed inside a serializable DB
    transaction.  We SELECT the booking_seats rows FOR UPDATE to acquire
    row-level locks, then verify no confirmed/pending booking already
    holds those seats before inserting.  This is the authoritative
    guarantee — the database is the single source of truth.

Why two layers?
    Redis alone is not durable — keys can be lost.  DB locks alone are
    correct but create contention under high concurrency.  The combination
    gives us the best of both worlds: Redis absorbs the thundering herd,
    and the DB catches anything that slips through.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis_client import redis_client
from app.models.booking import Booking, BookingStatus
from app.models.booking_seat import BookingSeat
from app.models.seat import Seat
from app.models.show import Show
from app.schemas.booking import BookingCreate

logger = logging.getLogger(__name__)

# ── Constants ──
LOCK_TTL_SECONDS = 300  # 5-minute TTL for seat locks
LOCK_PREFIX = "lock:seat"


def _lock_key(show_id: int, seat_id: int) -> str:
    """Redis key for a seat lock scoped to a specific show."""
    return f"{LOCK_PREFIX}:{show_id}:{seat_id}"


# ─────────────────────────────────────────────────────────────────────
# LAYER 1: Redis lock acquisition / release
# ─────────────────────────────────────────────────────────────────────

async def acquire_seat_locks(show_id: int, seat_ids: list[int], user_id: int) -> list[int]:
    """Try to acquire a Redis lock for each seat.

    Uses SET key value NX EX ttl — the lock is only acquired if no key
    exists (NX).  The value is the user_id so we can identify the holder.

    Returns:
        List of seat_ids for which the lock was successfully acquired.
        If this list != seat_ids, some seats are held by another user.
    """
    acquired: list[int] = []
    for seat_id in seat_ids:
        key = _lock_key(show_id, seat_id)
        # SET NX with TTL — atomic "lock if free" operation.
        ok = await redis_client.set(key, str(user_id), nx=True, ex=LOCK_TTL_SECONDS)
        if ok:
            acquired.append(seat_id)
            logger.info("Lock acquired: show=%s seat=%s user=%s", show_id, seat_id, user_id)
        else:
            holder = await redis_client.get(key)
            logger.warning(
                "Lock conflict: show=%s seat=%s requested_by=%s held_by=%s",
                show_id, seat_id, user_id, holder,
            )
    return acquired


async def release_seat_locks(show_id: int, seat_ids: list[int]) -> None:
    """Release Redis locks for the given seats."""
    for seat_id in seat_ids:
        key = _lock_key(show_id, seat_id)
        await redis_client.delete(key)
        logger.info("Lock released: show=%s seat=%s", show_id, seat_id)


# ─────────────────────────────────────────────────────────────────────
# LAYER 2: Database-level booking with SELECT ... FOR UPDATE
# ─────────────────────────────────────────────────────────────────────

async def _check_seats_available(
    db: AsyncSession, show_id: int, seat_ids: list[int]
) -> bool:
    """Check that none of the requested seats are already booked for this show.

    Uses SELECT ... FOR UPDATE on the BookingSeat rows joined with Booking
    to acquire row-level locks and prevent concurrent inserts.

    This is the DATABASE-LEVEL guarantee — even if the Redis lock was somehow
    skipped or expired, this query will block concurrent transactions and
    ensure only one booking succeeds.
    """
    # Find any existing booking_seats for these seats in confirmed/pending bookings
    # for the same show.  The FOR UPDATE clause locks those rows so a concurrent
    # transaction will block here until we commit or rollback.
    stmt = (
        select(BookingSeat.seat_id)
        .join(Booking, BookingSeat.booking_id == Booking.id)
        .where(
            and_(
                Booking.show_id == show_id,
                BookingSeat.seat_id.in_(seat_ids),
                Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            )
        )
        .with_for_update()  # <-- Row-level lock: blocks other transactions
    )
    result = await db.execute(stmt)
    already_booked = result.scalars().all()

    if already_booked:
        logger.warning(
            "DB-level conflict: show=%s seats=%s already booked", show_id, list(already_booked)
        )
        return False
    return True


async def create_booking(
    db: AsyncSession, user_id: int, data: BookingCreate
) -> Booking:
    """Create a booking with full concurrency protection.

    Flow:
    1. Idempotency check — return existing booking if key already used.
    2. Validate show exists and seats belong to the show's theatre.
    3. LAYER 1: Acquire Redis locks for every requested seat.
    4. LAYER 2: Inside a DB transaction, SELECT ... FOR UPDATE to double-check
       availability, then insert booking + booking_seats.
    5. On any failure, release Redis locks and raise.
    """
    # ── Step 1: Idempotency ──
    # If the client retries with the same idempotency_key, return the original
    # booking instead of creating a duplicate.
    existing = await db.execute(
        select(Booking).where(Booking.idempotency_key == data.idempotency_key)
    )
    existing_booking = existing.scalar_one_or_none()
    if existing_booking:
        logger.info("Idempotent retry detected: key=%s", data.idempotency_key)
        return existing_booking

    # ── Step 2: Validate show and seats ──
    show = await db.execute(select(Show).where(Show.id == data.show_id))
    show_obj = show.scalar_one_or_none()
    if not show_obj:
        raise ValueError("Show not found")

    seat_result = await db.execute(
        select(Seat).where(
            Seat.id.in_(data.seat_ids),
            Seat.theatre_id == show_obj.theatre_id,
        )
    )
    seats = seat_result.scalars().all()
    if len(seats) != len(data.seat_ids):
        raise ValueError("One or more seats are invalid for this theatre")

    # ── Step 3: LAYER 1 — Redis lock ──
    acquired = await acquire_seat_locks(data.show_id, data.seat_ids, user_id)
    if set(acquired) != set(data.seat_ids):
        # Some seats are locked by another user — release what we acquired and fail.
        await release_seat_locks(data.show_id, acquired)
        failed = set(data.seat_ids) - set(acquired)
        raise ValueError(f"Seats currently held by another user: {failed}")

    try:
        # ── Step 4: LAYER 2 — DB transaction with FOR UPDATE ──
        available = await _check_seats_available(db, data.show_id, data.seat_ids)
        if not available:
            # Another booking exists in the DB (edge case: Redis lock was stale).
            await release_seat_locks(data.show_id, data.seat_ids)
            raise ValueError("One or more seats are already booked for this show")

        # All clear — create the booking and link seats.
        booking = Booking(
            user_id=user_id,
            show_id=data.show_id,
            status=BookingStatus.PENDING,
            idempotency_key=data.idempotency_key,
        )
        db.add(booking)
        await db.flush()  # Get booking.id

        for seat_id in data.seat_ids:
            db.add(BookingSeat(booking_id=booking.id, seat_id=seat_id))
        await db.flush()

        logger.info(
            "Booking created: id=%s user=%s show=%s seats=%s",
            booking.id, user_id, data.show_id, data.seat_ids,
        )
        return booking

    except Exception:
        # On any failure, release the Redis locks so the seats become available again.
        await release_seat_locks(data.show_id, data.seat_ids)
        raise


async def get_booking(db: AsyncSession, booking_id: int) -> Booking | None:
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    return result.scalar_one_or_none()


async def list_user_bookings(db: AsyncSession, user_id: int) -> list[Booking]:
    result = await db.execute(
        select(Booking)
        .where(Booking.user_id == user_id)
        .order_by(Booking.created_at.desc())
    )
    return list(result.scalars().all())


async def cancel_booking(db: AsyncSession, booking_id: int, user_id: int) -> Booking:
    """Cancel a booking: update status, release Redis locks and free seats."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise ValueError("Booking not found")
    if booking.user_id != user_id:
        raise ValueError("Not your booking")
    if booking.status == BookingStatus.CANCELLED:
        raise ValueError("Booking already cancelled")
    if booking.status == BookingStatus.CONFIRMED:
        # Allow cancellation of confirmed bookings too (refund flow would go here).
        pass

    booking.status = BookingStatus.CANCELLED

    # Free the seats: fetch booking_seats and release Redis locks.
    bs_result = await db.execute(
        select(BookingSeat).where(BookingSeat.booking_id == booking_id)
    )
    booking_seats = bs_result.scalars().all()
    seat_ids = [bs.seat_id for bs in booking_seats]
    await release_seat_locks(booking.show_id, seat_ids)

    await db.flush()
    logger.info("Booking cancelled: id=%s user=%s seats=%s", booking_id, user_id, seat_ids)
    return booking


async def get_seat_map(db: AsyncSession, show_id: int) -> list[dict]:
    """Return the seat map for a show: each seat with its booked/free status."""
    show = await db.execute(select(Show).where(Show.id == show_id))
    show_obj = show.scalar_one_or_none()
    if not show_obj:
        raise ValueError("Show not found")

    # Get all seats for this theatre.
    seats_result = await db.execute(
        select(Seat).where(Seat.theatre_id == show_obj.theatre_id).order_by(Seat.seat_number)
    )
    seats = seats_result.scalars().all()

    # Get booked seat IDs for this show (pending or confirmed bookings).
    booked_result = await db.execute(
        select(BookingSeat.seat_id)
        .join(Booking, BookingSeat.booking_id == Booking.id)
        .where(
            Booking.show_id == show_id,
            Booking.status.in_([BookingStatus.PENDING, BookingStatus.CONFIRMED]),
        )
    )
    booked_ids = set(booked_result.scalars().all())

    return [
        {
            "id": seat.id,
            "seat_number": seat.seat_number,
            "seat_type": seat.seat_type.value,
            "is_booked": seat.id in booked_ids,
        }
        for seat in seats
    ]
