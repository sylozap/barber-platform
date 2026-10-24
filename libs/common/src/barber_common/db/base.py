"""Declarative base with a naming convention, so Alembic generates stable constraint names."""

from __future__ import annotations

import datetime
import decimal

from sqlalchemy import MetaData, Numeric
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import DeclarativeBase

__all__ = ["NAMING_CONVENTION", "Base", "metadata"]

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Base(DeclarativeBase):
    """Root of the ORM models.

    Datetimes are ``timestamptz``, money is ``numeric``, relationships use ``lazy="raise"``.
    ``eager_defaults`` returns server-generated columns via ``RETURNING``; without it,
    reading ``updated_at`` after a flush raises ``MissingGreenlet`` under asyncio.
    """

    metadata = metadata

    __mapper_args__ = {"eager_defaults": True}

    type_annotation_map = {
        datetime.datetime: TIMESTAMP(timezone=True),
        decimal.Decimal: Numeric(10, 2),
    }
