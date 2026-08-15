"""
Data Operations module.
Handles database clearance, JSON data imports, and full database exports.
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


def clear_all_tables(db: Session) -> None:
    """
    Deletes all records from all tables in the database.
    Operations are committed at the end.

    Args:
        db (Session): The active database session.
    """
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
    """
    Endpoint to completely clear all data from the database.
    """
    clear_all_tables(db)
    return {"message": "Database has been successfully cleared."}


@router.get("/api/export", response_class=Response)
def export_database(db: Session = Depends(get_db)):
    """
    Exports the entire database content into a single JSON file.

    Returns:
        Response: A downloadable JSON file containing all database records.
    """
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
        tournament_teams=[
            schemas.TournamentTeam.model_validate(x) for x in tournament_teams
        ],
        player_performances=[
            schemas.PlayerTournamentPerformance.model_validate(x) for x in performances
        ],
        matches=[schemas.Match.model_validate(x) for x in matches],
        maps=[schemas.Map.model_validate(x) for x in maps],
        player_ratings=[schemas.PlayerRating.model_validate(x) for x in ratings],
    )

    json_str = export_data.model_dump_json(indent=2)
    return Response(
        content=json_str,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=full_backup.json"},
    )


@router.post("/api/import")
async def import_database(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Imports a full database backup from a provided JSON file.
    WARNING: This operation clears the existing database before importing.
    """
    try:
        content = await file.read()
        data = json.loads(content)

        # Clear existing data before importing new data
        clear_all_tables(db)

        # Import Teams
        for item in data.get("teams", []):
            db.add(models.Team(**item))

        # Import Tournaments (handling string to date conversion)
        for item in data.get("tournaments", []):
            if "start_date" in item and isinstance(item["start_date"], str):
                item["start_date"] = date_type.fromisoformat(item["start_date"])
            db.add(models.Tournament(**item))

        db.commit()

        # Import Players
        for item in data.get("players", []):
            db.add(models.Player(**item))
        db.commit()

        # Import Tournament Teams (handling backwards compatibility for new phase columns)
        for item in data.get("tournament_teams", []):
            if "in_group" not in item:
                starts_semis = item.get("starts_in_semis", False)
                item["in_group"] = not starts_semis
                item["in_quarters"] = False
                item["in_semis"] = starts_semis
                item["in_final"] = False
                item["in_third_place"] = False
            db.add(models.TournamentTeam(**item))

        # Import Player Performances
        for item in data.get("player_performances", []):
            db.add(models.PlayerTournamentPerformance(**item))
        db.commit()

        # Import Legacy Matches
        for item in data.get("matches", []):
            if isinstance(item["date"], str):
                item["date"] = date_type.fromisoformat(item["date"])
            db.add(models.Match(**item))
        db.commit()

        # Import Legacy Maps and Player Ratings
        for item in data.get("maps", []):
            db.add(models.Map(**item))

        for item in data.get("player_ratings", []):
            db.add(models.PlayerRating(**item))
        db.commit()

        return {"message": "Database has been successfully restored from the file."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Import error: {str(e)}")


@router.post("/api/import/auto-from-files")
def import_auto_from_files(db: Session = Depends(get_db)):
    """
    Automatically loads initial seed data from JSON files located in the 'json_import_files' directory.
    Safe operation: does not overwrite or delete existing records.
    """
    base_folder = "json_import_files"
    if not os.path.exists(base_folder):
        raise HTTPException(
            status_code=404, detail="Directory 'json_import_files' does not exist."
        )

    try:
        # Import Teams
        teams_file = f"{base_folder}/teams.json"
        if os.path.exists(teams_file):
            with open(teams_file, "r", encoding="utf-8") as f:
                for t in json.load(f):
                    if not db.query(models.Team).filter_by(name=t["name"]).first():
                        db.add(models.Team(**t))
                        db.commit()


        # Import Players
        players_file = f"{base_folder}/players.json"
        if os.path.exists(players_file):
            with open(players_file, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    if (
                        not db.query(models.Player)
                        .filter_by(nickname=p["nickname"])
                        .first()
                    ):
                        # Nullify team_id if the team does not exist in DB
                        if p.get("team_id") and not db.query(models.Team).get(
                            p["team_id"]
                        ):
                            p["team_id"] = None
                        db.add(models.Player(**p))
                        db.commit()

        # Import Tournaments
        tournaments_file = f"{base_folder}/tournaments.json"
        if os.path.exists(tournaments_file):
            with open(tournaments_file, "r", encoding="utf-8") as f:
                for t in json.load(f):
                    if (
                        not db.query(models.Tournament)
                        .filter_by(name=t["name"])
                        .first()
                    ):
                        # Key mapping for older JSON versions
                        if "weight_overall" in t:
                            t["weight_group"] = t.pop("weight_overall")

                        valid_keys = {
                            "name",
                            "weight",
                            "bracket_type",
                            "weight_group",
                            "weight_quarters",
                            "weight_semis",
                            "weight_final",
                            "weight_semis_override",
                            "weight_final_override",
                        }
                        clean_t = {k: v for k, v in t.items() if k in valid_keys}
                        db.add(models.Tournament(**clean_t))
                        db.commit()


        # Import Matches (Legacy)
        matches_file = f"{base_folder}/matches.json"
        if os.path.exists(matches_file):
            with open(matches_file, "r", encoding="utf-8") as f:
                for m in json.load(f):
                    m_date = date_type.fromisoformat(m["date"])
                    match_exists = (
                        db.query(models.Match)
                        .filter_by(
                            date=m_date, team1_id=m["team1_id"], team2_id=m["team2_id"]
                        )
                        .first()
                    )

                    if not match_exists:
                        if db.query(models.Tournament).get(m["tournament_id"]):
                            m["date"] = m_date
                            db.add(models.Match(**m))
                            db.commit()


        # Import Player Performances
        performances_file = f"{base_folder}/performances.json"
        if os.path.exists(performances_file):
            with open(performances_file, "r", encoding="utf-8") as f:
                for p in json.load(f):
                    # Key mapping for older JSON versions
                    if "rating_overall" in p:
                        p["rating_group"] = p.pop("rating_overall")

                    perf_exists = (
                        db.query(models.PlayerTournamentPerformance)
                        .filter_by(
                            player_id=p["player_id"], tournament_id=p["tournament_id"]
                        )
                        .first()
                    )

                    if not perf_exists:
                        db.add(models.PlayerTournamentPerformance(**p))
                        db.commit()


        return {"message": "Initial seed data has been successfully loaded."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/import_data/")
def import_from_json(data: schemas.ImportData, db: Session = Depends(get_db)):
    """
    Imports teams and their respective players from a simplified JSON payload.
    Creates non-existing teams and players automatically.
    """
    count_teams = 0
    count_players = 0

    for t_data in data.teams:
        # 1. Check if the team exists; if not, create it
        team = db.query(models.Team).filter(models.Team.name == t_data.name).first()
        if not team:
            team = models.Team(name=t_data.name, logo_url=t_data.logo_url)
            db.add(team)
            db.commit()
            db.refresh(team)
            count_teams += 1

        # 2. Process players associated with this team
        for p_data in t_data.players:
            player = (
                db.query(models.Player)
                .filter(models.Player.nickname == p_data.nickname)
                .first()
            )
            if not player:
                player = models.Player(
                    nickname=p_data.nickname,
                    photo_url=p_data.photo_url,
                    team_id=team.id,
                )
                db.add(player)
                count_players += 1
            else:
                # Optional: Update the club affiliation of an existing player
                if player.team_id != team.id:
                    player.team_id = team.id
                    db.add(player)

    db.commit()
    return {
        "message": f"Success! Added {count_teams} new teams and {count_players} new players."
    }
