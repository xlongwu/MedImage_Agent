from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol


class PlannerProviderError(RuntimeError):
    """Raised when an LLM provider cannot return a valid planner payload."""


@dataclass
class PlannerProviderResponse:
    provider: str
    model: str
    raw_text: str
    payload: dict[str, Any]


class LLMPlannerProvider(Protocol):
    provider_name: str

    def draft_plan(self, request: dict[str, Any], candidate_pipelines: list[str]) -> PlannerProviderResponse:
        ...


def llm_configured() -> bool:
    return (
        os.environ.get("MEDIMAGE_LLM_ENABLED", "false").lower() == "true"
        and bool(os.environ.get("MEDIMAGE_LLM_API_KEY", ""))
    )


def _parse_json_object(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PlannerProviderError(f"LLM planner returned malformed JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlannerProviderError("LLM planner JSON must be an object.")
    return payload


class FixturePlannerProvider:
    provider_name = "fixture"

    def __init__(self, response_text: str, model: str = "fixture") -> None:
        self.response_text = response_text
        self.model = model

    def draft_plan(self, request: dict[str, Any], candidate_pipelines: list[str]) -> PlannerProviderResponse:
        del request, candidate_pipelines
        return PlannerProviderResponse(
            provider=self.provider_name,
            model=self.model,
            raw_text=self.response_text,
            payload=_parse_json_object(self.response_text),
        )


class OpenAICompatiblePlannerProvider:
    provider_name = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def draft_plan(self, request: dict[str, Any], candidate_pipelines: list[str]) -> PlannerProviderResponse:
        body = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a MedImage planning advisor. Return JSON only. "
                        "Do not call tools. Choose one recommended_pipeline_path from candidate_pipelines."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "request": request,
                            "candidate_pipelines": candidate_pipelines,
                            "required_keys": [
                                "recommended_pipeline_path",
                                "rationale",
                                "constraints",
                            ],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
        }
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            raise PlannerProviderError(f"LLM planner request failed: {exc}") from exc

        try:
            text = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise PlannerProviderError("LLM planner response missing choices[0].message.content.") from exc

        return PlannerProviderResponse(
            provider=self.provider_name,
            model=self.model,
            raw_text=text,
            payload=_parse_json_object(text),
        )


def get_planner_provider_from_env() -> LLMPlannerProvider | None:
    fixture = os.environ.get("MEDIMAGE_LLM_MOCK_RESPONSE")
    if fixture:
        return FixturePlannerProvider(fixture, model=os.environ.get("MEDIMAGE_LLM_MODEL", "fixture"))
    if not llm_configured():
        return None
    return OpenAICompatiblePlannerProvider(
        base_url=os.environ.get("MEDIMAGE_LLM_BASE_URL", "https://api.openai.com/v1"),
        api_key=os.environ["MEDIMAGE_LLM_API_KEY"],
        model=os.environ.get("MEDIMAGE_LLM_MODEL", "medimage-planner-default"),
        timeout_seconds=float(os.environ.get("MEDIMAGE_LLM_TIMEOUT_SECONDS", "30")),
    )
