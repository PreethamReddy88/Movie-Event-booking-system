# 🎬 Movie Ticket Booking System

A production-grade backend for booking movie tickets, built as a portfolio project for SDE placement interviews. Demonstrates **concurrency-safe seat booking** with a two-layer locking strategy (Redis distributed locks + PostgreSQL row-level locks), clean layered architecture, and complete CRUD workflows.

---

## ⚡ Tech Stack

| Layer | Technology |
|---|---|
| **Framework** | FastAPI (Python 3.10+) |
| **ORM** | SQLAlchemy 2.0 (asyncio) |
| **Migrations** | Alembic (auto-generates versioned DDL) |
| **Database** | PostgreSQL 16 (production/docker) & SQLite + aiosqlite (local dev/tests) |
| **Cache & Locking** | Redis 7 (async redis-py) & In-memory FakeRedis (zero-dependency local dev) |
| **Auth** | JWT (python-jose) + bcrypt password hashing (passlib) |
| **Validation** | Pydantic v2 + pydantic-settings |
| **Rate Limiting** | slowapi |
| **Testing** | pytest + httpx + pytest-asyncio (100% async test suite) |
| **Deployment** | Docker + Docker Compose |

---

## 📁 Project Architecture

```
├── alembic/                 # Alembic migration scripts and environment
│   └── versions/            # Version-controlled database migrations
├── app/
│   ├── core/                # Core infrastructure
│   │   ├── config.py        # Settings loaded via pydantic-settings (.env)
│   │   ├── database.py      # Async SQLAlchemy engine & session factory
│   │   ├── redis_client.py  # Async Redis client with in-memory fallback
│   │   └── security.py      # JWT token generation and password hashing
│   ├── models/              # SQLAlchemy ORM database models
│   │   ├── user.py          # Users & roles (USER, ADMIN)
│   │   ├── movie.py         # Movies catalog
│   │   ├── theatre.py       # Theatres & venues
│   │   ├── show.py          # Scheduled movie screenings
│   │   ├── seat.py          # Physical seats (REGULAR, PREMIUM)
│   │   ├── booking.py       # Bookings (PENDING, CONFIRMED, CANCELLED, FAILED)
│   │   ├── booking_seat.py  # Junction table for booked seats
│   │   └── payment.py       # Payments (PENDING, SUCCESS, FAILED)
│   ├── schemas/             # Pydantic validation schemas (request/response)
│   ├── services/            # Business logic
│   │   ├── auth_service.py
│   │   ├── movie_service.py
│   │   ├── theatre_service.py
│   │   ├── show_service.py
│   │   ├── booking_service.py   # ⭐ Core concurrency & locking engine
│   │   └── payment_service.py   # Payment settlement & lock release
│   ├── routers/             # FastAPI API route controllers
│   │   ├── auth.py          # /api/auth/signup, login, me
│   │   ├── admin.py         # /api/admin CRUD for movies, theatres, shows
│   │   ├── movies.py        # /api/movies search and details
│   │   ├── shows.py         # /api/shows and seat availability map
│   │   ├── bookings.py      # /api/bookings creation, viewing, cancellation
│   │   └── payments.py      # /api/payments payment processing
│   ├── dependencies.py      # Auth and authorization dependencies
│   └── main.py              # Application lifecycle, CORS, rate limiting, error handlers
├── scripts/
│   ├── seed.py              # Seeds movies, theatres, seats, shows, & test users
│   └── verify_api.py        # Full automated end-to-end API verification
├── tests/
│   ├── conftest.py          # Async test fixtures, test DB, test client
│   ├── test_auth.py         # Authentication & permission tests
│   ├── test_booking.py      # Transaction, idempotency & double-booking tests
│   └── concurrency_test.py  # High-concurrency race condition benchmark
├── .env                     # Local environment configuration
├── .env.example             # Template environment configuration
├── Dockerfile               # Container packaging
├── docker-compose.yml       # Multi-container orchestration (App + Postgres + Redis)
├── pyproject.toml           # Pytest configuration
├── requirements.txt         # Pinned Python dependencies
└── README.md
```

---

## 🚀 Quick Start

### Option A: Run Locally (Zero External Dependencies)

No Docker, Postgres, or Redis installation needed! The application includes built-in dual-driver support (`aiosqlite` for SQLite and `FakeRedis` for in-memory caching).

1. **Activate the virtual environment**:
   ```powershell
   # Windows:
   .\venv\Scripts\activate
   # Linux / macOS:
   source venv/bin/activate
   ```

2. **Run migrations**:
   ```bash
   alembic upgrade head
   ```

3. **Seed demo data**:
   ```bash
   python scripts/seed.py
   ```
   *Pre-seeded credentials:*
   - **Admin:** `admin@cinema.com` / `Admin@123`
   - **User:** `alex@example.com` / `User@123`

4. **Start the API server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

5. **Explore Swagger UI & Docs**:
   - Interactive Swagger API: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc documentation: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

### Option B: Run with Docker Compose (PostgreSQL + Redis + FastAPI)

1. **Launch containers**:
   ```bash
   docker-compose up --build -d
   ```
   This spins up:
   - PostgreSQL 16 on port `5432`
   - Redis 7 on port `6379`
   - FastAPI application on port `8000`

2. **Run migrations inside the container**:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

3. **Seed demo data**:
   ```bash
   docker-compose exec app python scripts/seed.py
   ```

---

## 🔒 Concurrency Control: How Double-Booking is Prevented

This is the central technical highlight of the architecture for SDE interviews. Seat booking employs a **two-layer defense-in-depth model**:

