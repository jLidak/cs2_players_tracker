from typing import List, Optional
import math
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db

router = APIRouter(tags=["Ranking"])

# --- STAŁE DO OBLICZEŃ (Konfiguracja) ---
RANKING_BASE_MULTIPLIER = 50.0  # Podstawowy mnożnik punktów
RANKING_ROUNDS_ROOT = 2.66  # Stopień pierwiastka dla rund
RANKING_RATING_EXPONENT_DIV = 1.0  # Dzielnik wykładnika ratingu
RANKING_BONUS = 0.15  # Bonus za fazy pucharowe (QF, SF, Final, 3rd)


@router.get("/api/ranking/", response_model=List[schemas.RankingEntry])
def get_ranking(db: Session = Depends(get_db), tournament_id: Optional[int] = None):
    players = db.query(models.Player).options(
        joinedload(models.Player.team),
        joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament),
    ).all()

    ranking = []

    for player in players:
        total_points = 0.0
        player_details = []
        has_participated_in_target_tournament = False

        for perf in player.tournament_performances:
            if tournament_id is not None:
                if perf.tournament_id != tournament_id:
                    continue
                else:
                    has_participated_in_target_tournament = True

            tour = perf.tournament

            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0
            r_third = participation.rounds_third_place if participation else 0
            starts_in_semis = participation.starts_in_semis if participation else False

            current_tour_phases = []
            tournament_points_sum = 0.0

            def process_phase(phase_name, rating, weight, phase_rounds, bonus=0.0):
                if rating is None or rating == 0 or phase_rounds == 0:
                    current_tour_phases.append({
                        "phase_name": phase_name,
                        "rating": rating if rating else 0.0,
                        "rounds": phase_rounds,
                        "weight": weight,
                        "points": 0.0,
                        "bonus": bonus
                    })
                    return 0.0

                effective_rating = rating + bonus
                diff = (effective_rating - 1.0) * 100
                exponent = 1 / RANKING_RATING_EXPONENT_DIV
                damped_diff = math.copysign(abs(diff) ** exponent, diff)
                rounds_factor = phase_rounds ** (1 / RANKING_ROUNDS_ROOT)
                points = damped_diff * RANKING_BASE_MULTIPLIER * weight * rounds_factor

                current_tour_phases.append({
                    "phase_name": phase_name,
                    "rating": round(effective_rating, 2),
                    "rounds": phase_rounds,
                    "weight": weight,
                    "points": round(points, 2),
                    "bonus": bonus
                })

                return points

            # --- OBLICZENIA FAZ ---
            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                w_group = tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group
                tournament_points_sum += process_phase("Group (Override)", perf.rating_group, w_group, r_group)
            else:
                tournament_points_sum += process_phase("Group Stage", perf.rating_group, tour.weight_group, r_group)

            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                remaining = 1.0 - (
                    tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group)
                w_semi = tour.weight_semis_override if tour.weight_semis_override is not None else remaining / 2
                w_final = tour.weight_final_override if tour.weight_final_override is not None else remaining / 2

                tournament_points_sum += process_phase("Semi-Final", perf.rating_semis, w_semi, r_semis,
                                                       bonus=RANKING_BONUS)
                tournament_points_sum += process_phase("Final", perf.rating_final, w_final, r_final,
                                                       bonus=RANKING_BONUS)
            else:
                tournament_points_sum += process_phase("Quarter-Final", perf.rating_quarters, tour.weight_quarters,
                                                       r_quarters, bonus=RANKING_BONUS)
                tournament_points_sum += process_phase("Semi-Final", perf.rating_semis, tour.weight_semis, r_semis,
                                                       bonus=RANKING_BONUS)
                tournament_points_sum += process_phase("Final", perf.rating_final, tour.weight_final, r_final,
                                                       bonus=RANKING_BONUS)

            if tour.has_third_place:
                tournament_points_sum += process_phase("3rd Place", perf.rating_third_place, tour.weight_third_place,
                                                       r_third, bonus=RANKING_BONUS)

            final_tour_points = max(0.0, tournament_points_sum) * tour.weight
            total_points += final_tour_points

            player_details.append({
                "tournament_name": tour.name,
                "tournament_weight": tour.weight,
                "phases": current_tour_phases,
                "total_tournament_points": round(final_tour_points, 2)
            })

        should_add = False
        if tournament_id is None:
            if total_points > 0:
                should_add = True
        else:
            if has_participated_in_target_tournament:
                should_add = True

        final_points_int = int(round(total_points))
        if should_add:
            ranking.append(schemas.RankingEntry(
                player_id=player.id,
                nickname=player.nickname,
                team_name=player.team.name if player.team else "No Team",
                total_points=final_points_int,
                photo_url=player.photo_url,
                details=player_details
            ))

    ranking.sort(key=lambda x: x.total_points, reverse=True)
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
        has_participated_in_target = False

        for perf in player.tournament_performances:
            tour = perf.tournament
            tid = tour.id

            if params.tournament_id is not None:
                if tid != params.tournament_id:
                    continue
                else:
                    has_participated_in_target = True

            user_weights = params.tournament_overrides.get(tid)
            w_group = tour.weight_group
            w_qf = tour.weight_quarters
            w_sf = tour.weight_semis
            w_final = tour.weight_final
            w_3rd = tour.weight_third_place
            t_weight = tour.weight  # Domyślna waga z bazy

            w_group_ov = tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group
            w_sf_ov = tour.weight_semis_override if tour.weight_semis_override is not None else (1.0 - w_group) / 2
            w_final_ov = tour.weight_final_override if tour.weight_final_override is not None else (1.0 - w_group) / 2

            if user_weights:
                if user_weights.tournament_weight is not None:
                    t_weight = user_weights.tournament_weight

                w_group = user_weights.weight_group
                w_qf = user_weights.weight_qf
                w_sf = user_weights.weight_sf
                w_final = user_weights.weight_final
                w_3rd = user_weights.weight_third_place

                if user_weights.weight_group_override is not None:
                    w_group_ov = user_weights.weight_group_override
                if user_weights.weight_semis_override is not None:
                    w_sf_ov = user_weights.weight_semis_override
                if user_weights.weight_final_override is not None:
                    w_final_ov = user_weights.weight_final_override

            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0
            r_third = participation.rounds_third_place if participation else 0
            starts_in_semis = participation.starts_in_semis if participation else False

            def calc_points(rating, weight, phase_rounds, bonus):
                if rating is None or rating == 0 or phase_rounds == 0:
                    return 0.0

                effective_rating = rating + bonus
                diff = (effective_rating - 1.0) * 100
                exp_div = params.rating_exponent_divisor if params.rating_exponent_divisor != 0 else 1.0
                exponent = 1 / exp_div
                damped_diff = math.copysign(abs(diff) ** exponent, diff)
                root_val = params.rounds_root if params.rounds_root != 0 else 1.0
                rounds_factor = phase_rounds ** (1 / root_val)

                return damped_diff * params.base_multiplier * weight * rounds_factor

            points_sum = 0.0

            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                points_sum += calc_points(perf.rating_group, w_group_ov, r_group, 0.0)
                points_sum += calc_points(perf.rating_semis, w_sf_ov, r_semis, params.bonus_sf)
                points_sum += calc_points(perf.rating_final, w_final_ov, r_final, params.bonus_final)
            else:
                points_sum += calc_points(perf.rating_group, w_group, r_group, 0.0)
                points_sum += calc_points(perf.rating_quarters, w_qf, r_quarters, params.bonus_qf)
                points_sum += calc_points(perf.rating_semis, w_sf, r_semis, params.bonus_sf)
                points_sum += calc_points(perf.rating_final, w_final, r_final, params.bonus_final)

            if tour.has_third_place:
                points_sum += calc_points(perf.rating_third_place, w_3rd, r_third, params.bonus_third_place)

            total_points += max(0.0, points_sum) * t_weight

        should_add = False
        if params.tournament_id is None:
            should_add = True
        else:
            if has_participated_in_target:
                should_add = True

        if should_add:
            ranking.append(schemas.RankingEntry(
                player_id=player.id,
                nickname=player.nickname,
                team_name=player.team.name if player.team else "No Team",
                total_points=int(round(total_points)),
                photo_url=player.photo_url,
                details=[]
            ))

    ranking.sort(key=lambda x: x.total_points, reverse=True)
    return ranking