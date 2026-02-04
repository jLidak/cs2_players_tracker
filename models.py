from __future__ import annotations  # <--- TA LINIA NAPRAWIA BŁĄD W PYTHON 3.9

"""
Modele SQLAlchemy (wersja 2.0 style) z poprawnymi adnotacjami typów (Mapped).
Zastosowano mapped_column oraz 'from __future__ import annotations' dla kompatybilności.
"""

from typing import List, Optional
from datetime import date
from sqlalchemy import Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base

class Team(Base):
    """
    Reprezentuje drużynę.
    """
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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
    """
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)

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
    """
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

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
    Reprezentuje pojedyncze spotkanie (serię).
    """
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)

    # Dzięki 'from __future__ import annotations' ta linia przestanie powodować błąd
    date: Mapped[date] = mapped_column(Date, nullable=False)

    format: Mapped[str] = mapped_column(String, nullable=False)
    team1_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    team2_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    result: Mapped[Optional[str]] = mapped_column(String, nullable=True)

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
    Reprezentuje konkretną mapę w meczu.
    """
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    map_name: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[str] = mapped_column(String, nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="maps")


class PlayerRating(Base):
    """
    Reprezentuje ocenę gracza.
    """
    __tablename__ = "player_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="player_ratings")
    player: Mapped["Player"] = relationship("Player", back_populates="ratings")


class PlayerRankingPoint(Base):
    """
    Reprezentuje punkty rankingowe.
    """
    __tablename__ = "player_ranking_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)

    player: Mapped["Player"] = relationship("Player", back_populates="ranking_points")
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="ranking_points")