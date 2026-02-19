from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    severity: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(1024), nullable=False)
    meta: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    __table_args__ = (
        Index("ix_alert_severity_ack", "severity", "acknowledged"),
    )

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, severity={self.severity}, ack={self.acknowledged})>"