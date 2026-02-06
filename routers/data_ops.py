"""
Moduł operacji na danych (Data Operations).
"""
import os
import json
from datetime import date as date_type
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

router = APIRouter(tags=["Data Operations"])

def clear_all_tables(db: Session):
    db.query(models.PlayerRating).delete()
    db.query(models.Map).delete()
    db.query(models.PlayerTournamentPerformance).delete()
    db.query(models.Match).delete()
    db.query(models.TournamentTeam).delete()
    db.query(models.Player).delete()
    db.query(models.Team).delete()
    db.query(models.Tournament).delete()
    db.commit()

@router.delete("/api/database/clear")
def clear_database(db: Session = Depends(get_db)):
    clear_all_tables(db)
    return {"message": "Baza danych została wyczyszczona."}

@router.get("/api/export", response_class=Response)
def export_database(db: Session = Depends(get_db)):
    teams = db.query(models.Team).all()
    tournaments = db.query(models.Tournament).all()
    players = db.query(models.Player).all()
    tournament_teams = db.query(models.TournamentTeam).all()
    performances = db.query(models.PlayerTournamentPerformance).all()
    matches = db.query(models.Match).all()
    maps = db.query(models.Map).all()
    ratings = db.query(models.PlayerRating).all()

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

    json_str = export_data.model_dump_json(indent=2)
    return Response(content=json_str, media_type="application/json", headers={"Content-Disposition": "attachment; filename=full_backup.json"})

@router.post("/api/import")
async def import_database(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        content = await file.read()
        data = json.loads(content)
        clear_all_tables(db)

        for item in data.get("teams", []): db.add(models.Team(**item))
        for item in data.get("tournaments", []): db.add(models.Tournament(**item))
        db.commit()
        for item in data.get("players", []): db.add(models.Player(**item))
        db.commit()
        for item in data.get("tournament_teams", []): db.add(models.TournamentTeam(**item))
        for item in data.get("player_performances", []): db.add(models.PlayerTournamentPerformance(**item))
        db.commit()
        for item in data.get("matches", []):
            if isinstance(item["date"], str): item["date"] = date_type.fromisoformat(item["date"])
            db.add(models.Match(**item))
        db.commit()
        for item in data.get("maps", []): db.add(models.Map(**item))
        for item in data.get("player_ratings", []): db.add(models.PlayerRating(**item))
        db.commit()
        return {"message": "Baza przywrócona z pliku."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Błąd importu: {str(e)}")

@router.post("/api/import/auto-from-files")
def import_auto_from_files(db: Session = Depends(get_db)):
    base_folder = "json_import_files"
    if not os.path.exists(base_folder): raise HTTPException(status_code=404, detail="Folder json_import_files nie istnieje")

    try:
        # Teams
        if os.path.exists(f"{base_folder}/teams.json"):
            with open(f"{base_folder}/teams.json", "r", encoding="utf-8") as f:
                for t in json.load(f):
                    if not db.query(models.Team).filter_by(name=t["name"]).first():
                        db.add(models.Team(**t))
                db.commit()

        # Players
        if os.path.exists(f"{base_folder}/players.json"):
            with open(f"{base_folder}/players.json", "r", encoding="utf-8") as f:
                for p in json.load(f):
                    if not db.query(models.Player).filter_by(nickname=p["nickname"]).first():
                        if p.get("team_id") and not db.query(models.Team).get(p["team_id"]): p["team_id"] = None
                        db.add(models.Player(**p))
                db.commit()

        # Tournaments
        if os.path.exists(f"{base_folder}/tournaments.json"):
            with open(f"{base_folder}/tournaments.json", "r", encoding="utf-8") as f:
                for t in json.load(f):
                    if not db.query(models.Tournament).filter_by(name=t["name"]).first():
                        # MAPOWANIE KLUCZY: Jeśli w JSON jest 'weight_overall', zamień na 'weight_group'
                        if "weight_overall" in t:
                            t["weight_group"] = t.pop("weight_overall")

                        valid = {"name", "weight", "bracket_type", "weight_group", "weight_quarters", "weight_semis", "weight_final", "weight_semis_override", "weight_final_override"}
                        clean_t = {k: v for k, v in t.items() if k in valid}
                        db.add(models.Tournament(**clean_t))
                db.commit()

        # Matches
        if os.path.exists(f"{base_folder}/matches.json"):
            with open(f"{base_folder}/matches.json", "r", encoding="utf-8") as f:
                for m in json.load(f):
                    m_date = date_type.fromisoformat(m["date"])
                    if not db.query(models.Match).filter_by(date=m_date, team1_id=m["team1_id"], team2_id=m["team2_id"]).first():
                         if db.query(models.Tournament).get(m["tournament_id"]):
                            m["date"] = m_date
                            db.add(models.Match(**m))
                db.commit()

        # Performances
        if os.path.exists(f"{base_folder}/performances.json"):
             with open(f"{base_folder}/performances.json", "r", encoding="utf-8") as f:
                for p in json.load(f):
                    # MAPOWANIE: 'rating_overall' -> 'rating_group'
                    if "rating_overall" in p:
                        p["rating_group"] = p.pop("rating_overall")

                    if not db.query(models.PlayerTournamentPerformance).filter_by(player_id=p["player_id"], tournament_id=p["tournament_id"]).first():
                        db.add(models.PlayerTournamentPerformance(**p))
                db.commit()

        return {"message": "Dane startowe załadowane."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))