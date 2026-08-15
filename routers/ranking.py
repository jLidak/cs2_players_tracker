"""
API router for Ranking calculations.
Contains the core mathematical algorithms for calculating both the default
global ranking and the highly customizable dynamic ranking system.
"""

import math
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

import models
import schemas
from database import get_db

router = APIRouter(tags=["Ranking"])

# ==========================================
# DEFAULT RANKING CONSTANTS
# ==========================================
RANKING_BASE_MULTIPLIER = 50.0  # Base pool of points awarded per phase
RANKING_ROUNDS_ROOT = 2.66  # Root exponent applied to the number of rounds played
RANKING_RATING_EXPONENT_DIV = 1.0  # Divisor for the rating differential exponent (damping)
RANKING_BONUS = 0.15  # Fixed bonus added to ratings in advanced knockout phases


# ==========================================
# INTERNAL ENGINE & HELPER FUNCTIONS
# ==========================================

def _process_phase(
    phase_name: str,
    rating: Optional[float],
    weight: float,
    phase_rounds: int,
    bonus: float,
    exp_div: float,
    rounds_root: float,
    base_mult: float,
    phases_list: list,
) -> float:
    """
    Core math helper to calculate points for a specific tournament phase
    and append the formatted result to the player's phases list.
    """
    if rating is None or rating == 0 or phase_rounds == 0:
        return 0.0

    effective_rating = rating + bonus

    # Math logic:
    # 1. Find the differential from the baseline rating (1.0).
    # 2. Dampen extreme differences using root/exponent logic to flatten curves.
    # 3. Apply the rounds root to reward longevity non-linearly.
    diff = (effective_rating - 1.0) * 100

    exp_div_safe = exp_div if exp_div != 0 else 1.0
    exponent = 1 / exp_div_safe
    damped_diff = math.copysign(abs(diff) ** exponent, diff)

    root_val_safe = rounds_root if rounds_root != 0 else 1.0
    rounds_factor = phase_rounds ** (1 / root_val_safe)

    points = damped_diff * base_mult * weight * rounds_factor

    phases_list.append(
        {
            "phase_name": phase_name,
            "rating": round(rating, 2),
            "rounds": phase_rounds,
            "weight": weight,
            "points": round(points, 2),
            "bonus": bonus,
        }
    )

    return points


