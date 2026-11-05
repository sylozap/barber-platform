"""Salon price list. Reads are public, writes require a salon admin.

There is no `DELETE`: bookings reference services, so a service is archived instead.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from barber_catalog.api.v1.dependencies import (
    ArchiveServiceScenario,
    CreateServiceScenario,
    ListSalonServicesScenario,
    ReadServiceScenario,
    UpdateServiceScenario,
)
from barber_catalog.domain.identifiers import SalonId, ServiceId
from barber_catalog.schemas.services import (
    ServiceCreateRequest,
    ServiceResponse,
    ServiceUpdateRequest,
)
from barber_catalog.services.authorization import SALON_ADMINISTRATORS
from barber_common.auth import Principal, require_roles
from barber_common.pagination import Page, Pagination

__all__ = ["router", "salon_services_router"]

router = APIRouter(prefix="/services", tags=["services"])
# The price list hangs off the salon that owns it; a single service is reached
# by its own identifier, because that is what a booking carries.
salon_services_router = APIRouter(prefix="/salons", tags=["services"])

SalonAdministrator = Annotated[Principal, Depends(require_roles(*SALON_ADMINISTRATORS))]


@salon_services_router.post(
    "/{salon_id}/services",
    status_code=status.HTTP_201_CREATED,
    summary="Add a service to a salon",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such salon"},
    },
)
async def create_service(
    salon_id: UUID,
    body: ServiceCreateRequest,
    caller: SalonAdministrator,
    scenario: CreateServiceScenario,
) -> ServiceResponse:
    """Add a service to the price list.

    `base_duration_min` and `base_price` can be overridden per master. Names need not be
    unique.
    """
    return await scenario.execute(caller=caller, salon_id=SalonId(salon_id), body=body)


@salon_services_router.get(
    "/{salon_id}/services",
    summary="List the services of a salon",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such salon"}},
)
async def list_salon_services(
    salon_id: UUID,
    pagination: Pagination,
    scenario: ListSalonServicesScenario,
) -> Page[ServiceResponse]:
    """Active services of a salon, alphabetically, cursor-paginated. Public.

    Archived services are never listed but can still be fetched by id.
    """
    return await scenario.execute(salon_id=SalonId(salon_id), request=pagination)


@router.get(
    "/{service_id}",
    summary="Read one service",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such service"}},
)
async def read_service(service_id: UUID, scenario: ReadServiceScenario) -> ServiceResponse:
    """One service, archived or not. **Open to anonymous callers.**

    Archived services are the point of this endpoint: a client looking at a
    booking from last year holds an identifier and needs a name for it.
    `is_archived` says which kind this is.
    """
    return await scenario.execute(service_id=ServiceId(service_id))


@router.patch(
    "/{service_id}",
    summary="Change a service",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such service"},
    },
)
async def update_service(
    service_id: UUID,
    body: ServiceUpdateRequest,
    caller: SalonAdministrator,
    scenario: UpdateServiceScenario,
) -> ServiceResponse:
    """Partially update a service.

    Existing bookings keep their snapshot and master overrides are untouched. Archiving is a
    separate endpoint.
    """
    return await scenario.execute(caller=caller, service_id=ServiceId(service_id), body=body)


@router.post(
    "/{service_id}/archive",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Withdraw a service",
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "Not an administrator of this salon"},
        status.HTTP_404_NOT_FOUND: {"description": "No such service"},
    },
)
async def archive_service(
    service_id: UUID,
    caller: SalonAdministrator,
    scenario: ArchiveServiceScenario,
) -> None:
    """Archive a service: hidden from listings, still readable by id. Idempotent (`204`).

    Master links are kept.
    """
    await scenario.execute(caller=caller, service_id=ServiceId(service_id))
