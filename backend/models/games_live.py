from __future__ import annotations
from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base

class GameLive(Base):
    __tablename__ = "games_live"

    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.game_id"), primary_key=True
    )

    sport: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    home_team_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    away_team_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    home_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    clock: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    period: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    possession: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Link to core Game only
    game: Mapped["Game"] = relationship(
        "Game", back_populates="live", foreign_keys=[game_id]
    )