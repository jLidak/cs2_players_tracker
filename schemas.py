"""
Pydantic schemas for data validation and serialization.
These models define the structure of data entering and leaving the API.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


# ==========================================
# TEAM SCHEMAS
# ==========================================


class TeamBase(BaseModel):
    """Base schema for team attributes."""

    name: str
    logo_url: Optional[str] = None


class TeamCreate(TeamBase):
    """Schema for creating a new team."""

    pass


class TeamUpdate(BaseModel):
    """Schema for updating an existing team."""

    name: Optional[str] = None
    logo_url: Optional[str] = None


class Team(TeamBase):
    """Schema representing a team retrieved from the database."""

    id: int
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PLAYER SCHEMAS
# ==========================================


class PlayerBase(BaseModel):
    """Base schema for player attributes."""

    nickname: str
    photo_url: Optional[str] = None
    team_id: Optional[int] = None


class PlayerCreate(PlayerBase):
    """Schema for creating a new player."""

    pass


class PlayerUpdate(BaseModel):
    """Schema for updating an existing player."""

    nickname: Optional[str] = None
    photo_url: Optional[str] = None
    team_id: Optional[int] = None


class Player(PlayerBase):
    """Schema representing a player retrieved from the database."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class PlayerWithTeam(Player):
    """Schema for a player including their associated team details."""

    team: Optional[Team] = None
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# TOURNAMENT SCHEMAS
# ==========================================


class TournamentBase(BaseModel):
    """Base schema defining tournament attributes and default phase weights."""

    name: str
    start_date: Optional[date] = None
    bracket_type: str = "Bracket 8 teams"
    weight: float = 1.0

    weight_group: float = 0.4
    weight_quarters: float = 0.2
    weight_semis: float = 0.2
    weight_final: float = 0.2

    has_third_place: bool = False
    weight_third_place: float = 0.1

    weight_group_override: Optional[float] = None
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None


class TournamentCreate(TournamentBase):
    """Schema for creating a new tournament."""

    pass


class TournamentUpdate(BaseModel):
    """Schema for updating an existing tournament's configuration."""

    name: Optional[str] = None
    start_date: Optional[date] = None
    bracket_type: Optional[str] = None
    weight: Optional[float] = None
    weight_group: Optional[float] = None
    weight_quarters: Optional[float] = None
    weight_semis: Optional[float] = None
    weight_final: Optional[float] = None

    has_third_place: Optional[bool] = None
    weight_third_place: Optional[float] = None

    weight_group_override: Optional[float] = None
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None


class Tournament(TournamentBase):
    """Schema representing a tournament retrieved from the database."""

    id: int
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# TOURNAMENT PARTICIPATION SCHEMAS
# ==========================================


class AddTeamToTournament(BaseModel):
    """Schema for adding or updating a team's participation in a tournament."""

    team_id: int
    starts_in_semis: bool = False

    in_group: bool = True
    in_quarters: bool = False
    in_semis: bool = False
    in_final: bool = False
    in_third_place: bool = False

    rounds_group: int = 1
    rounds_quarters: int = 0
    rounds_semis: int = 0
    rounds_final: int = 0
    rounds_third_place: int = 0


class TournamentTeam(BaseModel):
    """Schema representing a team's specific participation data in a tournament."""

    id: int
    tournament_id: int
    team_id: int
    starts_in_semis: bool

    in_group: bool
    in_quarters: bool
    in_semis: bool
    in_final: bool
    in_third_place: bool

    rounds_group: int
    rounds_quarters: int
    rounds_semis: int
    rounds_final: int
    rounds_third_place: int
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# PERFORMANCE SCHEMAS
# ==========================================


class PlayerTournamentPerformanceBase(BaseModel):
    """Base schema for recording player ratings across tournament phases."""

    rating_group: Optional[float] = None
    rating_quarters: Optional[float] = None
    rating_semis: Optional[float] = None
    rating_final: Optional[float] = None
    rating_third_place: Optional[float] = None


class PlayerTournamentPerformanceCreate(PlayerTournamentPerformanceBase):
    """Schema for creating a player's performance record."""

    player_id: int
    tournament_id: int


class PlayerTournamentPerformance(PlayerTournamentPerformanceBase):
    """Schema representing a player's performance retrieved from the database."""

    id: int
    player_id: int
    tournament_id: int
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# LEGACY SCHEMAS (Match / Map)
# ==========================================


class MapBase(BaseModel):
    """Legacy schema: Base attributes for a map."""

    map_name: str
    score: str


class MapCreate(MapBase):
    """Legacy schema: Creating a map record."""

    pass


class Map(MapBase):
    """Legacy schema: Retrieved map data."""

    id: int
    match_id: int
    model_config = ConfigDict(from_attributes=True)


class MatchBase(BaseModel):
    """Legacy schema: Base attributes for a match."""

    tournament_id: int
    phase: str
    date: date
    format: str
    team1_id: int
    team2_id: int
    result: Optional[str] = None


