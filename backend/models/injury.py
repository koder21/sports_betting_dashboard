from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base



class Injury(Base):
    __tablename__ = "injuries"
    __table_args__ = (
        UniqueConstraint(
            "player_id", "team_id", "description",
            name="uq_injury_player_team_desc"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("players.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    team_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    description: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(64))
    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    player: Mapped["Player"] = relationship("Player", backref="injuries")
    team: Mapped["Team"] = relationship("Team", backref="injuries")
