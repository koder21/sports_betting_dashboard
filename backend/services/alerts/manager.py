from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.alert_repo import AlertRepository
from ...models.alert import Alert
from .queue import AlertQueue


class AlertManager:
    def __init__(self, session: Optional[AsyncSession] = None, session_factory: Optional[Callable[[], AsyncSession]] = None):
        self.session = session
        self.session_factory = session_factory
        self.alerts = AlertRepository(session) if session else None
        self.queue = AlertQueue(session=session, session_factory=session_factory)

    async def create(self, severity: str, category: str, message: str, metadata: Any = "") -> None:
        """Create an alert (immediate if session provided, else queue)"""
        import json
        meta_str = metadata
        if isinstance(metadata, (dict, list)):
            try:
                meta_str = json.dumps(metadata)
            except Exception:
                meta_str = "{}"  # fallback to empty JSON
        elif isinstance(metadata, str):
            # Validate if string is valid JSON
            try:
                json.loads(metadata)
            except Exception:
                meta_str = "{}"  # fallback to empty JSON
        if self.session and self.alerts:
            alert = Alert(
                created_at=datetime.utcnow(),
                severity=severity,
                category=category,
                message=message,
                meta=meta_str,
                acknowledged=False,
            )
            self.alerts.add(alert)
            await self.session.commit()
            return

        self.queue.enqueue(severity, category, message, meta_str)
        # Explicitly return None for queued alerts
        return None

    async def list_unacknowledged(self) -> List[Dict[str, Any]]:
        if self.session and self.alerts:
            items = await self.alerts.list_unacknowledged()
        elif self.session_factory:
            async with self.session_factory() as session:
                repo = AlertRepository(session)
                items = await repo.list_unacknowledged()
        else:
            items = []
        import json
        result = []
        for a in items:
            meta = a.meta
            meta_dict = {}
            if meta:
                try:
                    meta_dict = json.loads(meta)
                except Exception:
                    meta_dict = {}
            result.append({
                "id": a.id,
                "created_at": a.created_at.isoformat(),
                "severity": a.severity,
                "category": a.category,
                "message": a.message,
                "metadata": meta_dict,
            })
        return result

    async def acknowledge(self, alert_id: int) -> None:
        if self.session and self.alerts:
            alert = await self.alerts.get(alert_id)
            if alert:
                alert.acknowledged = True
                await self.session.commit()
        elif self.session_factory:
            async with self.session_factory() as session:
                repo = AlertRepository(session)
                alert = await repo.get(alert_id)
                if alert:
                    alert.acknowledged = True
                    await session.commit()

    async def mark_all_as_read(self) -> None:
        if self.session and self.alerts:
            await self.alerts.mark_all_as_read()
            await self.session.commit()
        elif self.session_factory:
            async with self.session_factory() as session:
                repo = AlertRepository(session)
                await repo.mark_all_as_read()
                await session.commit()