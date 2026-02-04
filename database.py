"""
Moduł konfiguracyjny bazy danych SQLite dla aplikacji CS2 Player Tracker.
Zawiera inicjalizację silnika SQLAlchemy oraz funkcję do uzyskiwania sesji bazodanowej.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

SQLALCHEMY_DATABASE_URL = "sqlite:///./cs2_tracker.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Generator dependency injection dla sesji bazodanowej.
    
    Yields:
        Session: Instancja sesji SQLAlchemy.
        
    Użycie:
        Automatycznie zamyka sesję po zakończeniu requestu.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
