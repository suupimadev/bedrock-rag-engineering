from __future__ import annotations

import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.pricing import estimate_cost_usd


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
    bedrock_duration_ms: float
    estimated_cost_usd: Optional[float]


@lru_cache
def _get_client():
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    return boto3.client(
        "bedrock-runtime",
        region_name=region,
        config=Config(retries={"max_attempts": 5, "mode": "adaptive"}),
    )


def converse_with_bedrock(
    message: str,
    model_id: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> ChatResult:
    model_id = model_id or os.environ.get("BEDROCK_MODEL_ID")
    if not model_id:
        raise BedrockInvocationError("BEDROCK_MODEL_ID is not configured", status_code=500)

    if max_tokens is None:
        max_tokens = int(os.environ.get("BEDROCK_MAX_TOKENS", "512"))
    client = _get_client()

    inference_config: dict[str, float | int] = {"maxTokens": max_tokens}
    if temperature is not None:
        inference_config["temperature"] = temperature

    start_time = time.perf_counter()
    try:
        response = client.converse(
            modelId=model_id,
            messages=[{"role": "user", "content": [{"text": message}]}],
            inferenceConfig=inference_config,
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

    bedrock_duration_ms = (time.perf_counter() - start_time) * 1000

    reply = response["output"]["message"]["content"][0]["text"]
    usage = response["usage"]
    input_tokens = usage["inputTokens"]
    output_tokens = usage["outputTokens"]
    return ChatResult(
        reply=reply,
        model_id=model_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        bedrock_duration_ms=bedrock_duration_ms,
        estimated_cost_usd=estimate_cost_usd(model_id, input_tokens, output_tokens),
    )
