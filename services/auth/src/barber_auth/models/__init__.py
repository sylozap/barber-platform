"""ORM models of auth.

Shared models are imported so Alembic autogenerate sees ``outbox`` and ``processed_events``.
"""

from barber_auth.models.email_confirmation import EmailConfirmation
from barber_auth.models.refresh_token import RefreshToken
from barber_auth.models.service_client import ServiceClient
from barber_auth.models.signing_key import SigningKey
from barber_auth.models.user import User
from barber_auth.models.user_role import ROLES, UserRole
from barber_common.db.base import Base, metadata
from barber_common.kafka.dedup import ProcessedEvent
from barber_common.outbox.models import OutboxMessage

__all__ = [
    "ROLES",
    "Base",
    "EmailConfirmation",
    "OutboxMessage",
    "ProcessedEvent",
    "RefreshToken",
    "ServiceClient",
    "SigningKey",
    "User",
    "UserRole",
    "metadata",
]
