import time
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.bedrock_client import BedrockInvocationError, converse_with_bedrock
from app.models import AVAILABLE_MODELS, is_model_allowed

APP_NAME = "bedrock-rag-engineering"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    model_id: Optional[str] = None

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not is_model_allowed(value):
            raise ValueError(f"model_id '{value}' is not in the allowed list")
        return value


class ChatResponse(BaseModel):
    reply: str
    model_id: str
    input_tokens: int
    output_tokens: int
    bedrock_duration_ms: float
    total_duration_ms: float
    estimated_cost_usd: Optional[float]


@app.get("/")
def read_root() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/models")
def list_models() -> list[dict[str, str]]:
    return [
        {"id": model.id, "display_name": model.display_name, "provider": model.provider}
        for model in AVAILABLE_MODELS
    ]


def get_bedrock_call():
    return converse_with_bedrock


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, bedrock_call=Depends(get_bedrock_call)) -> ChatResponse:
    start_time = time.perf_counter()
    try:
        result = bedrock_call(request.message, request.model_id)
    except BedrockInvocationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    total_duration_ms = (time.perf_counter() - start_time) * 1000

    return ChatResponse(
        reply=result.reply,
        model_id=result.model_id,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        bedrock_duration_ms=result.bedrock_duration_ms,
        total_duration_ms=total_duration_ms,
        estimated_cost_usd=result.estimated_cost_usd,
    )
