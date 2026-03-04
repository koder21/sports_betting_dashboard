from __future__ import annotations

from typing import Optional

from sqlalchemy import Index, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base
from .team import Team


class Standing(Base):
    __tablename__: str = "standings" # type: ignore[assignment]

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign key ───────────────────────────────────────────────────────────
    team_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("teams.team_id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # ── Season ────────────────────────────────────────────────────────────────
    season_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # ── Standing data ─────────────────────────────────────────────────────────
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    record: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    team: Mapped["Team"] = relationship("Team", backref="standings")

    __table_args__ = (
        UniqueConstraint("team_id", "season_year", name="uq_standing_team_season"),
        Index("ix_standing_season_rank", "season_year", "rank"),
    )

    def __repr__(self) -> str:
        return (
            f"<Standing(team_id={self.team_id!r}, "
            f"season={self.season_year}, "
            f"rank={self.rank})>"
        )