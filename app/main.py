from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.bedrock_client import BedrockInvocationError, ChatResult, converse_with_bedrock

APP_NAME = "bedrock-rag-engineering"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str
    model_id: str
    input_tokens: int
    output_tokens: int


@app.get("/")
def read_root() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def get_bedrock_call():
    return converse_with_bedrock


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, bedrock_call=Depends(get_bedrock_call)) -> ChatResult:
    try:
        return bedrock_call(request.message)
    except BedrockInvocationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
