import os
from dataclasses import dataclass
from functools import lru_cache

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class BedrockInvocationError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class ChatResult:
    reply: str
    model_id: str
    input_tokens: int
    output_tokens: int


@lru_cache
def _get_client():
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 5, "mode": "adaptive"}),
    )


def converse_with_bedrock(message: str) -> ChatResult:
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    if not model_id:
        raise BedrockInvocationError("BEDROCK_MODEL_ID is not configured", status_code=500)

    max_tokens = int(os.environ.get("BEDROCK_MAX_TOKENS", "512"))
    client = _get_client()

    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": message}]}],
            inferenceConfig={"maxTokens": max_tokens},
        )
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "ThrottlingException":
            raise BedrockInvocationError("Bedrock is throttling requests, try again later", status_code=429) from exc
        if error_code == "AccessDeniedException":
            raise BedrockInvocationError("Not authorized to invoke this Bedrock model", status_code=403) from exc
        if error_code == "ValidationException":
            raise BedrockInvocationError(str(exc), status_code=400) from exc
        raise BedrockInvocationError("Bedrock invocation failed", status_code=502) from exc

    reply = response["output"]["message"]["content"][0]["text"]
    usage = response["usage"]
    return ChatResult(
        reply=reply,
        model_id=model_id,
        input_tokens=usage["inputTokens"],
        output_tokens=usage["outputTokens"],
    )
