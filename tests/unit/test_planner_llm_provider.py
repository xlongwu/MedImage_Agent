from __future__ import annotations

import json

from src.backend.app.planner.llm_provider import OpenAICompatiblePlannerProvider
from src.backend.app.planner.pipeline_planner import draft_pipeline_plan


class _FakeHttpResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_planner_valid_llm_fixture_selects_pipeline(monkeypatch):
    monkeypatch.setenv(
        "MEDIMAGE_LLM_MOCK_RESPONSE",
        json.dumps({
            "recommended_pipeline_path": "examples/pipeline_rsfmri_reho.yaml",
            "rationale": ["ReHo requested"],
            "constraints": [],
        }),
    )

    draft = draft_pipeline_plan({"downstream_task": "regional homogeneity"})

    assert draft["ok"] is True
    assert draft["llm_used"] is True
    assert draft["recommended_pipeline_path"].endswith("pipeline_rsfmri_reho.yaml")


def test_openai_compatible_provider_parses_chat_completion(monkeypatch):
    payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "recommended_pipeline_path": "examples/pipeline_rsfmri_core_plan.yaml",
                        "rationale": ["Core plan requested"],
                    })
                }
            }
        ]
    }

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        assert timeout == 5
        assert request.full_url == "https://provider.test/v1/chat/completions"
        return _FakeHttpResponse(payload)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    provider = OpenAICompatiblePlannerProvider(
        base_url="https://provider.test/v1",
        api_key="test-key",
        model="planner",
        timeout_seconds=5,
    )
    response = provider.draft_plan(
        {"downstream_task": "core preprocessing"},
        ["examples/pipeline_rsfmri_core_plan.yaml"],
    )

    assert response.provider == "openai_compatible"
    assert response.payload["recommended_pipeline_path"].endswith("core_plan.yaml")
