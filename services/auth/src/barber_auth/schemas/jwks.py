"""Body of ``/.well-known/jwks.json`` (RFC 7517)."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = ["JwksResponse"]


class JwksResponse(BaseModel):
    """Every public key a verifier may use to check a token of this platform.

    Only public material appears here: modulus, exponent, key type, ``kid``,
    intended use and algorithm. There is no code path that can put a private
    component into this response: the private key never leaves the signer and
    is never written to the table this is built from.
    """

    keys: list[dict[str, str]] = Field(
        description="Active public keys as JWK objects, oldest first.",
    )
