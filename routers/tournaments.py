"""
Obsługa turniejów: Tworzenie, edycja, usuwanie, dodawanie drużyn, wpisywanie wyników.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import models
import schemas
from database import get_db

router = APIRouter(tags=["Tournaments"])

@router.get("/api/tournaments/", response_model=List[schemas.Tournament])
def get_tournaments(db: Session = Depends(get_db)):
    return db.query(models.Tournament).order_by(models.Tournament.start_date).all()


@router.post("/api/tournaments/", response_model=schemas.Tournament)
def create_tournament(tournament: schemas.TournamentCreate, db: Session = Depends(get_db)):
    # 1. Walidacja standardowej ścieżki
    total_phase_weight = (
            tournament.weight_group +
            tournament.weight_quarters +
            tournament.weight_semis +
            tournament.weight_final
    )

    if abs(total_phase_weight - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"Suma standardowych wag (Group+QF+SF+Final) musi wynosić 1.0. Obecnie: {total_phase_weight}"
        )

    # 2. Walidacja ścieżki skróconej (tylko dla Bracket 6)
    if tournament.bracket_type == "Bracket 6 teams":
        wg = tournament.weight_group_override if tournament.weight_group_override is not None else 0.0
        ws = tournament.weight_semis_override if tournament.weight_semis_override is not None else 0.0
        wf = tournament.weight_final_override if tournament.weight_final_override is not None else 0.0

        if wg > 0 or ws > 0 or wf > 0:
            total_override = wg + ws + wf
            if abs(total_override - 1.0) > 0.001:
                raise HTTPException(
                    status_code=400,
                    detail=f"Suma wag dla ścieżki skróconej (Group Override + SF Override + Final Override) musi wynosić 1.0. Obecnie: {total_override}"
                )

    db_tournament = models.Tournament(**tournament.model_dump())
    db.add(db_tournament)

    try:
        db.commit()
        db.refresh(db_tournament)
        return db_tournament
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Turniej o nazwie '{tournament.name}' już istnieje w bazie!")


@router.put("/api/tournaments/{tournament_id}", response_model=schemas.Tournament)
def update_tournament(tournament_id: int, data: schemas.TournamentUpdate, db: Session = Depends(get_db)):
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    weights_to_check = ['weight_group', 'weight_quarters', 'weight_semis', 'weight_final']
    if any(getattr(data, w) is not None for w in weights_to_check):
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

    effective_bracket_type = data.bracket_type if data.bracket_type is not None else tournament.bracket_type

    if effective_bracket_type == "Bracket 6 teams":
        def get_val(attr_name):
            val = getattr(data, attr_name)
            if val is not None:
                return val
            val = getattr(tournament, attr_name)
            return val if val is not None else 0.0

        wg = get_val('weight_group_override')
        ws = get_val('weight_semis_override')
        wf = get_val('weight_final_override')

        if wg > 0 or ws > 0 or wf > 0:
            total_override = wg + ws + wf
            if abs(total_override - 1.0) > 0.001:
                raise HTTPException(
                    status_code=400,
                    detail=f"Suma wag dla ścieżki skróconej musi wynosić 1.0. Obecnie wynosi: {total_override:.2f}"
                )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tournament, key, value)

    try:
        db.commit()
        db.refresh(tournament)
        return tournament
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Turniej o takiej nazwie już istnieje w bazie!")

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
        exists.in_group = data.in_group
        exists.in_quarters = data.in_quarters
        exists.in_semis = data.in_semis
        exists.in_final = data.in_final
        exists.in_third_place = data.in_third_place

        exists.rounds_group = data.rounds_group
        exists.rounds_quarters = data.rounds_quarters
        exists.rounds_semis = data.rounds_semis
        exists.rounds_final = data.rounds_final
        exists.rounds_third_place = data.rounds_third_place
    else:
        new_entry = models.TournamentTeam(
            tournament_id=tournament_id,
            team_id=data.team_id,
            starts_in_semis=data.starts_in_semis,
            in_group=data.in_group,
            in_quarters=data.in_quarters,
            in_semis=data.in_semis,
            in_final=data.in_final,
            in_third_place=data.in_third_place,
            rounds_group=data.rounds_group,
            rounds_quarters=data.rounds_quarters,
            rounds_semis=data.rounds_semis,
            rounds_final=data.rounds_final,
            rounds_third_place=data.rounds_third_place
        )
        db.add(new_entry)

    db.commit()
    return {"message": "Team added/updated in tournament"}

@router.post("/api/performances/", response_model=schemas.PlayerTournamentPerformance)
def set_player_performance(
    perf: schemas.PlayerTournamentPerformanceCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(models.PlayerTournamentPerformance).filter(
        models.PlayerTournamentPerformance.tournament_id == perf.tournament_id,
        models.PlayerTournamentPerformance.player_id == perf.player_id
    ).first()

    if existing:
        # ZMIANA: Twarde nadpisywanie pozwala na resetowanie ocen do null
        existing.rating_group = perf.rating_group
        existing.rating_quarters = perf.rating_quarters
        existing.rating_semis = perf.rating_semis
        existing.rating_final = perf.rating_final
        existing.rating_third_place = perf.rating_third_place

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
    participation = db.query(models.TournamentTeam).filter(
        models.TournamentTeam.tournament_id == tournament_id,
        models.TournamentTeam.team_id == team_id
    ).first()

    if not participation:
        raise HTTPException(status_code=404, detail="Ta drużyna nie bierze udziału w tym turnieju")

    team_players = db.query(models.Player).filter(models.Player.team_id == team_id).all()
    player_ids = [p.id for p in team_players]

    if player_ids:
        db.query(models.PlayerTournamentPerformance).filter(
            models.PlayerTournamentPerformance.tournament_id == tournament_id,
            models.PlayerTournamentPerformance.player_id.in_(player_ids)
        ).delete(synchronize_session=False)

    db.delete(participation)
    db.commit()
    return {"message": "Drużyna została usunięta z turnieju"}