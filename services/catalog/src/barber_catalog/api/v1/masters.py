"""Master profiles. Reads are public, writes require a salon admin."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from barber_catalog.api.v1.dependencies import (
    ActivateMasterScenario,
    CreateMasterScenario,
    DeactivateMasterScenario,
    ListSalonMastersScenario,
    ReadMasterCardScenario,
    UpdateMasterScenario,
)
from barber_catalog.domain.identifiers import MasterId, SalonId
from barber_catalog.schemas.masters import MasterCreateRequest, MasterUpdateRequest
from barber_catalog.services.authorization import SALON_ADMINISTRATORS
from barber_common.auth import Principal, require_roles
from barber_common.contracts.catalog import MasterCardResponse, MasterResponse
from barber_common.pagination import Page, Pagination

__all__ = ["router", "salon_masters_router"]

router = APIRouter(prefix="/masters", tags=["masters"])
# The staff of one salon hangs off the salon, not off the master collection:
# the path says whose masters these are, and the listing needs it anyway.
salon_masters_router = APIRouter(prefix="/salons", tags=["masters"])

SalonAdministrator = Annotated[Principal, Depends(require_roles(*SALON_ADMINISTRATORS))]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Add a master to a salon",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such salon"},
    },
)
async def create_master(
    body: MasterCreateRequest,
    caller: SalonAdministrator,
    scenario: CreateMasterScenario,
) -> MasterResponse:
    """Create a master profile.

    A `super_admin` can add a master to any salon, a `salon_admin` only to their own.
    `user_id` is not checked against `auth`. Publishes `master.created` in the same
    transaction.
    """
    return await scenario.execute(caller=caller, body=body)


@router.get(
    "/{master_id}",
    summary="Read a master card",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such master"}},
)
async def read_master_card(
    master_id: UUID,
    scenario: ReadMasterCardScenario,
) -> MasterCardResponse:
    """Master profile with offered services. Public.

    Each service shows the master's price and duration and the salon's base values.
    Deactivated masters are still returned, with `is_active: false`.
    """
    return await scenario.execute(master_id=MasterId(master_id))


@router.patch(
    "/{master_id}",
    summary="Change a master profile",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such master"},
    },
)
async def update_master(
    master_id: UUID,
    body: MasterUpdateRequest,
    caller: SalonAdministrator,
    scenario: UpdateMasterScenario,
) -> MasterResponse:
    """Change a profile. Only the fields present in the body are touched.

    The salon and the account cannot be changed here: both are part of what
    makes this profile *this* profile, and moving a master between salons is
    creating a second profile, not editing the first.
    """
    return await scenario.execute(caller=caller, master_id=MasterId(master_id), body=body)


@salon_masters_router.get(
    "/{salon_id}/masters",
    summary="List the masters of a salon",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such salon"}},
)
async def list_salon_masters(
    salon_id: UUID,
    pagination: Pagination,
    scenario: ListSalonMastersScenario,
    is_active: Annotated[
        bool | None,
        Query(description="Show only active masters, or only deactivated ones."),
    ] = None,
) -> Page[MasterResponse]:
    """Masters of a salon, alphabetically, cursor-paginated. Public; filter with `is_active`."""
    return await scenario.execute(
        salon_id=SalonId(salon_id), request=pagination, is_active=is_active
    )


@router.post(
    "/{master_id}/deactivate",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Stop a master working",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such master"},
    },
)
async def deactivate_master(
    master_id: UUID,
    caller: SalonAdministrator,
    scenario: DeactivateMasterScenario,
) -> MasterResponse:
    """Deactivate a master.

    Returns `202`: the profile is deactivated immediately, while `booking` cancels the
    master's future bookings asynchronously after `master.deactivated`. Repeating the call
    publishes no second event. Reactivation does not restore cancelled bookings.
    """
    return await scenario.execute(caller=caller, master_id=MasterId(master_id))


@router.post(
    "/{master_id}/activate",
    summary="Put a master back to work",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such master"},
    },
)
async def activate_master(
    master_id: UUID,
    caller: SalonAdministrator,
    scenario: ActivateMasterScenario,
) -> MasterResponse:
    """Reactivate a master. Bookings cancelled by the deactivation are not restored."""
    return await scenario.execute(caller=caller, master_id=MasterId(master_id))
