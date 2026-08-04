"""
API router for Players.
Contains CRUD operations for players and regex-based search functionality.
"""

import re
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from database import get_db

router = APIRouter(tags=["Players"])


# ==========================================
# PLAYER CRUD OPERATIONS
# ==========================================


@router.post("/api/players/", response_model=schemas.Player)
def create_player(
    player: schemas.PlayerCreate, db: Session = Depends(get_db)
) -> models.Player:
    """
    Creates a new player in the database.

    Args:
        player (schemas.PlayerCreate): The player data payload.
        db (Session): The database session.

    Returns:
        models.Player: The newly created player object.

    Raises:
        HTTPException: If the nickname is already taken (400) or if the assigned team is not found (404).
    """
    existing_player = (
        db.query(models.Player)
        .filter(models.Player.nickname == player.nickname)
        .first()
    )
    if existing_player:
        raise HTTPException(
            status_code=400, detail="Player with this nickname already exists."
        )

    if player.team_id:
        team = db.query(models.Team).filter(models.Team.id == player.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Selected team does not exist.")

    new_player = models.Player(**player.model_dump())
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@router.get("/api/players/", response_model=List[schemas.PlayerWithTeam])
def get_players(db: Session = Depends(get_db)) -> List[models.Player]:
    """
    Retrieves a list of all registered players.
    Eagerly loads the associated team data for each player.

    Args:
        db (Session): The database session.

    Returns:
        List[models.Player]: A list of player objects with their team relationships loaded.
    """
    return db.query(models.Player).options(joinedload(models.Player.team)).all()


@router.get("/api/players/{player_id}", response_model=schemas.PlayerWithTeam)
def get_player(player_id: int, db: Session = Depends(get_db)) -> models.Player:
    """
    Retrieves detailed information about a specific player by their ID.

    Args:
        player_id (int): The unique identifier of the player.
        db (Session): The database session.

    Returns:
        models.Player: The requested player object.

    Raises:
        HTTPException: If the player with the specified ID does not exist (404).
    """
    player = (
        db.query(models.Player)
        .options(joinedload(models.Player.team))
        .filter(models.Player.id == player_id)
        .first()
    )

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    return player


@router.put("/api/players/{player_id}", response_model=schemas.Player)
def update_player(
    player_id: int, player_data: schemas.PlayerUpdate, db: Session = Depends(get_db)
) -> models.Player:
    """
    Updates an existing player's details (nickname, team affiliation, photo URL).

    Args:
        player_id (int): The ID of the player to update.
        player_data (schemas.PlayerUpdate): The updated player data payload.
        db (Session): The database session.

    Returns:
        models.Player: The updated player object.

    Raises:
        HTTPException: If the player is not found (404) or if the new team is not found (404).
    """
    player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    if player_data.team_id is not None:
        team = (
            db.query(models.Team).filter(models.Team.id == player_data.team_id).first()
        )
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    update_dict = player_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(player, key, value)

    db.commit()
    db.refresh(player)
    return player


@router.delete("/api/players/{player_id}")
def delete_player(player_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Deletes a player from the system.

    Args:
        player_id (int): The ID of the player to delete.
        db (Session): The database session.

    Returns:
        Dict[str, str]: A success message confirming the deletion.

    Raises:
        HTTPException: If the player is not found (404).
    """
    db_player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    db.delete(db_player)
    db.commit()
    return {"message": "Player deleted successfully"}


# ==========================================
# SEARCH OPERATIONS
# ==========================================


@router.get("/api/search/players/", response_model=List[schemas.PlayerWithTeam])
def search_players(query: str, db: Session = Depends(get_db)) -> List[models.Player]:
    """
    Searches for players using a regular expression (Regex) pattern applied to their nicknames.
    Filtering is performed locally in Python after fetching all players.

    Args:
        query (str): The regex pattern to search for (e.g., "^s1").
        db (Session): The database session.

    Returns:
        List[models.Player]: A list of players whose nicknames match the regex pattern.
                             Returns an empty list if the regex is invalid.
    """
    all_players = db.query(models.Player).options(joinedload(models.Player.team)).all()

    try:
        pattern = re.compile(query, re.IGNORECASE)
        filtered_players = [p for p in all_players if pattern.search(p.nickname)]
        return filtered_players
    except re.error:
        return []
