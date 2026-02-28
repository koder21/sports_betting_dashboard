from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase, declared_attr

# SQLAlchemy naming convention — keeps migration tooling (Alembic) happy
# and avoids anonymous constraint names across all dialects.
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class Base(DeclarativeBase):
    """
    Project-wide declarative base.

    Automatically derives __tablename__ from the class name (lowercased).
    Override __tablename__ explicitly on any model that needs a different name.
    """

    metadata = metadata

    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: N805
        return cls.__name__.lower()