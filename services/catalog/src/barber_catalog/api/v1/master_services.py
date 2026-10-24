"""Master offerings. Admin only, idempotent."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from barber_catalog.api.v1.dependencies import (
    LinkMasterServiceScenario,
    UnlinkMasterServiceScenario,
)
from barber_catalog.domain.identifiers import MasterId, ServiceId
from barber_catalog.schemas.master_services import MasterServiceRequest, MasterServiceResponse
from barber_catalog.services.authorization import SALON_ADMINISTRATORS
from barber_common.auth import Principal, require_roles

__all__ = ["router"]

router = APIRouter(prefix="/masters", tags=["master services"])

SalonAdministrator = Annotated[Principal, Depends(require_roles(*SALON_ADMINISTRATORS))]


@router.put(
    "/{master_id}/services/{service_id}",
    summary="Say that a master offers a service",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such master, or no such service"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The service belongs to another salon, or has been archived"
        },
    },
)
async def link_master_service(
    master_id: UUID,
    service_id: UUID,
    body: MasterServiceRequest,
    caller: SalonAdministrator,
    scenario: LinkMasterServiceScenario,
) -> MasterServiceResponse:
    """Set the terms on which this master offers this service.

    `PUT` replaces the whole link: an omitted or `null` override falls back to the salon's
    base value, so `{}` means "salon price and duration". Repeating the call returns `200`.
    The service must belong to the master's salon and must not be archived (`422`). The
    response includes the resolved `price` and `duration_min`.
    """
    return await scenario.execute(
        caller=caller,
        master_id=MasterId(master_id),
        service_id=ServiceId(service_id),
        body=body,
    )


@router.delete(
    "/{master_id}/services/{service_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Say that a master no longer offers a service",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such master"},
    },
)
async def unlink_master_service(
    master_id: UUID,
    service_id: UUID,
    caller: SalonAdministrator,
    scenario: UnlinkMasterServiceScenario,
) -> None:
    """Withdraw the service from this master.

    Existing bookings are not affected, and the overrides are kept for a later re-link.
    Always `204` for a missing or already withdrawn link; `404` for an unknown master.
    """
    await scenario.execute(
        caller=caller,
        master_id=MasterId(master_id),
        service_id=ServiceId(service_id),
    )
