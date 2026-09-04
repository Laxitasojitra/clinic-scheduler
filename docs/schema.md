# Schema

## Tables

**users** — `id` (str/UUID PK), `email` (unique, indexed), `password_hash`, `full_name`, `role`
(enum: `front_desk` | `provider`), `created_at`.

**slots** — represents both an unbooked availability slot and, once booked, the appointment itself.
`id` (PK), `provider_id` (FK → users, the scheduling provider), `date`, `start_time`,
`duration_minutes`, `status` (enum: `open`/`requested`/`confirmed`/`checked_in`/`completed`/
`no_show`/`cancelled`), `patient_name` (nullable), `patient_contact` (nullable),
`cancellation_reason` (nullable), `archived_at` (nullable timestamp), `created_by` (FK → users),
`created_at`, `updated_at`.

**supporting_providers** — many-to-many join between `slots` and `users` for the care-team feature.
`id` (PK), `slot_id` (FK), `provider_id` (FK), `added_at`, `removed_at` (nullable — soft-remove so
history of who was ever on the care team is preserved).

**visit_notes** — `id` (PK), `slot_id` (FK, the appointment it belongs to), `provider_id` (FK, the
author), `content` (text), `created_at`, `updated_at`.

**audit_events** — append-only timeline. `id` (PK), `slot_id` (FK), `event_type` (string:
`status_change`/`reassigned`/`support_added`/`support_removed`/`visit_note_added`), `old_value`,
`new_value`, `reason` (nullable, used for cancellation reasons), `actor_id` (FK → users),
`created_at`. No route updates or deletes rows in this table.

**alert_dismissals** — `id` (PK), `slot_id` (FK), `dismissed_by` (FK → users), `dismissed_at`. The
alerts endpoint checks for a dismissal newer than "1 hour before scheduled time" to decide whether
to re-surface an alert — the row is never deleted, just superseded by the 1-hour rule.

## One-to-many vs many-to-many

- One-to-many: `users` → `slots` (a provider has many scheduling slots), `users` → `visit_notes`
  (a provider authors many notes), `slots` → `visit_notes` (one appointment, many notes),
  `slots` → `audit_events`.
- Many-to-many: `slots` ↔ `users` via `supporting_providers` — an appointment can have many
  supporting providers, and a provider can support many appointments.

## Constraints: database vs application

Database-enforced: primary keys, foreign keys, `NOT NULL` on required columns, `UNIQUE` on
`users.email`, the `role`/`status` enum column types.

Application-enforced: the appointment status state machine (`ALLOWED_TRANSITIONS` in
`scheduling.py`) — which transitions are legal from which state — because a database CHECK
constraint can't easily express "no-show only after the scheduled time has passed" or "cancel only
before check-in, and only with a reason." Role-based access (front-desk vs provider, and provider
ownership of a slot) is also application-level, since it depends on the requesting user, not just
the row's own data.

## Deliberate denormalization

`patient_name`/`patient_contact` live directly on `slots` rather than a separate `patients` table.
There are no patient accounts or patient-side features in this system (front desk enters the name
freeform when booking), so a `patients` table would add a join with no corresponding feature to
justify it. If patient self-service booking were added (a stretch goal in the brief), this would be
the first thing to normalize out.

## What would break first at 100x the data

The `/slots` search endpoint does an `ILIKE` scan over `patient_name` with no index — fine at demo
scale, would need a proper index (or full-text search) at 100x. The dashboard's weekly no-show-rate
calculation runs 8 separate `COUNT` queries in a loop rather than one grouped query — would need to
be rewritten as a single query with a date-bucket `GROUP BY` at scale. SQLite itself (used for local
dev) would not be appropriate at any real scale — it's explicitly local-dev-only here, Postgres is
used for deployment.
