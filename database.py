"""
Database configuration module for the CS2 Player Tracker application.
Contains SQLAlchemy engine initialization and a dependency generator for obtaining a database session.
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# Load environment variables from a .env file if it exists
load_dotenv()

# Use the database URL from the environment, fallback to local SQLite database
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./cs2_tracker.db")

# check_same_thread is set to False specifically for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection generator for the database session.

    Yields:
        Session: An instance of the SQLAlchemy session.

    Notes:
        Automatically closes the session after the request is completed, 
        ensuring safe database connections.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()