# Architecture

## Moving pieces and how they talk to each other

- **Frontend**: a single HTML page (`app/static/index.html`) with vanilla JavaScript
  (`app/static/app.js`) that calls the backend's JSON API via `fetch`. No build step, no framework.
  State lives in a single in-memory JS object; the whole `#app` div is re-rendered on every state
  change.
- **Backend**: a FastAPI application (`app/main.py`) exposing a REST API under a handful of
  routers — `auth` (signup/login, issues JWTs), `users` (provider lookup), and `scheduling` (slots,
  appointments, visit notes, care team, search, bulk generation, CSV export, dashboard, alerts).
- **Database**: SQLAlchemy ORM models (`app/models.py`) against SQLite locally / Postgres in
  deployment, with Alembic managing schema migrations.
- The frontend and backend are served by the **same process** — FastAPI serves the static
  HTML/CSS/JS directly (`StaticFiles` mount + a catch-all route for `index.html`), so there's one
  deployable service, not two.

## Where each piece runs

Everything — API and static frontend — runs in a single FastAPI/Uvicorn process. In deployment
this is one service (e.g. Render or similar), pointed at a managed Postgres database (Supabase)
via the `DATABASE_URL` environment variable.

## Request path for one representative action: front-desk confirms an appointment

1. Frontend: user clicks "confirmed" on the status buttons in the appointment detail modal
   (`app.js`, the `.statusBtn` click handler).
2. `fetch` sends `POST /slots/{id}/status` with `{"new_status": "confirmed"}` and the JWT in the
   `Authorization` header.
3. FastAPI resolves the route in `app/routers/scheduling.py::change_status`. The `get_current_user`
   dependency decodes the JWT and loads the `User` row.
4. The route checks: is this transition (`requested` → `confirmed`) in `ALLOWED_TRANSITIONS`? Is
   the actor a front-desk user (confirm is a front-desk-only action)?
5. On success: `slot.status` is updated, a row is appended to `audit_events` recording the old and
   new status and who made the change, and the change is committed.
6. The frontend re-fetches the slot detail and the appointment list, then re-renders.

## What I decided not to build

- **A real patient-facing UI or patient accounts.** The brief only requires front-desk/provider
  roles; patients are represented as free-text name/contact on the slot, entered by front desk.
  Listed as a stretch idea in the brief, not attempted.
- **A componentized, client-routed frontend.** Chosen for time (see `docs/decisions.md`,
  Decision 5) — a single re-rendering page was faster to get working correctly than a proper SPA
  framework setup with a separate build and deploy step.
- **Refresh tokens.** JWTs are long-lived (8 hours) with no refresh flow. Acceptable for a demo/
  assessment app; not something I'd ship in a real product without a refresh mechanism.
- **Recurring appointments, reminders, waitlists, room/equipment assignment** — all explicitly
  listed as optional stretch goals in the brief, not attempted given the time available.
