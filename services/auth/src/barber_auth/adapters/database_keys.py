"""Key source for ``auth`` itself: reads ``signing_keys`` from the database, no cache.

Keys registered by other replicas are visible immediately, which matters during rotation.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from barber_auth.repositories.signing_keys import SigningKeyRepository
from barber_common.auth.keys import PublicKey, UnknownSigningKey, key_from_pem

__all__ = ["DatabaseKeys"]


class DatabaseKeys:
    """The active public keys, read from the table that holds them."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def key_for(self, kid: str) -> PublicKey:
        """The key under this name, or nothing if it is not active.

        A key an operator deactivated is not returned, which is how a retired
        key stops verifying tokens rather than merely stopping to sign them.
        """
        async with self._session_factory() as session:
            keys = await SigningKeyRepository(session).list_active()

        for key in keys:
            if key.kid == kid:
                return key_from_pem(key.public_pem)

        raise UnknownSigningKey(kid)
