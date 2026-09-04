import csv
import io
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_, and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_front_desk
from app.models import (
    User, UserRole, Slot, SlotStatus, SupportingProvider, VisitNote,
    AuditEvent, AlertDismissal,
)

router = APIRouter(tags=["scheduling"])

# ---------- status machine ----------
ALLOWED_TRANSITIONS = {
    SlotStatus.requested: {SlotStatus.confirmed, SlotStatus.cancelled},
    SlotStatus.confirmed: {SlotStatus.checked_in, SlotStatus.no_show, SlotStatus.cancelled},
    SlotStatus.checked_in: {SlotStatus.completed},
    SlotStatus.completed: set(),
    SlotStatus.no_show: set(),
    SlotStatus.cancelled: set(),
}


def log_event(db: Session, slot_id: str, event_type: str, actor_id: str,
              old_value: str = None, new_value: str = None, reason: str = None):
    db.add(AuditEvent(slot_id=slot_id, event_type=event_type, actor_id=actor_id,
                       old_value=old_value, new_value=new_value, reason=reason))


def user_can_access_slot(user: User, slot: Slot, db: Session) -> bool:
    """Front-desk sees everything. Providers see slots where they are scheduling
    or supporting provider."""
    if user.role == UserRole.front_desk:
        return True
    if slot.provider_id == user.id:
        return True
    support = db.query(SupportingProvider).filter(
        SupportingProvider.slot_id == slot.id,
        SupportingProvider.provider_id == user.id,
        SupportingProvider.removed_at.is_(None),
    ).first()
    return support is not None


def get_slot_or_404(db: Session, slot_id: str) -> Slot:
    slot = db.query(Slot).filter(Slot.id == slot_id).first()
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Slot not found")
    return slot