```
Client Booking Request (show_id, [seat_1, seat_2])
                 │
                 ▼
 ┌──────────────────────────────────────────────────┐
 │ Layer 1: Distributed Lock (Redis SET NX EX 300) │
 └───────────────────────┬──────────────────────────┘
                         │ 
        [Lock Acquired?] ├── No ──► Reject (409 Conflict: Seats Temporarily Held)
                         │
                        Yes
                         ▼
 ┌──────────────────────────────────────────────────┐
 │ Layer 2: ACID Row Lock (PostgreSQL FOR UPDATE)   │
 └───────────────────────┬──────────────────────────┘
                         │
      [Seats Still Free?]├── No ──► Rollback + Release Locks (409 Conflict)
                         │
                        Yes
                         ▼
 ┌──────────────────────────────────────────────────┐
 │ Insert Booking (Status: PENDING)                 │
 │ Insert BookingSeats Junction Records             │
 │ Commit DB Transaction                            │
 └───────────────────────┬──────────────────────────┘
                         ▼
            201 Created (Booking Reserved)
                         │
                 Payment Completed
                         ▼
 ┌──────────────────────────────────────────────────┐
 │ Status -> CONFIRMED; Redis Locks Released        │
 └──────────────────────────────────────────────────┘
```

### Layer 1: Redis Distributed Lock (Fast Path)
- Key format: `lock:seat:{show_id}:{seat_id}`
- Atomic operation: `SET lock:seat:{show_id}:{seat_id} {user_id} NX EX 300`
- **`NX`**: Only succeeds if the key does not already exist.
- **`EX 300`**: 5-minute TTL guarantees that if a user disconnects or crashes, the lock auto-expires.
- **Fail-Fast Rollback**: If a user attempts to book seats `[A1, A2]` and `A2` is locked by someone else, `A1` is automatically released immediately.
- **Benefit**: Absorbs thundering herd traffic in microseconds with $O(1)$ operations, protecting the relational database.

### Layer 2: Relational Row-Level Lock (`SELECT ... FOR UPDATE`)
- Queries existing bookings for the requested show and seats:
  ```sql
  SELECT booking_seats.seat_id FROM booking_seats 
  JOIN bookings ON booking_seats.booking_id = bookings.id 
  WHERE bookings.show_id = :show_id 
    AND booking_seats.seat_id IN (:seat_ids) 
    AND bookings.status IN ('PENDING', 'CONFIRMED')
  FOR UPDATE;
  ```
- Any concurrent transaction attempting to read or write the same seats blocks until the active transaction commits.
- **Benefit**: Redis keys can be volatile; PostgreSQL enforces strict ACID guarantees and serves as the single source of truth.

### Layer 3: Idempotency Protection
- Every booking request requires a client-generated `idempotency_key` (e.g. UUIDv4).
- If network timeouts cause a client to retry the identical payload, the backend detects the duplicate key and returns the original booking payload without re-locking or re-charging.

---

## 🧪 Testing & Verification

### 1. Run Automated Unit & Integration Tests
```bash
pytest -v
```
All 10 tests run completely asynchronously in under 4 seconds:
- Signup & duplicate email rejection
- Login authentication & invalid password handling
- JWT `/api/auth/me` token resolution
- Seat reservation flow
- Idempotency deduplication
- Double-booking prevention
- Role-based authorization (Admin route protection)

### 2. Run End-to-End API Verification
```bash
python scripts/verify_api.py
```
Executes a complete 10-step journey from authentication, movie search, seat selection, booking reservation, mock payment settlement, and seat map availability updates.

### 3. Run High-Concurrency Race Benchmark
```bash
python tests/concurrency_test.py
```
Fires 20 simultaneous concurrent requests racing for the same seat to prove that exactly 1 booking succeeds and 19 are safely rejected.

---

## 📡 API Reference

### 🔐 Authentication (`/api/auth`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/auth/signup` | Register user account | No |
| `POST` | `/api/auth/login` | Login and receive JWT access token | No (Rate-limited: 10/min) |
| `GET` | `/api/auth/me` | Fetch authenticated user profile | Bearer Token |

### 🎬 Public Movie & Show Catalog
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/movies` | List movies (supports `genre`, `language`, `page`, `size`) | No |
| `GET` | `/api/movies/{id}` | Get movie details | No |
| `GET` | `/api/shows/movie/{movie_id}` | List scheduled shows for movie | No |
| `GET` | `/api/shows/{show_id}/seats` | Real-time seat availability map | No |

### 🎟️ Bookings (`/api/bookings`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/bookings` | Reserve seats with idempotency key | Bearer Token (Rate-limited: 5/min) |
| `GET` | `/api/bookings` | List user's booking history | Bearer Token |
| `GET` | `/api/bookings/{id}` | Fetch single booking by ID | Bearer Token |
| `POST` | `/api/bookings/{id}/cancel` | Cancel booking & release seats | Bearer Token |

### 💳 Payments (`/api/payments`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/payments` | Settle payment for pending booking | Bearer Token |

### 🛡️ Admin Operations (`/api/admin`)
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/admin/movies` | Create movie | Admin Role |
| `PUT` | `/api/admin/movies/{id}` | Update movie | Admin Role |
| `DELETE` | `/api/admin/movies/{id}` | Delete movie | Admin Role |
| `POST` | `/api/admin/theatres` | Create theatre | Admin Role |
| `POST` | `/api/admin/theatres/{id}/generate-seats` | Auto-generate seat grid | Admin Role |
| `POST` | `/api/admin/shows` | Schedule a show | Admin Role |
