from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class PlayerStats(Base):
    __tablename__ = "player_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    game_id: Mapped[str] = mapped_column(String, ForeignKey("games_results.game_id"))
    player_id: Mapped[str] = mapped_column(String, ForeignKey("players.player_id"))
    team_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("teams.team_id"), nullable=True)
    stats_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    sport: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    league: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    minutes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    fantasy_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rebounds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    steals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blocks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turnovers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fouls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fg: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    three_pt: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ft: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    passing_yards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    passing_tds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    interceptions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rushing_yards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rushing_tds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    receiving_yards: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    receiving_tds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tackles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sacks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    forced_fumbles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    hits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rbi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    so: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pitch_ip: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    pitch_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pitch_bb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pitch_er: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    nhl_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_shots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_hits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_blocks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_plus_minus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalie_saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalie_ga: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalie_sv_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    epl_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_shots_on_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_tackles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    strikes_landed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strikes_attempted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    takedowns_landed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    takedowns_attempted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    control_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rounds_won: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    game: Mapped["GameResult"] = relationship(
        back_populates="player_stats", foreign_keys=[game_id]
    )
    player: Mapped["Player"] = relationship(
        back_populates="stats", foreign_keys=[player_id]
    )


# Compatibility alias for old code
PlayerStat = PlayerStats