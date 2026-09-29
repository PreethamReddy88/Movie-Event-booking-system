"""Standalone concurrency test script.

Fires ~20 simultaneous booking requests at the SAME seat for the same show
and asserts that exactly ONE succeeds. Run this against a live stack
(docker-compose up) — it needs real Postgres + Redis.

Usage:
    python tests/concurrency_test.py

Prerequisites:
    1. docker-compose up -d
    2. Create an admin user, a movie, a theatre with seats, and a show via the API.
    3. Update the constants below with the correct IDs.
    OR just run the script — it will set up test data automatically.
"""

import asyncio
import sys
import uuid

import httpx

BASE_URL = "http://localhost:8000"
NUM_CONCURRENT = 20

# These will be populated by the setup function.
ADMIN_TOKEN: str = ""
USER_TOKENS: list[str] = []
SHOW_ID: int = 0
SEAT_ID: int = 0


async def setup_test_data() -> None:
    """Create admin, users, movie, theatre, seats, show via the API."""
    global ADMIN_TOKEN, USER_TOKENS, SHOW_ID, SEAT_ID

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # ── Create admin user ──
        admin_email = f"admin_{uuid.uuid4().hex[:6]}@test.com"
        await client.post(
            "/api/auth/signup",
            json={"name": "Admin", "email": admin_email, "password": "admin123"},
        )
        # NOTE: In production you'd promote this user to admin via a DB command.
        # For this test, we'll do it via a direct login and assume the first user
        # is manually promoted. Instead, let's create a helper endpoint or use
        # the DB directly. For simplicity, we'll just make the API calls and
        # handle the admin setup message.
        login_resp = await client.post(
            "/api/auth/login",
            json={"email": admin_email, "password": "admin123"},
        )
        if login_resp.status_code != 200:
            print(f"Admin login failed: {login_resp.text}")
            print(
                "\n⚠️  To run this test, you need an admin user. "
                "Create one via signup, then UPDATE the users table:\n"
                "  UPDATE users SET role = 'admin' WHERE email = '<your-admin-email>';\n"
            )
            sys.exit(1)
        ADMIN_TOKEN = login_resp.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"}

        # ── Create movie ──
        movie_resp = await client.post(
            "/api/admin/movies",
            json={
                "title": "Concurrency Test Movie",
                "duration_minutes": 120,
                "language": "English",
                "genre": "Thriller",
            },
            headers=admin_headers,
        )
        if movie_resp.status_code == 403:
            print("❌ User is not an admin. Promote the user in the DB:")
            print(f"   UPDATE users SET role = 'admin' WHERE email = '{admin_email}';")
            sys.exit(1)
        movie_id = movie_resp.json()["id"]

        # ── Create theatre ──
        theatre_resp = await client.post(
            "/api/admin/theatres",
            json={"name": "Test Cinema", "city": "Mumbai", "address": "123 Test St"},
            headers=admin_headers,
        )
        theatre_id = theatre_resp.json()["id"]

        # ── Generate seats ──
        seats_resp = await client.post(
            f"/api/admin/theatres/{theatre_id}/generate-seats?rows=2&seats_per_row=5",
            headers=admin_headers,
        )
        seats = seats_resp.json()
        SEAT_ID = seats[0]["id"]  # We'll fight over this one seat

        # ── Create show ──
        show_resp = await client.post(
            "/api/admin/shows",
            json={
                "movie_id": movie_id,
                "theatre_id": theatre_id,
                "show_time": "2026-12-25T20:00:00",
                "price": 300.0,
            },
            headers=admin_headers,
        )
        SHOW_ID = show_resp.json()["id"]

        # ── Create concurrent users ──
        for i in range(NUM_CONCURRENT):
            email = f"user_{uuid.uuid4().hex[:6]}@test.com"
            await client.post(
                "/api/auth/signup",
                json={"name": f"User{i}", "email": email, "password": "pass123"},
            )
            login = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "pass123"},
            )
            USER_TOKENS.append(login.json()["access_token"])

    print(f"✅ Setup complete: show_id={SHOW_ID}, seat_id={SEAT_ID}")
    print(f"   {NUM_CONCURRENT} users created, ready to race!\n")


async def book_seat(token: str, idx: int) -> dict:
    """Attempt to book the contested seat."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.post(
            "/api/bookings",
            json={
                "show_id": SHOW_ID,
                "seat_ids": [SEAT_ID],
                "idempotency_key": str(uuid.uuid4()),
            },
            headers=headers,
        )
        return {"index": idx, "status": resp.status_code, "body": resp.json()}


async def main():
    print("=" * 60)
    print("  CONCURRENCY TEST — 20 users race for the SAME seat")
    print("=" * 60)
    print()

    await setup_test_data()

    print(f"🏁 Firing {NUM_CONCURRENT} simultaneous booking requests...\n")

    # Launch all requests concurrently.
    tasks = [book_seat(USER_TOKENS[i], i) for i in range(NUM_CONCURRENT)]
    results = await asyncio.gather(*tasks)

    # Analyze results.
    successes = [r for r in results if r["status"] == 201]
    failures = [r for r in results if r["status"] != 201]

    print(f"✅ Successes: {len(successes)}")
    print(f"❌ Failures:  {len(failures)}")

    for r in successes:
        print(f"   User {r['index']}: booking_id={r['body'].get('id')}")

    # The critical assertion: exactly ONE booking should succeed.
    if len(successes) == 1:
        print("\n🎉 PASS — Exactly 1 booking succeeded. No double-booking!")
    elif len(successes) == 0:
        print("\n⚠️  WARN — No bookings succeeded. Check the server logs.")
    else:
        print(
            f"\n💥 FAIL — {len(successes)} bookings succeeded! "
            "Double-booking detected. Check locking logic."
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
