from typing import List
import math
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

            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0

            # Funkcja skalująca rundy (bazowe 27, potem co 9 rund o 40% mniej)
            def get_scaled_rounds(rounds):
                if rounds <= 0: return 0
                base_limit = 27
                step = 9
                decay = 0.6
                remaining = rounds
                scaled = 0
                current_multiplier = 1.0

                # Próg bazowy
                taken = min(remaining, base_limit)
                scaled += taken * current_multiplier
                remaining -= taken

                # Progi malejące
                while remaining > 0:
                    current_multiplier *= decay
                    taken = min(remaining, step)
                    scaled += taken * current_multiplier
                    remaining -= taken
                return scaled

            def calc_phase_points(rating, weight, phase_rounds, bonus=0.0):
                if rating is None or rating == 0 or phase_rounds == 0:
                    return 0.0

                effective_rating = rating + bonus

                # 1. Obliczamy różnicę od 1.0 i zamieniamy na jednostki (np. 1.60 -> 60)
                diff = (effective_rating - 1.0) * 100

                # 2. Pierwiastkujemy różnicę wykładnikiem 0.90 (Twoje 1.1 stopnia)
                # Obsługujemy ujemne różnice (rating < 1.0) przez math.copysign
                exponent = 1 / 1.1
                damped_diff = math.copysign(abs(diff) ** exponent, diff)

                # 3. Skalujemy rundy
                scaled_rounds = get_scaled_rounds(phase_rounds)

                # 4. Formuła końcowa: damped_diff * waga * (rundy / 27)
                # Mnożnik 10 zostaje, aby przywrócić skalę setkową
                return damped_diff * 10 * weight  * phase_rounds**(1/3)

            tournament_points_sum = 0.0
            starts_in_semis = participation.starts_in_semis if participation else False

            # Obliczenia dla każdej fazy
            tournament_points_sum += calc_phase_points(perf.rating_group, tour.weight_group, r_group)

            if starts_in_semis:
                semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else (
                                                                                                                1.0 - tour.weight_group) / 2
                final_w = tour.weight_final_override if tour.weight_final_override is not None else (
                                                                                                                1.0 - tour.weight_group) / 2
                tournament_points_sum += calc_phase_points(perf.rating_semis, semis_w, r_semis, bonus=0.2)
                tournament_points_sum += calc_phase_points(perf.rating_final, final_w, r_final, bonus=0.3)
            else:
                tournament_points_sum += calc_phase_points(perf.rating_quarters, tour.weight_quarters, r_quarters,
                                                           bonus=0.1)
                tournament_points_sum += calc_phase_points(perf.rating_semis, tour.weight_semis, r_semis, bonus=0.2)
                tournament_points_sum += calc_phase_points(perf.rating_final, tour.weight_final, r_final, bonus=0.3)

            total_points += max(0.0, tournament_points_sum) * tour.weight

        ranking.append({
            "player_id": player.id,
            "nickname": player.nickname,
            "team_name": player.team.name if player.team else "No Team",
            "total_points": round(total_points),
            "photo_url": player.photo_url
        })

    ranking.sort(key=lambda x: x["total_points"], reverse=True)
    return ranking