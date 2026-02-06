from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db

router = APIRouter(tags=["Ranking"])


@router.get("/api/ranking/", response_model=List[schemas.RankingEntry])
def get_ranking(db: Session = Depends(get_db)):
    players = db.query(models.Player).options(
        joinedload(models.Player.team),
        joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament),
    ).all()

    ranking = []

    for player in players:
        total_points = 0.0

        for perf in player.tournament_performances:
            tour = perf.tournament

            starts_in_semis = False
            if tour.bracket_type == "Bracket 6 teams" and player.team_id:
                participation = db.query(models.TournamentTeam).filter(
                    models.TournamentTeam.tournament_id == tour.id,
                    models.TournamentTeam.team_id == player.team_id
                ).first()
                if participation and participation.starts_in_semis:
                    starts_in_semis = True

            tournament_points = 0.0

            # 1. FAZA GRUPOWA (dawniej Overall)
            if perf.rating_group and perf.rating_group > 1.0:
                tournament_points += (perf.rating_group - 1.0) * 100 * tour.weight_group

            if starts_in_semis:
                # Ścieżka skrócona (Bracket 6)
                semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else (
                                                                                                                1.0 - tour.weight_group) / 2
                final_w = tour.weight_final_override if tour.weight_final_override is not None else (
                                                                                                                1.0 - tour.weight_group) / 2

                if perf.rating_semis and perf.rating_semis > 1.0:
                    tournament_points += (perf.rating_semis - 1.0) * 100 * semis_w
                if perf.rating_final and perf.rating_final > 1.0:
                    tournament_points += (perf.rating_final - 1.0) * 100 * final_w

            else:
                # Ścieżka standardowa
                if perf.rating_quarters and perf.rating_quarters > 1.0:
                    tournament_points += (perf.rating_quarters - 1.0) * 100 * tour.weight_quarters
                if perf.rating_semis and perf.rating_semis > 1.0:
                    tournament_points += (perf.rating_semis - 1.0) * 100 * tour.weight_semis
                if perf.rating_final and perf.rating_final > 1.0:
                    tournament_points += (perf.rating_final - 1.0) * 100 * tour.weight_final

            total_points += tournament_points * tour.weight

        ranking.append({
            "player_id": player.id,
            "nickname": player.nickname,
            "team_name": player.team.name if player.team else "No Team",
            "total_points": round(total_points, 2),
            "photo_url": player.photo_url
        })

    ranking.sort(key=lambda x: x["total_points"], reverse=True)
    return ranking