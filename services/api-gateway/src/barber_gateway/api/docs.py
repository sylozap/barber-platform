"""Merged OpenAPI document of the platform and Swagger UI for it."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.openapi.docs import get_swagger_ui_html
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from barber_gateway.openapi import PlatformDocument

__all__ = ["router"]

router = APIRouter(include_in_schema=False)


@router.get("/openapi.json")
async def platform_openapi(request: Request) -> JSONResponse:
    """Every endpoint of the platform, as the gateway exposes it."""
    document: PlatformDocument = request.app.state.openapi
    return JSONResponse(await document.get())


@router.get("/docs")
async def swagger_ui() -> HTMLResponse:
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Barber Platform API")
