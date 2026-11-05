"""Payload ``notification`` publishes to ``<topic>.dlq`` for a notification it gave up on.

Goes through the outbox so it is atomic with marking the notification ``failed``. Template
fields are omitted because they may contain one-time tokens.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

__all__ = [
    "NOTIFICATION_AGGREGATE_TYPE",
    "DeliveryFailureReason",
    "NotificationDeliveryFailed",
    "NotificationEventType",
]

# The partitioning key: the notification itself. The booking or the account
# behind it is not known here, and dead letters need no order between them.
NOTIFICATION_AGGREGATE_TYPE = "notifications"


class NotificationEventType(StrEnum):
    """``event_type`` of the envelope."""

    DELIVERY_FAILED = "notification.delivery_failed"


class DeliveryFailureReason(StrEnum):
    """Why the worker gave up. Also the ``reason`` label of ``dlq_messages_total``."""

    # Every attempt failed with an error worth retrying.
    RETRIES_EXHAUSTED = "retries_exhausted"
    # Another attempt would fail the same way: the bot is blocked, there is no
    # address, the recipient is deactivated.
    PERMANENT_FAILURE = "permanent_failure"


class NotificationDeliveryFailed(BaseModel):
    """A notification that will not be sent, and why."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    notification_id: UUID
    original_event_id: UUID
    user_id: UUID
    channel: str
    template: str

    dlq_reason: DeliveryFailureReason
    dlq_detail: str
    dlq_attempts: int
    dlq_original_topic: str
    dlq_at: AwareDatetime
