from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..db import get_session
from ..services.alerts.manager import AlertManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def list_alerts(session: AsyncSession = Depends(get_session)):
    """List all unacknowledged alerts"""
    try:
        svc = AlertManager(session)
        return await svc.list_unacknowledged()
    except Exception as e:
        logger.error("[Alerts] Failed to list alerts: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve alerts: {str(e)}")


@router.post("/{alert_id}/ack")
async def ack_alert(alert_id: int, session: AsyncSession = Depends(get_session)):
    """Mark an alert as acknowledged"""
    try:
        svc = AlertManager(session)
        await svc.acknowledge(alert_id)
        return {"status": "ok", "message": f"Alert {alert_id} acknowledged"}
    except Exception as e:
        logger.error("[Alerts] Failed to acknowledge alert %s: %s", alert_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.post("/mark-all-read")
async def mark_all_read(session: AsyncSession = Depends(get_session)):
    """Mark all alerts as read"""
    try:
        svc = AlertManager(session)
        await svc.mark_all_as_read()
        return {"status": "ok", "message": "All alerts marked as read"}
    except Exception as e:
        logger.error("[Alerts] Failed to mark all as read: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark alerts as read: {str(e)}")