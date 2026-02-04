"""
Moduł obsługujący widoki HTML (Frontend).
Odpowiada za renderowanie szablonów Jinja2 i przekazywanie do nich danych z bazy.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db

# Importujemy logikę biznesową z innych routerów, aby nie powielać kodu
from routers.ranking import get_ranking
from routers.matches import get_matches

# include_in_schema=False ukrywa te endpointy w automatycznej dokumentacji Swaggera (API docs),
# ponieważ służą one do serwowania stron HTML, a nie danych JSON.
router = APIRouter(include_in_schema=False)
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Strona główna aplikacji. Wyświetla kafelki z profilami wszystkich graczy.

    Args:
        request (Request): Obiekt żądania HTTP (wymagany przez Jinja2).
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'index.html' z listą graczy.
    """
    players_db = db.query(models.Player).options(joinedload(models.Player.team)).all()

    # Konwersja obiektów SQLAlchemy na słowniki przez Pydantic,
    # aby łatwiej operować danymi w szablonie (np. serializacja).
    players_data = [
        schemas.PlayerWithTeam.model_validate(p).model_dump(mode='json')
        for p in players_db
    ]

    return templates.TemplateResponse("index.html", {
        "request": request,
        "players": players_data
    })


@router.get("/player/{player_id}", response_class=HTMLResponse)
def player_profile(request: Request, player_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Strona profilowa konkretnego gracza.
    Wyświetla jego dane, zdjęcie oraz historię meczów wraz z ocenami.

    Args:
        request (Request): Obiekt żądania HTTP.
        player_id (int): ID gracza.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'player.html'.

    Raises:
        HTTPException(404): Jeśli gracz o podanym ID nie istnieje.
    """
    player = db.query(models.Player).options(joinedload(models.Player.team)).filter(
        models.Player.id == player_id
    ).first()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Pobieranie ocen gracza
    ratings = db.query(models.PlayerRating).filter(models.PlayerRating.player_id == player_id).all()
    match_ids = [r.match_id for r in ratings]

    # Pobieranie meczów, w których gracz brał udział (na podstawie ocen)
    matches = db.query(models.Match).options(
        joinedload(models.Match.tournament),
        joinedload(models.Match.team1),
        joinedload(models.Match.team2)
    ).filter(models.Match.id.in_(match_ids)).order_by(models.Match.date.desc()).all()

    # Łączenie meczu z oceną gracza w jeden obiekt dla szablonu
    matches_with_ratings = []
    for match in matches:
        rating = next((r.rating for r in ratings if r.match_id == match.id), None)
        matches_with_ratings.append({"match": match, "rating": rating})

    return templates.TemplateResponse("player.html", {
        "request": request,
        "player": player,
        "matches_with_ratings": matches_with_ratings
    })


@router.get("/ranking", response_class=HTMLResponse)
def ranking_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Strona wyświetlająca globalny ranking graczy.
    Wykorzystuje logikę obliczania punktów z routera `ranking.py`.

    Args:
        request (Request): Obiekt żądania HTTP.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'ranking.html'.
    """
    ranking_data = get_ranking(db)
    return templates.TemplateResponse("ranking.html", {
        "request": request,
        "ranking": ranking_data
    })


@router.get("/teams", response_class=HTMLResponse)
def teams_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Strona z listą wszystkich drużyn.

    Args:
        request (Request): Obiekt żądania HTTP.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'teams.html'.
    """
    teams = db.query(models.Team).all()
    return templates.TemplateResponse("teams.html", {
        "request": request,
        "teams": teams
    })


@router.get("/tournaments", response_class=HTMLResponse)
def tournaments_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Strona z listą wszystkich turniejów.

    Args:
        request (Request): Obiekt żądania HTTP.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'tournaments.html'.
    """
    tournaments = db.query(models.Tournament).all()
    return templates.TemplateResponse("tournaments.html", {
        "request": request,
        "tournaments": tournaments
    })


@router.get("/matches", response_class=HTMLResponse)
def matches_page(request: Request, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Strona z listą meczów (terminarz/wyniki).
    Pozwala również na filtrowanie (logika filtrowania jest po stronie JS/HTML, tu przekazujemy dane).

    Args:
        request (Request): Obiekt żądania HTTP.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'matches.html'.
    """
    matches_data = get_matches(db)
    teams = db.query(models.Team).all()
    tournaments = db.query(models.Tournament).all()

    return templates.TemplateResponse("matches.html", {
        "request": request,
        "matches": matches_data,
        "teams": teams,
        "tournaments": tournaments
    })


@router.get("/match/{match_id}", response_class=HTMLResponse)
def match_details(request: Request, match_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Szczegółowy widok meczu.
    Wyświetla składy obu drużyn oraz formularz do oceniania graczy.

    Args:
        request (Request): Obiekt żądania HTTP.
        match_id (int): ID meczu.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'match_details.html'.

    Raises:
        HTTPException(404): Jeśli mecz nie istnieje.
    """
    match = db.query(models.Match).options(
        joinedload(models.Match.tournament),
        joinedload(models.Match.team1),
        joinedload(models.Match.team2)
    ).filter(models.Match.id == match_id).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Pobieramy graczy należących do drużyn grających w tym meczu
    team1_players = db.query(models.Player).filter(models.Player.team_id == match.team1_id).all()
    team2_players = db.query(models.Player).filter(models.Player.team_id == match.team2_id).all()

    # Pobieramy istniejące oceny dla tego meczu, aby wyświetlić je w formularzu
    ratings = db.query(models.PlayerRating).filter(models.PlayerRating.match_id == match_id).all()
    ratings_dict = {r.player_id: r.rating for r in ratings}

    return templates.TemplateResponse("match_details.html", {
        "request": request,
        "match": match,
        "team1_players": team1_players,
        "team2_players": team2_players,
        "ratings_dict": ratings_dict
    })


@router.get("/tournament/{tournament_id}", response_class=HTMLResponse)
def tournament_details(request: Request, tournament_id: int, db: Session = Depends(get_db)) -> HTMLResponse:
    """
    Szczegółowy widok turnieju.
    Pozwala na przyznawanie punktów rankingowych graczom za ten konkretny turniej.

    Args:
        request (Request): Obiekt żądania HTTP.
        tournament_id (int): ID turnieju.
        db (Session): Sesja bazy danych.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'tournament_details.html'.

    Raises:
        HTTPException(404): Jeśli turniej nie istnieje.
    """
    tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    players = db.query(models.Player).options(joinedload(models.Player.team)).order_by(models.Player.nickname).all()

    # Pobieramy przyznane już punkty za ten turniej
    points = db.query(models.PlayerRankingPoint).filter(models.PlayerRankingPoint.tournament_id == tournament_id).all()
    points_dict = {p.player_id: p.points for p in points}

    return templates.TemplateResponse("tournament_details.html", {
        "request": request,
        "tournament": tournament,
        "players": players,
        "points_dict": points_dict
    })


@router.get("/import-json", response_class=HTMLResponse)
def import_json_page(request: Request) -> HTMLResponse:
    """
    Strona służąca do importu danych (JSON) do bazy danych.

    Args:
        request (Request): Obiekt żądania HTTP.

    Returns:
        HTMLResponse: Wyrenderowany szablon 'json_import.html'.
    """
    return templates.TemplateResponse("json_import.html", {"request": request})