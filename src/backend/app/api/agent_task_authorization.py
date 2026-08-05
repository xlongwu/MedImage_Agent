from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Header

from src.backend.app.core.config import ConfigService
from src.backend.app.core.exceptions import SafetyError


AGENT_APPROVAL_TOKEN_HEADER = "X-MedImage-Agent-Approval-Token"


def require_agent_task_approval_principal(
    approval_token: Annotated[
        str | None, Header(alias=AGENT_APPROVAL_TOKEN_HEADER)
    ] = None,
) -> str:
    """Authorize a privileged Agent Task approval with a launch-bound capability.

    The audit actor is intentionally derived from trusted server configuration.
    A request body must never select the principal that authorizes execution.
    """

    server = ConfigService().server
    expected_token = server.agent_approval_token
    actor = server.agent_approval_actor
    if not expected_token or not actor:
        raise SafetyError(
            "AGENT_APPROVAL_AUTH_UNCONFIGURED",
            code="AGENT_APPROVAL_AUTH_UNCONFIGURED",
            details={
                "required_environment": [
                    "MEDIMAGE_AGENT_APPROVAL_TOKEN",
                    "MEDIMAGE_AGENT_APPROVAL_ACTOR",
                ]
            },
        )
    if not approval_token or not hmac.compare_digest(approval_token, expected_token):
        raise SafetyError(
            "AGENT_APPROVAL_AUTH_REQUIRED",
            code="AGENT_APPROVAL_AUTH_REQUIRED",
        )
    return actor
