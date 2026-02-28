from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


from typing import Annotated

class Alert(Base):
    __tablename__: Annotated[str, Base.__tablename__] = "alerts"

    # ── Identity ──────────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, index=True
    )

    # ── Classification ────────────────────────────────────────────────────────
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # ── Content ───────────────────────────────────────────────────────────────
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    meta: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        # Most common query pattern: "unacknowledged alerts by severity"
        Index("ix_alert_severity_ack", "severity", "acknowledged"),
    )

    def __repr__(self) -> str:
        return (
            f"<Alert(id={self.id}, "
            f"severity={self.severity!r}, "
            f"category={self.category!r}, "
            f"ack={self.acknowledged})>"
        )