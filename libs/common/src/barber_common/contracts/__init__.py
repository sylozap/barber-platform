"""DTOs of the synchronous calls between services, shared by caller and callee."""

from barber_common.contracts.booking import AvailabilityResponse, DayAvailability
from barber_common.contracts.catalog import (
    CATALOG_READ_SCOPE,
    MasterCardResponse,
    MasterProfile,
    MasterResponse,
    MasterServiceDetails,
    OfferedServiceResponse,
    SalonPolicies,
)

__all__ = [
    "CATALOG_READ_SCOPE",
    "AvailabilityResponse",
    "DayAvailability",
    "MasterCardResponse",
    "MasterProfile",
    "MasterResponse",
    "MasterServiceDetails",
    "OfferedServiceResponse",
    "SalonPolicies",
]
