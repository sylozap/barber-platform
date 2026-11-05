"""ORM models of booking.

Shared models are imported so Alembic autogenerate sees ``outbox`` and ``processed_events``.
"""

from barber_booking.models.booking import Booking
from barber_booking.models.master_settings import MasterSettings
from barber_booking.models.schedule_exception import ScheduleException
from barber_booking.models.schedule_template import ScheduleTemplate
from barber_common.db.base import Base, metadata
from barber_common.idempotency import IdempotencyKey
from barber_common.kafka.dedup import ProcessedEvent
from barber_common.outbox.models import OutboxMessage

__all__ = [
    "Base",
    "Booking",
    "IdempotencyKey",
    "MasterSettings",
    "OutboxMessage",
    "ProcessedEvent",
    "ScheduleException",
    "ScheduleTemplate",
    "metadata",
]