def _generate_ranking(
    db: Session,
    target_tournament_id: Optional[int],
    config: Dict[str, float],
    overrides: Dict[int, Any]
) -> List[schemas.RankingEntry]:
    """
    Master engine for evaluating player performances and building the leaderboard.
    Unifies the logic for both the default ranking and the custom ranking simulator,
    preventing massive code duplication.
    """
    players = (
        db.query(models.Player)
        .options(
            joinedload(models.Player.team),
            joinedload(models.Player.tournament_performances).joinedload(
                models.PlayerTournamentPerformance.tournament
            ),
        )
        .all()
    )

    ranking = []

    for player in players:
        total_points = 0.0
        player_details = []
        has_participated_in_target = False

        for perf in player.tournament_performances:
            tour = perf.tournament
            tid = tour.id

            if target_tournament_id is not None:
                if tid != target_tournament_id:
                    continue
                else:
                    has_participated_in_target = True

            # 1. Fetch user overrides if any (Dictionary fallback to standard values)
            user_weights = overrides.get(tid)

            w_group = tour.weight_group
            w_qf = tour.weight_quarters
            w_sf = tour.weight_semis
            w_final = tour.weight_final
            w_3rd = tour.weight_third_place
            t_weight = tour.weight

            w_group_ov = tour.weight_group_override if tour.weight_group_override is not None else tour.weight_group
            w_sf_ov = tour.weight_semis_override if tour.weight_semis_override is not None else (1.0 - w_group) / 2
            w_final_ov = tour.weight_final_override if tour.weight_final_override is not None else (1.0 - w_group) / 2

            if user_weights:
                if getattr(user_weights, "tournament_weight", None) is not None:
                    t_weight = user_weights.tournament_weight

                w_group = getattr(user_weights, "weight_group", w_group)
                w_qf = getattr(user_weights, "weight_qf", w_qf)
                w_sf = getattr(user_weights, "weight_sf", w_sf)
                w_final = getattr(user_weights, "weight_final", w_final)
                w_3rd = getattr(user_weights, "weight_third_place", w_3rd)

                if getattr(user_weights, "weight_group_override", None) is not None:
                    w_group_ov = user_weights.weight_group_override
                if getattr(user_weights, "weight_semis_override", None) is not None:
                    w_sf_ov = user_weights.weight_semis_override
                if getattr(user_weights, "weight_final_override", None) is not None:
                    w_final_ov = user_weights.weight_final_override

            # 2. Fetch participation and rounds data
            participation = (
                db.query(models.TournamentTeam)
                .filter(
                    models.TournamentTeam.tournament_id == tid,
                    models.TournamentTeam.team_id == player.team_id,
                )
                .first()
            )

            r_group = participation.rounds_group if participation else 0
            r_quarters = participation.rounds_quarters if participation else 0
            r_semis = participation.rounds_semis if participation else 0
            r_final = participation.rounds_final if participation else 0
            r_third = participation.rounds_third_place if participation else 0
            starts_in_semis = participation.starts_in_semis if participation else False

            current_tour_phases = []
            points_sum = 0.0

            # 3. Process phases based on bracket type and inject config
            if tour.bracket_type == "Bracket 6 teams" and starts_in_semis:
                points_sum += _process_phase("Group (Override)", perf.rating_group, w_group_ov, r_group, 0.0, config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)
                points_sum += _process_phase("Semi-Final", perf.rating_semis, w_sf_ov, r_semis, config["bonus_sf"], config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)
                points_sum += _process_phase("Final", perf.rating_final, w_final_ov, r_final, config["bonus_final"], config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)
            else:
                points_sum += _process_phase("Group Stage", perf.rating_group, w_group, r_group, 0.0, config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)
                points_sum += _process_phase("Quarter-Final", perf.rating_quarters, w_qf, r_quarters, config["bonus_qf"], config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)
                points_sum += _process_phase("Semi-Final", perf.rating_semis, w_sf, r_semis, config["bonus_sf"], config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)
                points_sum += _process_phase("Final", perf.rating_final, w_final, r_final, config["bonus_final"], config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)

            if tour.has_third_place:
                points_sum += _process_phase("3rd Place", perf.rating_third_place, w_3rd, r_third, config["bonus_third"], config["exp_div"], config["rounds_root"], config["base_mult"], current_tour_phases)

            final_tour_points = max(0.0, points_sum) * t_weight
            total_points += final_tour_points

            # Add tournament entry only if the player actually participated
            if current_tour_phases:
                player_details.append(
                    {
                        "tournament_name": tour.name,
                        "tournament_weight": t_weight,
                        "phases": current_tour_phases,
                        "total_tournament_points": round(final_tour_points, 2),
                    }
                )

        # 4. Filter validation before appending to ranking
        should_add = False
        if target_tournament_id is None:
            if len(player_details) > 0:
                should_add = True
        else:
            if has_participated_in_target:
                should_add = True

        if should_add:
            ranking.append(
                schemas.RankingEntry(
                    player_id=player.id,
                    nickname=player.nickname,
                    team_name=player.team.name if player.team else "No Team",
                    total_points=int(round(total_points)),
                    photo_url=player.photo_url,
                    details=player_details,
                )
            )

    ranking.sort(key=lambda x: x.total_points, reverse=True)
    return ranking


# ==========================================
# PUBLIC API ENDPOINTS
# ==========================================

