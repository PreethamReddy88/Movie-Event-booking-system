"""Payment service — mock payment processing.

Simulates a real payment gateway by randomly succeeding or failing.
On success → confirm the booking and record the payment.
On failure → mark the booking as failed and release Redis seat locks.
"""

import logging
import random

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import Booking, BookingStatus
from app.models.booking_seat import BookingSeat
from app.models.payment import Payment, PaymentStatus
from app.models.show import Show
from app.services.booking_service import release_seat_locks

logger = logging.getLogger(__name__)


async def process_payment(
    db: AsyncSession,
    booking_id: int,
    user_id: int,
    simulate_failure: bool = False,
) -> Payment:
    """Process a mock payment for a pending booking.

    Flow:
    1. Validate booking exists, belongs to user, and is in PENDING status.
    2. Simulate payment gateway (success by default, or failure if simulate_failure=True).
    3a. On SUCCESS: set booking status = CONFIRMED, payment status = SUCCESS,
        release Redis locks (seats are now permanently booked in the DB).
    3b. On FAILURE: set booking status = FAILED, payment status = FAILED,
        release Redis locks (seats become available for others).
    """
    # ── Fetch and validate booking ──
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if not booking:
        raise ValueError("Booking not found")
    if booking.user_id != user_id:
        raise ValueError("Not your booking")
    if booking.status != BookingStatus.PENDING:
        raise ValueError(f"Booking is not pending (status: {booking.status.value})")

    # Check if payment already exists (idempotency at the payment level).
    existing_payment = await db.execute(
        select(Payment).where(Payment.booking_id == booking_id)
    )
    if existing_payment.scalar_one_or_none():
        raise ValueError("Payment already processed for this booking")

    # ── Calculate amount ──
    show_result = await db.execute(select(Show).where(Show.id == booking.show_id))
    show = show_result.scalar_one_or_none()
    bs_result = await db.execute(
        select(BookingSeat).where(BookingSeat.booking_id == booking_id)
    )
    booking_seats = bs_result.scalars().all()
    amount = float(show.price) * len(booking_seats)

    # ── Simulate payment gateway ──
    payment_success = not simulate_failure
    logger.info(
        "Payment attempt: booking=%s amount=%.2f result=%s",
        booking_id, amount, "SUCCESS" if payment_success else "FAILED",
    )

    seat_ids = [bs.seat_id for bs in booking_seats]

    if payment_success:
        # ── SUCCESS PATH ──
        booking.status = BookingStatus.CONFIRMED
        payment = Payment(
            booking_id=booking_id,
            amount=amount,
            status=PaymentStatus.SUCCESS,
        )
        db.add(payment)
        await db.flush()
        await db.refresh(payment)

        # Release Redis locks — the seats are now confirmed in the DB,
        # so the Redis lock is no longer needed.
        await release_seat_locks(booking.show_id, seat_ids)

        logger.info("Payment success: booking=%s confirmed", booking_id)
        return payment
    else:
        # ── FAILURE PATH ──
        booking.status = BookingStatus.FAILED
        payment = Payment(
            booking_id=booking_id,
            amount=amount,
            status=PaymentStatus.FAILED,
        )
        db.add(payment)
        await db.flush()
        await db.refresh(payment)

        # Release Redis locks — the seats are freed for other users.
        await release_seat_locks(booking.show_id, seat_ids)

        logger.info("Payment failed: booking=%s failed, seats released", booking_id)
        return payment
