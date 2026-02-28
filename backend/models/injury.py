from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .game import Game
    from .team import Team
    from .player import Player

class Injury(Base):
    __tablename__: str = "injuries"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
     # ── Foreign keys ─────────────────────────────────────────────────────────
    player_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("players.player_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    team_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    game_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("games.game_id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    # ── Details ───────────────────────────────────────────────────────────────
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    # ── Relationships ─────────────────────────────────────────────────────────
    player: Mapped["Player"] = relationship("Player", backref="injuries")
    team: Mapped["Team"] = relationship("Team", backref="injuries")
    game: Mapped[Optional["Game"]] = relationship("Game", backref="injuries")
    # ── Constraints / indexes ─────────────────────────────────────────────────
    __table_args__ = (
        # Prevent duplicate injury reports for the same player+team+description
        UniqueConstraint("player_id", "team_id", "description", name="uq_injury_player_team_desc"),
        Index("ix_injuries_status", "status"),
    )

    def __repr__(self) -> str:
        return (
            f"<Injury(id={self.id}, "
            f"player_id={self.player_id!r}, "
            f"status={self.status!r})>"
        )