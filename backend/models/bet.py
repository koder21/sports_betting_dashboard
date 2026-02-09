from typing import Optional
from sqlalchemy import String, Float, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .base import Base


class Bet(Base):
    __tablename__ = "bets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    placed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sport_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports.id"), nullable=False)
    game_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("games.game_id"), nullable=True)
    player_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("players.player_id"), nullable=True)
    parlay_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    raw_text: Mapped[str] = mapped_column(String, nullable=False)
    original_stake: Mapped[float] = mapped_column(Float, nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    odds: Mapped[float] = mapped_column(Float, nullable=False)
    parlay_odds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    bet_type: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    selection: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    stat_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    player_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    graded_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    result_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    profit: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    sport = relationship("Sport", backref="bets", foreign_keys=[sport_id])
    game = relationship("Game", backref="bets", foreign_keys=[game_id])
    player = relationship("Player", backref="bets", foreign_keys=[player_id])