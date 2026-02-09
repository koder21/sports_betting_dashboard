from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .base import BaseRepository
from ..models import Alert


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Alert)

    async def list_unacknowledged(self) -> Sequence[Alert]:
        stmt = select(Alert).where(Alert.acknowledged.is_(False))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_all_as_read(self) -> None:
        stmt = update(Alert).where(Alert.acknowledged.is_(False)).values(acknowledged=True)
        await self.session.execute(stmt)