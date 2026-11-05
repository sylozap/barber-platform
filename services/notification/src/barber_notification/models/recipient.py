"""Who a notification can reach, and on which channels."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, Boolean, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from barber_common.db.base import Base

__all__ = ["Recipient"]


class Recipient(Base):
    """Contacts of one account, copied from ``auth.users.v1``.

    ``contacts_updated_at`` prevents an older snapshot from overwriting a newer one.
    """

    __tablename__ = "recipients"

    user_id: Mapped[UUID] = mapped_column(primary_key=True)

    email: Mapped[str | None] = mapped_column(String(320), default=None)
    phone: Mapped[str | None] = mapped_column(String(32), default=None)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    preferences: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb")
    )
    contacts_updated_at: Mapped[datetime | None] = mapped_column(default=None)

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
