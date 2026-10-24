"""Booking endpoints: create, list, cancel, reschedule, close.

Create requires ``Idempotency-Key``; the other operations are idempotent by state.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, status
from pydantic import AwareDatetime

from barber_booking.api.v1.dependencies import (
    CancelBookingScenario,
    CloseVisitScenario,
    CreateBookingScenario,
    ListBookingsScenario,
    ReadBookingScenario,
    RescheduleBookingScenario,
)
from barber_booking.domain.booking_status import BookingStatus
from barber_booking.domain.identifiers import BookingId, MasterId, SalonId
from barber_booking.domain.visibility import BookingFilters
from barber_booking.schemas.bookings import (
    BookingCancelRequest,
    BookingCreateRequest,
    BookingRescheduleRequest,
    BookingResponse,
)
from barber_booking.services.authorization import BOOKING_ROLES
from barber_common.auth import Principal, require_roles
from barber_common.idempotency import RequiredIdempotencyKey
from barber_common.pagination import Page, Pagination

__all__ = ["router"]

router = APIRouter(prefix="/bookings", tags=["bookings"])

# A client books for themselves, the salon for a client. Every registered user
# is a client; the check is what keeps the endpoint closed to a service token.
Booker = Annotated[Principal, Depends(require_roles("client", "salon_admin", "super_admin"))]
# Anyone a booking may concern. Which booking, and in what capacity, is checked
# by the scenario once the booking is loaded.
Participant = Annotated[Principal, Depends(require_roles(*BOOKING_ROLES))]

_REFUSED: dict[int | str, dict[str, object]] = {
    status.HTTP_403_FORBIDDEN: {
        "description": "The booking is not the caller's, or their role does not allow this"
    },
    status.HTTP_404_NOT_FOUND: {"description": "No such booking"},
}


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Book a master for a service",
    responses={
        status.HTTP_403_FORBIDDEN: {
            "description": "`client_user_id` names somebody else and the caller does not run "
            "the master's salon"
        },
        status.HTTP_409_CONFLICT: {
            "description": "The slot was taken while this request was in flight"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": (
                "No Idempotency-Key, the key was used for another body, or the booking "
                "breaks one of the salon's windows"
            )
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "The catalog is not answering"},
    },
)
async def create_booking(
    body: BookingCreateRequest,
    caller: Booker,
    request: RequiredIdempotencyKey,
    scenario: CreateBookingScenario,
) -> BookingResponse:
    """Create a confirmed booking.

    `client_user_id` lets a `salon_admin` of the salon or a `super_admin` book for a client;
    anyone else gets `403`. The service name, price and duration are stored as a snapshot.

    `Idempotency-Key` is required: the same key and body return the original response, a
    different body returns `422 idempotency_key_reuse`.

    Errors: `booking_too_late`, `booking_too_far`, `slot_outside_schedule`,
    `master_inactive`, `service_not_offered`, and `409 slot_taken` if the slot was taken
    concurrently.
    """
    return await scenario.execute(caller=caller, request=request, body=body)


@router.get(
    "",
    summary="List bookings",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The period ends before it starts, or the cursor is not valid"
        }
    },
)
async def list_bookings(
    caller: Participant,
    scenario: ListBookingsScenario,
    pagination: Pagination,
    starts_from: Annotated[
        AwareDatetime | None,
        Query(alias="from", description="Bookings starting at or after this instant."),
    ] = None,
    starts_before: Annotated[
        AwareDatetime | None,
        Query(alias="to", description="Bookings starting before this instant."),
    ] = None,
    master_id: Annotated[UUID | None, Query()] = None,
    salon_id: Annotated[UUID | None, Query()] = None,
    statuses: Annotated[
        list[BookingStatus] | None,
        Query(alias="status", description="Repeat to accept several statuses."),
    ] = None,
) -> Page[BookingResponse]:
    """Bookings visible to the caller, ordered by `start_at`, cursor-paginated.

    Clients see their own bookings, masters also see bookings with them, a `salon_admin`
    sees the salon's, a `super_admin` sees all. Filters only narrow that set.
    """
    filters = BookingFilters(
        starts_from=starts_from,
        starts_before=starts_before,
        master_id=MasterId(master_id) if master_id is not None else None,
        salon_id=SalonId(salon_id) if salon_id is not None else None,
        statuses=frozenset(statuses or ()),
    )
    return await scenario.execute(caller=caller, filters=filters, request=pagination)


@router.get(
    "/{booking_id}",
    summary="Read one booking",
    responses={status.HTTP_404_NOT_FOUND: {"description": "No such booking, or not visible"}},
)
async def read_booking(
    booking_id: UUID, caller: Participant, scenario: ReadBookingScenario
) -> BookingResponse:
    """One booking, if the caller may see it: by the same rules as the list.

    A booking the caller may not see is `404`, exactly like one that does not
    exist: the answer says nothing about other people's appointments.
    """
    return await scenario.execute(caller=caller, booking_id=BookingId(booking_id))


@router.post(
    "/{booking_id}/cancel",
    summary="Cancel a booking",
    responses={
        **_REFUSED,
        status.HTTP_409_CONFLICT: {
            "description": "The visit is already completed or marked as a no-show"
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "The client's deadline has passed, or the visit has already started"
        },
    },
)
async def cancel_booking(
    booking_id: UUID,
    caller: Participant,
    scenario: CancelBookingScenario,
    body: Annotated[BookingCancelRequest | None, Body()] = None,
) -> BookingResponse:
    """Cancel a booking.

    The client can cancel until the salon's deadline (as it was at booking time); after that
    only a `salon_admin` or `super_admin` can. Masters cannot cancel. Errors:
    `cancel_deadline_passed`, `booking_already_started`, `409 booking_status_conflict`.
    Cancelling an already cancelled booking returns it unchanged.
    """
    return await scenario.execute(caller=caller, booking_id=BookingId(booking_id), body=body)


@router.post(
    "/{booking_id}/reschedule",
    summary="Move a booking to another time",
    responses={
        **_REFUSED,
        status.HTTP_409_CONFLICT: {
            "description": (
                "The new time was taken while this request was in flight, or the booking "
                "is no longer open"
            )
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": (
                "The client's deadline has passed, the visit has started, or the new time "
                "breaks one of the salon's windows"
            )
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "The catalog is not answering"},
    },
)
async def reschedule_booking(
    booking_id: UUID,
    body: BookingRescheduleRequest,
    caller: Participant,
    scenario: RescheduleBookingScenario,
) -> BookingResponse:
    """Move a booking to another start time atomically.

    Same permissions and deadline as cancellation, same checks as creation. If the new slot
    is taken, returns `409 slot_taken` with `alternatives` and the booking is unchanged.
    """
    return await scenario.execute(caller=caller, booking_id=BookingId(booking_id), body=body)


_CLOSE_RESPONSES: dict[int | str, dict[str, object]] = {
    **_REFUSED,
    status.HTTP_409_CONFLICT: {
        "description": "The booking is cancelled, or its visit is already closed the other way"
    },
    status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "The visit has not started yet"},
}


@router.post(
    "/{booking_id}/complete", summary="Mark a visit as completed", responses=_CLOSE_RESPONSES
)
async def complete_visit(
    booking_id: UUID, caller: Participant, scenario: CloseVisitScenario
) -> BookingResponse:
    """Mark a visit as completed.

    Allowed for the master and the salon once the visit has started (`booking_not_started`
    before). A no-show cannot be completed (`409 booking_status_conflict`).
    """
    return await scenario.execute(
        caller=caller, booking_id=BookingId(booking_id), outcome=BookingStatus.COMPLETED
    )


@router.post("/{booking_id}/no-show", summary="Mark a visit as missed", responses=_CLOSE_RESPONSES)
async def mark_no_show(
    booking_id: UUID, caller: Participant, scenario: CloseVisitScenario
) -> BookingResponse:
    """Record that the client did not come.

    The same people and the same rules as for completing a visit. The time
    stays taken: the master kept it free for the client, and it is in the
    past.
    """
    return await scenario.execute(
        caller=caller, booking_id=BookingId(booking_id), outcome=BookingStatus.NO_SHOW
    )
