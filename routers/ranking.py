from typing import List, Optional
import math
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload
import models
import schemas
from database import get_db

router = APIRouter(tags=["Ranking"])
# --- STAŁE DO OBLICZEŃ (Konfiguracja) ---
RANKING_BASE_MULTIPLIER = 67.0  # Podstawowy mnożnik punktów
RANKING_ROUNDS_ROOT = 2.66  # Stopień pierwiastka dla rund (np. rounds^(1/2.66))
RANKING_RATING_EXPONENT_DIV = 1.1  # Dzielnik wykładnika ratingu (np. diff^(1/1.1))


@router.get("/api/ranking/", response_model=List[schemas.RankingEntry])
def get_ranking(db: Session = Depends(get_db), tournament_id: Optional[int] = None):
    # Pobieramy graczy wraz z potrzebnymi relacjami
    players = db.query(models.Player).options(
        joinedload(models.Player.team),
        joinedload(models.Player.tournament_performances).joinedload(models.PlayerTournamentPerformance.tournament),
    ).all()

    ranking = []

    for player in players:
        total_points = 0.0
        player_details = []  # Lista szczegółów dla tego gracza
        has_participated_in_target_tournament = False  # Flaga czy gracz grał w wybranym turnieju

        for perf in player.tournament_performances:
            # 1. Filtrowanie po ID turnieju (jeśli podano)
            if tournament_id is not None:
                if perf.tournament_id != tournament_id:
                    continue  # Pomijamy inne turnieje
                else:
                    has_participated_in_target_tournament = True

            tour = perf.tournament

            # Pobieramy dane o rundach (participation)
            participation = db.query(models.TournamentTeam).filter(
                models.TournamentTeam.tournament_id == tour.id,
                models.TournamentTeam.team_id == player.team_id
            ).first()

            # Jeśli nie znaleziono participation (np. błąd danych), przyjmujemy 0 rund
            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0
            r_third = participation.rounds_third_place if participation else 0
            starts_in_semis = participation.starts_in_semis if participation else False

            # Lista faz dla obecnego turnieju
            current_tour_phases = []
            tournament_points_sum = 0.0

            # Funkcja wewnętrzna licząca punkty i zapisująca szczegóły
            def process_phase(phase_name, rating, weight, phase_rounds, bonus=0.0):
                # Zabezpieczenie: jeśli brak ratingu lub rund, punkty = 0
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

                # Wzór: różnica ratingu
                diff = (effective_rating - 1.0) * 100

                # Wzór: Tłumienie ratingu (Damping)
                exponent = 1 / RANKING_RATING_EXPONENT_DIV
                damped_diff = math.copysign(abs(diff) ** exponent, diff)

                # Wzór: Pierwiastek rund
                rounds_factor = phase_rounds ** (1 / RANKING_ROUNDS_ROOT)

                # Finalne punkty fazy
                points = damped_diff * RANKING_BASE_MULTIPLIER * weight * rounds_factor

                # Dodajemy do szczegółów
                current_tour_phases.append({
                    "phase_name": phase_name,
                    "rating": round(effective_rating, 2),  # Zapisujemy rating z bonusem
                    "rounds": phase_rounds,
                    "weight": weight,
                    "points": round(points, 2),
                    "bonus": bonus
                })

                return points

            # --- OBLICZENIA FAZ ---

            # 1. Faza Grupowa
            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                w_group = tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group
                tournament_points_sum += process_phase("Group (Override)", perf.rating_group, w_group, r_group)
            else:
                tournament_points_sum += process_phase("Group Stage", perf.rating_group, tour.weight_group, r_group)

            # 2. Play-offs
            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                remaining = 1.0 - (
                    tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group)
                w_semi = tour.weight_semis_override if tour.weight_semis_override is not None else remaining / 2
                w_final = tour.weight_final_override if tour.weight_final_override is not None else remaining / 2

                tournament_points_sum += process_phase("Semi-Final", perf.rating_semis, w_semi, r_semis, bonus=0.15)
                tournament_points_sum += process_phase("Final", perf.rating_final, w_final, r_final, bonus=0.15)
            else:
                tournament_points_sum += process_phase("Quarter-Final", perf.rating_quarters, tour.weight_quarters,
                                                       r_quarters, bonus=0.15)
                tournament_points_sum += process_phase("Semi-Final", perf.rating_semis, tour.weight_semis, r_semis,
                                                       bonus=0.15)
                tournament_points_sum += process_phase("Final", perf.rating_final, tour.weight_final, r_final,
                                                       bonus=0.15)

            # 3. Mecz o 3. miejsce
            if tour.has_third_place:
                tournament_points_sum += process_phase("3rd Place", perf.rating_third_place, tour.weight_third_place,
                                                       r_third, bonus=0.15)

            # Suma punktów z turnieju przemnożona przez wagę turnieju
            # Zabezpieczenie: punkty z turnieju nie mogą być ujemne w sumie (chyba że tak chcesz, ale max(0, ...) jest bezpieczniejsze)
            final_tour_points = max(0.0, tournament_points_sum) * tour.weight
            total_points += final_tour_points

            # Dodajemy szczegóły turnieju do listy szczegółów gracza
            player_details.append({
                "tournament_name": tour.name,
                "tournament_weight": tour.weight,
                "phases": current_tour_phases,
                "total_tournament_points": round(final_tour_points, 2)
            })

        # --- DECYZJA O DODANIU DO RANKINGU ---
        should_add = False

        # Przypadek 1: Ranking ogólny (tournament_id is None) -> Dodajemy jeśli ma > 0 punktów
        if tournament_id is None:
            if total_points > 0:
                should_add = True

        # Przypadek 2: Ranking konkretnego turnieju -> Dodajemy jeśli brał udział (nawet jak ma 0 pkt, np. słaby rating)
        else:
            if has_participated_in_target_tournament:
                should_add = True
        final_points_int = int(round(total_points))
        if should_add:
            ranking.append(schemas.RankingEntry(
                player_id=player.id,
                nickname=player.nickname,
                team_name=player.team.name if player.team else "No Team",
                total_points=final_points_int,  # Tutaj jest teraz INT
                photo_url=player.photo_url,
                details=player_details  # Przekazujemy szczegóły
            ))

    # Sortowanie
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
