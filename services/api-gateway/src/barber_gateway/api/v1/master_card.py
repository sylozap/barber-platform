"""``GET /api/v1/masters/{id}/card``: the one endpoint the gateway answers itself."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from starlette.requests import Request

from barber_gateway.api.dependencies import admit
from barber_gateway.schemas.master_card import MasterCard
from barber_gateway.services.master_card import ReadMasterCard
from barber_gateway.settings import GatewaySettings

__all__ = ["router"]

router = APIRouter(prefix="/masters", tags=["master card"])


def get_read_master_card(request: Request) -> ReadMasterCard:
    """The scenario, over the clients the lifespan built."""
    settings: GatewaySettings = request.app.state.settings
    return ReadMasterCard(
        catalog=request.app.state.catalog,
        booking=request.app.state.booking,
        window_days=settings.card_slots_window_days,
        slots_limit=settings.card_slots_limit,
    )


ReadMasterCardScenario = Annotated[ReadMasterCard, Depends(get_read_master_card)]


@router.get(
    "/{master_id}/card",
    summary="Profile, services and the nearest free slots of a master",
    # The token, if one is sent, and the limits, like any proxied request.
    dependencies=[Depends(admit)],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "No such master"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The master does not offer this service, or an id is malformed"
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "The catalog is not answering"},
    },
)
async def read_master_card(
    master_id: UUID,
    scenario: ReadMasterCardScenario,
    service_id: Annotated[
        UUID | None, Query(description="The service to show free slots for.")
    ] = None,
) -> MasterCard:
    """Master profile, services and nearest free slots in one request.

    Public. Without `service_id` there are no slots (`slots_status: not_requested`). If
    booking is down the card is still returned with `slots_status: unavailable`; if catalog
    is down the answer is `503`.
    """
    return await scenario.execute(master_id=master_id, service_id=service_id)
