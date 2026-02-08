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

            if starts_in_semis:
                semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else (1.0 - tour.weight_group) / 2
                final_w = tour.weight_final_override if tour.weight_final_override is not None else (1.0 - tour.weight_group) / 2
                tournament_points_sum += calc_phase_points(perf.rating_semis, semis_w, r_semis, bonus=0.15)
                tournament_points_sum += calc_phase_points(perf.rating_final, final_w, r_final, bonus=0.15)
            else:
                tournament_points_sum += calc_phase_points(perf.rating_quarters, tour.weight_quarters, r_quarters,
                                                           bonus=0.15)
                tournament_points_sum += calc_phase_points(perf.rating_semis, tour.weight_semis, r_semis, bonus=0.15)
                tournament_points_sum += calc_phase_points(perf.rating_final, tour.weight_final, r_final, bonus=0.15)

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
    """
    Oblicza ranking na podstawie parametrów przesłanych przez użytkownika.
    Nie zmienia nic w bazie danych.
    """
    players = db.query(models.Player).options(
        joinedload(models.Player.team),
        joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament),
    ).all()

    ranking = []

    for player in players:
        total_points = 0.0

        for perf in player.tournament_performances:
            tour = perf.tournament

            # Ustalanie wag faz (z bazy lub nadpisane przez użytkownika)
            w_group = params.weight_group if params.override_weights else tour.weight_group
            w_qf = params.weight_qf if params.override_weights else tour.weight_quarters
            w_sf = params.weight_sf if params.override_weights else tour.weight_semis
            w_final = params.weight_final if params.override_weights else tour.weight_final

            # Dla bracket 6 teams
            w_sf_bracket6 = tour.weight_semis_override if tour.weight_semis_override is not None else (
                                                                                                                  1.0 - w_group) / 2
            w_final_bracket6 = tour.weight_final_override if tour.weight_final_override is not None else (
                                                                                                                     1.0 - w_group) / 2
            # Jeśli nadpisujemy wagi globalnie, musimy też dostosować bracket 6
            if params.override_weights:
                remaining = 1.0 - w_group
                w_sf_bracket6 = remaining / 2
                w_final_bracket6 = remaining / 2

            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0

            # --- DYNAMICZNA FUNKCJA PUNKTACJI ---
            def calc_points(rating, weight, phase_rounds, bonus):
                if rating is None or rating == 0 or phase_rounds == 0:
                    return 0.0

                effective_rating = rating + bonus

                # 1. Różnica
                diff = (effective_rating - 1.0) * 100

                # 2. Wykładnik z parametrów (zabezpieczenie przed dzieleniem przez 0)
                exp_div = params.rating_exponent_divisor if params.rating_exponent_divisor != 0 else 1.0
                exponent = 1 / exp_div

                damped_diff = math.copysign(abs(diff) ** exponent, diff)

                # 3. Pierwiastek rund z parametrów
                root_val = params.rounds_root if params.rounds_root != 0 else 1.0
                rounds_factor = phase_rounds ** (1 / root_val)

                # 4. Finalne obliczenie z parametrami
                return damped_diff * params.base_multiplier * weight * rounds_factor

            points_sum = 0.0
            starts_in_semis = participation.starts_in_semis if participation else False

            # Grupa
            points_sum += calc_points(perf.rating_group, w_group, r_group, 0.0)

            if starts_in_semis:
                points_sum += calc_points(perf.rating_semis, w_sf_bracket6, r_semis, params.bonus_sf)
                points_sum += calc_points(perf.rating_final, w_final_bracket6, r_final, params.bonus_final)
            else:
                points_sum += calc_points(perf.rating_quarters, w_qf, r_quarters, params.bonus_qf)
                points_sum += calc_points(perf.rating_semis, w_sf, r_semis, params.bonus_sf)
                points_sum += calc_points(perf.rating_final, w_final, r_final, params.bonus_final)

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