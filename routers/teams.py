"""
API router for Teams.
Contains CRUD operations: creating, retrieving, updating, and deleting teams.
"""

from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import models
import schemas
from database import get_db

router = APIRouter(
    prefix="/api/teams",
    tags=["Teams"]
)


@router.post("/", response_model=schemas.Team)
def create_team(team: schemas.TeamCreate, db: Session = Depends(get_db)) -> models.Team:
    """
    Creates a new team in the database.

    Args:
        team (schemas.TeamCreate): The team data payload (name, logo_url).
        db (Session): The database session.

    Returns:
        models.Team: The newly created team object.

    Raises:
        HTTPException: If a team with the specified name already exists (400).
    """
    existing = db.query(models.Team).filter(models.Team.name == team.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Team with this name already exists")

    db_team = models.Team(**team.model_dump())
    db.add(db_team)
    db.commit()
    db.refresh(db_team)
    return db_team


@router.get("/", response_model=List[schemas.Team])
def get_teams(db: Session = Depends(get_db)) -> List[models.Team]:
    """
    Retrieves a list of all teams.

    Args:
        db (Session): The database session.

    Returns:
        List[models.Team]: A list of all team objects.
    """
    return db.query(models.Team).all()


@router.get("/{team_id}", response_model=schemas.Team)
def get_team(team_id: int, db: Session = Depends(get_db)) -> models.Team:
    """
    Retrieves details of a specific team by its ID.

    Args:
        team_id (int): The ID of the team to retrieve.
        db (Session): The database session.

    Returns:
        models.Team: The requested team object.

    Raises:
        HTTPException: If the team is not found (404).
    """
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/{team_id}", response_model=schemas.Team)
def update_team(team_id: int, team: schemas.TeamUpdate, db: Session = Depends(get_db)) -> models.Team:
    """
    Updates an existing team's details.

    Args:
        team_id (int): The ID of the team to update.
        team (schemas.TeamUpdate): The updated team data payload.
        db (Session): The database session.

    Returns:
        models.Team: The updated team object.

    Raises:
        HTTPException: If the team is not found (404).
    """
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    update_data = team.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_team, key, value)

    db.commit()
    db.refresh(db_team)
    return db_team


@router.delete("/{team_id}")
def delete_team(team_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Deletes a team from the database.

    Args:
        team_id (int): The ID of the team to delete.
        db (Session): The database session.

    Returns:
        Dict[str, str]: A success message confirming deletion.

    Raises:
        HTTPException: If the team is not found (404).
    """
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    db.delete(db_team)
    db.commit()
    return {"message": "Team deleted successfully"}