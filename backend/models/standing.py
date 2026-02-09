from __future__ import annotations

from typing import Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base


class Standing(Base):
    __tablename__ = "standings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[str] = mapped_column(String, ForeignKey("teams.team_id"))
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    record: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    season_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    team: Mapped["Team"] = relationship("Team", backref="standings")
