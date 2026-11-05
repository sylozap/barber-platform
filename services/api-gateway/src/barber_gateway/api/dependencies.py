"""Gateway dependency: token check, then rate limit, then rejecting invalid tokens.

The limit is applied before rejecting a bad token, so token guessing is rate limited too.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from barber_common.auth.dependencies import get_token_verifier
from barber_common.errors import RateLimited, Unauthorized
from barber_common.logging import get_logger
from barber_gateway.auth import Identity, identify, is_public
from barber_gateway.rate_limit import RateLimitPolicy, SlidingWindowLimiter, client_address
from barber_gateway.settings import GatewaySettings

__all__ = ["Admitted", "admit"]

_logger = get_logger(__name__)


async def admit(request: Request) -> Identity:
    """Let the request through, or refuse it with a ``401`` or a ``429``."""
    identity = await identify(request, get_token_verifier(request))
    await _count(request, identity)

    if identity.token_rejected:
        raise Unauthorized("The access token is not valid")
    if not identity.is_authenticated and not is_public(request.method, request.url.path):
        raise Unauthorized("Authentication required")
    return identity


async def _count(request: Request, identity: Identity) -> None:
    """Count the request against every limit it falls under."""
    settings: GatewaySettings = request.app.state.settings
    policy: RateLimitPolicy = request.app.state.rate_limits
    limiter: SlidingWindowLimiter = request.app.state.rate_limiter

    user_id = identity.principal.subject if identity.principal is not None else None
    limits = policy.limits_for(
        method=request.method,
        path=request.url.path,
        user_id=user_id,
        client_ip=client_address(request, trusted_proxy_hops=settings.trusted_proxy_hops),
    )
    for limit, subject in limits:
        decision = await limiter.hit(limit, subject)
        if decision.allowed:
            continue
        # INFO, not WARNING: a refused burst is the limiter working, not an
        # incident. The subject is not logged, it is an address or a user.
        _logger.info("rate limit exceeded", scope=limit.scope)
        raise RateLimited(
            "Too many requests, try again later",
            headers={"Retry-After": str(decision.retry_after_seconds)},
            extra={"scope": limit.scope.value},
        )


Admitted = Annotated[Identity, Depends(admit)]
