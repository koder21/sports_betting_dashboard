from typing import Type, TypeVar, Generic, Optional, Sequence, Iterable, Any, Union

from sqlalchemy import inspect, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: Type[ModelT]) -> None:
        self.session = session
        self.model = model

    def _pk_column(self):
        return inspect(self.model).primary_key[0]

    async def get(self, id_: Union[int, str]) -> Optional[ModelT]:
        return await self.session.get(self.model, id_)

    async def list(self) -> Sequence[ModelT]:
        result = await self.session.execute(select(self.model))
        return result.scalars().all()

    async def list_by_ids(self, ids: Iterable[Any]) -> Sequence[ModelT]:
        pk = self._pk_column()
        stmt = select(self.model).where(pk.in_(list(ids)))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)

    async def delete_by_id(self, id_: Union[int, str]) -> None:
        pk = self._pk_column()
        await self.session.execute(delete(self.model).where(pk == id_))