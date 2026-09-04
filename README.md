<<<<<<< HEAD
=======
<<<<<<< HEAD
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
# Clinic Appointment Scheduling

Multi-provider clinic scheduling app. Front-desk staff manage availability and bookings;
providers manage their own schedule and visit notes.

## Stack

- Backend: FastAPI + SQLAlchemy + PostgreSQL, Alembic for migrations
- Frontend: React (Vite)

## Running locally

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
<<<<<<< HEAD
cp .env.example .env          # defaults to local SQLite — no setup needed
=======
cp .env.example .env          # then edit .env with your local Postgres URL and a JWT secret
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
alembic revision --autogenerate -m "init schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs

<<<<<<< HEAD
Local dev uses SQLite (`clinic.db`, gitignored) so there's zero network/database setup —
just works. For deployment, set `DATABASE_URL` in the environment to a Postgres connection
string (e.g. Supabase's **pooler** URL, not the direct connection — the direct one is
IPv6-only and fails to resolve on many networks/hosts) and re-run the two alembic commands
against it.

=======
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
### Frontend

```bash
cd frontend
npm install
npm run dev
```

See `docs/` for architecture, schema, decisions, plan, and AI usage notes.
<<<<<<< HEAD
=======
=======
# clinic-scheduler
>>>>>>> 2f9b2e15c3814482f05430b4f03f67eb9f8eeae3
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
