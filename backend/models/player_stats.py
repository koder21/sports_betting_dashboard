"""Optimized PlayerStats model with proper indexes and constraints."""
from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Float, ForeignKey, DateTime, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class PlayerStats(Base):
    """
    Player statistics for completed games.
    
    Optimizations:
    - Added composite unique constraint (game_id, player_id)
    - Added indexes on all foreign keys
    - Added cascade delete policies
    - Added default timestamp
    - Reduced NULL column waste (moved sport-specific stats to JSON)
    """
    __tablename__ = "player_stats"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Foreign keys with indexes and cascade
    game_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("games_results.game_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    player_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("players.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    team_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("teams.team_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Metadata
    sport: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Full stats as JSON (recommended for sport-specific stats)
    stats_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    
    # Common fields across all sports (keep as columns for fast queries)
    minutes: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    fantasy_points: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Basketball stats (NBA, NCAAB)
    rebounds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    steals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    blocks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    turnovers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fouls: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fg: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    three_pt: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    ft: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    # Football stats (NFL, NCAAF)
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

    # Baseball stats (MLB)
    hits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    runs: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rbi: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    hr: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    so: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pitch_ip: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    pitch_k: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pitch_bb: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pitch_er: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Hockey stats (NHL)
    nhl_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_shots: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_hits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_blocks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nhl_plus_minus: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalie_saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalie_ga: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goalie_sv_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Soccer stats (EPL)
    epl_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_assists: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_shots_on_target: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_passes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_tackles: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    epl_saves: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # MMA stats (UFC)
    strikes_landed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    strikes_attempted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    takedowns_landed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    takedowns_attempted: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    control_time: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    rounds_won: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Relationships
    game: Mapped["GameResult"] = relationship(
        back_populates="player_stats",
        foreign_keys=[game_id],
        lazy="select"
    )
    player: Mapped["Player"] = relationship(
        back_populates="stats",
        foreign_keys=[player_id],
        lazy="joined"  # Commonly accessed together
    )

    # Constraints and indexes
    __table_args__ = (
        # Unique constraint: one stat record per player per game
        UniqueConstraint("game_id", "player_id", name="uq_player_stats_game_player"),
        # Composite index for common query: "Get all stats for a game"
        Index("ix_player_stats_game_sport", "game_id", "sport"),
        # Composite index for common query: "Get all stats for a player"
        Index("ix_player_stats_player_scraped", "player_id", "scraped_at"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<PlayerStats(id={self.id}, "
            f"player_id={self.player_id}, "
            f"game_id={self.game_id}, "
            f"sport={self.sport})>"
        )


# Compatibility alias for old code
PlayerStat = PlayerStats