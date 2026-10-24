"""Domain metrics of booking.

The salon is a label, the master is not (too many values).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from barber_booking.domain.booking import Booking
from barber_common.db import after_commit
from barber_common.metrics import counter, gauge, histogram

__all__ = [
    "AVAILABILITY_DURATION",
    "BOOKINGS_CLOSED",
    "BOOKINGS_CREATED",
    "BOOKINGS_UPCOMING",
    "BOOKING_CONFLICTS",
    "REMINDER_SCHEDULER_LAST_RUN",
    "AvailabilitySource",
    "count_closed",
]

BOOKINGS_CREATED = counter(
    "bookings_created_total",
    "Bookings created, by salon and status",
    labelnames=("salon", "status"),
)

# Every way a booking ends: completed, no_show, cancelled_by_client and
# cancelled_by_salon. Counted after the commit, so a handler that is retried
# does not count its cancellations twice.
BOOKINGS_CLOSED = counter(
    "bookings_closed_total",
    "Bookings that reached a final status, by salon and status",
    labelnames=("salon", "status"),
)

# Seconds of open bookings in the week ahead. Absolute time rather than a share
# of working hours: the share would need every master's schedule worked out on
# each pass, and the trend of a salon is visible without it.
BOOKINGS_UPCOMING = gauge(
    "bookings_upcoming_seconds",
    "Time booked with the masters of a salon over the week ahead",
    labelnames=("salon",),
)

BOOKING_CONFLICTS = counter(
    "booking_conflicts_total",
    "Bookings refused because the slot was taken while the request was in flight",
    labelnames=("salon",),
)

# Labelled by where the answer came from: a p95 that mixes cache hits with
# database reads hides the query it is supposed to watch.
AVAILABILITY_DURATION = histogram(
    "availability_query_duration_seconds",
    "Time to answer one availability request",
    labelnames=("source",),
)


# Unix time of the last pass that committed. The alert is on its age.
REMINDER_SCHEDULER_LAST_RUN = gauge(
    "reminder_scheduler_last_run_timestamp",
    "When the reminder scheduler last finished a pass, as Unix time",
)


class AvailabilitySource:
    """Label values of :data:`AVAILABILITY_DURATION`."""

    CACHE = "cache"
    DATABASE = "database"


def count_closed(session: AsyncSession, bookings: Sequence[Booking]) -> None:
    """Count bookings that reached a final status, once their transaction commits."""

    def record() -> None:
        for booking in bookings:
            BOOKINGS_CLOSED.labels(salon=str(booking.salon_id), status=booking.status.value).inc()

    after_commit(session, record)
