"""End-to-end API verification script against the live application and database.
"""

import asyncio
from pathlib import Path
import sys
import uuid

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from httpx import ASGITransport, AsyncClient
from app.main import app


async def test_full_flow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        res = await client.get("/health")
        assert res.status_code == 200, f"Health check failed: {res.text}"
        print("[+] Health check OK: /health -> 200")

        # 2. Login as demo user
        res = await client.post(
            "/api/auth/login",
            json={"email": "alex@example.com", "password": "User@123"},
        )
        assert res.status_code == 200, f"Login failed: {res.text}"
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("[+] User login OK: JWT access token acquired")

        # 3. Check /api/auth/me
        res = await client.get("/api/auth/me", headers=headers)
        assert res.status_code == 200
        user_info = res.json()
        print(f"[+] /api/auth/me OK: Welcome {user_info['name']} ({user_info['role']})")

        # 4. List Movies
        res = await client.get("/api/movies")
        assert res.status_code == 200
        movies = res.json()
        print(f"[+] /api/movies OK: Found {len(movies)} movies in catalog")
        first_movie = movies[0]

        # 5. List Shows for Movie
        res = await client.get(f"/api/shows/movie/{first_movie['id']}")
        assert res.status_code == 200
        shows = res.json()
        print(f"[+] /api/shows/movie/{first_movie['id']} OK: Found {len(shows)} shows")
        first_show = shows[0]

        # 6. Check Available Seats
        res = await client.get(f"/api/shows/{first_show['id']}/seats")
        assert res.status_code == 200
        seats_data = res.json()
        print(f"[+] /api/shows/{first_show['id']}/seats OK: Found {len(seats_data)} seats")
        
        # Pick 2 available seats
        available_seats = [s for s in seats_data if not s["is_booked"]]
        assert len(available_seats) >= 2, "Not enough available seats!"
        seat_ids_to_book = [available_seats[0]["id"], available_seats[1]["id"]]
        seat_names = [available_seats[0]["seat_number"], available_seats[1]["seat_number"]]
        print(f"[+] Selecting seats: {seat_names} (IDs: {seat_ids_to_book})")

        # 7. Create Booking
        idempotency_key = f"verify-{uuid.uuid4()}"
        booking_payload = {
            "show_id": first_show["id"],
            "seat_ids": seat_ids_to_book,
            "idempotency_key": idempotency_key,
        }
        res = await client.post("/api/bookings", json=booking_payload, headers=headers)
        assert res.status_code == 201, f"Booking creation failed: {res.text}"
        booking_data = res.json()
        booking_id = booking_data["id"]
        print(f"[+] Booking Created OK: ID={booking_id}, Status={booking_data['status']}, Seats={booking_data['seats']}")

        # 8. Complete Mock Payment
        payment_payload = {
            "booking_id": booking_id,
        }
        res = await client.post("/api/payments", json=payment_payload, headers=headers)
        assert res.status_code == 201, f"Payment charge failed: {res.text}"
        payment_data = res.json()
        print(f"[+] Payment Processed OK: Payment ID={payment_data['id']}, Amount=Rs.{payment_data['amount']}, Status={payment_data['status']}")

        # 9. Verify Booking is Confirmed
        res = await client.get(f"/api/bookings/{booking_id}", headers=headers)
        assert res.status_code == 200
        confirmed_booking = res.json()
        assert confirmed_booking["status"].lower() == "confirmed", f"Expected confirmed, got {confirmed_booking['status']}"
        print(f"[+] Booking Verified OK: Status={confirmed_booking['status']}")

        # 10. Verify Seats are now marked booked
        res = await client.get(f"/api/shows/{first_show['id']}/seats")
        assert res.status_code == 200
        updated_seats = res.json()
        booked_seat_ids = {s["id"] for s in updated_seats if s["is_booked"]}
        for s_id in seat_ids_to_book:
            assert s_id in booked_seat_ids, f"Seat {s_id} should be marked booked!"
        print("[+] Seat Map updated OK: Booked seats are accurately marked as unavailable")

        print("\n=======================================================")
        print("ALL 10 END-TO-END FLOW CHECKS PASSED WITH FLYING COLORS!")
        print("=======================================================")


if __name__ == "__main__":
    asyncio.run(test_full_flow())
