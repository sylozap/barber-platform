"""Keeps master settings in sync with ``catalog.masters.v1``.

Separate consumer group from cache invalidation, so a Redis outage doesn't block it.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from barber_booking.domain.identifiers import MasterId
from barber_booking.services.cascade_cancel import CancelMasterBookings
from barber_booking.services.master_lifecycle import FollowMaster
from barber_common.events.catalog import (
    CATALOG_MASTERS_TOPIC,
    MasterCreated,
    MasterDeactivated,
    MasterEventType,
    MasterUpdated,
)
from barber_common.events.envelope import JsonEnvelope
from barber_common.kafka import EventHandler

__all__ = ["MASTER_LIFECYCLE_GROUP", "MASTER_LIFECYCLE_TOPICS", "MasterLifecycle"]

MASTER_LIFECYCLE_GROUP = "booking.masters"
MASTER_LIFECYCLE_TOPICS = (CATALOG_MASTERS_TOPIC,)


class MasterLifecycle:
    """The handlers that keep master settings in step with catalog."""

    def handlers(self) -> dict[str, EventHandler]:
        """Event types this group reacts to, and how."""
        return {
            MasterEventType.CREATED: self.master_created,
            MasterEventType.UPDATED: self.master_updated,
            MasterEventType.DEACTIVATED: self.master_deactivated,
        }

    async def master_created(self, session: AsyncSession, envelope: JsonEnvelope) -> None:
        await FollowMaster(session).created(MasterCreated.model_validate(envelope.payload))

    async def master_updated(self, session: AsyncSession, envelope: JsonEnvelope) -> None:
        """Covers reactivation too: it is announced as an update with is_active."""
        await FollowMaster(session).updated(MasterUpdated.model_validate(envelope.payload))

    async def master_deactivated(self, session: AsyncSession, envelope: JsonEnvelope) -> None:
        """The cascade: every visit of the master still ahead is cancelled."""
        event = MasterDeactivated.model_validate(envelope.payload)
        await CancelMasterBookings(session).execute(
            master_id=MasterId(event.master_id), cause=envelope.event_id
        )
