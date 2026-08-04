"""
SQLAlchemy database models for the CS2 Player Tracker application.

This module defines the relational database schema, including teams, players,
tournaments, matches, and the performance metrics required for ranking calculations.
It utilizes SQLAlchemy 2.0 syntax (Mapped and mapped_column) for robust type hinting.
"""

from __future__ import annotations

from typing import List, Optional, Any
from datetime import date, datetime

from sqlalchemy import Integer, String, Float, Boolean, ForeignKey, Date, JSON, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column

from database import Base


class Team(Base):
    """
    Represents a Counter-Strike 2 team.
    Teams consist of multiple players and participate in multiple tournaments.
    """

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    players: Mapped[List["Player"]] = relationship(
        "Player", back_populates="team", cascade="all, delete-orphan"
    )
    tournament_participations: Mapped[List["TournamentTeam"]] = relationship(
        "TournamentTeam", back_populates="team", cascade="all, delete-orphan"
    )
    matches_as_team1: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.team1_id",
        back_populates="team1",
        cascade="all, delete-orphan",
    )
    matches_as_team2: Mapped[List["Match"]] = relationship(
        "Match",
        foreign_keys="Match.team2_id",
        back_populates="team2",
        cascade="all, delete-orphan",
    )


class Player(Base):
    """
    Represents an individual Counter-Strike 2 player.
    A player belongs to one team at a time and accumulates tournament performances.
    """

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = mapped_column(
        String, unique=True, nullable=False, index=True
    )
    photo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )

    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="players")
    ratings: Mapped[List["PlayerRating"]] = relationship(
        "PlayerRating", back_populates="player", cascade="all, delete-orphan"
    )
    tournament_performances: Mapped[List["PlayerTournamentPerformance"]] = relationship(
        "PlayerTournamentPerformance",
        back_populates="player",
        cascade="all, delete-orphan",
    )


class Tournament(Base):
    """
    Represents a specific tournament event.
    Stores the configuration weights needed to calculate ranking points for this event.
    """

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    bracket_type: Mapped[str] = mapped_column(String, default="Bracket 8 teams")
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    has_third_place: Mapped[bool] = mapped_column(Boolean, default=False)

    weight_third_place: Mapped[float] = mapped_column(Float, default=0.1)
    weight_group: Mapped[float] = mapped_column(Float, default=0.4)
    weight_quarters: Mapped[float] = mapped_column(Float, default=0.2)
    weight_semis: Mapped[float] = mapped_column(Float, default=0.2)
    weight_final: Mapped[float] = mapped_column(Float, default=0.2)

    # Overrides used specifically for 'Bracket 6 teams' format
    weight_group_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_semis_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_final_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    matches: Mapped[List["Match"]] = relationship(
        "Match", back_populates="tournament", cascade="all, delete-orphan"
    )
    participating_teams: Mapped[List["TournamentTeam"]] = relationship(
        "TournamentTeam", back_populates="tournament", cascade="all, delete-orphan"
    )
    player_performances: Mapped[List["PlayerTournamentPerformance"]] = relationship(
        "PlayerTournamentPerformance",
        back_populates="tournament",
        cascade="all, delete-orphan",
    )


class TournamentTeam(Base):
    """
    Association table representing a team's participation in a specific tournament.
    Tracks which phases the team reached and how many rounds they played in each phase.
    """

    __tablename__ = "tournament_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )

    starts_in_semis: Mapped[bool] = mapped_column(Boolean, default=False)

    # Boolean flags tracking phase participation
    in_group: Mapped[bool] = mapped_column(Boolean, default=True)
    in_quarters: Mapped[bool] = mapped_column(Boolean, default=False)
    in_semis: Mapped[bool] = mapped_column(Boolean, default=False)
    in_final: Mapped[bool] = mapped_column(Boolean, default=False)
    in_third_place: Mapped[bool] = mapped_column(Boolean, default=False)

    # Integer values tracking rounds played per phase
    rounds_group: Mapped[int] = mapped_column(Integer, default=1)
    rounds_quarters: Mapped[int] = mapped_column(Integer, default=1)
    rounds_semis: Mapped[int] = mapped_column(Integer, default=1)
    rounds_final: Mapped[int] = mapped_column(Integer, default=1)
    rounds_third_place: Mapped[int] = mapped_column(Integer, default=0)

    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="participating_teams"
    )
    team: Mapped["Team"] = relationship(
        "Team", back_populates="tournament_participations"
    )


class PlayerTournamentPerformance(Base):
    """
    Stores the aggregated ratings of a specific player during different phases
    of a single tournament. Crucial for dynamic point calculations.
    """

    __tablename__ = "player_tournament_performances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False
    )

    rating_group: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_quarters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_semis: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_third_place: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_final: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    player: Mapped["Player"] = relationship(
        "Player", back_populates="tournament_performances"
    )
    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="player_performances"
    )


class Match(Base):
    """
    Legacy model: Represents a single match between two teams within a tournament.
    """

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False
    )
    phase: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    team1_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    team2_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=False
    )
    result: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    tournament: Mapped["Tournament"] = relationship(
        "Tournament", back_populates="matches"
    )
    team1: Mapped["Team"] = relationship(
        "Team", foreign_keys=[team1_id], back_populates="matches_as_team1"
    )
    team2: Mapped["Team"] = relationship(
        "Team", foreign_keys=[team2_id], back_populates="matches_as_team2"
    )
    maps: Mapped[List["Map"]] = relationship(
        "Map", back_populates="match", cascade="all, delete-orphan"
    )
    player_ratings: Mapped[List["PlayerRating"]] = relationship(
        "PlayerRating", back_populates="match", cascade="all, delete-orphan"
    )


class Map(Base):
    """
    Legacy model: Represents a single map played during a match.
    """

    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    map_name: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[str] = mapped_column(String, nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="maps")


class PlayerRating(Base):
    """
    Legacy model: Stores the individual rating of a player for a specific match.
    """

    __tablename__ = "player_ratings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("matches.id"), nullable=False
    )
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    rating: Mapped[float] = mapped_column(Float, nullable=False)

    match: Mapped["Match"] = relationship("Match", back_populates="player_ratings")
    player: Mapped["Player"] = relationship("Player", back_populates="ratings")


class PlayerRankingPoint(Base):
    """
    Legacy model: Previously stored pre-calculated ranking points.
    Currently, ranking points are calculated dynamically on-the-fly.
    """

    __tablename__ = "player_ranking_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("players.id"), nullable=False
    )
    tournament_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tournaments.id"), nullable=False
    )
    points: Mapped[float] = mapped_column(Float, nullable=False)


class CustomRankingPreset(Base):
    """
    Stores user-defined ranking configurations (presets) containing
    custom math parameters, bonus values, and overridden tournament weights.
    """

    __tablename__ = "custom_ranking_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    settings: Mapped[Any] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
