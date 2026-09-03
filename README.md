<<<<<<< HEAD
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
cp .env.example .env          # then edit .env with your local Postgres URL and a JWT secret
alembic revision --autogenerate -m "init schema"
alembic upgrade head
uvicorn app.main:app --reload
```

API docs at http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

See `docs/` for architecture, schema, decisions, plan, and AI usage notes.
=======
# clinic-scheduler
>>>>>>> 2f9b2e15c3814482f05430b4f03f67eb9f8eeae3
