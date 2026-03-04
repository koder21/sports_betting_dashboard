from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game
    
class GameLive(Base):
    __tablename__ = "games_live" # type: ignore[assignment]

    # ── Identity (shared PK with games) ──────────────────────────────────────
    game_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("games.game_id", ondelete="CASCADE"), primary_key=True
    )

    # ── Classification ────────────────────────────────────────────────────────
    sport: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── Teams ─────────────────────────────────────────────────────────────────
    home_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    home_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    away_logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ── Live state ────────────────────────────────────────────────────────────
    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    clock: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    possession: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Metadata ──────────────────────────────────────────────────────────────
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    game: Mapped["Game"] = relationship("Game", back_populates="live", foreign_keys=[game_id])

    __table_args__ = (
        Index("ix_live_sport_updated", "sport", "updated_at"),
    )

    def __repr__(self) -> str:
        return (
            f"<GameLive(game_id={self.game_id!r}, "
            f"{self.away_score}-{self.home_score}, "
            f"period={self.period!r})>"
        )