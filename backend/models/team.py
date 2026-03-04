from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .games_upcoming import GameUpcoming
    from .games_results import GameResult
    from .player import Player
    from .sport import Sport


class Team(Base):
    __tablename__: str = "teams" # type: ignore[assignment]

    # ── Identity ──────────────────────────────────────────────────────────────
    team_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    espn_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── Display ───────────────────────────────────────────────────────────────
    name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    abbreviation: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    logo: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    color_primary: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    color_secondary: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # ── Classification ────────────────────────────────────────────────────────
    sport_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sport_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    conference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    division: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    # ── Venue / record ────────────────────────────────────────────────────────
    stadium: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    record: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Blob data ─────────────────────────────────────────────────────────────
    stats_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    sport: Mapped["Sport"] = relationship("Sport", backref="teams")
    players: Mapped[list["Player"]] = relationship(back_populates="team")

    upcoming_home_games: Mapped[list["GameUpcoming"]] = relationship(
        back_populates="home_team_obj", foreign_keys="GameUpcoming.home_team_id"
    )
    upcoming_away_games: Mapped[list["GameUpcoming"]] = relationship(
        back_populates="away_team_obj", foreign_keys="GameUpcoming.away_team_id"
    )
    results_home_games: Mapped[list["GameResult"]] = relationship(
        back_populates="home_team_obj", foreign_keys="GameResult.home_team_id"
    )
    results_away_games: Mapped[list["GameResult"]] = relationship(
        back_populates="away_team_obj", foreign_keys="GameResult.away_team_id"
    )

    __table_args__ = (
        Index("ix_teams_sport_id", "sport_id"),
        Index("ix_teams_league", "league"),
    )

    def __repr__(self) -> str:
        return f"<Team(team_id={self.team_id!r}, name={self.name!r})>"