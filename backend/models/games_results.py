from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game
    from .team import Team
from .player_stats import PlayerStats

class GameResult(Base):
    __tablename__ = "games_results"  # type: ignore[assignment]

    # ── Identity (shared PK with games) ──────────────────────────────────────
    game_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("games.game_id", ondelete="CASCADE"), primary_key=True
    )

    # ── Classification ────────────────────────────────────────────────────────
    sport: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    season: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    season_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    week: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    round: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Timing / venue ────────────────────────────────────────────────────────
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    attendance: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    referees: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    weather: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # ── Teams (FK + denormalised display cols) ────────────────────────────────
    home_team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    away_team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    home_team_name: Mapped[Optional[str]] = mapped_column("home_team", String(128), nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column("away_team", String(128), nullable=True)
    home_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    away_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ── Final scores ──────────────────────────────────────────────────────────
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    moved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    game: Mapped["Game"] = relationship("Game", back_populates="result", foreign_keys=[game_id])
    home_team_obj: Mapped["Team"] = relationship(
        back_populates="results_home_games", foreign_keys=[home_team_id]
    )
    away_team_obj: Mapped["Team"] = relationship(
        back_populates="results_away_games", foreign_keys=[away_team_id]
    )
    player_stats: Mapped[list["PlayerStats"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        foreign_keys="PlayerStats.game_id",
    )

    __table_args__ = (
        Index("ix_results_sport_start", "sport", "start_time"),
    )

    def __repr__(self) -> str:
        return (
            f"<GameResult(game_id={self.game_id!r}, "
            f"{self.away_team_name} {self.away_score} @ "
            f"{self.home_team_name} {self.home_score})>"
        )