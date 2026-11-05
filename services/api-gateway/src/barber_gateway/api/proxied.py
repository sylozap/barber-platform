"""Catch-all routes that proxy everything else to the services.

Two routes instead of ``/{path:path}`` so ``/metrics`` and other chassis routes still match.
"""

from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request
from starlette.responses import Response

from barber_common.errors import NotFound
from barber_gateway.api.dependencies import Admitted
from barber_gateway.proxy import Proxy
from barber_gateway.routing import route_for

__all__ = ["router"]

# OPTIONS for completeness: the gateway has no CORS policy of its own, so a
# preflight is the service's to answer.
PROXIED_METHODS = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]

router = APIRouter(include_in_schema=False)


@router.api_route("/api/{path:path}", methods=PROXIED_METHODS)
@router.api_route("/.well-known/jwks.json", methods=PROXIED_METHODS)
async def proxy_to_service(request: Request, caller: Admitted) -> Response:
    """Forward the request to the service the routing table names."""
    upstream = route_for(request.url.path)
    if upstream is None:
        raise NotFound("No service answers this path")

    proxy: Proxy = request.app.state.proxy
    return await proxy.forward(request, upstream, identity=caller.headers())
