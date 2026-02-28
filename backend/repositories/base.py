from typing import Generic, Sequence, Type, TypeVar, Union, Optional

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Bound T to DeclarativeBase ensures T is actually a Model
T = TypeVar("T", bound=DeclarativeBase)
ID = Union[int, str]


class BaseRepository(Generic[T]):
    """
    Base async repository implementing the Repository Pattern.
    
    Features:
    - Centralized session management.
    - Type-safe CRUD operations.
    - Batch fetching with order preservation.
    """

    DEFAULT_LIMIT = 100
    DEFAULT_BATCH_SIZE = 1000

    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

        # Inspect model to ensure it has a valid PK
        mapper = inspect(self.model)
        if not mapper or not mapper.primary_key:
             raise ValueError(f"Model {model.__name__} does not have a primary key mapped.")
        
        pk_columns = mapper.primary_key
        if len(pk_columns) != 1:
            raise ValueError(f"Model {model.__name__} must have a single-column primary key for BaseRepository support.")

        self._pk_column = pk_columns[0]

    async def get(self, id_: ID) -> 'Optional[T]':
        """Fetch a single entity by ID."""
        return await self.session.get(self.model, id_)

    async def list(
        self,
        *,
        limit: int = DEFAULT_LIMIT,
        offset: int = 0,
    ) -> Sequence[T]:
        """List entities with pagination."""
        if limit <= 0:
            raise ValueError("Limit must be greater than 0")

        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list_by_ids(
        self,
        ids: Sequence[ID],
        *,
        preserve_order: bool = False,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> Sequence[T]:
        """
        Fetch entities by a list of IDs. Handles large lists by batching.
        """
        if not ids:
            return []

        # Remove duplicates to save DB work, unless order strictly matters implies duplicates matter
        unique_ids = list(set(ids)) if not preserve_order else list(ids)
        results: list[T] = []

        for i in range(0, len(unique_ids), batch_size):
            batch = unique_ids[i : i + batch_size]
            stmt = select(self.model).where(self._pk_column.in_(batch))
            batch_result = await self.session.execute(stmt)
            results.extend(batch_result.scalars().all())

        if preserve_order:
            # Map by PK for O(1) lookup
            by_id = {getattr(obj, self._pk_column.name): obj for obj in results}
            # Return in the order of the original 'ids' list, skipping missing ones
            return [by_id[i] for i in ids if i in by_id]

        return results

    def add(self, obj: T) -> T:
        """Add an object to the session (pending flush)."""
        self.session.add(obj)
        return obj

    async def delete(self, obj: T) -> None:
        """Delete an object from the session."""
        await self.session.delete(obj)

    async def delete_by_id(self, id_: ID) -> bool:
        """Fetch and delete by ID. Returns True if found and deleted."""
        obj = await self.get(id_)
        if not obj:
            return False
        await self.session.delete(obj)
        return True