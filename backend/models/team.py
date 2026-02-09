from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Team(Base):
    __tablename__ = "teams"

    team_id: Mapped[str] = mapped_column(String, primary_key=True)
    espn_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    abbreviation: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    record: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stats_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    sport_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sports.id"))
    sport: Mapped["Sport"] = relationship("Sport", backref="teams")

    sport_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    logo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color_primary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    color_secondary: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    stadium: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    conference: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    division: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships to players
    players: Mapped[list["Player"]] = relationship(back_populates="team")

    # Relationships to games (new ingestion)
    upcoming_home_games: Mapped[list["GameUpcoming"]] = relationship(
        back_populates="home_team", foreign_keys="GameUpcoming.home_team_id"
    )
    upcoming_away_games: Mapped[list["GameUpcoming"]] = relationship(
        back_populates="away_team", foreign_keys="GameUpcoming.away_team_id"
    )
    results_home_games: Mapped[list["GameResult"]] = relationship(
        back_populates="home_team", foreign_keys="GameResult.home_team_id"
    )
    results_away_games: Mapped[list["GameResult"]] = relationship(
        back_populates="away_team", foreign_keys="GameResult.away_team_id"
    )