@router.get("/api/ranking/", response_model=List[schemas.RankingEntry])
def get_ranking(
    db: Session = Depends(get_db), tournament_id: Optional[int] = None
) -> List[schemas.RankingEntry]:
    """
    Calculates and retrieves the default player ranking based on global constants.

    Args:
        db (Session): The database session.
        tournament_id (Optional[int]): Limits the ranking to a specific tournament if provided.

    Returns:
        List[schemas.RankingEntry]: A sorted list of players with their calculated points.
    """
    config = {
        "exp_div": RANKING_RATING_EXPONENT_DIV,
        "rounds_root": RANKING_ROUNDS_ROOT,
        "base_mult": RANKING_BASE_MULTIPLIER,
        "bonus_qf": RANKING_BONUS,
        "bonus_sf": RANKING_BONUS,
        "bonus_final": RANKING_BONUS,
        "bonus_third": RANKING_BONUS,
    }

    return _generate_ranking(db, tournament_id, config, overrides={})


@router.post("/api/custom-ranking/", response_model=List[schemas.RankingEntry])
def calculate_custom_ranking(
    params: schemas.CustomRankingParams, db: Session = Depends(get_db)
) -> List[schemas.RankingEntry]:
    """
    Calculates a custom ranking simulation based on parameters provided by the user.
    Allows overriding multipliers, root exponents, phase weights, and tournament weights.

    Args:
        params (schemas.CustomRankingParams): The JSON payload with custom configuration.
        db (Session): The database session.

    Returns:
        List[schemas.RankingEntry]: The sorted ranking resulting from the custom simulation.
    """
    config = {
        "exp_div": params.rating_exponent_divisor,
        "rounds_root": params.rounds_root,
        "base_mult": params.base_multiplier,
        "bonus_qf": params.bonus_qf,
        "bonus_sf": params.bonus_sf,
        "bonus_final": params.bonus_final,
        "bonus_third": params.bonus_third_place,
    }

    return _generate_ranking(db, params.tournament_id, config, params.tournament_overrides)


# ==========================================
# CUSTOM RANKING PRESETS CRUD
# ==========================================

@router.get("/api/ranking-presets/", response_model=List[schemas.CustomRankingPreset])
def get_ranking_presets(
    db: Session = Depends(get_db),
) -> List[models.CustomRankingPreset]:
    """
    Retrieves a list of all saved custom ranking configurations (presets).

    Args:
        db (Session): The database session.

    Returns:
        List[models.CustomRankingPreset]: List of available presets.
    """
    return db.query(models.CustomRankingPreset).all()


@router.post("/api/ranking-presets/", response_model=schemas.CustomRankingPreset)
def create_ranking_preset(
    preset: schemas.CustomRankingPresetCreate, db: Session = Depends(get_db)
) -> models.CustomRankingPreset:
    """
    Saves a new custom ranking configuration to the database.
    If a preset with the same name exists, it overwrites its settings.

    Args:
        preset (schemas.CustomRankingPresetCreate): Preset details containing name and payload.
        db (Session): The database session.

    Returns:
        models.CustomRankingPreset: The newly created or updated preset object.
    """
    existing = (
        db.query(models.CustomRankingPreset)
        .filter(models.CustomRankingPreset.name == preset.name)
        .first()
    )

    if existing:
        existing.settings = preset.settings
        db.commit()
        db.refresh(existing)
        return existing

    db_preset = models.CustomRankingPreset(name=preset.name, settings=preset.settings)
    db.add(db_preset)
    db.commit()
    db.refresh(db_preset)
    return db_preset


@router.delete("/api/ranking-presets/{preset_id}")
def delete_ranking_preset(preset_id: int, db: Session = Depends(get_db)):
    """
    Deletes a saved custom ranking preset by its ID.

    Args:
        preset_id (int): The ID of the preset to delete.
        db (Session): The database session.

    Raises:
        HTTPException: 404 if the preset does not exist.

    Returns:
        dict: A success confirmation message.
    """
    db_preset = (
        db.query(models.CustomRankingPreset)
        .filter(models.CustomRankingPreset.id == preset_id)
        .first()
    )

    if not db_preset:
        raise HTTPException(status_code=404, detail="Preset not found")

    db.delete(db_preset)
    db.commit()
    return {"message": "Preset deleted successfully"}