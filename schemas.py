from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Optional
from datetime import date

class TeamBase(BaseModel):
    name: str
    logo_url: Optional[str] = None
class TeamCreate(TeamBase): pass
class TeamUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None
class Team(TeamBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class PlayerBase(BaseModel):
    nickname: str
    photo_url: Optional[str] = None
    team_id: Optional[int] = None
class PlayerCreate(PlayerBase): pass
class PlayerUpdate(BaseModel):
    nickname: Optional[str] = None
    photo_url: Optional[str] = None
    team_id: Optional[int] = None
class Player(PlayerBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
class PlayerWithTeam(Player):
    team: Optional[Team] = None
    model_config = ConfigDict(from_attributes=True)

# --- TOURNAMENTS ---
class TournamentBase(BaseModel):
    name: str
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

class TournamentCreate(TournamentBase): pass

class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    bracket_type: Optional[str] = None
    weight: Optional[float] = None
    weight_group: Optional[float] = None # Zmiana
    weight_quarters: Optional[float] = None
    weight_semis: Optional[float] = None
    weight_final: Optional[float] = None

    has_third_place: Optional[bool] = None
    weight_third_place: Optional[float] = None

    weight_group_override: Optional[float] = None
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None

class Tournament(TournamentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AddTeamToTournament(BaseModel):
    team_id: int
    starts_in_semis: bool = False
    rounds_group: int = 1
    rounds_quarters: int = 0
    rounds_semis: int = 0
    rounds_final: int = 0
    rounds_third_place: int = 0

class TournamentTeam(BaseModel):
    id: int
    tournament_id: int
    team_id: int
    starts_in_semis: bool
    model_config = ConfigDict(from_attributes=True)
    rounds_group: int
    rounds_quarters: int
    rounds_semis: int
    rounds_final: int
    model_config = ConfigDict(from_attributes=True)

# --- PERFORMANCE ---
class PlayerTournamentPerformanceBase(BaseModel):
    rating_group: Optional[float] = None # Zmiana
    rating_quarters: Optional[float] = None
    rating_semis: Optional[float] = None
    rating_final: Optional[float] = None
    rating_third_place: Optional[float] = None  # Nowe pole

class PlayerTournamentPerformanceCreate(PlayerTournamentPerformanceBase):
    player_id: int
    tournament_id: int
class PlayerTournamentPerformance(PlayerTournamentPerformanceBase):
    id: int
    player_id: int
    tournament_id: int
    model_config = ConfigDict(from_attributes=True)

class RankingEntry(BaseModel):
    player_id: int
    nickname: str
    team_name: Optional[str] = None
    total_points: float
    photo_url: Optional[str] = None

# --- LEGACY ---
class MapBase(BaseModel):
    map_name: str
    score: str
class MapCreate(MapBase): pass
class Map(MapBase):
    id: int
    match_id: int
    model_config = ConfigDict(from_attributes=True)
class MatchBase(BaseModel):
    tournament_id: int
    phase: str
    date: date
    format: str
    team1_id: int
    team2_id: int
    result: Optional[str] = None
class MatchCreate(MatchBase): pass
class MatchUpdate(BaseModel):
    tournament_id: Optional[int] = None
    phase: Optional[str] = None
    date: Optional[date] = None
    format: Optional[str] = None
    team1_id: Optional[int] = None
    team2_id: Optional[int] = None
    result: Optional[str] = None
class Match(MatchBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
class MatchWithDetails(Match):
    tournament: Tournament
    team1: Team
    team2: Team
    maps: List[Map] = []
    model_config = ConfigDict(from_attributes=True)
class PlayerRatingBase(BaseModel):
    match_id: int
    player_id: int
    rating: float
class PlayerRatingCreate(PlayerRatingBase): pass
class PlayerRating(PlayerRatingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
class PlayerRankingPoint(BaseModel):
    id: int
    player_id: int
    tournament_id: int
    points: float
    model_config = ConfigDict(from_attributes=True)
class PlayerRankingPointCreate(BaseModel):
    player_id: int
    tournament_id: int
    points: float
class DatabaseExport(BaseModel):
    teams: List[Team]
    tournaments: List[Tournament]
    players: List[Player]
    tournament_teams: List[TournamentTeam]
    player_performances: List[PlayerTournamentPerformance]
    matches: List[Match]
    maps: List[Map]
    player_ratings: List[PlayerRating]

# --- IMPORT ---
class PlayerImport(BaseModel):
    nickname: str
    photo_url: Optional[str] = None

class TeamImport(BaseModel):
    name: str
    logo_url: Optional[str] = None
    players: List[PlayerImport] = []

class ImportData(BaseModel):
    teams: List[TeamImport]


# --- CUSTOM RANKING ---
class PhaseWeights(BaseModel):
    weight_group: float
    weight_qf: float
    weight_sf: float
    weight_final: float
    weight_third_place: float = 0.1


class CustomRankingParams(BaseModel):
    # Parametry matematyczne
    rating_exponent_divisor: float = 1.1
    rounds_root: float = 2.0
    base_multiplier: float = 15.0

    # Bonusy fazowe
    bonus_qf: float = 0.15
    bonus_sf: float = 0.15
    bonus_final: float = 0.15
    bonus_third_place: float = 0.15  # Nowy bonus
    # Słownik: ID Turnieju -> Wagi Faz
    # Jeśli ID turnieju nie ma w tym słowniku, używamy danych z bazy
    tournament_overrides: Dict[int, PhaseWeights] = {}


# Nowy model dla szczegółów fazy (np. punkty za grupę)
class PhasePointsDetail(BaseModel):
    phase_name: str
    rating: float
    rounds: int
    weight: float
    points: float
    bonus: float  # Dodajemy informację o bonusie

# Nowy model dla szczegółów turnieju
class TournamentPointsDetail(BaseModel):
    tournament_name: str
    tournament_weight: float
    phases: List[PhasePointsDetail]
    total_tournament_points: float


# Rozszerzony model RankingEntry
class RankingEntry(BaseModel):
    player_id: int
    nickname: str
    team_name: Optional[str] = None
    total_points: float
    photo_url: Optional[str] = None

    # Lista szczegółów (może być pusta, jeśli nie potrzebujemy detali wszędzie)
    details: List[TournamentPointsDetail] = []