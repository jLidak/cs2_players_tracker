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

            total_tour_rounds = r_group + r_quarters + r_semis + r_final

            # Funkcja pomocnicza do obliczania punktów za konkretną fazę
            def calc_phase_points(rating, weight, phase_rounds, bonus=0.0):
                if rating is None or total_tour_rounds == 0:
                    return 0.0

                # Dodajemy bonus do ratingu (np. +0.08 w półfinale)
                effective_rating = rating + bonus

                # Obliczamy punkty: (Rating_efektywny - 1.0) * 100 * waga_fazy * (rundy_fazy / rundy_turnieju)
                return (effective_rating - 1.0) * 10000 * weight * (phase_rounds / total_tour_rounds)

            tournament_points_sum = 0.0

            # Sprawdzamy czy drużyna zaczynała od półfinału (Bracket 6)
            starts_in_semis = participation.starts_in_semis if participation else False

            # --- OBLICZENIA DLA KAŻDEJ FAZY ---

            # FAZA GRUPOWA (brak bonusu)
            tournament_points_sum += calc_phase_points(perf.rating_group, tour.weight_group, r_group)

            if starts_in_semis:
                # Ścieżka skrócona (Bracket 6)
                semis_w = tour.weight_semis_override if tour.weight_semis_override is not None else (
                                                                                                                1.0 - tour.weight_group) / 2
                final_w = tour.weight_final_override if tour.weight_final_override is not None else (
                                                                                                                1.0 - tour.weight_group) / 2

                # Półfinał (Bonus +0.08)
                tournament_points_sum += calc_phase_points(perf.rating_semis, semis_w, r_semis, bonus=0.08)
                # Finał (Bonus +0.16)
                tournament_points_sum += calc_phase_points(perf.rating_final, final_w, r_final, bonus=0.16)

            else:
                # Ścieżka standardowa
                # Ćwierćfinał (brak bonusu)
                tournament_points_sum += calc_phase_points(perf.rating_quarters, tour.weight_quarters, r_quarters, bonus=0.1)
                # Półfinał (Bonus +0.08)
                tournament_points_sum += calc_phase_points(perf.rating_semis, tour.weight_semis, r_semis, bonus=0.2)
                # Finał (Bonus +0.16)
                tournament_points_sum += calc_phase_points(perf.rating_final, tour.weight_final, r_final, bonus=0.3)

            # --- ZABEZPIECZENIE PRZED PUNKTAMI UJEMNYMI Z TURNIEJU ---
            # Jeśli suma punktów z wszystkich faz jest ujemna, ustawiamy 0.
            # Dzięki temu słaby rating może obniżyć wynik z innych faz, ale nie "zadłuży" gracza w rankingu ogólnym.
            tournament_points_final = max(0.0, tournament_points_sum)

            # Wynik końcowy mnożymy przez wagę całego turnieju i dodajemy do sumy gracza
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