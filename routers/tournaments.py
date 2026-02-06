"""
Obsługa turniejów: Tworzenie, dodawanie drużyn, wpisywanie wyników (ratingów).
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db

router = APIRouter(tags=["Tournaments"])

@router.get("/api/tournaments/", response_model=List[schemas.Tournament])
def get_tournaments(db: Session = Depends(get_db)):
    return db.query(models.Tournament).all()

@router.post("/api/tournaments/", response_model=schemas.Tournament)
def create_tournament(tournament: schemas.TournamentCreate, db: Session = Depends(get_db)):
    db_tournament = models.Tournament(**tournament.model_dump())
    db.add(db_tournament)
    db.commit()
    db.refresh(db_tournament)
    return db_tournament

@router.post("/api/tournaments/{tournament_id}/add_team")
def add_team_to_tournament(
    tournament_id: int,
    data: schemas.AddTeamToTournament,
    db: Session = Depends(get_db)
):
    """Dodaje drużynę do turnieju (z opcją starts_in_semis)."""
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Sprawdź czy już dodana
    exists = db.query(models.TournamentTeam).filter(
        models.TournamentTeam.tournament_id == tournament_id,
        models.TournamentTeam.team_id == data.team_id
    ).first()

    if exists:
        # Update flagi starts_in_semis
        exists.starts_in_semis = data.starts_in_semis
    else:
        new_entry = models.TournamentTeam(
            tournament_id=tournament_id,
            team_id=data.team_id,
            starts_in_semis=data.starts_in_semis
        )
        db.add(new_entry)

    db.commit()
    return {"message": "Team added/updated in tournament"}

@router.post("/api/performances/", response_model=schemas.PlayerTournamentPerformance)
def set_player_performance(
    perf: schemas.PlayerTournamentPerformanceCreate,
    db: Session = Depends(get_db)
):
    """Ustawia lub aktualizuje ratingi gracza w danym turnieju."""
    existing = db.query(models.PlayerTournamentPerformance).filter(
        models.PlayerTournamentPerformance.tournament_id == perf.tournament_id,
        models.PlayerTournamentPerformance.player_id == perf.player_id
    ).first()

    if existing:
        # Update tylko przekazanych pól (jeśli nie None)
        if perf.rating_overall is not None: existing.rating_overall = perf.rating_overall
        if perf.rating_quarters is not None: existing.rating_quarters = perf.rating_quarters
        if perf.rating_semis is not None: existing.rating_semis = perf.rating_semis
        if perf.rating_final is not None: existing.rating_final = perf.rating_final
        db.commit()
        db.refresh(existing)
        return existing
    else:
        new_perf = models.PlayerTournamentPerformance(**perf.model_dump())
        db.add(new_perf)
        db.commit()
        db.refresh(new_perf)
        return new_perf