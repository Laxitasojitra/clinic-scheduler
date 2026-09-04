# Plan

<<<<<<< HEAD
## How I broke the work into sessions, and what order

1. **Session 1** — project scaffold, database schema (all tables up front, since the rest of the
   app depends on it), JWT auth with server-side role dependencies.
2. **Session 2** — debugging: an Alembic migration bug, then a Supabase connectivity/DNS problem
   that led to switching local dev to SQLite, which in turn surfaced portability bugs (Postgres-only
   UUID columns, a passlib/bcrypt incompatibility) that had to be fixed before the schema would even
   run.
3. **Session 3** — with roughly 2-3 hours left before the deadline, built the remaining 9 of 10
   goals (slot CRUD, the appointment status state machine, visit notes, care team, search/
   pagination, bulk generation, CSV export, dashboard, alerts) plus a minimal frontend, all in one
   push rather than incrementally, and verified it end-to-end (signup/login, listing, an illegal
   status transition correctly rejected, a legal one correctly logged to the audit trail) before
   accepting it.

I built auth and the schema first because every other feature depends on knowing who the user is
and what the data model looks like — get those wrong and everything downstream has to be redone.

## Estimated vs actual

I estimated the Postgres/Supabase setup at effectively zero time (managed service, should just
work). It cost most of two sessions instead, between the DNS/IPv6 issue and the SQLite-portability
bugs it surfaced. That was the single biggest estimation miss in this project.

## What I cut

I did not build any of the stretch ideas (reminders, recurring appointments, patient self-service,
waitlist, per-visit-type durations, room assignment, printable day sheet, billing notes, email
digest) — none were required, and time went to the 10 required goals instead. Within the required
goals, I cut a componentized/build-tooled frontend in favor of a single static page (see
`docs/decisions.md`, Decision 5) purely because of the time remaining in the final session.

**[Fill in honestly once you've actually run and tested everything]:** how much of the 12-hour
budget you actually used, and — separately — how much of that final rushed session's code you've
personally read and could defend line-by-line versus accepted after black-box testing. Say so
plainly; that's exactly what this document is for.
=======
Answer each of these, in your own words.

- How did you break the work into sessions?
- What order did you build in, and why that order?
- What did you estimate versus what it actually took?
- What did you cut when you ran short?
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
