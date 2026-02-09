from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Game(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String, primary_key=True)
    sport: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sport_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sports.id"), nullable=True)

    home_team_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("teams.team_id"), nullable=True)
    away_team_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("teams.team_id"), nullable=True)
    home_team_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    clock: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    score: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    lines_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    odds_history_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    play_by_play_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    boxscore_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    head_to_head_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    sport_rel: Mapped["Sport"] = relationship("Sport", backref="games")

    home_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[home_team_id], backref="home_games"
    )
    away_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[away_team_id], backref="away_games"
    )

    # State relationships (one-to-one)
    upcoming: Mapped[Optional["GameUpcoming"]] = relationship(
        "GameUpcoming", back_populates="game", uselist=False
    )
    live: Mapped[Optional["GameLive"]] = relationship(
        "GameLive", back_populates="game", uselist=False
    )
    result: Mapped[Optional["GameResult"]] = relationship(
        "GameResult", back_populates="game", uselist=False
    )