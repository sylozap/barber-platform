"""ORM models of catalog.

Shared models are imported so Alembic autogenerate sees ``outbox`` and ``processed_events``.
"""

from barber_catalog.models.master import Master
from barber_catalog.models.master_service import MasterService
from barber_catalog.models.salon import (
    DEFAULT_BOOKING_HORIZON_DAYS,
    DEFAULT_BOOKING_MIN_LEAD_MIN,
    DEFAULT_CANCEL_DEADLINE_MIN,
    DEFAULT_SLOT_STEP_MIN,
    Salon,
)
from barber_catalog.models.service import Service
from barber_common.db.base import Base, metadata
from barber_common.kafka.dedup import ProcessedEvent
from barber_common.outbox.models import OutboxMessage

__all__ = [
    "DEFAULT_BOOKING_HORIZON_DAYS",
    "DEFAULT_BOOKING_MIN_LEAD_MIN",
    "DEFAULT_CANCEL_DEADLINE_MIN",
    "DEFAULT_SLOT_STEP_MIN",
    "Base",
    "Master",
    "MasterService",
    "OutboxMessage",
    "ProcessedEvent",
    "Salon",
    "Service",
    "metadata",
]
