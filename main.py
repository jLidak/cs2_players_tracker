"""
Main FastAPI application entry point for the CS2 Player Tracker.
Configures routing, static files, and database table initialization.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import models
from database import engine
from routers import (
    data_ops,
    matches,
    players,
    ranking,
    teams,
    tournaments,
    views,
    websocket,
)

import os
import json
from datetime import date as date_type
from database import SessionLocal

# Initialize database tables automatically based on SQLAlchemy models
models.Base.metadata.create_all(bind=engine)

# Initialize the FastAPI application
app = FastAPI(
    title="CS2 Player Tracker",
    version="1.0.0",
    description="Advanced ranking and tournament management API for Counter-Strike 2.",
)


@app.on_event("startup")
def load_initial_data_on_startup():
    """
    Sprawdza, czy baza jest pusta. Jeśli tak, automatycznie ładuje
    dane z pełnego backupu json_import_files/initial_data.json.
    """
    db = SessionLocal()
    try:
        # Sprawdzamy, czy w bazie są jakiekolwiek drużyny. Jeśli nie, uznajemy ją za pustą.
        if db.query(models.Team).first() is None:
            backup_path = "json_import_files/initial_data.json"

            if os.path.exists(backup_path):
                print(f"Baza jest pusta. Ładowanie danych z {backup_path}...")
                with open(backup_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 1. Import Drużyn
                for item in data.get("teams", []):
                    db.add(models.Team(**item))
                db.commit()

                # 2. Import Turniejów
                for item in data.get("tournaments", []):
                    if "start_date" in item and isinstance(item["start_date"], str):
                        item["start_date"] = date_type.fromisoformat(item["start_date"])
                    db.add(models.Tournament(**item))
                db.commit()

                # 3. Import Graczy
                for item in data.get("players", []):
                    db.add(models.Player(**item))
                db.commit()

                # 4. Import Udziałów w turniejach (TournamentTeams)
                for item in data.get("tournament_teams", []):
                    if "in_group" not in item:
                        starts_semis = item.get("starts_in_semis", False)
                        item["in_group"] = not starts_semis
                        item["in_quarters"] = False
                        item["in_semis"] = starts_semis
                        item["in_final"] = False
                        item["in_third_place"] = False
                    db.add(models.TournamentTeam(**item))

                # 5. Import Osiągnięć graczy
                for item in data.get("player_performances", []):
                    db.add(models.PlayerTournamentPerformance(**item))
                db.commit()

                # 6. Import reszty danych (mecze, oceny)
                for item in data.get("matches", []):
                    if isinstance(item["date"], str):
                        item["date"] = date_type.fromisoformat(item["date"])
                    db.add(models.Match(**item))
                db.commit()

                for item in data.get("maps", []):
                    db.add(models.Map(**item))
                for item in data.get("player_ratings", []):
                    db.add(models.PlayerRating(**item))
                db.commit()

                print("Dane początkowe załadowane pomyślnie!")
            else:
                print(f"Brak pliku backupu w lokalizacji: {backup_path}")
    except Exception as e:
        print(f"Błąd podczas automatycznego ładowania danych: {e}")
        db.rollback()
    finally:
        db.close()

# Mount static files directory (for CSS, images, etc.)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include all API routers
app.include_router(teams.router)
app.include_router(players.router)
app.include_router(tournaments.router)
app.include_router(matches.router)
app.include_router(ranking.router)
app.include_router(data_ops.router)
app.include_router(websocket.router)
app.include_router(views.router)

