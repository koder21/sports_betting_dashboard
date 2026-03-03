from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Bet(Base):
    """
    A single wagered bet or one leg of a parlay.

    Parlay legs share a `parlay_id`; standalone bets leave it NULL.
    Lifecycle: pending → graded (won / lost / push / void).
    """

    __tablename__ = "bets"  # type: ignore[assignment]

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    placed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    sport_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    game_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("games.game_id", ondelete="SET NULL"), nullable=True, index=True
    )
    player_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("players.player_id", ondelete="SET NULL"), nullable=True, index=True
    )

    # ── Parlay grouping ───────────────────────────────────────────────────────
    parlay_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    # ── Wager details ─────────────────────────────────────────────────────────
    raw_text: Mapped[str] = mapped_column(String(512), nullable=False)
    original_stake: Mapped[float] = mapped_column(Float, nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    parlay_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Classification ────────────────────────────────────────────────────────
    bet_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    selection: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stat_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )

    # ── Result ────────────────────────────────────────────────────────────────
    result_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    sport = relationship("Sport", backref="bets", foreign_keys=[sport_id], lazy="joined")
    game = relationship("Game", backref="bets", foreign_keys=[game_id], lazy="select")
    player = relationship("Player", backref="bets", foreign_keys=[player_id], lazy="select")

    # ── Composite indexes ─────────────────────────────────────────────────────
    __table_args__ = (
        # "All pending bets for a sport"
        Index("ix_bets_sport_status", "sport_id", "status"),
        # "All bets for a game"
        Index("ix_bets_game_status", "game_id", "status"),
        # "Recent bets dashboard"
        Index("ix_bets_placed_at_status", "placed_at", "status"),
        # Partial index — only rows that actually belong to a parlay
        Index(
            "ix_bets_parlay",
            "parlay_id",
            postgresql_where="parlay_id IS NOT NULL",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<Bet(id={self.id}, "
            f"status={self.status!r}, "
            f"stake={self.stake}, "
            f"odds={self.odds}, "
            f"parlay_id={self.parlay_id!r})>"
        )