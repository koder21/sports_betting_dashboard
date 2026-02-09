from typing import Dict, Any, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ...repositories.alert_repo import AlertRepository


class AlertService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.alerts = AlertRepository(session)

    async def create_alert(self, severity: str, category: str, message: str, metadata: str = ""):
        from ...models.alert import Alert

        alert = Alert(
            created_at=datetime.utcnow(),
            severity=severity,
            category=category,
            message=message,
            meta=metadata,
            acknowledged=False,
        )
        await self.alerts.add(alert)
        await self.session.commit()

    async def list_alerts(self) -> List[Dict[str, Any]]:
        items = await self.alerts.list_unacknowledged()
        return [
            {
                "id": a.id,
                "created_at": a.created_at.isoformat(),
                "severity": a.severity,
                "category": a.category,
                "message": a.message,
                "metadata": a.meta,
            }
            for a in items
        ]