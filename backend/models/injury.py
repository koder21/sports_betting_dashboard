from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Injury(Base):
    __tablename__ = "injuries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(String, ForeignKey("players.player_id"))
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.team_id"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    last_updated: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    player: Mapped["Player"] = relationship("Player", backref="injuries")
    team: Mapped["Team"] = relationship("Team", backref="injuries")
