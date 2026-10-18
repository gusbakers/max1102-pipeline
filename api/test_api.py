"""Pruebas locales: no necesitan claves reales ni consumen Gemini."""
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from google.genai import errors, types

import main

CLAIM = {
    "claim_id": "CLM-00001",
    "claim_amount": 1250.50,
    "claim_status": "PAID",
    "service_date": "2025-12-10",
}
HEADERS = {"X-API-Key": "local-test-only"}
SUMMARY = "El claim del 10 de diciembre de 2025 tiene un monto de 1250.50 y está pagado."


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setenv("APP_API_KEY", "local-test-only")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-not-a-real-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    response = types.GenerateContentResponse(candidates=[types.Candidate(
        finish_reason=types.FinishReason.STOP,
        content=types.Content(parts=[types.Part(text=SUMMARY)]),
    )])
    generate = AsyncMock(return_value=response)
    async_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate))
    context = MagicMock()
    context.__aenter__ = AsyncMock(return_value=async_client)
    context.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=SimpleNamespace(aio=context))
    monkeypatch.setattr(main.genai, "Client", factory)
    with TestClient(main.app) as client:
        yield client, generate, factory


def test_success_and_minimized_prompt(setup):
    client, generate, factory = setup
    response = client.post("/claims/llm-summary", json=CLAIM, headers=HEADERS)
    assert response.status_code == 200
    assert response.json() == {
        "claim_id": CLAIM["claim_id"], "summary": SUMMARY,
        "model": "gemini-2.5-flash-lite",
    }
    kwargs = generate.await_args.kwargs
    assert kwargs["model"] == "gemini-2.5-flash-lite"
    assert "1250.50" in kwargs["contents"] and "2025-12-10" in kwargs["contents"]
    assert CLAIM["claim_id"] not in kwargs["contents"]
    assert "fake-not-a-real-key" not in str(kwargs)
    assert factory.call_args.kwargs["http_options"].timeout == 30000


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
def test_auth_blocks_request_before_llm(setup, headers):
    client, generate, _ = setup
    response = client.post("/claims/llm-summary", json=CLAIM, headers=headers)
    assert response.status_code == 401
    generate.assert_not_awaited()


@pytest.mark.parametrize("changes", [
    {"claim_amount": -1}, {"claim_amount": 50000.01},
    {"claim_amount": 12.345}, {"service_date": "2025-02-30"},
    {"claim_status": "UNKNOWN"}, {"member_name": "Synthetic Example"},
])
def test_bad_input_never_calls_llm(setup, changes):
    client, generate, _ = setup
    response = client.post("/claims/llm-summary", json=CLAIM | changes, headers=HEADERS)
    assert response.status_code == 422
    generate.assert_not_awaited()


@pytest.mark.parametrize("name", ["GEMINI_API_KEY", "APP_API_KEY"])
def test_missing_configuration(setup, monkeypatch, name):
    client, generate, _ = setup
    monkeypatch.delenv(name)
    response = client.post("/claims/llm-summary", json=CLAIM, headers=HEADERS)
    assert response.status_code == 503
    generate.assert_not_awaited()


@pytest.mark.parametrize("provider_status, api_status", [
    (429, 429), (401, 502), (403, 502), (404, 502), (500, 502), (504, 504),
])
def test_provider_errors_are_sanitized(setup, provider_status, api_status):
    client, generate, _ = setup
    generate.side_effect = errors.APIError(provider_status, {
        "error": {"message": "private-provider-detail", "code": provider_status}
    })
    response = client.post("/claims/llm-summary", json=CLAIM, headers=HEADERS)
    assert response.status_code == api_status
    assert "private-provider-detail" not in response.text


@pytest.mark.parametrize("exception, status", [
    (httpx.ReadTimeout("private-timeout-detail"), 504),
    (httpx.ConnectError("private-connection-detail"), 502),
])
def test_network_errors(setup, exception, status):
    client, generate, _ = setup
    generate.side_effect = exception
    response = client.post("/claims/llm-summary", json=CLAIM, headers=HEADERS)
    assert response.status_code == status
    assert "private-" not in response.text


@pytest.mark.parametrize("candidate", [
    None,
    types.Candidate(finish_reason=types.FinishReason.SAFETY),
    types.Candidate(finish_reason=types.FinishReason.MAX_TOKENS,
                    content=types.Content(parts=[types.Part(text="Texto incompleto")])),
    types.Candidate(finish_reason=types.FinishReason.STOP,
                    content=types.Content(parts=[types.Part(text=" ")])),
])
def test_empty_or_incomplete_output_fails(setup, candidate):
    client, generate, _ = setup
    generate.return_value = types.GenerateContentResponse(
        candidates=[] if candidate is None else [candidate])
    response = client.post("/claims/llm-summary", json=CLAIM, headers=HEADERS)
    assert response.status_code == 502


def test_health_does_not_require_provider_keys(setup, monkeypatch):
    client, generate, _ = setup
    monkeypatch.delenv("APP_API_KEY")
    monkeypatch.delenv("GEMINI_API_KEY")
    assert client.get("/health").json() == {"status": "ok"}
    generate.assert_not_awaited()


def test_real_sdk_serializes_request_without_network(monkeypatch):
    """Ejercita el SDK real; HTTP se intercepta localmente, sin llamadas a Google."""
    monkeypatch.setenv("APP_API_KEY", "local-test-only")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-sdk-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    import json
    real_client = main.genai.Client
    captured = []

    def handle(request):
        captured.append(request)
        return httpx.Response(200, json={"candidates": [{
            "finishReason": "STOP",
            "content": {"role": "model", "parts": [{"text": SUMMARY}]},
        }]})

    def factory(**kwargs):
        kwargs["http_options"].httpx_client = httpx.Client(
            transport=httpx.MockTransport(handle))
        kwargs["http_options"].httpx_async_client = httpx.AsyncClient(
            transport=httpx.MockTransport(handle))
        return real_client(**kwargs)

    monkeypatch.setattr(main.genai, "Client", factory)
    with TestClient(main.app) as client:
        response = client.post("/claims/llm-summary", json=CLAIM, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["summary"] == SUMMARY
    assert len(captured) == 1
    assert "gemini-2.5-flash-lite:generateContent" in captured[0].url.path
    body = json.loads(captured[0].content)
    assert body["generationConfig"]["maxOutputTokens"] == 512
    assert CLAIM["claim_id"] not in captured[0].content.decode()
