"""
Moduł obsługujący endpointy API dla Graczy (Players).
Zawiera CRUD dla graczy oraz funkcjonalność wyszukiwania (Search).
"""
from typing import List, Dict
import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db


router = APIRouter(
    tags=["Players"]
)

# --- CRUD ---

# --- NOWY ENDPOINT: DODAWANIE GRACZA ---
@router.post("/api/players/", response_model=schemas.Player)
def create_player(player: schemas.PlayerCreate, db: Session = Depends(get_db)):
    """Tworzy nowego zawodnika."""
    # Sprawdź czy nick jest zajęty (opcjonalne, ale dobra praktyka)
    existing_player = db.query(models.Player).filter(models.Player.nickname == player.nickname).first()
    if existing_player:
        raise HTTPException(status_code=400, detail="Zawodnik o takim nicku już istnieje.")

    # Sprawdź czy drużyna istnieje (jeśli podano team_id)
    if player.team_id:
        team = db.query(models.Team).filter(models.Team.id == player.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Wybrana drużyna nie istnieje.")

    new_player = models.Player(**player.model_dump())
    db.add(new_player)
    db.commit()
    db.refresh(new_player)
    return new_player


@router.get("/api/players/", response_model=List[schemas.PlayerWithTeam])
def get_players(db: Session = Depends(get_db)) -> List[models.Player]:
    """
    Pobiera listę wszystkich graczy zarejestrowanych w systemie.
    Do każdego gracza dołączane są dane o jego drużynie (eager loading).

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        List[models.Player]: Lista obiektów graczy.
    """
    return db.query(models.Player).options(joinedload(models.Player.team)).all()


@router.get("/api/players/{player_id}", response_model=schemas.PlayerWithTeam)
def get_player(player_id: int, db: Session = Depends(get_db)) -> models.Player:
    """
    Pobiera szczegółowe dane pojedynczego gracza na podstawie ID.

    Args:
        player_id (int): Unikalny identyfikator gracza.
        db (Session): Sesja bazy danych.

    Returns:
        models.Player: Znaleziony obiekt gracza.

    Raises:
        HTTPException(404): Jeśli gracz o podanym ID nie istnieje.
    """
    player = db.query(models.Player).options(joinedload(models.Player.team)).filter(models.Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.put("/api/players/{player_id}", response_model=schemas.Player)
def update_player(player_id: int, player: schemas.PlayerUpdate, db: Session = Depends(get_db)) -> models.Player:
    """
    Aktualizuje dane istniejącego gracza.
    Pozwala na zmianę nicku, zdjęcia lub drużyny.

    Args:
        player_id (int): ID gracza do edycji.
        player (schemas.PlayerUpdate): Model danych z polami do aktualizacji (opcjonalne).
        db (Session): Sesja bazy danych.

    Returns:
        models.Player: Zaktualizowany obiekt gracza.

    Raises:
        HTTPException(404): Jeśli gracz nie istnieje lub nowa drużyna nie istnieje.
    """
    db_player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Walidacja teamu przy update
    if player.team_id is not None:
        team = db.query(models.Team).filter(models.Team.id == player.team_id).first()
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

    update_data = player.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_player, key, value)

    db.commit()
    db.refresh(db_player)
    return db_player


@router.delete("/api/players/{player_id}")
def delete_player(player_id: int, db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Usuwa gracza z systemu.

    Args:
        player_id (int): ID gracza do usunięcia.
        db (Session): Sesja bazy danych.

    Returns:
        Dict[str, str]: Słownik z komunikatem potwierdzającym usunięcie.

    Raises:
        HTTPException(404): Jeśli gracz o podanym ID nie istnieje.
    """
    db_player = db.query(models.Player).filter(models.Player.id == player_id).first()
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not found")

    db.delete(db_player)
    db.commit()
    return {"message": "Player deleted successfully"}

# --- Search ---

@router.get("/api/search/players/", response_model=List[schemas.PlayerWithTeam])
def search_players(query: str, db: Session = Depends(get_db)) -> List[models.Player]:
    """
    Wyszukuje graczy na podstawie wyrażenia regularnego (Regex).
    Filtrowanie odbywa się po stronie Pythona.

    Args:
        query (str): Wzorzec regex do przeszukania nicków (np. "^s1").
        db (Session): Sesja bazy danych.

    Returns:
        List[models.Player]: Lista graczy, których nick pasuje do wzorca.
    """
    all_players = db.query(models.Player).options(joinedload(models.Player.team)).all()
    try:
        pattern = re.compile(query, re.IGNORECASE)
        filtered_players = [p for p in all_players if pattern.search(p.nickname)]
        return filtered_players
    except re.error:
        # W przypadku błędnego regexa zwracamy pustą listę
        return []