# ---------- create / edit slots (goal 2) ----------
@router.post("/slots", status_code=status.HTTP_201_CREATED)
def create_slot(payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    provider_id = payload["provider_id"]
    if user.role == UserRole.provider and provider_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Providers can only create slots for themselves")

    slot = Slot(
        provider_id=provider_id,
        date=date.fromisoformat(payload["date"]),
        start_time=datetime.strptime(payload["start_time"], "%H:%M").time(),
        duration_minutes=payload["duration_minutes"],
        status=SlotStatus.open,
        created_by=user.id,
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


@router.patch("/slots/{slot_id}")
def edit_slot(slot_id: str, payload: dict, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    slot = get_slot_or_404(db, slot_id)
    if slot.status != SlotStatus.open:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only unbooked (open) slots can be edited")
    if user.role == UserRole.provider and slot.provider_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your slot")

    if "date" in payload:
        slot.date = date.fromisoformat(payload["date"])
    if "start_time" in payload:
        slot.start_time = datetime.strptime(payload["start_time"], "%H:%M").time()
    if "duration_minutes" in payload:
        slot.duration_minutes = payload["duration_minutes"]
    if "provider_id" in payload and user.role == UserRole.front_desk:
        slot.provider_id = payload["provider_id"]

    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


@router.post("/slots/{slot_id}/archive")
def archive_slot(slot_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    slot = get_slot_or_404(db, slot_id)
    if user.role == UserRole.provider and slot.provider_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your slot")
    slot.archived_at = datetime.utcnow()
    db.commit()
    return {"ok": True}


@router.post("/slots/{slot_id}/restore")
def restore_slot(slot_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    slot = get_slot_or_404(db, slot_id)
    if user.role == UserRole.provider and slot.provider_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your slot")
    slot.archived_at = None
    db.commit()
    return {"ok": True}


# ---------- booking / status machine (goal 4) ----------
@router.post("/slots/{slot_id}/request")
def request_appointment(slot_id: str, payload: dict, db: Session = Depends(get_db),
                         user: User = Depends(require_front_desk)):
    slot = get_slot_or_404(db, slot_id)
    if slot.status != SlotStatus.open:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Slot is not open for booking")
    slot.patient_name = payload["patient_name"]
    slot.patient_contact = payload.get("patient_contact")
    old = slot.status
    slot.status = SlotStatus.requested
    log_event(db, slot.id, "status_change", user.id, old.value, slot.status.value)
    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


@router.post("/slots/{slot_id}/status")
def change_status(slot_id: str, payload: dict, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    slot = get_slot_or_404(db, slot_id)
    new_status = SlotStatus(payload["new_status"])

    is_front_desk = user.role == UserRole.front_desk
    is_own_provider = user.role == UserRole.provider and user_can_access_slot(user, slot, db)

    # confirm / cancel / reassign are front-desk actions
    if new_status in (SlotStatus.confirmed, SlotStatus.cancelled) and not is_front_desk:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only front-desk staff can confirm or cancel")
    if new_status in (SlotStatus.checked_in, SlotStatus.completed, SlotStatus.no_show):
        if not (is_front_desk or is_own_provider):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized for this appointment")

    if new_status not in ALLOWED_TRANSITIONS.get(slot.status, set()):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot move from {slot.status.value} to {new_status.value}",
        )

    if new_status == SlotStatus.cancelled:
        if slot.status not in (SlotStatus.requested, SlotStatus.confirmed):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot cancel after check-in")
        reason = payload.get("reason")
        if not reason:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cancellation requires a reason")
        slot.cancellation_reason = reason

    if new_status == SlotStatus.no_show:
        scheduled_dt = datetime.combine(slot.date, slot.start_time)
        if datetime.utcnow() < scheduled_dt:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot mark no-show before the scheduled time has passed")

    old = slot.status
    slot.status = new_status
    log_event(db, slot.id, "status_change", user.id, old.value, new_status.value,
              reason=payload.get("reason"))
    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


@router.post("/slots/{slot_id}/reassign")
def reassign(slot_id: str, payload: dict, db: Session = Depends(get_db),
             user: User = Depends(require_front_desk)):
    slot = get_slot_or_404(db, slot_id)
    if slot.status not in (SlotStatus.requested, SlotStatus.confirmed):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Can only reassign before check-in")
    old_provider = slot.provider_id
    slot.provider_id = payload["new_provider_id"]
    log_event(db, slot.id, "reassigned", user.id, old_provider, slot.provider_id)
    db.commit()
    db.refresh(slot)
    return slot_to_dict(slot)


# ---------- search / list (goal 6) ----------
@router.get("/slots")
def list_slots(
    q: str = None, provider_id: str = None, status_filter: str = Query(None, alias="status"),
    date_from: str = None, date_to: str = None,
    sort_by: str = "date", sort_dir: str = "asc",
    page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    query = db.query(Slot)

    if user.role == UserRole.provider:
        supporting_ids = [s.slot_id for s in db.query(SupportingProvider).filter(
            SupportingProvider.provider_id == user.id, SupportingProvider.removed_at.is_(None)
        ).all()]
        query = query.filter(or_(Slot.provider_id == user.id, Slot.id.in_(supporting_ids or [""])))

    if q:
        query = query.filter(Slot.patient_name.ilike(f"%{q}%"))
    if provider_id:
        query = query.filter(Slot.provider_id == provider_id)
    if status_filter:
        query = query.filter(Slot.status == SlotStatus(status_filter))
    if date_from:
        query = query.filter(Slot.date >= date.fromisoformat(date_from))
    if date_to:
        query = query.filter(Slot.date <= date.fromisoformat(date_to))

    total = query.count()

    sort_col = {"date": Slot.date, "status": Slot.status, "provider": Slot.provider_id}.get(sort_by, Slot.date)
    sort_col = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    query = query.order_by(sort_col, Slot.start_time)

    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [slot_to_dict(s) for s in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/slots/{slot_id}")
def get_slot(slot_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    slot = get_slot_or_404(db, slot_id)
    if not user_can_access_slot(user, slot, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not authorized")

    notes = db.query(VisitNote).filter(VisitNote.slot_id == slot_id).order_by(VisitNote.created_at).all()
    support = db.query(SupportingProvider).filter(
        SupportingProvider.slot_id == slot_id, SupportingProvider.removed_at.is_(None)
    ).all()
    timeline = db.query(AuditEvent).filter(AuditEvent.slot_id == slot_id).order_by(AuditEvent.created_at).all()

    result = slot_to_dict(slot)
    result["visit_notes"] = [
        {"id": n.id, "provider_id": n.provider_id, "provider_name": n.provider.full_name,
         "content": n.content, "created_at": n.created_at.isoformat(), "updated_at": n.updated_at.isoformat()}
        for n in notes
    ]
    result["supporting_providers"] = [
        {"provider_id": s.provider_id, "provider_name": s.provider.full_name} for s in support
    ]
    result["timeline"] = [
        {"event_type": e.event_type, "old_value": e.old_value, "new_value": e.new_value,
         "reason": e.reason, "actor_name": e.actor.full_name, "created_at": e.created_at.isoformat()}
        for e in timeline
    ]
    return result


def slot_to_dict(slot: Slot) -> dict:
    return {
        "id": slot.id,
        "provider_id": slot.provider_id,
        "provider_name": slot.provider.full_name if slot.provider else None,
        "date": slot.date.isoformat(),
        "start_time": slot.start_time.strftime("%H:%M"),
        "duration_minutes": slot.duration_minutes,
        "status": slot.status.value,
        "patient_name": slot.patient_name,
        "patient_contact": slot.patient_contact,
        "cancellation_reason": slot.cancellation_reason,
        "archived": slot.archived_at is not None,
    }


# ---------- visit notes (goal 3) ----------
@router.post("/slots/{slot_id}/visit-notes", status_code=status.HTTP_201_CREATED)
def add_visit_note(slot_id: str, payload: dict, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    slot = get_slot_or_404(db, slot_id)
    if user.role != UserRole.provider or not user_can_access_slot(user, slot, db):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only providers on this appointment can add notes")
    note = VisitNote(slot_id=slot_id, provider_id=user.id, content=payload["content"])
    db.add(note)
    log_event(db, slot_id, "visit_note_added", user.id)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "content": note.content, "created_at": note.created_at.isoformat()}


@router.patch("/visit-notes/{note_id}")
def edit_visit_note(note_id: str, payload: dict, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    note = db.query(VisitNote).filter(VisitNote.id == note_id).first()
    if not note:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found")
    if note.provider_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can edit this note")
    note.content = payload["content"]
    db.commit()
    return {"id": note.id, "content": note.content, "updated_at": note.updated_at.isoformat()}


# ---------- care team (goal 5) ----------
@router.post("/slots/{slot_id}/care-team", status_code=status.HTTP_201_CREATED)
def add_supporting_provider(slot_id: str, payload: dict, db: Session = Depends(get_db),
                             user: User = Depends(require_front_desk)):
    slot = get_slot_or_404(db, slot_id)
    sp = SupportingProvider(slot_id=slot_id, provider_id=payload["provider_id"])
    db.add(sp)
    log_event(db, slot_id, "support_added", user.id, new_value=payload["provider_id"])
    db.commit()
    return {"ok": True}


@router.delete("/slots/{slot_id}/care-team/{provider_id}")
def remove_supporting_provider(slot_id: str, provider_id: str, db: Session = Depends(get_db),
                                user: User = Depends(require_front_desk)):
    sp = db.query(SupportingProvider).filter(
        SupportingProvider.slot_id == slot_id, SupportingProvider.provider_id == provider_id,
        SupportingProvider.removed_at.is_(None),
    ).first()
    if not sp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")
    sp.removed_at = datetime.utcnow()
    log_event(db, slot_id, "support_removed", user.id, old_value=provider_id)
    db.commit()
    return {"ok": True}


# ---------- bulk generation + CSV export (goal 7) ----------
@router.post("/slots/bulk-generate")
def bulk_generate(payload: dict, db: Session = Depends(get_db), user: User = Depends(require_front_desk)):
    provider_id = payload["provider_id"]
    d_from = date.fromisoformat(payload["date_from"])
    d_to = date.fromisoformat(payload["date_to"])
    days_of_week = set(payload["days_of_week"])  # 0=Mon ... 6=Sun
    start_time = datetime.strptime(payload["start_time"], "%H:%M").time()
    duration_minutes = payload["duration_minutes"]

    created, skipped = [], []
    current = d_from
    while current <= d_to:
        if current.weekday() in days_of_week:
            clash = db.query(Slot).filter(
                Slot.provider_id == provider_id, Slot.date == current,
                Slot.start_time == start_time, Slot.archived_at.is_(None),
            ).first()
            if clash:
                skipped.append(current.isoformat())
            else:
                slot = Slot(provider_id=provider_id, date=current, start_time=start_time,
                            duration_minutes=duration_minutes, status=SlotStatus.open, created_by=user.id)
                db.add(slot)
                created.append(current.isoformat())
        current += timedelta(days=1)
    db.commit()
    return {"created": created, "skipped": skipped}


@router.get("/slots/export-csv")
def export_csv(day: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    d = date.fromisoformat(day)
    query = db.query(Slot).filter(Slot.date == d).order_by(Slot.start_time)
    if user.role == UserRole.provider:
        query = query.filter(Slot.provider_id == user.id)
    slots = query.all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Time", "Provider", "Duration (min)", "Status", "Patient"])
    for s in slots:
        writer.writerow([s.start_time.strftime("%H:%M"), s.provider.full_name, s.duration_minutes,
                          s.status.value, s.patient_name or ""])
    buf.seek(0)
    return StreamingResponse(buf, media_type="text/csv",
                              headers={"Content-Disposition": f"attachment; filename=schedule-{day}.csv"})


# ---------- dashboard (goal 8) ----------
@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    appts_today = db.query(Slot).filter(Slot.date == today, Slot.status != SlotStatus.open).count()
    checked_in_now = db.query(Slot).filter(Slot.status == SlotStatus.checked_in).count()
    no_shows_this_week = db.query(Slot).filter(
        Slot.status == SlotStatus.no_show, Slot.date >= week_start
    ).count()
    confirmed_upcoming = db.query(Slot).filter(
        Slot.status == SlotStatus.confirmed, Slot.date >= today
    ).count()

    by_provider = dict(
        db.query(User.full_name, func.count(Slot.id))
        .join(Slot, Slot.provider_id == User.id)
        .filter(Slot.status != SlotStatus.open)
        .group_by(User.full_name).all()
    )
    by_status = dict(
        db.query(Slot.status, func.count(Slot.id)).filter(Slot.status != SlotStatus.open)
        .group_by(Slot.status).all()
    )
    by_status = {k.value: v for k, v in by_status.items()}

    no_show_weekly = []
    for i in range(7, -1, -1):
        wk_start = week_start - timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=6)
        total = db.query(Slot).filter(
            Slot.date >= wk_start, Slot.date <= wk_end, Slot.status != SlotStatus.open
        ).count()
        no_shows = db.query(Slot).filter(
            Slot.date >= wk_start, Slot.date <= wk_end, Slot.status == SlotStatus.no_show
        ).count()
        rate = round(100 * no_shows / total, 1) if total else 0
        no_show_weekly.append({"week_start": wk_start.isoformat(), "no_show_rate": rate})

    return {
        "appointments_today": appts_today,
        "checked_in_now": checked_in_now,
        "no_shows_this_week": no_shows_this_week,
        "confirmed_upcoming": confirmed_upcoming,
        "by_provider": by_provider,
        "by_status": by_status,
        "no_show_rate_weekly": no_show_weekly,
    }


# ---------- alerts (goal 10) ----------
@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), user: User = Depends(require_front_desk)):
    now = datetime.utcnow()
    horizon = now + timedelta(hours=24)
    reappear_cutoff = now + timedelta(hours=1)

    candidates = db.query(Slot).filter(Slot.status == SlotStatus.requested).all()
    alerts = []
    for s in candidates:
        scheduled_dt = datetime.combine(s.date, s.start_time)
        if scheduled_dt > horizon:
            continue
        dismissal = db.query(AlertDismissal).filter(AlertDismissal.slot_id == s.id).order_by(
            AlertDismissal.dismissed_at.desc()
        ).first()
        # reappears regardless of dismissal once within 1 hour of scheduled time
        if dismissal and scheduled_dt > reappear_cutoff:
            continue
        alerts.append(slot_to_dict(s))

    return {"count": len(alerts), "alerts": alerts}


@router.post("/alerts/{slot_id}/dismiss")
def dismiss_alert(slot_id: str, db: Session = Depends(get_db), user: User = Depends(require_front_desk)):
    db.add(AlertDismissal(slot_id=slot_id, dismissed_by=user.id))
    db.commit()
    return {"ok": True}
