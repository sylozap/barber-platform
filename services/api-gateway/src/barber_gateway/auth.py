"""Token checks at the gateway.

Services verify tokens again, the gateway only rejects early and sets ``X-User-Id`` and
``X-Roles`` (client-sent values are always dropped). An invalid token is ``401`` even on
public paths; service tokens are not accepted from outside.
"""

from __future__ import annotations

from dataclasses import dataclass

from starlette.requests import Request

from barber_common.auth import (
    ACCESS_TOKEN_TYPE,
    InvalidToken,
    Principal,
    RoleClaim,
    TokenVerifier,
)
from barber_gateway.routing import PathPattern

__all__ = [
    "PUBLIC_ENDPOINTS",
    "Identity",
    "PublicEndpoint",
    "identify",
    "is_public",
    "roles_header",
]

_READ_METHODS = frozenset({"GET", "HEAD"})


@dataclass(frozen=True, slots=True)
class PublicEndpoint:
    """Requests that need no token: these methods on paths of this pattern."""

    methods: frozenset[str]
    pattern: PathPattern


def _public(methods: frozenset[str], template: str, *, exact: bool = True) -> PublicEndpoint:
    return PublicEndpoint(methods=methods, pattern=PathPattern(template, exact=exact))


_POST = frozenset({"POST"})

# Everything else needs a token. The contract test checks the list against the
# endpoints that declare no security in the OpenAPI of their service.
PUBLIC_ENDPOINTS: tuple[PublicEndpoint, ...] = (
    # Becoming a user, and the session. Logout spends a refresh token from the
    # body rather than an access token, so it is open too.
    _public(_POST, "/api/v1/auth/register"),
    _public(_POST, "/api/v1/auth/confirm-email"),
    _public(_POST, "/api/v1/auth/login"),
    _public(_POST, "/api/v1/auth/refresh"),
    _public(_POST, "/api/v1/auth/logout"),
    _public(_READ_METHODS, "/.well-known/jwks.json"),
    # The shop window: reading the catalog, the free slots and the card of a
    # master. Not "any GET under /masters": the schedule of a master is a GET
    # too, and it is closed.
    _public(_READ_METHODS, "/api/v1/salons", exact=False),
    _public(_READ_METHODS, "/api/v1/services", exact=False),
    _public(_READ_METHODS, "/api/v1/masters/{master_id}"),
    _public(_READ_METHODS, "/api/v1/masters/{master_id}/card"),
    _public(_READ_METHODS, "/api/v1/availability"),
)


def is_public(method: str, path: str) -> bool:
    """Whether this request may be made without a token."""
    upper = method.upper()
    return any(
        upper in endpoint.methods and endpoint.pattern.matches(path)
        for endpoint in PUBLIC_ENDPOINTS
    )


@dataclass(frozen=True, slots=True)
class Identity:
    """The caller as the gateway sees it.

    ``principal`` is set when a token was sent and verified. ``token_rejected``
    when one was sent and refused: told apart from no token at all, because
    the first is a ``401`` on every path and the second only on closed ones.
    """

    principal: Principal | None = None
    token_rejected: bool = False

    @property
    def is_authenticated(self) -> bool:
        return self.principal is not None

    def headers(self) -> dict[str, str]:
        """The identity headers the gateway vouches for; none for a stranger."""
        if self.principal is None:
            return {}
        return {
            "x-user-id": self.principal.subject,
            "x-roles": roles_header(self.principal.roles),
        }


def roles_header(roles: tuple[RoleClaim, ...]) -> str:
    """``X-Roles``: comma separated, a salon role followed by its salon.

    ``client,salon_admin:0192f3c1-...``. The salon is part of the grant (an
    admin of one salon is nobody in another), so it travels with it.
    """
    return ",".join(
        grant.role if grant.salon_id is None else f"{grant.role}:{grant.salon_id}"
        for grant in roles
    )


async def identify(request: Request, verifier: TokenVerifier) -> Identity:
    """Read and verify the token of the request, if it carries one."""
    header = request.headers.get("authorization")
    if header is None:
        return Identity()

    scheme, _, token = header.partition(" ")
    token = token.strip()
    if scheme.lower() != "bearer" or not token:
        return Identity(token_rejected=True)

    try:
        principal = await verifier.verify(token)
    except InvalidToken:
        return Identity(token_rejected=True)

    if principal.token_type != ACCESS_TOKEN_TYPE:
        return Identity(token_rejected=True)
    return Identity(principal=principal)
