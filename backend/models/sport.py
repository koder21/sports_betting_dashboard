from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Sport(Base):
    __tablename__: str = "sports" # type: ignore[assignment]

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    espn_league_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<Sport(id={self.id}, name={self.name!r}, code={self.espn_league_code!r})>"