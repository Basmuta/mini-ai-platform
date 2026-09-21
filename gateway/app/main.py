import os
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://inference:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen3-0.6B")


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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    max_tokens: int = Field(default=128, ge=1, le=512)
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)


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
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    return {
        "response": result["choices"][0]["message"]["content"],
        "model": result["model"],
        "usage": result.get("usage"),
        "latency_ms": latency_ms,
    }