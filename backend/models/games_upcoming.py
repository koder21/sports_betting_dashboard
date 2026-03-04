from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game
    from .team import Team


class GameUpcoming(Base):
    __tablename__ = "games_upcoming" # type: ignore[assignment]

    # ── Identity (shared PK with games) ──────────────────────────────────────
    game_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("games.game_id", ondelete="CASCADE"), primary_key=True
    )

    # ── Classification ────────────────────────────────────────────────────────
    sport: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    season: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    season_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    round: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Scheduling ────────────────────────────────────────────────────────────
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    broadcast: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    weather: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    neutral_site: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # ── Teams ─────────────────────────────────────────────────────────────────
    home_team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    away_team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    home_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    home_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    away_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ── Odds ──────────────────────────────────────────────────────────────────
    odds_home: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    odds_away: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread_home: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    spread_away: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    scraped_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=datetime.utcnow, index=True
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    game: Mapped["Game"] = relationship("Game", back_populates="upcoming", foreign_keys=[game_id])
    home_team_obj: Mapped["Team"] = relationship(
        back_populates="upcoming_home_games", foreign_keys=[home_team_id]
    )
    away_team_obj: Mapped["Team"] = relationship(
        back_populates="upcoming_away_games", foreign_keys=[away_team_id]
    )

    __table_args__ = (
        Index("ix_upcoming_sport_start", "sport", "start_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<GameUpcoming(game_id={self.game_id!r}, "
            f"{self.away_team_name} @ {self.home_team_name}, "
            f"start={self.start_time})>"
        )