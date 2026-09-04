from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

<<<<<<< HEAD
# SQLite needs this connect_arg; Postgres doesn't, and ignores it if present via this guard.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
=======
engine = create_engine(settings.database_url)
>>>>>>> 8df9d12187793dd9f3eeda5aadd288ed11a34f98
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
