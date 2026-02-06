"""
Moduł operacji na danych (Data Operations).
Obsługuje import/export całej bazy danych oraz operacje czyszczenia.
"""
import os
import json
from datetime import date as date_type
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

router = APIRouter(tags=["Data Operations"])

# --- FUNKCJE POMOCNICZE ---

def clear_all_tables(db: Session):
    """Usuwa dane ze wszystkich tabel w bezpiecznej kolejności."""
    # Usuwanie dzieci (tabel zależnych)
    db.query(models.PlayerRating).delete()
    db.query(models.Map).delete()
    db.query(models.PlayerTournamentPerformance).delete()
    db.query(models.Match).delete()
    db.query(models.TournamentTeam).delete()

    # Usuwanie rodziców
    db.query(models.Player).delete()
    db.query(models.Team).delete()
    db.query(models.Tournament).delete()
    db.commit()

# --- ENDPOINTY ---

@router.delete("/api/database/clear")
def clear_database(db: Session = Depends(get_db)):
    clear_all_tables(db)
    return {"message": "Baza danych została wyczyszczona."}

@router.get("/api/export", response_class=Response)
def export_database(db: Session = Depends(get_db)):
    """
    Eksportuje całą zawartość bazy danych do jednego pliku JSON.
    """
    # 1. Pobieramy dane
    teams = db.query(models.Team).all()
    tournaments = db.query(models.Tournament).all()
    players = db.query(models.Player).all()
    tournament_teams = db.query(models.TournamentTeam).all()
    performances = db.query(models.PlayerTournamentPerformance).all()
    matches = db.query(models.Match).all()
    maps = db.query(models.Map).all()
    ratings = db.query(models.PlayerRating).all()

    # 2. Walidujemy przez Pydantic (zamiana na słowniki/JSON)
    export_data = schemas.DatabaseExport(
        teams=[schemas.Team.model_validate(x) for x in teams],
        tournaments=[schemas.Tournament.model_validate(x) for x in tournaments],
        players=[schemas.Player.model_validate(x) for x in players],
        tournament_teams=[schemas.TournamentTeam.model_validate(x) for x in tournament_teams],
        player_performances=[schemas.PlayerTournamentPerformance.model_validate(x) for x in performances],
        matches=[schemas.Match.model_validate(x) for x in matches],
        maps=[schemas.Map.model_validate(x) for x in maps],
        player_ratings=[schemas.PlayerRating.model_validate(x) for x in ratings]
    )

    # 3. Zwracamy jako plik do pobrania
    json_str = export_data.model_dump_json(indent=2)

    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=full_backup.json"}
    )

@router.post("/api/import")
async def import_database(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Importuje pełny zrzut bazy danych. UWAGA: CZYŚCI OBECNĄ BAZĘ!
    """
    try:
        content = await file.read()
        data = json.loads(content)

        # Wyczyść obecne dane
        clear_all_tables(db)

        # Wstawianie w kolejności (zależności kluczy obcych)

        # 1. Teams & Tournaments (niezależne)
        for item in data.get("teams", []):
            db.add(models.Team(**item))
        for item in data.get("tournaments", []):
            db.add(models.Tournament(**item))
        db.commit() # Commit, żeby ID były dostępne dla następnych

        # 2. Players (zależy od Teams)
        for item in data.get("players", []):
            db.add(models.Player(**item))
        db.commit()

        # 3. TournamentTeams (zależy od Teams, Tournaments)
        for item in data.get("tournament_teams", []):
            db.add(models.TournamentTeam(**item))

        # 4. Performances (zależy od Players, Tournaments)
        for item in data.get("player_performances", []):
            db.add(models.PlayerTournamentPerformance(**item))
        db.commit()

        # 5. Matches (zależy od Teams, Tournaments)
        for item in data.get("matches", []):
            # Konwersja daty ze stringa na obiekt date
            if isinstance(item["date"], str):
                item["date"] = date_type.fromisoformat(item["date"])
            db.add(models.Match(**item))
        db.commit()

        # 6. Maps & Ratings (zależy od Matches)
        for item in data.get("maps", []):
            db.add(models.Map(**item))
        for item in data.get("player_ratings", []):
            db.add(models.PlayerRating(**item))
        db.commit()

        return {"message": "Baza danych została pomyślnie przywrócona z pliku!"}

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Nieprawidłowy format pliku JSON")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd importu: {str(e)}")

@router.post("/api/import/auto-from-files")
def import_auto_from_files(db: Session = Depends(get_db)):
    """
    Importuje dane startowe z folderu json_import_files (stara metoda, bezpieczna, nie usuwa danych).
    """
    base_folder = "json_import_files"
    if not os.path.exists(base_folder):
        raise HTTPException(status_code=404, detail="Folder json_import_files nie istnieje")

    try:
        # 1. Teams
        if os.path.exists(f"{base_folder}/teams.json"):
            with open(f"{base_folder}/teams.json", "r", encoding="utf-8") as f:
                for t in json.load(f):
                    if not db.query(models.Team).filter_by(name=t["name"]).first():
                        db.add(models.Team(**t))
                db.commit()

        # 2. Players
        if os.path.exists(f"{base_folder}/players.json"):
            with open(f"{base_folder}/players.json", "r", encoding="utf-8") as f:
                for p in json.load(f):
                    if not db.query(models.Player).filter_by(nickname=p["nickname"]).first():
                        if p.get("team_id") and not db.query(models.Team).get(p["team_id"]): p["team_id"] = None
                        db.add(models.Player(**p))
                db.commit()

        # 3. Tournaments
        if os.path.exists(f"{base_folder}/tournaments.json"):
            with open(f"{base_folder}/tournaments.json", "r", encoding="utf-8") as f:
                for t in json.load(f):
                    if not db.query(models.Tournament).filter_by(name=t["name"]).first():
                        # Filtrowanie kluczy
                        valid = {"name", "weight", "bracket_type", "weight_overall", "weight_quarters", "weight_semis", "weight_final", "weight_semis_override", "weight_final_override"}
                        clean_t = {k: v for k, v in t.items() if k in valid}
                        db.add(models.Tournament(**clean_t))
                db.commit()

        # 4. Matches
        if os.path.exists(f"{base_folder}/matches.json"):
            with open(f"{base_folder}/matches.json", "r", encoding="utf-8") as f:
                for m in json.load(f):
                    m_date = date_type.fromisoformat(m["date"])
                    if not db.query(models.Match).filter_by(date=m_date, team1_id=m["team1_id"], team2_id=m["team2_id"]).first():
                         if db.query(models.Tournament).get(m["tournament_id"]):
                            m["date"] = m_date
                            db.add(models.Match(**m))
                db.commit()

        # 5. Performances
        if os.path.exists(f"{base_folder}/performances.json"):
             with open(f"{base_folder}/performances.json", "r", encoding="utf-8") as f:
                for p in json.load(f):
                    if not db.query(models.PlayerTournamentPerformance).filter_by(player_id=p["player_id"], tournament_id=p["tournament_id"]).first():
                        db.add(models.PlayerTournamentPerformance(**p))
                db.commit()

        return {"message": "Dane startowe załadowane."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))