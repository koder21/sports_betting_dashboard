"""Optimized Bet model with proper indexes and constraints."""
from __future__ import annotations

from typing import Optional
from datetime import datetime
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Bet(Base):
    """
    Betting records with comprehensive tracking.
    
    Optimizations:
    - Added indexes on all foreign keys
    - Added composite indexes for common queries
    - Added cascade delete policies
    - Added default timestamp
    - Added __repr__ for debugging
    """
    __tablename__ = "bets"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Timestamps with defaults
    placed_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True  # Common filter
    )
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Foreign keys with indexes and cascade
    sport_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("sports.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    game_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("games.game_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    player_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        ForeignKey("players.player_id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Parlay grouping with index
    parlay_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        index=True  # For grouping parlay legs
    )

    # Bet details with length limits
    raw_text: Mapped[str] = mapped_column(String(512), nullable=False)
    original_stake: Mapped[float] = mapped_column(Float, nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    parlay_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Classification fields with length limits
    bet_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    market: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    selection: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stat_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)  # Increased limit
    
    # Status tracking with default and index
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        index=True  # Very common filter
    )
    
    # Results
    result_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships with lazy loading strategy
    sport = relationship(
        "Sport",
        backref="bets",
        foreign_keys=[sport_id],
        lazy="joined"  # Commonly accessed together
    )
    game = relationship(
        "Game",
        backref="bets",
        foreign_keys=[game_id],
        lazy="select"
    )
    player = relationship(
        "Player",
        backref="bets",
        foreign_keys=[player_id],
        lazy="select"
    )
    
    # Composite indexes for common queries
    __table_args__ = (
        # Query: "Get all pending bets for a sport"
        Index("ix_bets_sport_status", "sport_id", "status"),
        # Query: "Get all bets for a parlay"
        Index("ix_bets_parlay", "parlay_id", postgresql_where="parlay_id IS NOT NULL"),
        # Query: "Get recent bets"
        Index("ix_bets_placed_at_status", "placed_at", "status"),
        # Query: "Get all bets for a game"
        Index("ix_bets_game_status", "game_id", "status"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<Bet(id={self.id}, "
            f"status={self.status}, "
            f"stake={self.stake}, "
            f"odds={self.odds}, "
            f"parlay_id={self.parlay_id})>"
        )