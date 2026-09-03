import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Date, Time, Integer, ForeignKey, DateTime,
    Enum, Text, Boolean, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    front_desk = "front_desk"
    provider = "provider"


class SlotStatus(str, enum.Enum):
    open = "open"                # unbooked, editable
    requested = "requested"      # patient requested -> now an appointment
    confirmed = "confirmed"
    checked_in = "checked_in"
    completed = "completed"
    no_show = "no_show"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Slot(Base):
    """
    A slot IS the appointment record once a patient requests it — same row,
    per goal #2. Before that, patient_name is null and status = 'open'.
    """
    __tablename__ = "slots"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False)
    start_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, nullable=False)

    status = Column(Enum(SlotStatus), nullable=False, default=SlotStatus.open)

    patient_name = Column(String, nullable=True)
    patient_contact = Column(String, nullable=True)
    cancellation_reason = Column(Text, nullable=True)

    archived_at = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    provider = relationship("User", foreign_keys=[provider_id])
    supporting_providers = relationship("SupportingProvider", back_populates="slot")
    visit_notes = relationship("VisitNote", back_populates="slot")
    audit_events = relationship("AuditEvent", back_populates="slot")


class SupportingProvider(Base):
    """Many-to-many: an appointment can have many supporting providers,
    a provider can support many appointments."""
    __tablename__ = "supporting_providers"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slot_id = Column(UUID(as_uuid=False), ForeignKey("slots.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    removed_at = Column(DateTime, nullable=True)  # soft-remove, keeps history

    __table_args__ = (UniqueConstraint("slot_id", "provider_id", "removed_at", name="uq_active_support"),)

    slot = relationship("Slot", back_populates="supporting_providers")
    provider = relationship("User")


class VisitNote(Base):
    __tablename__ = "visit_notes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slot_id = Column(UUID(as_uuid=False), ForeignKey("slots.id"), nullable=False)
    provider_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    slot = relationship("Slot", back_populates="visit_notes")
    provider = relationship("User")


class AuditEvent(Base):
    """Append-only timeline: status changes, care-team changes, cancellations.
    No update/delete route will ever be exposed for this table."""
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slot_id = Column(UUID(as_uuid=False), ForeignKey("slots.id"), nullable=False)
    event_type = Column(String, nullable=False)  # 'status_change' | 'support_added' | 'support_removed' | 'cancelled'
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    reason = Column(Text, nullable=True)
    actor_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    slot = relationship("Slot", back_populates="audit_events")
    actor = relationship("User")


class AlertDismissal(Base):
    __tablename__ = "alert_dismissals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    slot_id = Column(UUID(as_uuid=False), ForeignKey("slots.id"), nullable=False)
    dismissed_by = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)
    dismissed_at = Column(DateTime, default=datetime.utcnow)
