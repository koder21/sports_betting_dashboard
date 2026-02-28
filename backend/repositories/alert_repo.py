from typing import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.alert import Alert
from .base import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    """
    Repository for Alert management.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(Alert, session)

    async def list_unacknowledged(
        self,
        *,
        limit: int = BaseRepository.DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Sequence[Alert]:
        if limit <= 0:
            raise ValueError("Limit must be > 0")

        stmt = (
            select(Alert)
            .where(Alert.acknowledged.is_(False))
            .limit(limit)
            .offset(offset)
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def mark_all_as_read(self) -> int:
        """
        Marks all unacknowledged alerts as read.
        Returns the count of modified rows.
        """
        stmt = (
            update(Alert)
            .where(Alert.acknowledged.is_(False))
            .values(acknowledged=True)
            .execution_options(synchronize_session="fetch")
        )

        result = await self.session.execute(stmt)
        await self.session.commit()
        
        count = getattr(result, "rowcount", None)
        if count is None:
            # Fallback: count alerts now acknowledged
            count_stmt = select(Alert).where(Alert.acknowledged.is_(True))
            count_result = await self.session.execute(count_stmt)
            count = len(count_result.scalars().all())
        return count