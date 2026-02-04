"""
Schematy Pydantic dla walidacji danych w aplikacji CS2 Player Tracker.
Definiuje modele Request (dane wejściowe) i Response (dane wyjściowe) dla wszystkich endpointów API.
Służy do automatycznej serializacji danych z bazy SQL na format JSON oraz walidacji danych przesyłanych przez użytkownika.
"""

from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date


# --- TEAMS SCHEMAS ---

class TeamBase(BaseModel):
    """
    Bazowy schemat drużyny zawierający wspólne pola.

    Attributes:
        name (str): Nazwa drużyny (wymagana).
        logo_url (str | None): Link do loga drużyny (opcjonalny).
    """
    name: str
    logo_url: Optional[str] = None


class TeamCreate(TeamBase):
    """
    Schemat używany przy tworzeniu nowej drużyny (POST).
    Dziedziczy wszystkie pola z TeamBase.
    """
    pass


class TeamUpdate(BaseModel):
    """
    Schemat używany przy aktualizacji drużyny (PUT/PATCH).
    Wszystkie pola są opcjonalne, co pozwala na edycję tylko wybranych atrybutów.
    """
    name: Optional[str] = None
    logo_url: Optional[str] = None


class Team(TeamBase):
    """
    Schemat odpowiedzi (Response) reprezentujący drużynę z bazy danych.
    Zawiera ID nadane przez bazę.

    Attributes:
        id (int): Unikalny identyfikator drużyny.
    """
    id: int

    # Konfiguracja umożliwiająca czytanie danych bezpośrednio z obiektów SQLAlchemy
    model_config = ConfigDict(from_attributes=True)


# --- PLAYERS SCHEMAS ---

class PlayerBase(BaseModel):
    """
    Bazowy schemat gracza.

    Attributes:
        nickname (str): Pseudonim gracza.
        photo_url (str | None): Link do zdjęcia gracza.
        team_id (int | None): ID drużyny, do której gracz należy.
    """
    nickname: str
    photo_url: Optional[str] = None
    team_id: Optional[int] = None


class PlayerCreate(PlayerBase):
    """
    Schemat używany przy dodawaniu nowego gracza.
    """
    pass


class PlayerUpdate(BaseModel):
    """
    Schemat używany przy edycji danych gracza.
    """
    nickname: Optional[str] = None
    photo_url: Optional[str] = None
    team_id: Optional[int] = None


class Player(PlayerBase):
    """
    Schemat odpowiedzi reprezentujący gracza z bazy danych.
    """
    id: int
    model_config = ConfigDict(from_attributes=True)


class PlayerWithTeam(Player):
    """
    Rozszerzony schemat gracza, który zawiera zagnieżdżony obiekt drużyny.
    Używany, aby frontend nie musiał wysyłać osobnego zapytania o nazwę drużyny.

    Attributes:
        team (Team | None): Pełny obiekt drużyny (lub None, jeśli brak).
    """
    team: Optional[Team] = None

    model_config = ConfigDict(from_attributes=True)


# --- TOURNAMENTS SCHEMAS ---

class TournamentBase(BaseModel):
    """
    Bazowy schemat turnieju.

    Attributes:
        name (str): Nazwa turnieju.
        weight (float): Waga turnieju wpływająca na punkty rankingowe (domyślnie 1.0).
    """
    name: str
    weight: float = 1.0


class TournamentCreate(TournamentBase):
    """Schemat tworzenia turnieju."""
    pass


class TournamentUpdate(BaseModel):
    """Schemat aktualizacji turnieju."""
    name: Optional[str] = None
    weight: Optional[float] = None


class Tournament(TournamentBase):
    """Schemat odpowiedzi turnieju z ID."""
    id: int

    model_config = ConfigDict(from_attributes=True)


# --- MAPS SCHEMAS ---

class MapBase(BaseModel):
    """
    Bazowy schemat mapy rozegranej w meczu.

    Attributes:
        map_name (str): Nazwa mapy (np. 'Mirage').
        score (str): Wynik mapy (np. '13:11').
    """
    map_name: str
    score: str


class MapCreate(MapBase):
    """Schemat dodawania mapy."""
    pass


class Map(MapBase):
    """
    Schemat odpowiedzi mapy.

    Attributes:
        id (int): ID mapy.
        match_id (int): ID meczu, do którego mapa należy.
    """
    id: int
    match_id: int

    model_config = ConfigDict(from_attributes=True)


