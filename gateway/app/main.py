import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field


VLLM_BASE_URL = os.getenv(
    "VLLM_BASE_URL",
    "http://inference:8000",
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "Qwen/Qwen3-0.6B",
)

LOG_LEVEL = os.getenv(
    "LOG_LEVEL",
    "INFO",
).upper()


logging.basicConfig(
    level=LOG_LEVEL,
    format="%(message)s",
)

logger = logging.getLogger("mini-ai-gateway")
logging.getLogger("httpx").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(timeout=60.0)

    yield

    await app.state.http_client.aclose()


app = FastAPI(
    title="Mini AI Platform Gateway",
    version="0.1.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    started_at = time.perf_counter()

    try:
        response = await call_next(request)

    except Exception as error:
        duration_ms = round(
            (time.perf_counter() - started_at) * 1000,
            2,
        )

        logger.error(
            json.dumps(
                {
                    "event": "http_request_failed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                    "error_type": type(error).__name__,
                }
            )
        )

        raise

    duration_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    response.headers["X-Request-ID"] = request_id

    health_paths = {
        "/health/live",
        "/health/ready",
    }

    should_log = (
        request.url.path not in health_paths
        or response.status_code >= 400
    )

    if should_log:
        logger.info(
            json.dumps(
                {
                    "event": "http_request_completed",
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                }
            )
        )

    return response


class ChatRequest(BaseModel):
    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    max_tokens: int = Field(
        default=128,
        ge=1,
        le=512,
    )

    temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
    )


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    try:
        response = await app.state.http_client.get(
            f"{VLLM_BASE_URL}/health",
            timeout=5.0,
        )

        response.raise_for_status()

        return {
            "status": "ready",
            "inference_service": "available",
        }

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=503,
            detail="Inference service is unavailable",
        ) from error


@app.post("/chat")
async def chat(request: ChatRequest):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are a concise and helpful assistant.",
            },
            {
                "role": "user",
                "content": request.message,
            },
        ],
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "chat_template_kwargs": {
            "enable_thinking": False,
        },
    }

    started_at = time.perf_counter()

    try:
        response = await app.state.http_client.post(
            f"{VLLM_BASE_URL}/v1/chat/completions",
            json=payload,
        )

        response.raise_for_status()

    except httpx.HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail="Inference request failed",
        ) from error

    result = response.json()

    latency_ms = round(
        (time.perf_counter() - started_at) * 1000,
        2,
    )

    return {
        "response": result["choices"][0]["message"]["content"],
        "model": result["model"],
        "usage": result.get("usage"),
        "latency_ms": latency_ms,
    }