class MatchCreate(MatchBase):
    """Legacy schema: Creating a match."""

    pass


class MatchUpdate(BaseModel):
    """Legacy schema: Updating a match."""

    tournament_id: Optional[int] = None
    phase: Optional[str] = None
    date: Optional[date] = None
    format: Optional[str] = None
    team1_id: Optional[int] = None
    team2_id: Optional[int] = None
    result: Optional[str] = None


class Match(MatchBase):
    """Legacy schema: Retrieved match data."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class MatchWithDetails(Match):
    """Legacy schema: Match with associated relations."""

    tournament: Tournament
    team1: Team
    team2: Team
    maps: List[Map] = []
    model_config = ConfigDict(from_attributes=True)


class PlayerRatingBase(BaseModel):
    """Legacy schema: Base player rating per match."""

    match_id: int
    player_id: int
    rating: float


class PlayerRatingCreate(PlayerRatingBase):
    """Legacy schema: Creating a player rating."""

    pass


class PlayerRating(PlayerRatingBase):
    """Legacy schema: Retrieved player rating data."""

    id: int
    model_config = ConfigDict(from_attributes=True)


class PlayerRankingPoint(BaseModel):
    """Legacy schema: Pre-calculated ranking points (now calculated dynamically)."""

    id: int
    player_id: int
    tournament_id: int
    points: float
    model_config = ConfigDict(from_attributes=True)


class PlayerRankingPointCreate(BaseModel):
    """Legacy schema: Creating player ranking points."""

    player_id: int
    tournament_id: int
    points: float


# ==========================================
# IMPORT / EXPORT SCHEMAS
# ==========================================


class DatabaseExport(BaseModel):
    """Schema defining the entire JSON export payload of the database."""

    teams: List[Team]
    tournaments: List[Tournament]
    players: List[Player]
    tournament_teams: List[TournamentTeam]
    player_performances: List[PlayerTournamentPerformance]
    matches: List[Match]
    maps: List[Map]
    player_ratings: List[PlayerRating]


class PlayerImport(BaseModel):
    """Schema for validating player details during JSON import."""

    nickname: str
    photo_url: Optional[str] = None


class TeamImport(BaseModel):
    """Schema for validating team details during JSON import."""

    name: str
    logo_url: Optional[str] = None
    players: List[PlayerImport] = []


class ImportData(BaseModel):
    """Schema representing the root structure for data importing."""

    teams: List[TeamImport]


# ==========================================
# CUSTOM RANKING SCHEMAS
# ==========================================


class PhaseWeights(BaseModel):
    """Schema defining overridden phase weights for a specific tournament."""

    tournament_weight: Optional[float] = None
    weight_group: float
    weight_qf: float
    weight_sf: float
    weight_final: float
    weight_third_place: float = 0.1
    weight_group_override: Optional[float] = None
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None


class CustomRankingParams(BaseModel):
    """Schema for passing dynamic math parameters and overrides to the ranking simulator."""

    rating_exponent_divisor: float = 1.1
    rounds_root: float = 2.0
    base_multiplier: float = 15.0

    bonus_qf: float = 0.15
    bonus_sf: float = 0.15
    bonus_final: float = 0.15
    bonus_third_place: float = 0.15

    tournament_id: Optional[int] = None
    tournament_overrides: Dict[int, PhaseWeights] = {}


class PhasePointsDetail(BaseModel):
    """Schema detailing how points were calculated for a specific phase."""

    phase_name: str
    rating: float
    rounds: int
    weight: float
    points: float
    bonus: float


class TournamentPointsDetail(BaseModel):
    """Schema aggregating the calculation details for a specific tournament."""

    tournament_name: str
    tournament_weight: float
    phases: List[PhasePointsDetail]
    total_tournament_points: float


class RankingEntry(BaseModel):
    """Schema representing a final calculated position in the leaderboard."""

    player_id: int
    nickname: str
    team_name: Optional[str] = None
    total_points: float
    photo_url: Optional[str] = None
    details: List[TournamentPointsDetail] = []


class TournamentWeightOverride(BaseModel):
    """Alternative schema representing weight overrides."""

    weight_group: float
    weight_qf: float
    weight_sf: float
    weight_final: float
    weight_group_override: Optional[float] = None
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None
    weight_third_place: Optional[float] = 0.0


# ==========================================
# RANKING PRESET SCHEMAS
# ==========================================


class CustomRankingPresetBase(BaseModel):
    """Base schema for a saved custom ranking configuration profile."""

    name: str
    settings: Dict[str, Any]


class CustomRankingPresetCreate(CustomRankingPresetBase):
    """Schema for creating a new ranking preset."""

    pass


class CustomRankingPreset(CustomRankingPresetBase):
    """Schema representing a saved ranking preset retrieved from the database."""

    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
