"""Domain metrics of notification: delivery results, send latency, queue size and age."""

from __future__ import annotations

from barber_common.metrics import counter, gauge, histogram

__all__ = [
    "NOTIFICATIONS_OLDEST_DUE_AGE",
    "NOTIFICATIONS_PENDING",
    "NOTIFICATIONS_SENT",
    "NOTIFICATION_SEND_DURATION",
]

# One per attempt, whatever its outcome; ``result`` is a DeliveryOutcome.
NOTIFICATIONS_SENT = counter(
    "notifications_sent_total",
    "Attempts to deliver a notification, by channel and outcome",
    labelnames=("channel", "result"),
)

# Only the call to the provider: a notification refused before it (no
# address, a deactivated recipient) took no time worth measuring.
NOTIFICATION_SEND_DURATION = histogram(
    "notification_send_duration_seconds",
    "Time a provider took to deliver or refuse one notification",
    labelnames=("channel",),
)

NOTIFICATIONS_PENDING = gauge(
    "notifications_pending_messages",
    "Notifications queued and not yet sent or given up on",
)

NOTIFICATIONS_OLDEST_DUE_AGE = gauge(
    "notifications_oldest_due_age_seconds",
    "How long the oldest notification due for sending has waited for a worker",
)
