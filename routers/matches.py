"""
API router for Matches and Player Ratings (Legacy).
Contains CRUD operations for matches and logic for adding/updating individual player ratings.
"""

from typing import List, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from database import get_db

router = APIRouter(tags=["Matches"])


# ==========================================
# MATCH CRUD OPERATIONS
# ==========================================


@router.post("/api/matches/", response_model=schemas.Match)
def create_match(
    match: schemas.MatchCreate, db: Session = Depends(get_db)
) -> models.Match:
    """
    Creates a new match in the database.

    Args:
        match (schemas.MatchCreate): The match data payload.
        db (Session): The database session.

    Returns:
        models.Match: The created match object.
    """
    db_match = models.Match(**match.model_dump())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match


@router.get("/api/matches/", response_model=List[schemas.MatchWithDetails])
def get_matches(db: Session = Depends(get_db)) -> List[models.Match]:
    """
    Retrieves a list of all matches along with their details (tournament, teams, maps).

    Args:
        db (Session): The database session.

    Returns:
        List[models.Match]: A list of matches with eager-loaded relationships.
    """
    return (
        db.query(models.Match)
        .options(
            joinedload(models.Match.tournament),
            joinedload(models.Match.team1),
            joinedload(models.Match.team2),
            joinedload(models.Match.maps),
        )
        .all()
    )


@router.get("/api/matches/{match_id}", response_model=schemas.MatchWithDetails)
def get_match(match_id: int, db: Session = Depends(get_db)) -> models.Match:
    """
    Retrieves the details of a specific match by its ID.

    Args:
        match_id (int): The unique identifier of the match.
        db (Session): The database session.

    Returns:
        models.Match: The requested match object.

    Raises:
        HTTPException: If the match with the specified ID does not exist (404).
    """
    match = (
        db.query(models.Match)
        .options(
            joinedload(models.Match.tournament),
            joinedload(models.Match.team1),
            joinedload(models.Match.team2),
            joinedload(models.Match.maps),
        )
        .filter(models.Match.id == match_id)
        .first()
    )

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.put("/api/matches/{match_id}", response_model=schemas.Match)
def update_match(
    match_id: int, match: schemas.MatchUpdate, db: Session = Depends(get_db)
) -> models.Match:
    """
    Updates the data of an existing match.

    Args:
        match_id (int): The ID of the match to update.
        match (schemas.MatchUpdate): The updated match data payload.
        db (Session): The database session.

    Returns:
        models.Match: The updated match object.

    Raises:
        HTTPException: If the match is not found (404).
    """
    db_match = db.query(models.Match).filter(models.Match.id == match_id).first()

    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")

    update_data = match.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_match, key, value)

    db.commit()
    db.refresh(db_match)
    return db_match


@router.delete("/api/matches/{match_id}")
def delete_match(match_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Deletes a specific match from the database.

    Args:
        match_id (int): The ID of the match to delete.
        db (Session): The database session.

    Returns:
        Dict[str, str]: A success message confirming deletion.

    Raises:
        HTTPException: If the match is not found (404).
    """
    db_match = db.query(models.Match).filter(models.Match.id == match_id).first()

    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")

    db.delete(db_match)
    db.commit()
    return {"message": "Match deleted successfully"}


# ==========================================
# PLAYER RATINGS (LEGACY)
# ==========================================


@router.post("/api/player_ratings/", response_model=schemas.PlayerRating)
def create_player_rating(
    rating: schemas.PlayerRatingCreate, db: Session = Depends(get_db)
) -> models.PlayerRating:
    """
    Adds a new rating or updates an existing rating for a player in a specific match.

    Args:
        rating (schemas.PlayerRatingCreate): The rating data (match_id, player_id, rating value).
        db (Session): The database session.

    Returns:
        models.PlayerRating: The created or updated rating object.

    Raises:
        HTTPException: If the associated match or player does not exist (404).
    """
    # Check if a rating already exists for this player in this match
    existing_rating = (
        db.query(models.PlayerRating)
        .filter(
            models.PlayerRating.match_id == rating.match_id,
            models.PlayerRating.player_id == rating.player_id,
        )
        .first()
    )

    if existing_rating:
        # Update existing rating
        existing_rating.rating = rating.rating
        db.commit()
        db.refresh(existing_rating)
        return existing_rating

    # Validate that the match exists
    match = db.query(models.Match).filter(models.Match.id == rating.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    # Validate that the player exists
    player = (
        db.query(models.Player).filter(models.Player.id == rating.player_id).first()
    )
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Create new rating
    db_rating = models.PlayerRating(**rating.model_dump())
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating
