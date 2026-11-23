from fastapi.testclient import TestClient

from app.bedrock_client import BedrockInvocationError, ChatResult
from app.main import APP_NAME, APP_VERSION, app, get_bedrock_call

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"name": APP_NAME, "version": APP_VERSION}


def test_chat_success() -> None:
    def fake_call(message: str, model_id=None) -> ChatResult:
        assert message == "こんにちは"
        return ChatResult(
            reply="こんにちは、ご用件は？",
            model_id="amazon.nova-lite-v1:0",
            input_tokens=5,
            output_tokens=8,
            bedrock_duration_ms=123.4,
            estimated_cost_usd=0.00001,
        )

    app.dependency_overrides[get_bedrock_call] = lambda: fake_call
    try:
        response = client.post("/chat", json={"message": "こんにちは"})
    finally:
        app.dependency_overrides.pop(get_bedrock_call, None)

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "こんにちは、ご用件は？"
    assert body["model_id"] == "amazon.nova-lite-v1:0"
    assert body["input_tokens"] == 5
    assert body["output_tokens"] == 8
    assert body["bedrock_duration_ms"] == 123.4
    assert body["estimated_cost_usd"] == 0.00001
    assert body["total_duration_ms"] >= 0


def test_chat_empty_message_is_rejected() -> None:
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_bedrock_error_is_translated_to_http_error() -> None:
    def fake_call(message: str, model_id=None) -> ChatResult:
        raise BedrockInvocationError("Bedrock is throttling requests, try again later", status_code=429)

    app.dependency_overrides[get_bedrock_call] = lambda: fake_call
    try:
        response = client.post("/chat", json={"message": "hello"})
    finally:
        app.dependency_overrides.pop(get_bedrock_call, None)

    assert response.status_code == 429
    assert "throttling" in response.json()["detail"]


def test_list_models_returns_allowed_models() -> None:
    response = client.get("/models")
    assert response.status_code == 200
    body = response.json()
    model_ids = [model["id"] for model in body]
    assert "amazon.nova-lite-v1:0" in model_ids
    assert "apac.amazon.nova-micro-v1:0" in model_ids
    assert "apac.amazon.nova-pro-v1:0" in model_ids
    assert all({"id", "display_name", "provider"} <= set(model.keys()) for model in body)


def test_chat_with_valid_model_id_override() -> None:
    received_model_id = {}

    def fake_call(message: str, model_id=None) -> ChatResult:
        received_model_id["value"] = model_id
        return ChatResult(
            reply="ok",
            model_id=model_id,
            input_tokens=1,
            output_tokens=1,
            bedrock_duration_ms=10.0,
            estimated_cost_usd=None,
        )

    app.dependency_overrides[get_bedrock_call] = lambda: fake_call
    try:
        response = client.post(
            "/chat", json={"message": "hello", "model_id": "apac.amazon.nova-pro-v1:0"}
        )
    finally:
        app.dependency_overrides.pop(get_bedrock_call, None)

    assert response.status_code == 200
    assert received_model_id["value"] == "apac.amazon.nova-pro-v1:0"
    assert response.json()["model_id"] == "apac.amazon.nova-pro-v1:0"


def test_chat_with_unknown_model_id_is_rejected() -> None:
    response = client.post(
        "/chat", json={"message": "hello", "model_id": "some-unapproved-model"}
    )
    assert response.status_code == 422
