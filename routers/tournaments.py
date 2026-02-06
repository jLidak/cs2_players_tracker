"""
Obsługa turniejów: Tworzenie, edycja, usuwanie, dodawanie drużyn, wpisywanie wyników.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
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

# --- TU JEST ENDPOINT DO EDYCJI (PUT) ---
@router.put("/api/tournaments/{tournament_id}", response_model=schemas.Tournament)
def update_tournament(tournament_id: int, data: schemas.TournamentUpdate, db: Session = Depends(get_db)):
    """Aktualizuje dane turnieju (nazwa, wagi, typ)."""
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Aktualizuj tylko przesłane pola
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tournament, key, value)

    db.commit()
    db.refresh(tournament)
    return tournament
# ----------------------------------------

@router.delete("/api/tournaments/{tournament_id}")
def delete_tournament(tournament_id: int, db: Session = Depends(get_db)):
    """Usuwa turniej oraz kaskadowo wszystkie powiązane mecze i wyniki."""
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    db.delete(tournament)
    db.commit()
    return {"message": "Turniej usunięty"}

@router.post("/api/tournaments/{tournament_id}/add_team")
def add_team_to_tournament(
    tournament_id: int,
    data: schemas.AddTeamToTournament,
    db: Session = Depends(get_db)
):
    """Dodaje drużynę do turnieju."""
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    exists = db.query(models.TournamentTeam).filter(
        models.TournamentTeam.tournament_id == tournament_id,
        models.TournamentTeam.team_id == data.team_id
    ).first()

    if exists:
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
    """Ustawia ratingi gracza."""
    existing = db.query(models.PlayerTournamentPerformance).filter(
        models.PlayerTournamentPerformance.tournament_id == perf.tournament_id,
        models.PlayerTournamentPerformance.player_id == perf.player_id
    ).first()

    if existing:
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