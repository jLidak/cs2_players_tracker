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
            r_third = participation.rounds_third_place if participation else 0  # Pobieramy rundy 3rd

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

                return damped_diff * 100 * weight  * phase_rounds**(1/3)

            tournament_points_sum = 0.0
            starts_in_semis = participation.starts_in_semis if participation else False

            # Obliczenia dla każdej fazy
            tournament_points_sum += calc_phase_points(perf.rating_group, tour.weight_group, r_group)

            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                group_w = tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group
                remaining_for_playoff = 1.0 - group_w
                semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else remaining_for_playoff / 2
                final_w = tour.weight_final_override if tour.weight_final_override is not None else remaining_for_playoff / 2

                tournament_points_sum += calc_phase_points(perf.rating_group, group_w, r_group)
                tournament_points_sum += calc_phase_points(perf.rating_semis, semis_w, r_semis, bonus=0.15)
                tournament_points_sum += calc_phase_points(perf.rating_final, final_w, r_final, bonus=0.15)

                # Logika Standardowa (Bracket 8, Bracket 16, i Bracket 6 bez skipa)
            else:
                tournament_points_sum += calc_phase_points(perf.rating_quarters, tour.weight_quarters, r_quarters,bonus=0.15)
                tournament_points_sum += calc_phase_points(perf.rating_semis, tour.weight_semis, r_semis, bonus=0.15)
                tournament_points_sum += calc_phase_points(perf.rating_final, tour.weight_final, r_final, bonus=0.15)

            if tour.has_third_place:
                tournament_points_sum += calc_phase_points(
                    perf.rating_third_place,
                    tour.weight_third_place,
                    r_third,
                    bonus=0.15
                )

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


@router.post("/api/custom-ranking/", response_model=List[schemas.RankingEntry])
def calculate_custom_ranking(params: schemas.CustomRankingParams, db: Session = Depends(get_db)):
    players = db.query(models.Player).options(
        joinedload(models.Player.team),
        joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament),
    ).all()

    ranking = []

    for player in players:
        total_points = 0.0

        for perf in player.tournament_performances:
            tour = perf.tournament
            tid = tour.id

            # --- USTALANIE WAG ---
            # Sprawdzamy czy użytkownik przesłał nadpisanie dla TEGO KONKRETNEGO turnieju
            user_weights = params.tournament_overrides.get(tid)
            w_group = tour.weight_group
            w_qf = tour.weight_quarters
            w_sf = tour.weight_semis
            w_final = tour.weight_final
            w_3rd = tour.weight_third_place  # Domyślna waga 3rd z bazy

            if user_weights:
                # Używamy wag od użytkownika
                w_group = user_weights.weight_group
                w_qf = user_weights.weight_qf
                w_sf = user_weights.weight_sf
                w_final = user_weights.weight_final
                w_3rd = user_weights.weight_third_place  # Nadpisana waga 3rd

                # Dla Bracket 6 (start w semis), jeśli użytkownik nadpisał wagi,
                # zakładamy, że to co wpisał w polu SF i Final ma być użyte.
                w_sf_bracket6 = w_sf
                w_final_bracket6 = w_final
            else:
                # Używamy wag z bazy danych (Domyślne)
                w_group = tour.weight_group
                w_qf = tour.weight_quarters
                w_sf = tour.weight_semis
                w_final = tour.weight_final

                # Logika override z bazy dla Bracket 6
                w_group_ov = tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group
                w_sf_ov = tour.weight_semis_override if tour.weight_semis_override is not None else (1.0 - w_group) / 2
                w_final_ov = tour.weight_final_override if tour.weight_final_override is not None else (1.0 - w_group) / 2

            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0
            r_third = participation.rounds_third_place if participation else 0

            def calc_points(rating, weight, phase_rounds, bonus):
                if rating is None or rating == 0 or phase_rounds == 0:
                    return 0.0

                effective_rating = rating + bonus
                diff = (effective_rating - 1.0) * 100

                exp_div = params.rating_exponent_divisor if params.rating_exponent_divisor != 0 else 1.0
                exponent = 1 / exp_div
                damped_diff = math.copysign(abs(diff) ** exponent, diff)

                # Pierwiastek
                root_val = params.rounds_root if params.rounds_root != 0 else 1.0
                rounds_factor = phase_rounds ** (1 / root_val)

                return damped_diff * params.base_multiplier * weight * rounds_factor

            points_sum = 0.0
            starts_in_semis = participation.starts_in_semis if participation else False

            # Grupa
            points_sum += calc_points(perf.rating_group, w_group, r_group, 0.0)

            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                points_sum += calc_points(perf.rating_semis, w_sf_bracket6, r_semis, params.bonus_sf)
                points_sum += calc_points(perf.rating_final, w_final_bracket6, r_final, params.bonus_final)
            else:
                points_sum += calc_points(perf.rating_quarters, w_qf, r_quarters, params.bonus_qf)
                points_sum += calc_points(perf.rating_semis, w_sf, r_semis, params.bonus_sf)
                points_sum += calc_points(perf.rating_final, w_final, r_final, params.bonus_final)

            # --- Mecz o 3 miejsce ---
            if tour.has_third_place:
                points_sum += calc_points(
                    perf.rating_third_place,
                    w_3rd,  # Używamy wagi (z bazy lub customowej)
                    r_third,
                    params.bonus_third_place
                )

            total_points += max(0.0, points_sum) * tour.weight

        ranking.append({
            "player_id": player.id,
            "nickname": player.nickname,
            "team_name": player.team.name if player.team else "No Team",
            "total_points": round(total_points),
            "photo_url": player.photo_url
        })

    ranking.sort(key=lambda x: x["total_points"], reverse=True)
    return ranking