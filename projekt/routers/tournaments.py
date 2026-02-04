"""
Moduł obsługujący endpointy API dla Turniejów.
"""
from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

router = APIRouter(
    prefix="/api/tournaments",
    tags=["Tournaments"]
)


@router.post("/", response_model=schemas.Tournament)
def create_tournament(tournament: schemas.TournamentCreate, db: Session = Depends(get_db)) -> models.Tournament:
    """
    Tworzy nowy turniej.

    Args:
        tournament (schemas.TournamentCreate): Dane turnieju.
        db (Session): Sesja bazy danych.

    Returns:
        models.Tournament: Utworzony turniej.
    """
    db_tournament = models.Tournament(**tournament.model_dump())
    db.add(db_tournament)
    db.commit()
    db.refresh(db_tournament)
    return db_tournament


@router.get("/", response_model=List[schemas.Tournament])
def get_tournaments(db: Session = Depends(get_db)) -> List[models.Tournament]:
    """
    Pobiera wszystkie turnieje.

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        List[models.Tournament]: Lista turniejów.
    """
    return db.query(models.Tournament).all()


@router.put("/{tournament_id}", response_model=schemas.Tournament)
def update_tournament(tournament_id: int, tournament: schemas.TournamentUpdate,
                      db: Session = Depends(get_db)) -> models.Tournament:
    """
    Aktualizuje dane turnieju (np. wagę punktową).

    Args:
        tournament_id (int): ID turnieju.
        tournament (schemas.TournamentUpdate): Nowe dane.
        db (Session): Sesja bazy danych.

    Returns:
        models.Tournament: Zaktualizowany turniej.
    """
    db_tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    update_data = tournament.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_tournament, key, value)

    db.commit()
    db.refresh(db_tournament)
    return db_tournament


@router.delete("/{tournament_id}")
def delete_tournament(tournament_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Usuwa turniej z bazy.

    Args:
        tournament_id (int): ID turnieju.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Potwierdzenie usunięcia.
    """
    db_tournament = db.query(models.Tournament).filter(models.Tournament.id == tournament_id).first()
    if not db_tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    db.delete(db_tournament)
    db.commit()
    return {"message": "Tournament deleted successfully"}