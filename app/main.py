from fastapi import FastAPI

APP_NAME = "bedrock-rag-engineering"
APP_VERSION = "0.1.0"

app = FastAPI(title=APP_NAME, version=APP_VERSION)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"name": APP_NAME, "version": APP_VERSION}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
