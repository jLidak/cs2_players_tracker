"""
Moduł obsługujący endpointy API dla Drużyn (Teams).
Zawiera operacje CRUD: tworzenie, pobieranie, aktualizacja i usuwanie drużyn.
"""
from typing import List, Dict
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
    Tworzy nową drużynę w bazie danych.

    Args:
        team (schemas.TeamCreate): Dane nowej drużyny (nazwa, logo).
        db (Session): Sesja bazy danych.

    Returns:
        models.Team: Obiekt utworzonej drużyny.

    Raises:
        HTTPException(400): Jeśli drużyna o podanej nazwie już istnieje.
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
    Pobiera listę wszystkich drużyn.

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        List[models.Team]: Lista obiektów drużyn.
    """
    return db.query(models.Team).all()


@router.get("/{team_id}", response_model=schemas.Team)
def get_team(team_id: int, db: Session = Depends(get_db)) -> models.Team:
    """
    Pobiera szczegóły pojedynczej drużyny na podstawie ID.

    Args:
        team_id (int): ID szukanej drużyny.
        db (Session): Sesja bazy danych.

    Returns:
        models.Team: Znaleziona drużyna.

    Raises:
        HTTPException(404): Jeśli drużyna nie zostanie znaleziona.
    """
    team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/{team_id}", response_model=schemas.Team)
def update_team(team_id: int, team: schemas.TeamUpdate, db: Session = Depends(get_db)) -> models.Team:
    """
    Aktualizuje dane istniejącej drużyny.

    Args:
        team_id (int): ID drużyny do edycji.
        team (schemas.TeamUpdate): Nowe dane.
        db (Session): Sesja bazy danych.

    Returns:
        models.Team: Zaktualizowany obiekt drużyny.

    Raises:
        HTTPException(404): Jeśli drużyna nie istnieje.
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
    Usuwa drużynę z bazy danych.

    Args:
        team_id (int): ID drużyny do usunięcia.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Komunikat potwierdzający usunięcie.

    Raises:
        HTTPException(404): Jeśli drużyna nie istnieje.
    """
    db_team = db.query(models.Team).filter(models.Team.id == team_id).first()
    if not db_team:
        raise HTTPException(status_code=404, detail="Team not found")

    db.delete(db_team)
    db.commit()
    return {"message": "Team deleted successfully"}