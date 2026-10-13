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
    def fake_call(message: str) -> ChatResult:
        assert message == "こんにちは"
        return ChatResult(reply="こんにちは、ご用件は？", model_id="jp.anthropic.claude-haiku-5-5", input_tokens=5, output_tokens=8)

    app.dependency_overrides[get_bedrock_call] = lambda: fake_call
    try:
        response = client.post("/chat", json={"message": "こんにちは"})
    finally:
        app.dependency_overrides.pop(get_bedrock_call, None)

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "こんにちは、ご用件は？"
    assert body["model_id"] == "jp.anthropic.claude-haiku-5-5"
    assert body["input_tokens"] == 5
    assert body["output_tokens"] == 8


def test_chat_empty_message_is_rejected() -> None:
    response = client.post("/chat", json={"message": ""})
    assert response.status_code == 422


def test_chat_bedrock_error_is_translated_to_http_error() -> None:
    def fake_call(message: str) -> ChatResult:
        raise BedrockInvocationError("Bedrock is throttling requests, try again later", status_code=429)

    app.dependency_overrides[get_bedrock_call] = lambda: fake_call
    try:
        response = client.post("/chat", json={"message": "hello"})
    finally:
        app.dependency_overrides.pop(get_bedrock_call, None)

    assert response.status_code == 429
    assert "throttling" in response.json()["detail"]
