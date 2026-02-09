from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base, declared_attr

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)


class _CustomBase:
    @declared_attr
    def __tablename__(cls) -> str:  # type: ignore
        return cls.__name__.lower()


Base = declarative_base(cls=_CustomBase, metadata=metadata)