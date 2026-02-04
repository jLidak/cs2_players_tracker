"""
Moduł obsługujący endpointy API dla Meczów (Matches) oraz Ocen Graczy (Ratings).
Zawiera logikę CRUD dla meczów oraz dodawanie ocen za występ.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db

router = APIRouter(
    tags=["Matches"]
)


# --- Match CRUD ---

@router.post("/api/matches/", response_model=schemas.Match)
def create_match(match: schemas.MatchCreate, db: Session = Depends(get_db)) -> models.Match:
    """
    Tworzy nowy mecz.

    Args:
        match (schemas.MatchCreate): Dane meczu.
        db (Session): Sesja bazy danych.

    Returns:
        models.Match: Utworzony obiekt meczu.
    """
    db_match = models.Match(**match.model_dump())
    db.add(db_match)
    db.commit()
    db.refresh(db_match)
    return db_match


@router.get("/api/matches/", response_model=List[schemas.MatchWithDetails])
def get_matches(db: Session = Depends(get_db)) -> List[models.Match]:
    """
    Pobiera listę wszystkich meczów wraz ze szczegółami (turniej, drużyny, mapy).

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        List[models.Match]: Lista meczów z załadowanymi relacjami.
    """
    return db.query(models.Match).options(
        joinedload(models.Match.tournament),
        joinedload(models.Match.team1),
        joinedload(models.Match.team2),
        joinedload(models.Match.maps)
    ).all()


@router.get("/api/matches/{match_id}", response_model=schemas.MatchWithDetails)
def get_match(match_id: int, db: Session = Depends(get_db)) -> models.Match:
    """
    Pobiera szczegóły pojedynczego meczu.

    Args:
        match_id (int): ID meczu.
        db (Session): Sesja bazy danych.

    Returns:
        models.Match: Obiekt meczu.

    Raises:
        HTTPException(404): Jeśli mecz nie istnieje.
    """
    match = db.query(models.Match).options(
        joinedload(models.Match.tournament),
        joinedload(models.Match.team1),
        joinedload(models.Match.team2),
        joinedload(models.Match.maps)
    ).filter(models.Match.id == match_id).first()

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match


@router.put("/api/matches/{match_id}", response_model=schemas.Match)
def update_match(match_id: int, match: schemas.MatchUpdate, db: Session = Depends(get_db)) -> models.Match:
    """
    Aktualizuje dane meczu.

    Args:
        match_id (int): ID meczu.
        match (schemas.MatchUpdate): Nowe dane.
        db (Session): Sesja bazy danych.

    Returns:
        models.Match: Zaktualizowany mecz.
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
    Usuwa mecz z bazy danych.

    Args:
        match_id (int): ID meczu.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Potwierdzenie usunięcia.
    """
    db_match = db.query(models.Match).filter(models.Match.id == match_id).first()
    if not db_match:
        raise HTTPException(status_code=404, detail="Match not found")

    db.delete(db_match)
    db.commit()
    return {"message": "Match deleted successfully"}


# --- Player Ratings ---

@router.post("/api/player_ratings/", response_model=schemas.PlayerRating)
def create_player_rating(rating: schemas.PlayerRatingCreate, db: Session = Depends(get_db)) -> models.PlayerRating:
    """
    Dodaje lub aktualizuje ocenę gracza za dany mecz.

    Args:
        rating (schemas.PlayerRatingCreate): Dane oceny (mecz, gracz, wartość).
        db (Session): Sesja bazy danych.

    Returns:
        models.PlayerRating: Utworzona lub zaktualizowana ocena.

    Raises:
        HTTPException(404): Jeśli mecz lub gracz nie istnieje.
    """
    existing_rating = db.query(models.PlayerRating).filter(
        models.PlayerRating.match_id == rating.match_id,
        models.PlayerRating.player_id == rating.player_id
    ).first()

    if existing_rating:
        existing_rating.rating = rating.rating
        db.commit()
        db.refresh(existing_rating)
        return existing_rating

    match = db.query(models.Match).filter(models.Match.id == rating.match_id).first()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    player = db.query(models.Player).filter(models.Player.id == rating.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    db_rating = models.PlayerRating(**rating.model_dump())
    db.add(db_rating)
    db.commit()
    db.refresh(db_rating)
    return db_rating