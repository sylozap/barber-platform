"""Free slots of a master for a service. Public endpoint."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from barber_booking.api.v1.dependencies import ReadAvailabilityScenario
from barber_booking.domain.identifiers import MasterId, ServiceId
from barber_common.contracts.booking import AvailabilityResponse

__all__ = ["router"]

router = APIRouter(prefix="/availability", tags=["availability"])


@router.get(
    "",
    summary="Free starts of one master for one service",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The window is wider than two weeks, or service_id is missing"
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "The catalog is not answering"},
    },
)
async def read_availability(
    scenario: ReadAvailabilityScenario,
    master_id: Annotated[UUID, Query()],
    service_id: Annotated[UUID, Query(description="Mandatory: the duration depends on it.")],
    date_from: Annotated[date, Query(description="First date, in the salon's time zone.")],
    date_to: Annotated[
        date | None, Query(description="Last date, inclusive. Equal to date_from if absent.")
    ] = None,
) -> AvailabilityResponse:
    """Free start times by date for a master and a service.

    `service_id` is required; the window is at most two weeks. The result is an estimate: a
    listed slot may be taken before booking, which then returns `409 slot_taken`. Dates are
    in the salon's calendar, start times in UTC. An inactive master or one without a
    schedule returns empty days.
    """
    return await scenario.execute(
        master_id=MasterId(master_id),
        service_id=ServiceId(service_id),
        date_from=date_from,
        date_to=date_to,
    )
