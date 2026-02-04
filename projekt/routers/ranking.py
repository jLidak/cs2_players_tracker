"""
Moduł odpowiedzialny za logikę rankingu.
Oblicza punkty na podstawie wyników turniejowych i wag turniejów.
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import models
import schemas
from database import get_db

router = APIRouter(
    tags=["Ranking"]
)


@router.get("/api/ranking/", response_model=List[schemas.RankingEntry])
def get_ranking(db: Session = Depends(get_db)) -> List[Dict[str, Any]]:
    """
    Generuje globalny ranking graczy.

    Algorytm:
    1. Pobiera wszystkich graczy.
    2. Dla każdego gracza pobiera punkty zdobyte w turniejach.
    3. Mnoży punkty przez wagę danego turnieju (np. Major ma wagę = 1.0).
    4. Sumuje wyniki i sortuje listę malejąco.

    Args:
        db (Session): Sesja bazy danych.

    Returns:
        List[Dict[str, Any]]: Posortowana lista słowników zawierających dane gracza i jego całkowity wynik.
    """
    # Pobieramy podstawowe dane graczy i ich drużyn (Left Join)
    ranking_data = db.query(
        models.Player.id,
        models.Player.nickname,
        models.Player.photo_url,
        models.Team.name.label("team_name")
    ).outerjoin(models.Team, models.Player.team_id == models.Team.id).all()

    ranking = []
    for player_id, nickname, photo_url, team_name in ranking_data:
        # Pobieramy punkty gracza ze wszystkich turniejów
        points = db.query(models.PlayerRankingPoint).filter(
            models.PlayerRankingPoint.player_id == player_id
        ).all()

        total = 0.0
        for point in points:
            # Znajdujemy wagę turnieju, aby przemnożyć punkty
            tournament = db.query(models.Tournament).filter(
                models.Tournament.id == point.tournament_id
            ).first()
            if tournament:
                total += point.points * tournament.weight

        ranking.append({
            "player_id": player_id,
            "nickname": nickname,
            "team_name": team_name,
            "total_points": total,
            "photo_url": photo_url
        })

    # Sortowanie listy: gracze z największą liczbą punktów na górze
    ranking.sort(key=lambda x: x["total_points"], reverse=True)
    return ranking


@router.post("/api/ranking_points/", response_model=schemas.PlayerRankingPoint)
def create_ranking_point(points: schemas.PlayerRankingPointCreate,
                         db: Session = Depends(get_db)) -> models.PlayerRankingPoint:
    """
    Przyznaje lub aktualizuje punkty rankingowe graczowi za konkretny turniej.
    Jeśli wpis dla pary (gracz, turniej) już istnieje, aktualizuje liczbę punktów.

    Args:
        points (schemas.PlayerRankingPointCreate): Dane punktowe (ID gracza, ID turnieju, punkty).
        db (Session): Sesja bazy danych.

    Returns:
        models.PlayerRankingPoint: Utworzony lub zaktualizowany obiekt punktów.

    Raises:
        HTTPException(404): Jeśli gracz lub turniej nie istnieje w bazie.
    """
    # Sprawdzenie czy punkty już istnieją (Update zamiast Insert)
    existing_points = db.query(models.PlayerRankingPoint).filter(
        models.PlayerRankingPoint.tournament_id == points.tournament_id,
        models.PlayerRankingPoint.player_id == points.player_id
    ).first()

    if existing_points:
        existing_points.points = points.points
        db.commit()
        db.refresh(existing_points)
        return existing_points

    # Walidacja istnienia gracza
    player = db.query(models.Player).filter(models.Player.id == points.player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Walidacja istnienia turnieju
    tournament = db.query(models.Tournament).filter(models.Tournament.id == points.tournament_id).first()
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")

    # Tworzenie nowego wpisu
    db_points = models.PlayerRankingPoint(**points.model_dump())
    db.add(db_points)
    db.commit()
    db.refresh(db_points)
    return db_points