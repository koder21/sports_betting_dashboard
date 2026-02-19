from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Standing(Base):
    __tablename__ = "standings"
    __table_args__ = (
        UniqueConstraint("team_id", "season_year", name="uq_standing_team_season"),
        Index("ix_standing_season_rank", "season_year", "rank"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    season_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    record: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    team: Mapped["Team"] = relationship("Team", backref="standings")

    def __repr__(self) -> str:
        return f"<Standing(team_id={self.team_id}, season={self.season_year}, rank={self.rank})>"
