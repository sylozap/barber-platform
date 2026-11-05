"""ORM models of notification.

Shared models are imported so Alembic autogenerate sees ``outbox`` and ``processed_events``.
"""

from barber_common.db.base import Base, metadata
from barber_common.kafka.dedup import ProcessedEvent
from barber_common.outbox.models import OutboxMessage
from barber_notification.models.notification import Notification
from barber_notification.models.recipient import Recipient
from barber_notification.models.telegram_link_code import TelegramLinkCode

__all__ = [
    "Base",
    "Notification",
    "OutboxMessage",
    "ProcessedEvent",
    "Recipient",
    "TelegramLinkCode",
    "metadata",
]
