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
        # Jeśli użytkownik nie podał override'ów, możemy je tu opcjonalnie wyliczyć automatycznie,
        # albo wymagać ich podania. Tutaj zakładam, że jeśli są podane (nie None), to muszą się sumować.
        # Jeśli są None, backend może je uzupełnić lub zostawić puste (zależy od logiki biznesowej).
        # Przyjmijmy wersję: Jeśli podano którekolwiek override, sprawdzamy sumę tych trzech.

        wg = tournament.weight_group_override if tournament.weight_group_override is not None else 0.0
        ws = tournament.weight_semis_override if tournament.weight_semis_override is not None else 0.0
        wf = tournament.weight_final_override if tournament.weight_final_override is not None else 0.0

        # Sprawdzamy tylko, jeśli użytkownik wpisał cokolwiek w override'ach
        if wg > 0 or ws > 0 or wf > 0:
            total_override = wg + ws + wf
            if abs(total_override - 1.0) > 0.001:
                raise HTTPException(
                    status_code=400,
                    detail=f"Suma wag dla ścieżki skróconej (Group Override + SF Override + Final Override) musi wynosić 1.0. Obecnie: {total_override}"
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

    # 1. Walidacja standardowych wag (musi sumować się do 1.0)
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

    # 2. Walidacja wag dla ścieżki skróconej (Bracket 6)
    # Sprawdzamy typ turnieju (nowy z danych lub stary z bazy)
    effective_bracket_type = data.bracket_type if data.bracket_type is not None else tournament.bracket_type

    if effective_bracket_type == "Bracket 6 teams":
        # Funkcja pomocnicza do pobierania "efektywnej" wartości wagi (nowa > stara > 0.0)
        def get_val(attr_name):
            val = getattr(data, attr_name)
            if val is not None:
                return val
            val = getattr(tournament, attr_name)
            return val if val is not None else 0.0

        wg = get_val('weight_group_override')
        ws = get_val('weight_semis_override')
        wf = get_val('weight_final_override')

        # Jeśli którykolwiek override jest ustawiony (>0), sprawdzamy czy suma to 1.0
        if wg > 0 or ws > 0 or wf > 0:
            total_override = wg + ws + wf
            if abs(total_override - 1.0) > 0.001:
                raise HTTPException(
                    status_code=400,
                    detail=f"Suma wag dla ścieżki skróconej (Group Override + SF Override + Final Override) musi wynosić 1.0. Obecnie wynosi: {total_override:.2f}"
                )

    # Aktualizacja pól w bazie
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
        # Aktualizacja istniejącego wpisu
        exists.starts_in_semis = data.starts_in_semis
        exists.rounds_group = data.rounds_group
        exists.rounds_quarters = data.rounds_quarters
        exists.rounds_semis = data.rounds_semis
        exists.rounds_final = data.rounds_final
        exists.rounds_third_place = data.rounds_third_place  # Aktualizacja
    else:
        # Tworzenie nowego wpisu
        new_entry = models.TournamentTeam(
            tournament_id=tournament_id,
            team_id=data.team_id,
            starts_in_semis=data.starts_in_semis,
            rounds_group=data.rounds_group,
            rounds_quarters=data.rounds_quarters,
            rounds_semis=data.rounds_semis,
            rounds_final=data.rounds_final,
            rounds_third_place = data.rounds_third_place  # Nowy
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
        if perf.rating_third_place is not None: existing.rating_third_place = perf.rating_third_place  # Update
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