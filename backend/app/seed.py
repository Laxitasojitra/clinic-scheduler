"""Run with: python -m app.seed"""
from datetime import date, timedelta, time

from app.database import SessionLocal, engine, Base
from app.models import User, UserRole, Slot, SlotStatus
from app.security import hash_password

Base.metadata.create_all(bind=engine)  # safety net if migrations weren't run
db = SessionLocal()

if not db.query(User).filter(User.email == "frontdesk@clinic.com").first():
    front_desk = User(email="frontdesk@clinic.com", password_hash=hash_password("password123"),
                       full_name="Riya Desai", role=UserRole.front_desk)
    dr_shah = User(email="dr.shah@clinic.com", password_hash=hash_password("password123"),
                    full_name="Dr. Shah", role=UserRole.provider)
    dr_mehta = User(email="dr.mehta@clinic.com", password_hash=hash_password("password123"),
                     full_name="Dr. Mehta", role=UserRole.provider)
    db.add_all([front_desk, dr_shah, dr_mehta])
    db.commit()
    db.refresh(front_desk); db.refresh(dr_shah); db.refresh(dr_mehta)

    today = date.today()
    demo_slots = [
        Slot(provider_id=dr_shah.id, date=today, start_time=time(9, 0), duration_minutes=30,
             status=SlotStatus.confirmed, patient_name="Amit Kumar", patient_contact="9876543210",
             created_by=front_desk.id),
        Slot(provider_id=dr_shah.id, date=today, start_time=time(10, 0), duration_minutes=30,
             status=SlotStatus.requested, patient_name="Priya Nair", patient_contact="9876543211",
             created_by=front_desk.id),
        Slot(provider_id=dr_mehta.id, date=today, start_time=time(11, 0), duration_minutes=45,
             status=SlotStatus.checked_in, patient_name="Rohit Sharma", patient_contact="9876543212",
             created_by=front_desk.id),
        Slot(provider_id=dr_mehta.id, date=today - timedelta(days=1), start_time=time(14, 0), duration_minutes=30,
             status=SlotStatus.no_show, patient_name="Sneha Rao", patient_contact="9876543213",
             created_by=front_desk.id),
        Slot(provider_id=dr_shah.id, date=today + timedelta(days=1), start_time=time(9, 30), duration_minutes=30,
             status=SlotStatus.open, created_by=front_desk.id),
        Slot(provider_id=dr_mehta.id, date=today + timedelta(days=1), start_time=time(10, 30), duration_minutes=30,
             status=SlotStatus.open, created_by=front_desk.id),
    ]
    db.add_all(demo_slots)
    db.commit()
    print("Seed data created.")
    print("Front desk login: frontdesk@clinic.com / password123")
    print("Provider login:   dr.shah@clinic.com / password123")
else:
    print("Seed data already present, skipping.")

db.close()
