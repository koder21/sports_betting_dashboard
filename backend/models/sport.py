from typing import Optional
from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import DateTime
from .base import Base


class Sport(Base):
    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    espn_league_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    league: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