# --- MATCHES SCHEMAS ---

class MatchBase(BaseModel):
    """
    Bazowy schemat meczu.

    Attributes:
        tournament_id (int): ID turnieju.
        phase (str): Faza rozgrywek (np. 'Group A').
        date (date): Data meczu (RRRR-MM-DD).
        format (str): Format meczu (np. 'BO3').
        team1_id (int): ID pierwszej drużyny.
        team2_id (int): ID drugiej drużyny.
        result (str | None): Wynik końcowy (np. '2:1').
    """
    tournament_id: int
    phase: str
    date: date
    format: str
    team1_id: int
    team2_id: int
    result: Optional[str] = None


class MatchCreate(MatchBase):
    """Schemat tworzenia meczu."""
    pass


class MatchUpdate(BaseModel):
    """Schemat aktualizacji meczu (edycja wyniku, daty itp.)."""
    tournament_id: Optional[int] = None
    phase: Optional[str] = None
    date: Optional[date] = None
    format: Optional[str] = None
    team1_id: Optional[int] = None
    team2_id: Optional[int] = None
    result: Optional[str] = None


class Match(MatchBase):
    """Schemat odpowiedzi meczu."""
    id: int

    model_config = ConfigDict(from_attributes=True)


class MatchWithDetails(Match):
    """
    Rozszerzony schemat meczu zawierający pełne obiekty powiązane.
    Służy do wyświetlania szczegółów meczu bez konieczności dopytywania o nazwy drużyn czy turnieju.

    Attributes:
        tournament (Tournament): Obiekt turnieju.
        team1 (Team): Obiekt pierwszej drużyny.
        team2 (Team): Obiekt drugiej drużyny.
        maps (List[Map]): Lista rozegranych map.
    """
    tournament: Tournament
    team1: Team
    team2: Team
    maps: List[Map] = []

    model_config = ConfigDict(from_attributes=True)


# --- RATINGS & RANKING SCHEMAS ---

class PlayerRatingBase(BaseModel):
    """
    Bazowy schemat oceny gracza.

    Attributes:
        match_id (int): ID meczu.
        player_id (int): ID gracza.
        rating (float): Ocena liczbowa (np. 1.15).
    """
    match_id: int
    player_id: int
    rating: float


class PlayerRatingCreate(PlayerRatingBase):
    """Schemat dodawania oceny."""
    pass


class PlayerRating(PlayerRatingBase):
    """Schemat odpowiedzi oceny."""
    id: int

    model_config = ConfigDict(from_attributes=True)


class PlayerRankingPointBase(BaseModel):
    """
    Bazowy schemat punktów rankingowych za turniej.

    Attributes:
        player_id (int): ID gracza.
        tournament_id (int): ID turnieju.
        points (float): Ilość zdobytych punktów bazowych.
    """
    player_id: int
    tournament_id: int
    points: float


class PlayerRankingPointCreate(PlayerRankingPointBase):
    """Schemat przyznawania punktów."""
    pass


class PlayerRankingPoint(PlayerRankingPointBase):
    """Schemat odpowiedzi punktów."""
    id: int

    model_config = ConfigDict(from_attributes=True)


class RankingEntry(BaseModel):
    """
    Schemat pojedynczego wiersza w tabeli rankingu.
    Nie odwzorowuje bezpośrednio tabeli w bazie, lecz wynik obliczeń (agregacji).

    Attributes:
        player_id (int): ID gracza.
        nickname (str): Nick gracza.
        team_name (str | None): Nazwa drużyny.
        total_points (float): Suma punktów ważonych ze wszystkich turniejów.
        photo_url (str | None): Zdjęcie gracza.
    """
    player_id: int
    nickname: str
    team_name: Optional[str] = None
    total_points: float
    photo_url: Optional[str] = None


class DatabaseExport(BaseModel):
    """
    Zbiorczy schemat eksportu danych.
    Zawiera listy wszystkich encji w systemie. Używany do backupu danych.
    """
    teams: List[Team]
    players: List[Player]
    tournaments: List[Tournament]
    matches: List[Match]
    maps: List[Map]
    player_ratings: List[PlayerRating]
    player_ranking_points: List[PlayerRankingPoint]