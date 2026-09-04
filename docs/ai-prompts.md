# AI prompts

<<<<<<< HEAD
I used Claude heavily for this assignment, especially in the final session under significant time
pressure (submitted with ~2-3 hours left). Below is an honest account grouped by what I was trying
to do. I did not write most of this code myself — I directed, reviewed, and tested it, and I'm
recording that plainly rather than pretending otherwise, per the brief's instructions.

## Initial scaffold — schema, auth, JWT roles

### Prompt
Asked for a FastAPI + React + Postgres stack, working through the 10 goals step by step, with
explanations at each stage.

### What I got
SQLAlchemy models (`Slot` doubling as the appointment record once booked, per goal #2), JWT auth
with bcrypt password hashing, and `require_front_desk`/`require_provider` FastAPI dependencies for
server-side role enforcement.

### What I corrected
Nothing at this stage — reviewed the schema and auth logic and understood the reasoning
(one `Slot` table instead of two, so a booking doesn't require a join or a data migration between
tables).

## Alembic migration bug

### Prompt
Pasted a `NameError: name 'config' is not defined` traceback from `alembic revision --autogenerate`.

### What I got
The fix: the custom code in `alembic/env.py` (pointing Alembic at our SQLAlchemy models) had been
inserted *before* Alembic's own `config = context.config` line, so `config` didn't exist yet when
referenced.

### What I corrected
Moved the block to after Alembic's default `config`/`fileConfig` setup — a real bug in generated
code, caught only by actually running the command and reading the traceback.

## Database connection failures (DNS / IPv6)

### Prompt
Pasted a `could not translate host name ... No such host is known` error connecting to Supabase.

### What I got
Diagnosis: Supabase's direct-connection hostname is IPv6-only and doesn't resolve on many
networks. Told to use the connection pooler URL instead.

### What I corrected
Given continued time pressure, decided (with Claude's recommendation) to switch local development
to SQLite entirely instead of continuing to chase the Supabase network issue — Postgres only for
deployment. This was the right call for the time I had left.

## Database-portability bugs introduced by the SQLite switch

### What happened
Claude ran the actual `alembic revision --autogenerate` command against SQLite rather than just
describing the fix, and it failed for real reasons that weren't visible from description alone:
- Model `id` columns used Postgres-specific `UUID` types that don't compile against SQLite.
- `passlib`, used for password hashing, crashes on its own internal self-test when combined with
  any bcrypt 4.x version (unrelated to the actual password used).
- `EmailStr` in Pydantic needs the separate `email-validator` package, missing from
  `requirements.txt`.

### What I corrected
Had Claude fix all three: switched UUID columns to `String(36)`, dropped `passlib` in favor of
calling `bcrypt` directly, and added `email-validator` to `requirements.txt`. I did not personally
diagnose these — they were caught by actually running the code, not by reading it. Recording that
honestly rather than claiming otherwise.

## Final build under time pressure (~2-3 hours left)

### Prompt
Told Claude I had run out of time and asked for a working submission — full backend for all 10
goals plus a minimal frontend, generated directly rather than built incrementally by me.

### What I got
A single scheduling router (`app/routers/scheduling.py`) covering slot CRUD, the appointment status
state machine, visit notes, care team, search/pagination, bulk generation, CSV export, the
dashboard, and alerts — plus a plain HTML/vanilla-JS frontend (`app/static/`) served directly by
FastAPI (no separate React build/deploy step, chosen purely for time).

### What I corrected / verified
I did not write this code myself. I ran it end-to-end before accepting it (signup, login, listing
appointments, dashboard numbers, an illegal status transition correctly rejected with a 400, a
legal transition correctly logged to the audit timeline). I can explain the status-machine logic in
`scheduling.py` (the `ALLOWED_TRANSITIONS` map and the extra rules around cancellation-requires-
reason and no-show-only-after-scheduled-time), but I have not reviewed the frontend JavaScript in
the same depth. That's a genuine gap in this submission and I'm recording it here rather than
hiding it, per the brief's instructions.
=======
The prompts you actually used, in the order you used them, grouped by what you were trying to achieve. For each significant one: what you asked, what you got back, and what you had to correct.

Include at least one prompt that produced something wrong, and what you did about it.

If you did not use AI at all, say so here, and describe your process instead.

## <What you were trying to achieve>

### Prompt

### What you got

### What you corrected
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
