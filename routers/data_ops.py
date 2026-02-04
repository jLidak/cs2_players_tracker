"""
Moduł operacji na danych (Data Operations).
Obsługuje import/export JSON, masowe dodawanie danych (batch) oraz czyszczenie bazy.
Umożliwia szybkie przywracanie stanu bazy danych lub jej migrację.
"""
import os
import json
from datetime import date as date_type
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

router = APIRouter(
    tags=["Data Operations"]
)


# --- JSON BATCH OPERATIONS ---

@router.post("/api/batch/teams/")
def batch_create_teams(teams: List[schemas.TeamCreate], db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Masowe dodawanie drużyn do bazy danych.
    Pomija drużyny, których nazwy już istnieją w bazie.

    Args:
        teams (List[schemas.TeamCreate]): Lista obiektów drużyn do dodania.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Informacja o liczbie dodanych drużyn.
    """
    added_count = 0
    for team_data in teams:
        exists = db.query(models.Team).filter(models.Team.name == team_data.name).first()
        if not exists:
            db_team = models.Team(**team_data.model_dump())
            db.add(db_team)
            added_count += 1
    db.commit()
    return {"message": f"Dodano {added_count} nowych drużyn."}


@router.post("/api/batch/tournaments/")
def batch_create_tournaments(tournaments: List[schemas.TournamentCreate], db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Masowe dodawanie turniejów.
    Pomija turnieje o istniejących nazwach.

    Args:
        tournaments (List[schemas.TournamentCreate]): Lista turniejów.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Informacja o liczbie dodanych turniejów.
    """
    added_count = 0
    for t_data in tournaments:
        exists = db.query(models.Tournament).filter(models.Tournament.name == t_data.name).first()
        if not exists:
            db_t = models.Tournament(**t_data.model_dump())
            db.add(db_t)
            added_count += 1
    db.commit()
    return {"message": f"Dodano {added_count} nowych turniejów."}


@router.post("/api/batch/matches/")
def batch_create_matches(matches: List[schemas.MatchCreate], db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Masowe dodawanie meczów.
    Dodaje mecz tylko wtedy, gdy istnieją powiązane ID turnieju oraz obu drużyn.

    Args:
        matches (List[schemas.MatchCreate]): Lista meczów do dodania.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Informacja o liczbie pomyślnie dodanych meczów.
    """
    added_count = 0
    for m_data in matches:
        t_exists = db.query(models.Tournament).filter(models.Tournament.id == m_data.tournament_id).first()
        team1_exists = db.query(models.Team).filter(models.Team.id == m_data.team1_id).first()
        team2_exists = db.query(models.Team).filter(models.Team.id == m_data.team2_id).first()

        if t_exists and team1_exists and team2_exists:
            db_match = models.Match(**m_data.model_dump())
            db.add(db_match)
            added_count += 1

    db.commit()
    return {"message": f"Dodano {added_count} meczów (pominięto błędne ID)."}


@router.post("/api/batch/players/")
def batch_create_players(players: List[schemas.PlayerCreate], db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Masowe dodawanie graczy.
    Jeśli podane ID drużyny nie istnieje, gracz jest dodawany jako "wolny agent" (team_id=None).

    Args:
        players (List[schemas.PlayerCreate]): Lista graczy.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Informacja o liczbie dodanych graczy.
    """
    added_count = 0
    for p_data in players:
        exists = db.query(models.Player).filter(models.Player.nickname == p_data.nickname).first()
        if not exists:
            if p_data.team_id:
                team_exists = db.query(models.Team).filter(models.Team.id == p_data.team_id).first()
                if not team_exists:
                    p_data.team_id = None

            db_player = models.Player(**p_data.model_dump())
            db.add(db_player)
            added_count += 1
    db.commit()
    return {"message": f"Dodano {added_count} graczy."}


# --- DATABASE MANAGEMENT ---

@router.delete("/api/database/clear")
def clear_database(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Całkowite czyszczenie bazy danych.
    Usuwa rekordy w odpowiedniej kolejności, aby nie naruszyć więzów integralności.

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Potwierdzenie wyczyszczenia bazy.
    """
    # Usuwanie tabel zależnych (dzieci)
    db.query(models.PlayerRankingPoint).delete()
    db.query(models.PlayerRating).delete()
    db.query(models.Map).delete()

    # Usuwanie tabel pośrednich
    db.query(models.Match).delete()
    db.query(models.Player).delete()

    # Usuwanie tabel głównych (rodziców)
    db.query(models.Team).delete()
    db.query(models.Tournament).delete()

    db.commit()
    return {"message": "Baza danych została wyczyszczona."}


@router.get("/api/export/")
def export_database(db: Session = Depends(get_db)) -> JSONResponse:
    """
    Eksportuje całą zawartość bazy danych do jednego strukturalnego obiektu JSON.
    Przydatne do tworzenia kopii zapasowych.

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        JSONResponse: Obiekt JSON zawierający listy wszystkich encji (drużyny, gracze, mecze, itd.).
    """
    teams = db.query(models.Team).all()
    players = db.query(models.Player).all()
    tournaments = db.query(models.Tournament).all()
    matches = db.query(models.Match).all()
    maps = db.query(models.Map).all()
    player_ratings = db.query(models.PlayerRating).all()
    player_ranking_points = db.query(models.PlayerRankingPoint).all()

    export_data = {
        "teams": [schemas.Team.model_validate(t).model_dump() for t in teams],
        "players": [schemas.Player.model_validate(p).model_dump() for p in players],
        "tournaments": [schemas.Tournament.model_validate(t).model_dump() for t in tournaments],
        "matches": [schemas.Match.model_validate(m).model_dump(mode='json') for m in matches],
        "maps": [schemas.Map.model_validate(m).model_dump() for m in maps],
        "player_ratings": [schemas.PlayerRating.model_validate(pr).model_dump() for pr in player_ratings],
        "player_ranking_points": [schemas.PlayerRankingPoint.model_validate(prp).model_dump() for prp in
                                  player_ranking_points]
    }

    return JSONResponse(content=export_data)


@router.post("/api/import/")
async def import_database(file: UploadFile = File(...), db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Czyści całą obecną bazę danych, a następnie importuje pełną bazę danych z przesłanego pliku JSON.

    Args:
        file (UploadFile): Przesłany plik JSON zgodny ze strukturą eksportu.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Komunikat o sukcesie importu.
    """
    content = await file.read()
    data = json.loads(content)

    clear_database(db)

    for team_data in data.get("teams", []):
        db.add(models.Team(**team_data))
    db.commit()

    for player_data in data.get("players", []):
        db.add(models.Player(**player_data))
    db.commit()

    for tournament_data in data.get("tournaments", []):
        db.add(models.Tournament(**tournament_data))
    db.commit()

    for match_data in data.get("matches", []):
        # Konwersja stringa daty z JSON na obiekt python date
        match_data["date"] = date_type.fromisoformat(match_data["date"])
        db.add(models.Match(**match_data))
    db.commit()

    for map_data in data.get("maps", []):
        db.add(models.Map(**map_data))
    db.commit()

    for rating_data in data.get("player_ratings", []):
        db.add(models.PlayerRating(**rating_data))
    db.commit()

    for ranking_data in data.get("player_ranking_points", []):
        db.add(models.PlayerRankingPoint(**ranking_data))
    db.commit()

    return {"message": "Database imported successfully"}


@router.post("/api/import/auto-from-files")
def import_auto_from_files(db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Automatycznie importuje dane z plików JSON znajdujących się w folderze 'json_import_files'.
    Służy do szybkiego zasypania bazy danymi testowymi/startowymi.

    Wymagana struktura plików w folderze:
    - teams.json
    - players.json
    - tournaments.json
    - matches.json

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Komunikat o sukcesie.

    Raises:
        HTTPException(404): Jeśli folder lub któryś z plików nie istnieje.
        HTTPException(400): Jeśli pliki zawierają błędy składni JSON.
    """
    base_folder = "json_import_files"

    if not os.path.exists(base_folder):
        raise HTTPException(status_code=404, detail=f"Nie znaleziono folderu '{base_folder}'")

    try:
        # 1. Teams
        with open(os.path.join(base_folder, "teams.json"), "r", encoding="utf-8") as f:
            teams_data = json.load(f)
            for t_data in teams_data:
                if not db.query(models.Team).filter(models.Team.name == t_data["name"]).first():
                    db.add(models.Team(**t_data))
            db.commit()

        # 2. Players
        with open(os.path.join(base_folder, "players.json"), "r", encoding="utf-8") as f:
            players_data = json.load(f)
            for p_data in players_data:
                if not db.query(models.Player).filter(models.Player.nickname == p_data["nickname"]).first():
                    # Walidacja relacji team_id
                    if p_data.get("team_id") and not db.query(models.Team).filter(
                            models.Team.id == p_data["team_id"]).first():
                        p_data["team_id"] = None
                    db.add(models.Player(**p_data))
            db.commit()

        # 3. Tournaments
        with open(os.path.join(base_folder, "tournaments.json"), "r", encoding="utf-8") as f:
            tournaments_data = json.load(f)
            for t_data in tournaments_data:
                if not db.query(models.Tournament).filter(models.Tournament.name == t_data["name"]).first():
                    db.add(models.Tournament(**t_data))
            db.commit()

        # 4. Matches
        with open(os.path.join(base_folder, "matches.json"), "r", encoding="utf-8") as f:
            matches_data = json.load(f)
            for m_data in matches_data:
                m_date = date_type.fromisoformat(m_data["date"])
                exists = db.query(models.Match).filter(
                    models.Match.date == m_date,
                    models.Match.team1_id == m_data["team1_id"],
                    models.Match.team2_id == m_data["team2_id"]
                ).first()

                if not exists:
                    m_data["date"] = m_date
                    db.add(models.Match(**m_data))
            db.commit()

        return {"message": "Wszystkie pliki zostały zaimportowane pomyślnie!"}

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Brak pliku: {e.filename}")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Błąd w składni jednego z plików JSON")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))