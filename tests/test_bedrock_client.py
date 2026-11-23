from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from app.bedrock_client import BedrockInvocationError, converse_with_bedrock


def _client_error(code: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": "boom"}}, "Converse")


@pytest.fixture
def fake_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("app.bedrock_client._get_client", lambda: client)
    return client


def test_converse_with_bedrock_success_builds_chat_result(fake_client) -> None:
    fake_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "hello"}]}},
        "usage": {"inputTokens": 3, "outputTokens": 5},
    }

    result = converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0")

    assert result.reply == "hello"
    assert result.model_id == "amazon.nova-lite-v1:0"
    assert result.input_tokens == 3
    assert result.output_tokens == 5
    assert result.bedrock_duration_ms >= 0
    assert result.estimated_cost_usd is not None


def test_converse_with_bedrock_throttling_maps_to_429(fake_client) -> None:
    fake_client.converse.side_effect = _client_error("ThrottlingException")

    with pytest.raises(BedrockInvocationError) as exc_info:
        converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0")

    assert exc_info.value.status_code == 429


def test_converse_with_bedrock_access_denied_maps_to_403(fake_client) -> None:
    fake_client.converse.side_effect = _client_error("AccessDeniedException")

    with pytest.raises(BedrockInvocationError) as exc_info:
        converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0")

    assert exc_info.value.status_code == 403


def test_converse_with_bedrock_validation_error_maps_to_400(fake_client) -> None:
    fake_client.converse.side_effect = _client_error("ValidationException")

    with pytest.raises(BedrockInvocationError) as exc_info:
        converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0")

    assert exc_info.value.status_code == 400


def test_converse_with_bedrock_unknown_error_maps_to_502(fake_client) -> None:
    fake_client.converse.side_effect = _client_error("SomeOtherException")

    with pytest.raises(BedrockInvocationError) as exc_info:
        converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0")

    assert exc_info.value.status_code == 502


def test_converse_with_bedrock_missing_model_id_raises_500(monkeypatch) -> None:
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)

    with pytest.raises(BedrockInvocationError) as exc_info:
        converse_with_bedrock("hi", model_id=None)

    assert exc_info.value.status_code == 500


def test_converse_with_bedrock_passes_temperature_and_max_tokens(fake_client) -> None:
    fake_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "ok"}]}},
        "usage": {"inputTokens": 1, "outputTokens": 1},
    }

    converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0", temperature=0.3, max_tokens=128)

    _, kwargs = fake_client.converse.call_args
    assert kwargs["inferenceConfig"]["temperature"] == 0.3
    assert kwargs["inferenceConfig"]["maxTokens"] == 128


def test_converse_with_bedrock_omits_temperature_when_not_given(fake_client) -> None:
    fake_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "ok"}]}},
        "usage": {"inputTokens": 1, "outputTokens": 1},
    }

    converse_with_bedrock("hi", model_id="amazon.nova-lite-v1:0")

    _, kwargs = fake_client.converse.call_args
    assert "temperature" not in kwargs["inferenceConfig"]
