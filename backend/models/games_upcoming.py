from __future__ import annotations
from typing import Optional
from sqlalchemy import String, Boolean, Integer, Float, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class GameUpcoming(Base):
    __tablename__ = "games_upcoming"

    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.game_id"), primary_key=True
    )

    sport: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    season: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    season_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    round: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    broadcast: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    weather: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    neutral_site: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Team IDs (string)
    home_team_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("teams.team_id"), nullable=True)
    away_team_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("teams.team_id"), nullable=True)

    # Relationships to Team
    home_team: Mapped["Team"] = relationship(
        back_populates="upcoming_home_games",
        foreign_keys=[home_team_id]
    )
    away_team: Mapped["Team"] = relationship(
        back_populates="upcoming_away_games",
        foreign_keys=[away_team_id]
    )

    # Display metadata
    home_team_name: Mapped[Optional[str]] = mapped_column("home_team", String, nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column("away_team", String, nullable=True)
    home_logo: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    away_logo: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Odds
    odds_home: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    odds_away: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread_home: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread_away: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Link to core Game
    game: Mapped["Game"] = relationship(
        "Game", back_populates="upcoming", foreign_keys=[game_id]
    )