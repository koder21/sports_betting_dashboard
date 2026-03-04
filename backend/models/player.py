from __future__ import annotations

from typing import Optional

from sqlalchemy import Boolean, Index, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .player_stats import PlayerStats
from .team import Team


class Player(Base):
    __tablename__: str = "players" # type: ignore[assignment]

    # ── Identity ──────────────────────────────────────────────────────────────
    player_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    espn_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    espn_ref: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    # ── Name ──────────────────────────────────────────────────────────────────
    full_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── Team / sport ──────────────────────────────────────────────────────────
    team_id: Mapped[Optional[str]] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="SET NULL"), nullable=True, index=True
    )
    sport: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── Profile ───────────────────────────────────────────────────────────────
    position: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    headshot: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    jersey: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    height: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    weight: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    birthdate: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    nationality: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    active: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)

    # ── Blob data ─────────────────────────────────────────────────────────────
    season_stats_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    team: Mapped["Team"] = relationship("Team", back_populates="players")
    stats: Mapped[list["PlayerStats"]] = relationship(back_populates="player")

    __table_args__ = (
        Index("ix_players_sport_active", "sport", "active"),
    )

    def __repr__(self) -> str:
        return f"<Player(player_id={self.player_id!r}, name={self.full_name!r})>"