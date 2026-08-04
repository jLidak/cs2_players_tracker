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

# Initialize database tables automatically based on SQLAlchemy models
models.Base.metadata.create_all(bind=engine)

# Initialize the FastAPI application
app = FastAPI(
    title="CS2 Player Tracker",
    version="1.0.0",
    description="Advanced ranking and tournament management API for Counter-Strike 2.",
)

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
