"""
Schematy Pydantic.
Wersja kompletna: zawiera wszystkie modele potrzebne do działania aplikacji.
Naprawia błąd 'AttributeError: module schemas has no attribute MatchUpdate'.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date

# --- TEAMS ---
class TeamBase(BaseModel):
    name: str
    logo_url: Optional[str] = None

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    logo_url: Optional[str] = None

class Team(TeamBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- PLAYERS ---
class PlayerBase(BaseModel):
    nickname: str
    photo_url: Optional[str] = None
    team_id: Optional[int] = None

class PlayerCreate(PlayerBase):
    pass

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

    # Standardowe wagi
    weight_overall: float = 0.4
    weight_quarters: float = 0.2
    weight_semis: float = 0.2
    weight_final: float = 0.2

    # Nadpisania dla Bracket 6 (dla drużyn omijających QF)
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None

class TournamentCreate(TournamentBase):
    pass

class TournamentUpdate(BaseModel):
    name: Optional[str] = None
    bracket_type: Optional[str] = None
    weight_overall: Optional[float] = None
    weight_quarters: Optional[float] = None
    weight_semis: Optional[float] = None
    weight_final: Optional[float] = None
    weight_semis_override: Optional[float] = None
    weight_final_override: Optional[float] = None

class Tournament(TournamentBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class AddTeamToTournament(BaseModel):
    team_id: int
    starts_in_semis: bool = False

# --- MAPS ---
class MapBase(BaseModel):
    map_name: str
    score: str

class MapCreate(MapBase):
    pass

class Map(MapBase):
    id: int
    match_id: int
    model_config = ConfigDict(from_attributes=True)

# --- MATCHES ---
class MatchBase(BaseModel):
    tournament_id: int
    phase: str
    date: date
    format: str
    team1_id: int
    team2_id: int
    result: Optional[str] = None

class MatchCreate(MatchBase):
    pass

class MatchUpdate(BaseModel):
    """Brakujący schemat, który powodował błąd."""
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

# --- PLAYER RATINGS (STARE) ---
class PlayerRatingBase(BaseModel):
    match_id: int
    player_id: int
    rating: float

class PlayerRatingCreate(PlayerRatingBase):
    pass

class PlayerRating(PlayerRatingBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

# --- NEW: TOURNAMENT PERFORMANCE (NOWE) ---
class PlayerTournamentPerformanceBase(BaseModel):
    rating_overall: Optional[float] = None
    rating_quarters: Optional[float] = None
    rating_semis: Optional[float] = None
    rating_final: Optional[float] = None

class PlayerTournamentPerformanceCreate(PlayerTournamentPerformanceBase):
    player_id: int
    tournament_id: int

class PlayerTournamentPerformance(PlayerTournamentPerformanceBase):
    id: int
    player_id: int
    tournament_id: int
    model_config = ConfigDict(from_attributes=True)

# --- RANKING ---
class RankingEntry(BaseModel):
    player_id: int
    nickname: str
    team_name: Optional[str] = None
    total_points: float
    photo_url: Optional[str] = None

# Dla wstecznej kompatybilności (jeśli gdzieś jest używane)
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

# --- DATA OPS ---
class DatabaseExport(BaseModel):
    teams: List[Team]
    players: List[Player]
    tournaments: List[Tournament]
    matches: List[Match]
    maps: List[Map]