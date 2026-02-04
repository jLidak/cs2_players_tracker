"""
Modele SQLAlchemy (wersja 2.0 style) z poprawnymi adnotacjami typów (Mapped).
Naprawia błąd "Type annotation can't be correctly interpreted".
"""

from typing import List, Optional
from datetime import date
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base

class Team(Base):
    """
    Reprezentuje drużynę.

    Attributes:
        id (int): Unikalny identyfikator drużyny.
        name (str): Nazwa drużyny (musi być unikalna).
        logo_url (str | None): Opcjonalny link do loga drużyny.
        players (List[Player]): Lista zawodników należących do tej drużyny.
        matches_as_team1 (List[Match]): Lista meczów, gdzie drużyna gra jako "Team 1".
        matches_as_team2 (List[Match]): Lista meczów, gdzie drużyna gra jako "Team 2".
    """
    __tablename__ = "teams"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String, unique=True, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = Column(String, nullable=True)

    players: Mapped[List["Player"]] = relationship(
        "Player",
        back_populates="team",
        cascade="all, delete-orphan"
    )
    matches_as_team1: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.team1_id",
        back_populates="team1",
        cascade="all, delete-orphan"
    )
    matches_as_team2: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.team2_id",
        back_populates="team2",
        cascade="all, delete-orphan"
    )


class Player(Base):
    """
    Reprezentuje gracza.

    Attributes:
        id (int): Unikalny identyfikator gracza.
        nickname (str): Pseudonim gracza (musi być unikalny).
        photo_url (str | None): Opcjonalny link do zdjęcia gracza.
        team_id (int | None): ID drużyny, do której należy gracz (Klucz Obcy).
        team (Team | None): Obiekt drużyny (relacja).
        ratings (List[PlayerRating]): Historia ocen gracza z meczów.
        ranking_points (List[PlayerRankingPoint]): Historia punktów rankingowych gracza.
    """
    __tablename__ = "players"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = Column(String, unique=True, nullable=False, index=True)
    photo_url: Mapped[Optional[str]] = Column(String, nullable=True)
    team_id: Mapped[Optional[int]] = Column(Integer, ForeignKey("teams.id"), nullable=True)

    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="players")

    ratings: Mapped[List["PlayerRating"]] = relationship(
        "PlayerRating",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    ranking_points: Mapped[List["PlayerRankingPoint"]] = relationship(
        "PlayerRankingPoint",
        back_populates="player",
        cascade="all, delete-orphan"
    )


class Tournament(Base):
    """
    Reprezentuje turniej CS2.

    Attributes:
        id (int): Unikalny identyfikator turnieju.
        name (str): Nazwa turnieju.
        weight (float): Waga turnieju wpływająca na ranking (domyślnie 1.0).
        matches (List[Match]): Lista meczów rozegranych w ramach turnieju.
        ranking_points (List[PlayerRankingPoint]): Punkty przyznane w tym turnieju.
    """
    __tablename__ = "tournaments"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    name: Mapped[str] = Column(String, unique=True, nullable=False, index=True)
    weight: Mapped[float] = Column(Float, default=1.0, nullable=False)

    matches: Mapped[List["Match"]] = relationship(
        "Match",
        back_populates="tournament",
        cascade="all, delete-orphan"
    )
    ranking_points: Mapped[List["PlayerRankingPoint"]] = relationship(
        "PlayerRankingPoint",
        back_populates="tournament",
        cascade="all, delete-orphan"
    )


class Match(Base):
    """
    Reprezentuje pojedyncze spotkanie (serię) między dwiema drużynami.

    Attributes:
        id (int): Unikalny identyfikator meczu.
        tournament_id (int): ID turnieju, w którym odbywa się mecz.
        phase (str): Faza turnieju (np. "Group Stage", "Final").
        date (date): Data rozegrania meczu.
        format (str): Format meczu (np. "BO1", "BO3").
        team1_id (int): ID pierwszej drużyny.
        team2_id (int): ID drugiej drużyny.
        result (str | None): Wynik końcowy (np. "2:1").
        tournament (Tournament): Obiekt turnieju.
        team1 (Team): Obiekt pierwszej drużyny.
        team2 (Team): Obiekt drugiej drużyny.
        maps (List[Map]): Lista rozegranych map.
        player_ratings (List[PlayerRating]): Oceny graczy z tego meczu.
    """
    __tablename__ = "matches"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    phase: Mapped[str] = Column(String, nullable=False)
    date: Mapped[date] = Column(Date, nullable=False)
    format: Mapped[str] = Column(String, nullable=False)
    team1_id: Mapped[int] = Column(Integer, ForeignKey("teams.id"), nullable=False)
    team2_id: Mapped[int] = Column(Integer, ForeignKey("teams.id"), nullable=False)
    result: Mapped[Optional[str]] = Column(String, nullable=True)

    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="matches")
    team1: Mapped["Team"] = relationship("Team", foreign_keys=[team1_id], back_populates="matches_as_team1")
    team2: Mapped["Team"] = relationship("Team", foreign_keys=[team2_id], back_populates="matches_as_team2")

    maps: Mapped[List["Map"]] = relationship(
        "Map",
        back_populates="match",
        cascade="all, delete-orphan"
    )
    player_ratings: Mapped[List["PlayerRating"]] = relationship(
        "PlayerRating",
        back_populates="match",
        cascade="all, delete-orphan"
    )


class Map(Base):
    """
    Reprezentuje konkretną mapę rozegraną w ramach meczu.

    Attributes:
        id (int): Unikalny identyfikator mapy.
        match_id (int): ID meczu, do którego należy mapa.
        map_name (str): Nazwa mapy (np. "Mirage", "Nuke").
        score (str): Wynik mapy (np. "13:10").
        match (Match): Obiekt meczu.
    """
    __tablename__ = "maps"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = Column(Integer, ForeignKey("matches.id"), nullable=False)
    map_name: Mapped[str] = Column(String, nullable=False)
    score: Mapped[str] = Column(String, nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="maps")


class PlayerRating(Base):
    """
    Reprezentuje ocenę (rating) gracza za występ w konkretnym meczu.

    Attributes:
        id (int): Unikalny identyfikator oceny.
        match_id (int): ID meczu.
        player_id (int): ID gracza.
        rating (float): Wartość oceny (np. 1.25).
        match (Match): Obiekt meczu.
        player (Player): Obiekt gracza.
    """
    __tablename__ = "player_ratings"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = Column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id: Mapped[int] = Column(Integer, ForeignKey("players.id"), nullable=False)
    rating: Mapped[float] = Column(Float, nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="player_ratings")
    player: Mapped["Player"] = relationship("Player", back_populates="ratings")


class PlayerRankingPoint(Base):
    """
    Reprezentuje punkty rankingowe przyznane graczowi za dany turniej.
    Służy do obliczania globalnego rankingu (punkty * waga turnieju).

    Attributes:
        id (int): Unikalny identyfikator wpisu punktowego.
        player_id (int): ID gracza.
        tournament_id (int): ID turnieju.
        points (float): Bazowa liczba punktów zdobyta w turnieju.
        player (Player): Obiekt gracza.
        tournament (Tournament): Obiekt turnieju.
    """
    __tablename__ = "player_ranking_points"

    id: Mapped[int] = Column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = Column(Integer, ForeignKey("players.id"), nullable=False)
    tournament_id: Mapped[int] = Column(Integer, ForeignKey("tournaments.id"), nullable=False)
    points: Mapped[float] = Column(Float, nullable=False)

    player: Mapped["Player"] = relationship("Player", back_populates="ranking_points")
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="ranking_points")