from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Player(Base):
    __tablename__ = "players"

    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    espn_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    season_stats_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    espn_ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    team_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("teams.team_id"))
    team: Mapped["Team"] = relationship("Team", back_populates="players")

    sport: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    headshot: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    jersey: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    height: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    weight: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    birthdate: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # Relationship to player stats
    stats: Mapped[list["PlayerStats"]] = relationship(back_populates="player")