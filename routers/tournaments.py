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
    # WALIDACJA WAG: Muszą sumować się do 1.0
    total_phase_weight = (
            tournament.weight_group +
            tournament.weight_quarters +
            tournament.weight_semis +
            tournament.weight_final
    )

    if abs(total_phase_weight - 1.0) > 0.001:  # Tolerancja dla float
        raise HTTPException(
            status_code=400,
            detail=f"Suma wag faz musi wynosić 1.0. Obecnie wynosi: {total_phase_weight}"
        )

    db_tournament = models.Tournament(**tournament.model_dump())
    db.add(db_tournament)
    db.commit()
    db.refresh(db_tournament)
    return db_tournament


@router.put("/api/tournaments/{tournament_id}", response_model=schemas.Tournament)
def update_tournament(tournament_id: int, data: schemas.TournamentUpdate, db: Session = Depends(get_db)):
    """Aktualizuje dane turnieju z walidacją sumy wag."""
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Sprawdzamy sumę wag, jeśli jakakolwiek waga jest aktualizowana
    weights_to_check = ['weight_group', 'weight_quarters', 'weight_semis', 'weight_final']
    if any(getattr(data, w) is not None for w in weights_to_check):
        # Budujemy słownik "nowych" wag (bierzemy z data, a jak None to z bazy)
        proposed_weights = {}
        for w in weights_to_check:
            new_val = getattr(data, w)
            proposed_weights[w] = new_val if new_val is not None else getattr(tournament, w)

        total = sum(proposed_weights.values())
        if abs(total - 1.0) > 0.001:
            raise HTTPException(
                status_code=400,
                detail=f"Błąd walidacji: Suma wag faz musi wynosić 1.0. Twoje zmiany dają sumę: {total:.2f}"
            )

    # Aktualizuj pola
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tournament, key, value)

    db.commit()
    db.refresh(tournament)
    return tournament
@router.delete("/api/tournaments/{tournament_id}")
def delete_tournament(tournament_id: int, db: Session = Depends(get_db)):
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
    """Ustawia ratingi gracza. Zmieniono rating_overall na rating_group."""
    existing = db.query(models.PlayerTournamentPerformance).filter(
        models.PlayerTournamentPerformance.tournament_id == perf.tournament_id,
        models.PlayerTournamentPerformance.player_id == perf.player_id
    ).first()

    if existing:
        if perf.rating_group is not None: existing.rating_group = perf.rating_group
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

@router.delete("/api/tournaments/{tournament_id}/teams/{team_id}")
def remove_team_from_tournament(tournament_id: int, team_id: int, db: Session = Depends(get_db)):
    """
    Usuwa drużynę z turnieju oraz usuwa wyniki (ratingi) graczy tej drużyny w tym turnieju.
    """
    # 1. Szukamy wpisu w tabeli łączącej (udział w turnieju)
    participation = db.query(models.TournamentTeam).filter(
        models.TournamentTeam.tournament_id == tournament_id,
        models.TournamentTeam.team_id == team_id
    ).first()

    if not participation:
        raise HTTPException(status_code=404, detail="Ta drużyna nie bierze udziału w tym turnieju")

    # 2. Usuwamy wyniki (performances) graczy tej drużyny z tego turnieju
    # Najpierw znajdujemy graczy tej drużyny
    team_players = db.query(models.Player).filter(models.Player.team_id == team_id).all()
    player_ids = [p.id for p in team_players]

    if player_ids:
        db.query(models.PlayerTournamentPerformance).filter(
            models.PlayerTournamentPerformance.tournament_id == tournament_id,
            models.PlayerTournamentPerformance.player_id.in_(player_ids)
        ).delete(synchronize_session=False)

    # 3. Usuwamy wpis o udziale drużyny
    db.delete(participation)
    db.commit()

    return {"message": "Drużyna została usunięta z turnieju"}