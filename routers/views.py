"""
Widoki HTML (Frontend).
Zaktualizowane: Przekazuje listę ID drużyn startujących w półfinale do szablonu.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db
from routers.ranking import get_ranking

router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    players_db = db.query(models.Player).options(joinedload(models.Player.team)).all()
    players_data = [
        schemas.PlayerWithTeam.model_validate(p).model_dump(mode='json')
        for p in players_db
    ]

    teams = db.query(models.Team).order_by(models.Team.name).all()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "players": players_data,
        "teams": teams  # Przekazujemy do szablonu
    })


@router.get("/ranking", response_class=HTMLResponse)
def ranking_page(request: Request, db: Session = Depends(get_db)):
    ranking_data = get_ranking(db)
    return templates.TemplateResponse("ranking.html", {
        "request": request,
        "ranking": ranking_data
    })


@router.get("/tournaments", response_class=HTMLResponse)
def tournaments_page(request: Request, db: Session = Depends(get_db)):
    tournaments = db.query(models.Tournament).all()
    return templates.TemplateResponse("tournaments.html", {
        "request": request,
        "tournaments": tournaments
    })


@router.get("/tournament/{tournament_id}", response_class=HTMLResponse)
def tournament_details(request: Request, tournament_id: int, db: Session = Depends(get_db)):
    """
    Szczegóły turnieju.
    """
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    all_teams = db.query(models.Team).order_by(models.Team.name).all()

    # Drużyny w turnieju
    participations = db.query(models.TournamentTeam).options(
        joinedload(models.TournamentTeam.team)
    ).filter(
        models.TournamentTeam.tournament_id == tournament_id
    ).all()

    participating_team_ids = [p.team_id for p in participations]

    # --- NOWOŚĆ: Lista ID drużyn, które zaczynają od półfinału ---
    semis_team_ids = {p.team_id for p in participations if p.starts_in_semis}
    # -------------------------------------------------------------

    players = db.query(models.Player).options(joinedload(models.Player.team)).filter(
        models.Player.team_id.in_(participating_team_ids)
    ).order_by(models.Player.team_id).all()

    perfs = db.query(models.PlayerTournamentPerformance).filter(
        models.PlayerTournamentPerformance.tournament_id == tournament_id
    ).all()
    perfs_dict = {p.player_id: p for p in perfs}

    return templates.TemplateResponse("tournament_details.html", {
        "request": request,
        "tournament": tournament,
        "all_teams": all_teams,
        "participations": participations,
        "players": players,
        "perfs_dict": perfs_dict,
        "semis_team_ids": semis_team_ids # Przekazujemy do szablonu
    })

# Reszta widoków bez zmian...
@router.get("/teams", response_class=HTMLResponse)
def teams_page(request: Request, db: Session = Depends(get_db)):
    teams = db.query(models.Team).all()
    return templates.TemplateResponse("teams.html", {"request": request, "teams": teams})

@router.get("/matches", response_class=HTMLResponse)
def matches_page(request: Request, db: Session = Depends(get_db)):
    matches = db.query(models.Match).all()
    tournaments = db.query(models.Tournament).all()
    teams = db.query(models.Team).all()
    return templates.TemplateResponse("matches.html", {"request": request, "matches": matches, "tournaments": tournaments, "teams": teams})

@router.get("/player/{player_id}", response_class=HTMLResponse)
def player_profile(request: Request, player_id: int, db: Session = Depends(get_db)):
    """Profil pojedynczego gracza."""
    player = db.query(models.Player).options(
        joinedload(models.Player.team),
        # Ładujemy też historię występów w turniejach
        joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament)
    ).filter(models.Player.id == player_id).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return templates.TemplateResponse("player.html", {"request": request, "player": player})
@router.get("/import-json", response_class=HTMLResponse)
def import_json_page(request: Request):
    return templates.TemplateResponse("json_import.html", {"request": request})