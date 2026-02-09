from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..services.alerts.manager import AlertManager

router = APIRouter()


@router.get("/")
async def list_alerts(session: AsyncSession = Depends(get_session)):
    svc = AlertManager(session)
    return await svc.list_unacknowledged()


@router.post("/{alert_id}/ack")
async def ack_alert(alert_id: int, session: AsyncSession = Depends(get_session)):
    svc = AlertManager(session)
    await svc.acknowledge(alert_id)
    return {"status": "ok"}


@router.post("/mark-all-read")
async def mark_all_read(session: AsyncSession = Depends(get_session)):
    svc = AlertManager(session)
    await svc.mark_all_as_read()
    return {"status": "ok"}