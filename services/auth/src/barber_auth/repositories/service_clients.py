"""Machine-to-machine clients: one row per service that calls another."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from barber_auth.models.service_client import ServiceClient

__all__ = ["ServiceClientRepository"]


class ServiceClientRepository:
    """Access to ``service_clients``.

    The secret never reaches this layer as a plain value: what is stored and
    what is compared is a hash, exactly as for a password.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active(self, client_id: str) -> ServiceClient | None:
        """One client, if it exists and has not been switched off.

        Inactive clients are filtered here rather than in the scenario: an
        operator disabling a client expects it to stop working, and a code path
        that reads the row and forgets the flag is how it keeps working.
        """
        statement = select(ServiceClient).where(
            ServiceClient.client_id == client_id,
            ServiceClient.is_active,
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def upsert(self, *, client_id: str, secret_hash: str, scopes: Sequence[str]) -> None:
        """Insert or update a configured service client.

        Secret and scopes are updated on conflict; ``is_active`` is left as the operator set
        it.
        """
        statement = insert(ServiceClient).values(
            client_id=client_id,
            secret_hash=secret_hash,
            scopes=list(scopes),
        )
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=[ServiceClient.client_id],
                set_={
                    "secret_hash": statement.excluded.secret_hash,
                    "scopes": statement.excluded.scopes,
                },
            )
        )
