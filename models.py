from __future__ import annotations
from typing import List, Optional
from datetime import date
from sqlalchemy import Integer, String, Float, ForeignKey, Date, Boolean
from sqlalchemy.orm import relationship, Mapped, mapped_column
from database import Base


class Team(Base):
    __tablename__ = "teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    players: Mapped[List["Player"]] = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    tournament_participations: Mapped[List["TournamentTeam"]] = relationship("TournamentTeam", back_populates="team",
                                                                             cascade="all, delete-orphan")
    matches_as_team1: Mapped[List["Match"]] = relationship("Match", foreign_keys="Match.team1_id",
                                                           back_populates="team1", cascade="all, delete-orphan")
    matches_as_team2: Mapped[List["Match"]] = relationship("Match", foreign_keys="Match.team2_id",
                                                           back_populates="team2", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nickname: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    team_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("teams.id"), nullable=True)
    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="players")
    ratings: Mapped[List["PlayerRating"]] = relationship("PlayerRating", back_populates="player",
                                                         cascade="all, delete-orphan")
    tournament_performances: Mapped[List["PlayerTournamentPerformance"]] = relationship("PlayerTournamentPerformance",
                                                                                        back_populates="player",
                                                                                        cascade="all, delete-orphan")


class Tournament(Base):
    __tablename__ = "tournaments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    bracket_type: Mapped[str] = mapped_column(String, default="Bracket 8 teams")
    weight: Mapped[float] = mapped_column(Float, default=1.0)

    # --- ZMIANA NAZEWNICTWA ---
    weight_group: Mapped[float] = mapped_column(Float, default=0.4)  # Zamiast weight_overall
    # --------------------------

    weight_quarters: Mapped[float] = mapped_column(Float, default=0.2)
    weight_semis: Mapped[float] = mapped_column(Float, default=0.2)
    weight_final: Mapped[float] = mapped_column(Float, default=0.2)
    weight_semis_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight_final_override: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    matches: Mapped[List["Match"]] = relationship("Match", back_populates="tournament", cascade="all, delete-orphan")
    participating_teams: Mapped[List["TournamentTeam"]] = relationship("TournamentTeam", back_populates="tournament",
                                                                       cascade="all, delete-orphan")
    player_performances: Mapped[List["PlayerTournamentPerformance"]] = relationship("PlayerTournamentPerformance",
                                                                                    back_populates="tournament",
                                                                                    cascade="all, delete-orphan")


class TournamentTeam(Base):
    __tablename__ = "tournament_teams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    starts_in_semis: Mapped[bool] = mapped_column(Boolean, default=False)
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="participating_teams")
    team: Mapped["Team"] = relationship("Team", back_populates="tournament_participations")

    # --- NOWE POLA: LICZBA RUND ---
    rounds_group: Mapped[int] = mapped_column(Integer, default=1)
    rounds_quarters: Mapped[int] = mapped_column(Integer, default=1)
    rounds_semis: Mapped[int] = mapped_column(Integer, default=1)
    rounds_final: Mapped[int] = mapped_column(Integer, default=1)


class PlayerTournamentPerformance(Base):
    __tablename__ = "player_tournament_performances"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)

    # --- ZMIANA NAZEWNICTWA ---
    rating_group: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Zamiast rating_overall
    # --------------------------

    rating_quarters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_semis: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating_final: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    player: Mapped["Player"] = relationship("Player", back_populates="tournament_performances")
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="player_performances")


# --- Legacy Models (Bez zmian) ---
class Match(Base):
    __tablename__ = "matches"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    phase: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    format: Mapped[str] = mapped_column(String, nullable=False)
    team1_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    team2_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"), nullable=False)
    result: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tournament: Mapped["Tournament"] = relationship("Tournament", back_populates="matches")
    team1: Mapped["Team"] = relationship("Team", foreign_keys=[team1_id], back_populates="matches_as_team1")
    team2: Mapped["Team"] = relationship("Team", foreign_keys=[team2_id], back_populates="matches_as_team2")
    maps: Mapped[List["Map"]] = relationship("Map", back_populates="match", cascade="all, delete-orphan")
    player_ratings: Mapped[List["PlayerRating"]] = relationship("PlayerRating", back_populates="match",
                                                                cascade="all, delete-orphan")


class Map(Base):
    __tablename__ = "maps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    map_name: Mapped[str] = mapped_column(String, nullable=False)
    score: Mapped[str] = mapped_column(String, nullable=False)
    match: Mapped["Match"] = relationship("Match", back_populates="maps")


class PlayerRating(Base):
    __tablename__ = "player_ratings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=False)
    match: Mapped["Match"] = relationship("Match", back_populates="player_ratings")
    player: Mapped["Player"] = relationship("Player", back_populates="ratings")


class PlayerRankingPoint(Base):
    __tablename__ = "player_ranking_points"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    tournament_id: Mapped[int] = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)