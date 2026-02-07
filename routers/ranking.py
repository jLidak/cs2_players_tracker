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

            # 1. Pobieramy dane o udziale drużyny, aby znać liczbę rund
            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            # Pobieramy rundy (domyślnie 0 jeśli brak danych)
            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0

            # Funkcja pomocnicza do obliczania punktów za konkretną fazę z użyciem PIERWIASTKA
            def calc_phase_points(rating, weight, phase_rounds, bonus=0.0):
                if rating is None or rating == 0 or phase_rounds == 0:
                    return 0.0

                # Dodajemy bonusy fazowe (QF +0.1, SF +0.2, Final +0.3)
                if 0.01 < rating < 5.0:
                    effective_rating = rating + bonus
                else:
                    effective_rating = rating

                # NOWA LOGIKA (Poprawka nr 1):
                # (Rating_efektywny - 1.0) * 1000 * waga_fazy * sqrt(rundy_fazy)
                # Używamy mnożnika 1000 zamiast 10000, aby wyniki były czytelne przy sqrt
                return (effective_rating - 1.0) * 1000 * weight * phase_rounds**(1/2)

            tournament_points_sum = 0.0

            # Sprawdzamy czy drużyna zaczynała od półfinału (Bracket 6)
            starts_in_semis = participation.starts_in_semis if participation else False

            # --- OBLICZENIA DLA KAŻDEJ FAZY ---

            # GS (brak bonusu)
            tournament_points_sum += calc_phase_points(perf.rating_group, tour.weight_group, r_group)

            if starts_in_semis:
                # Ścieżka skrócona (Bracket 6)
                semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else (1.0 - tour.weight_group) / 2
                final_w = tour.weight_final_override if tour.weight_final_override is not None else (1.0 - tour.weight_group) / 2

                tournament_points_sum += calc_phase_points(perf.rating_semis, semis_w, r_semis, bonus=0.2)
                tournament_points_sum += calc_phase_points(perf.rating_final, final_w, r_final, bonus=0.3)

            else:
                # Ścieżka standardowa
                # QF (Bonus +0.1)
                tournament_points_sum += calc_phase_points(perf.rating_quarters, tour.weight_quarters, r_quarters, bonus=0.1)
                # SF (Bonus +0.2)
                tournament_points_sum += calc_phase_points(perf.rating_semis, tour.weight_semis, r_semis, bonus=0.2)
                # Final (Bonus +0.3)
                tournament_points_sum += calc_phase_points(perf.rating_final, tour.weight_final, r_final, bonus=0.3)

            # --- ZABEZPIECZENIE PRZED PUNKTAMI UJEMNYMI Z TURNIEJU ---
            tournament_points_final = max(0.0, tournament_points_sum)

            # Wynik mnożymy przez ogólną wagę turnieju
            total_points += tournament_points_final * tour.weight

        ranking.append({
            "player_id": player.id,
            "nickname": player.nickname,
            "team_name": player.team.name if player.team else "No Team",
            "total_points": round(total_points),
            "photo_url": player.photo_url
        })

    ranking.sort(key=lambda x: x["total_points"], reverse=True)
    return ranking



# SCALED
#
# from typing import List
# import math
# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session, joinedload
# import models
# import schemas
# from database import get_db
#
# router = APIRouter(tags=["Ranking"])
#
#
# @router.get("/api/ranking/", response_model=List[schemas.RankingEntry])
# def get_ranking(db: Session = Depends(get_db)):
#     players = db.query(models.Player).options(
#         joinedload(models.Player.team),
#         joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament),
#     ).all()
#
#     ranking = []
#
#     for player in players:
#         total_points = 0.0
#
#         for perf in player.tournament_performances:
#             tour = perf.tournament
#
#             participation = db.query(models.TournamentTeam).filter(
#                 models.TournamentTeam.tournament_id == tour.id,
#                 models.TournamentTeam.team_id == player.team_id
#             ).first()
#
#             r_group = participation.rounds_group if participation else 0
#             r_quarters = participation.rounds_quarters if participation else 0
#             r_semis = participation.rounds_semis if participation else 0
#             r_final = participation.rounds_final if participation else 0
#
#             # Funkcja obliczająca "skalowane rundy" według Twojego pomysłu
#             def get_scaled_rounds(rounds):
#                 if rounds <= 0: return 0
#
#                 base_limit = 27  # Pierwsze 27 rund (100% wartości)
#                 step = 9  # Każdy kolejny skok o 9 rund
#                 decay = 0.6  # Kolejny próg wart 60% poprzedniego (o 40% mniej)
#
#                 remaining = rounds
#                 scaled = 0
#                 current_multiplier = 1.0
#
#                 # 1. Próg bazowy (0-27)
#                 taken = min(remaining, base_limit)
#                 scaled += taken * current_multiplier
#                 remaining -= taken
#
#                 # 2. Próg malejący (pętle co 9 rund)
#                 while remaining > 0:
#                     current_multiplier *= decay  # Spadek o 40% (zostaje 60%)
#                     taken = min(remaining, step)
#                     scaled += taken * current_multiplier
#                     remaining -= taken
#
#                 return scaled
#
#             def calc_phase_points(rating, weight, phase_rounds, bonus=0.0):
#                 if rating is None or rating == 0 or phase_rounds == 0:
#                     return 0.0
#
#                 if 0.01 < rating < 5.0:
#                     effective_rating = rating + bonus
#                 else:
#                     effective_rating = rating
#
#                 # Obliczamy skalowane rundy dla tej fazy
#                 scaled = get_scaled_rounds(phase_rounds)
#
#                 # Formuła: (Rating-1) * 1000 * waga * (skalowane_rundy / 27)
#                 # Dzielimy przez 27, żeby "standardowy mecz" był punktem odniesienia
#                 return (effective_rating - 1.0) * 1000 * weight * (scaled / 27)
#
#             tournament_points_sum = 0.0
#             starts_in_semis = participation.starts_in_semis if participation else False
#
#             # Obliczenia faz
#             tournament_points_sum += calc_phase_points(perf.rating_group, tour.weight_group, r_group)
#
#             if starts_in_semis:
#                 semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else (
#                                                                                                                 1.0 - tour.weight_group) / 2
#                 final_w = tour.weight_final_override if tour.weight_final_override is not None else (
#                                                                                                                 1.0 - tour.weight_group) / 2
#                 tournament_points_sum += calc_phase_points(perf.rating_semis, semis_w, r_semis, bonus=0.2)
#                 tournament_points_sum += calc_phase_points(perf.rating_final, final_w, r_final, bonus=0.3)
#             else:
#                 tournament_points_sum += calc_phase_points(perf.rating_quarters, tour.weight_quarters, r_quarters,
#                                                            bonus=0.1)
#                 tournament_points_sum += calc_phase_points(perf.rating_semis, tour.weight_semis, r_semis, bonus=0.2)
#                 tournament_points_sum += calc_phase_points(perf.rating_final, tour.weight_final, r_final, bonus=0.3)
#
#             total_points += max(0.0, tournament_points_sum) * tour.weight
#
#         ranking.append({
#             "player_id": player.id,
#             "nickname": player.nickname,
#             "team_name": player.team.name if player.team else "No Team",
#             "total_points": round(total_points),
#             "photo_url": player.photo_url
#         })
#
#     ranking.sort(key=lambda x: x["total_points"], reverse=True)
#     return ranking