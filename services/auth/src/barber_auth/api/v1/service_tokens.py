"""``POST /internal/v1/token``: client credentials for service-to-service calls."""

from __future__ import annotations

from fastapi import APIRouter, status

from barber_auth.api.v1.dependencies import IssueServiceTokenScenario
from barber_auth.schemas.service_tokens import ServiceTokenRequest, ServiceTokenResponse

__all__ = ["router"]

router = APIRouter(prefix="/internal/v1", tags=["internal"])


@router.post(
    "/token",
    status_code=status.HTTP_200_OK,
    summary="Exchange client credentials for a service token",
    responses={status.HTTP_401_UNAUTHORIZED: {"description": "Client id or secret is not correct"}},
)
async def issue_service_token(
    body: ServiceTokenRequest, scenario: IssueServiceTokenScenario
) -> ServiceTokenResponse:
    """Issue a short-lived service token (`scopes`, `typ: service`, no refresh).

    Unknown client, wrong secret and deactivated client all return the same `401`.
    """
    issued = await scenario.execute(
        client_id=body.client_id,
        client_secret=body.client_secret,
    )
    return ServiceTokenResponse(
        access_token=issued.access_token,
        expires_at=issued.expires_at,
        scopes=list(issued.scopes),
    )
