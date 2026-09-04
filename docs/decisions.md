# Decisions

<<<<<<< HEAD
## Decision 1

- **Chose:** One `Slot` table that represents both an unbooked availability slot and, once a
  patient requests it, the appointment itself (nullable `patient_name`/`patient_contact`/`status`
  columns).
- **Rejected:** Separate `Slot` and `Appointment` tables with a foreign key between them.
- **Why:** The brief states a slot "becomes" an appointment on request — same identity, not a new
  entity. One table avoids a join on every read and avoids the question of what happens to the slot
  row when the appointment is cancelled. Trade-off: the table has several columns that are only
  meaningful once `status != open` (patient name, contact, cancellation reason).

## Decision 2

- **Chose:** Role enforcement as FastAPI dependencies (`require_front_desk`, `require_provider`,
  and per-endpoint ownership checks) rather than checking `user.role` inline in each route body.
- **Rejected:** Inline `if user.role != ...: raise HTTPException(...)` at the top of every function.
- **Why:** Dependencies are declared in the function signature, so the required role is visible
  without reading the function body, and it's impossible to add a new route and forget the check —
  FastAPI won't run the route at all until the dependency passes.

## Decision 3

- **Chose:** SQLite for local development, Postgres only for deployment.
- **Rejected:** Postgres (via Supabase) for both local dev and deployment from the start.
- **Why — Later reversed:** Originally set up entirely on Supabase Postgres, including locally. Hit
  a DNS resolution failure connecting to Supabase's direct-connection hostname (it's IPv6-only and
  doesn't resolve on many networks) that cost real time to diagnose. Under time pressure, switched
  local dev to SQLite — zero network dependency, works instantly — and kept Postgres only for the
  deployed version, since SQLAlchemy abstracts the dialect and it's a one-line `DATABASE_URL`
  change. This surfaced a second problem (see Decision 4) but was still the right call for the time
  available.

## Decision 4

- **Chose:** Database-agnostic column types (`String(36)` for IDs instead of Postgres's native
  `UUID` type; plain `bcrypt` instead of `passlib`).
- **Rejected:** Postgres-specific `UUID` columns and `passlib` for password hashing.
- **Why:** The SQLite switch (Decision 3) broke on Postgres-only types, and separately `passlib`
  1.7.4 is incompatible with all bcrypt 4.x releases (crashes on its own internal self-test,
  unrelated to any real password). Switching to portable types and calling `bcrypt` directly fixed
  both and reduced dependencies.

## Decision 5

- **Chose:** A single-page frontend in plain HTML/CSS and vanilla JavaScript (`app/static/`),
  served directly by FastAPI as static files — no separate frontend service, no build step.
- **Rejected:** A separate React app (Vite) deployed independently to Vercel, calling the FastAPI
  backend over CORS.
- **Why:** Made under significant time pressure in the final session. One deployable service is
  simpler to reason about, run locally, and deploy (no CORS configuration, no separate build/deploy
  pipeline to debug). The real trade-off: it's not componentized, there's no client-side routing,
  and the whole UI re-renders on every state change rather than diffing — acceptable for a scheduling
  demo at this scope, would not scale well as a real product's frontend.

## Decision 6

- **Chose:** Append-only `AuditEvent` table with no update or delete route ever exposed for it,
  rather than storing "last changed by/at" columns directly on `Slot`.
- **Rejected:** Mutable audit columns on the `Slot` row itself (e.g. `last_status_changed_by`).
- **Why:** Goal #9 requires a full history of every status change, care-team change, and
  cancellation that "cannot be edited or deleted after the fact, including by front-desk staff." A
  separate append-only table is the only way to guarantee that — there's no route in the codebase
  that updates or deletes rows in `audit_events`, so it can't happen by omission later even by
  accident.
=======
Log the decisions that actually shaped this codebase — the ones where a real alternative existed and
you picked one. At least five entries. For each: what you chose, what you rejected, and why. At least
one entry must be a decision you later reversed — say what changed your mind. It can be any entry
below, not necessarily the last one; add a **Later reversed:** line to whichever one it is.

## Decision 1

- **Chose:**
- **Rejected:**
- **Why:**

## Decision 2

- **Chose:**
- **Rejected:**
- **Why:**

## Decision 3

- **Chose:**
- **Rejected:**
- **Why:**

## Decision 4

- **Chose:**
- **Rejected:**
- **Why:**

## Decision 5

- **Chose:**
- **Rejected:**
- **Why:**
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
