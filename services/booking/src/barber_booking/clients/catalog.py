"""Client for the internal ``catalog`` endpoints.

``404`` for an offering maps to ``service_not_offered``, for a master to ``not_found``; an
unreachable catalog or open breaker to ``503 upstream_unavailable``.
"""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from barber_booking.clients.service_token import ServiceTokenProvider
from barber_booking.domain.errors import MasterNotFound, ServiceNotOffered
from barber_booking.domain.identifiers import MasterId, ServiceId
from barber_common.contracts.catalog import MasterProfile, MasterServiceDetails
from barber_common.errors import DomainError
from barber_common.http import ServiceClient
from barber_common.http.client import UpstreamError

__all__ = ["CatalogClient"]

_NOT_FOUND = 404
_UNAUTHORIZED = 401


class CatalogClient:
    """Typed access to the internal endpoints of ``catalog``."""

    def __init__(self, *, http: ServiceClient, tokens: ServiceTokenProvider) -> None:
        self._http = http
        self._tokens = tokens

    async def get_offering(
        self, *, master_id: MasterId, service_id: ServiceId
    ) -> MasterServiceDetails:
        """What this master charges for this service, and the salon's policies."""
        return await self._get(
            f"/internal/v1/masters/{master_id}/services/{service_id}",
            MasterServiceDetails,
            not_found=ServiceNotOffered("This master does not offer this service"),
        )

    async def get_master(self, *, master_id: MasterId) -> MasterProfile:
        """Who this master is: account, salon, the salon's zone, and whether they work."""
        return await self._get(
            f"/internal/v1/masters/{master_id}",
            MasterProfile,
            not_found=MasterNotFound("No such master"),
        )

    async def _get[ContractT: BaseModel](
        self, path: str, contract: type[ContractT], *, not_found: DomainError
    ) -> ContractT:
        try:
            return await self._request(path, contract, not_found)
        except UpstreamError as error:
            if error.upstream != self._http.upstream or error.status_code != _UNAUTHORIZED:
                raise
            # A token refused before its expiry: fetched again, tried once more.
            self._tokens.forget()
            return await self._request(path, contract, not_found)

    async def _request[ContractT: BaseModel](
        self, path: str, contract: type[ContractT], not_found: DomainError
    ) -> ContractT:
        token = await self._tokens.token()
        try:
            response = await self._http.get(path, service_token=token)
        except UpstreamError as error:
            if error.status_code == _NOT_FOUND:
                raise not_found from error
            raise

        try:
            return contract.model_validate_json(response.content)
        except ValidationError as error:
            raise UpstreamError(
                upstream=self._http.upstream,
                status_code=response.status_code,
                remote_code=None,
                detail="catalog answered with something that is not the contract",
            ) from error
