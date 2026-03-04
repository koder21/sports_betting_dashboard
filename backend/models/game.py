from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .games_results import GameResult
from .games_upcoming import GameUpcoming
from .games_live import GameLive
from .team import Team
from .sport import Sport

class Game(Base):
    """
    Core game record — a single source of truth for every contest.

    The three state sub-tables (GameUpcoming, GameLive, GameResult) hang off
    this row via one-to-one relationships. At most one of them should be
    populated at a time; the current lifecycle state is reflected by `status`.
    """

    __tablename__ = "games" # type: ignore[assignment]

    # ── Identity ──────────────────────────────────────────────────────────────
    game_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    
    # ── Classification ────────────────────────────────────────────────────────
    sport_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sport: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── Teams ─────────────────────────────────────────────────────────────────
    home_team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    away_team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Denormalised names for cheap display without a join
    home_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── Scores / live state ───────────────────────────────────────────────────
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Composite score string kept for backwards-compat ("21-14")
    score: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    clock: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # ── Blob data ─────────────────────────────────────────────────────────────
    lines_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    odds_history_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    play_by_play_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    boxscore_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    head_to_head_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    sport_rel: Mapped["Sport"] = relationship("Sport", backref="games")
    home_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[home_team_id], backref="home_games"
    )
    away_team: Mapped["Team"] = relationship(
        "Team", foreign_keys=[away_team_id], backref="away_games"
    )

    # One-to-one lifecycle states
    upcoming: Mapped[Optional["GameUpcoming"]] = relationship(
        "GameUpcoming", back_populates="game", uselist=False
    )
    live: Mapped[Optional["GameLive"]] = relationship(
        "GameLive", back_populates="game", uselist=False
    )
    result: Mapped[Optional["GameResult"]] = relationship(
        "GameResult", back_populates="game", uselist=False
    )

    __table_args__ = (
        Index("ix_games_sport_status", "sport", "status"),
        Index("ix_games_start_time_sport", "start_time", "sport"),
    )

    def __repr__(self) -> str:
        return (
            f"<Game(game_id={self.game_id!r}, "
            f"{self.away_team_name} @ {self.home_team_name}, "
            f"status={self.status!r})>"
        )