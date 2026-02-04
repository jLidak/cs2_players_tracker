"""
Główna aplikacja FastAPI dla CS2 Player Tracker.
Struktura z użyciem routerów.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import models
from database import engine

from routers import (
    teams,
    players,
    tournaments,
    matches,
    ranking,
    data_ops,
    websocket,
    views
)

models.Base.metadata.create_all(bind=engine)

# Inicjalizacja aplikacji
app = FastAPI(title="CS2 Player Tracker", version="1.0.0")

# Montowanie plików static
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(teams.router)
app.include_router(players.router)
app.include_router(tournaments.router)
app.include_router(matches.router)
app.include_router(ranking.router)
app.include_router(data_ops.router)
app.include_router(websocket.router)
app.include_router(views.router)