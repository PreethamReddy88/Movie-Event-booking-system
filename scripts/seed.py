"""Database seed script for local development and testing.

Populates the database with:
- Admin and standard test users
- Sample movies
- Theatres and seat layouts (VIP, Premium, Regular)
- Upcoming shows
"""

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.movie import Movie
from app.models.theatre import Theatre
from app.models.seat import Seat, SeatType
from app.models.show import Show


async def seed():
    async with async_session_factory() as db:
        # Check if already seeded
        result = await db.execute(select(User).filter_by(email="admin@cinema.com"))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        print("Seeding database...")

        # 1. Users
        admin_user = User(
            name="System Admin",
            email="admin@cinema.com",
            password_hash=hash_password("Admin@123"),
            role=UserRole.ADMIN,
        )
        demo_user = User(
            name="Alex Mercer",
            email="alex@example.com",
            password_hash=hash_password("User@123"),
            role=UserRole.USER,
        )
        db.add_all([admin_user, demo_user])
        await db.flush()
        print("[+] Created Users (Admin: admin@cinema.com / Admin@123, User: alex@example.com / User@123)")

        # 2. Movies
        movie1 = Movie(
            title="Dune: Part Two",
            duration_minutes=166,
            language="English",
            genre="Sci-Fi / Adventure",
        )
        movie2 = Movie(
            title="Oppenheimer",
            duration_minutes=180,
            language="English",
            genre="Biography / Drama / History",
        )
        movie3 = Movie(
            title="Interstellar",
            duration_minutes=169,
            language="English",
            genre="Sci-Fi / Drama",
        )
        db.add_all([movie1, movie2, movie3])
        await db.flush()
        print("[+] Created Movies")

        # 3. Theatres & Seats
        theatre1 = Theatre(name="PVR ICON - Palladium IMAX", city="Mumbai")
        theatre2 = Theatre(name="INOX Megaplex - CyberHub", city="Gurugram")
        db.add_all([theatre1, theatre2])
        await db.flush()

        theatre1_seats = []
        for row_letter, seat_type in [("A", SeatType.PREMIUM), ("B", SeatType.PREMIUM), ("C", SeatType.REGULAR), ("D", SeatType.REGULAR), ("E", SeatType.REGULAR)]:
            for col in range(1, 9):
                theatre1_seats.append(
                    Seat(theatre_id=theatre1.id, seat_number=f"{row_letter}{col}", seat_type=seat_type)
                )
        db.add_all(theatre1_seats)

        theatre2_seats = []
        for row_letter, seat_type in [("A", SeatType.PREMIUM), ("B", SeatType.REGULAR), ("C", SeatType.REGULAR), ("D", SeatType.REGULAR)]:
            for col in range(1, 7):
                theatre2_seats.append(
                    Seat(theatre_id=theatre2.id, seat_number=f"{row_letter}{col}", seat_type=seat_type)
                )
        db.add_all(theatre2_seats)
        await db.flush()
        print("[+] Created Theatres & Seat Layouts")

        # 4. Shows
        now = datetime.now(timezone.utc)
        shows = [
            Show(
                movie_id=movie1.id,
                theatre_id=theatre1.id,
                show_time=now + timedelta(days=1, hours=3),
                price=350.0,
            ),
            Show(
                movie_id=movie1.id,
                theatre_id=theatre1.id,
                show_time=now + timedelta(days=1, hours=7),
                price=400.0,
            ),
            Show(
                movie_id=movie2.id,
                theatre_id=theatre1.id,
                show_time=now + timedelta(days=2, hours=4),
                price=320.0,
            ),
            Show(
                movie_id=movie3.id,
                theatre_id=theatre2.id,
                show_time=now + timedelta(days=1, hours=5),
                price=280.0,
            ),
        ]
        db.add_all(shows)
        await db.commit()
        print("[+] Created Shows")
        print("\nSeed completed successfully!")


if __name__ == "__main__":
    asyncio.run(seed())
